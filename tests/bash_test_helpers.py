from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from subprocess import PIPE, run, CompletedProcess

PathLike = Path | str
StrList = list[str]
ExportList = str | StrList
ArgList = tuple[str, ...]


@dataclass(frozen=True)
class BashFunctionCallResult:
    returncode: int
    stderr: str
    function_output: str
    namespace: dict[str, str]


def call_bash_function(
    source_file: PathLike, function: str, exports: ExportList, *args: str
) -> BashFunctionCallResult:
    """
    Calls a bash function during construction and stores the results as members:
    returncode, stderr, function_output, and namespace. The standard output from
    the function goes into function_output. All variables named in exports
    (a string or list) are exported from bash into namespace.
    """

    commands_str = build_command_list(source_file, function, exports, args)
    result = run(
        ["bash"],
        input=commands_str,
        check=False,
        encoding="utf-8",
        errors="backslashreplace",
        stdout=PIPE,
        stderr=PIPE,
    )
    pprint(result)
    return convert_completed_process(result)


def build_command_list(
    source_file: PathLike, function: str, exports: ExportList, args: ArgList
) -> str:
    commands = (
        start_bash_session(source_file)
        + call_bash_function_command(function, args)
        + build_export_commands(exports)
    )
    pprint(commands)
    # ^^^ For each variable we want to export from bash, serialize the value
    # using base64 to prevent whitespace issues.
    commands_str = "\n".join(commands)
    return commands_str


def start_bash_session(source_file: PathLike) -> StrList:
    return [
        "set -uo pipefail",
        f"source {source_file}",
    ]


def call_bash_function_command(function: str, args: ArgList) -> StrList:
    argstr = " ".join([f"'{arg}'" for arg in args])
    return [
        f"{function} {argstr}",
        "_save_err=$?",
        "echo MARKER",
        build_export_command("err", "$_save_err"),
    ]


def build_export_commands(exports: ExportList) -> StrList:
    if isinstance(exports, str):
        exports = exports.split()
    print(exports)
    return [build_export_command(name) for name in exports]


def build_export_command(name: str, expression: str | None = None) -> str:
    if not expression:
        expression = f'"${name}"'
    return f"echo -n {name}=; echo -n {expression} | base64"


def convert_completed_process(result: CompletedProcess) -> BashFunctionCallResult:
    lines = result.stdout.splitlines()
    pprint(lines)
    # Use the LAST occurence of a line that is just MARKER to separate
    # function output from exported variables:
    marker_index = [i for i, s in enumerate(lines) if s == "MARKER"][-1]
    function_output = "\n".join(lines[:marker_index])
    err_line, *var_data = lines[marker_index + 1 :]
    err_num = int(parse_var_defs([err_line])["err"])
    namespace = parse_var_defs(var_data)
    stderr = result.stderr
    return BashFunctionCallResult(err_num, stderr, function_output, namespace)


def parse_var_defs(var_data: StrList) -> dict[str, str]:
    return {
        k: b64decode(v).decode()
        for k, v in (record.split("=", 1) for record in var_data)
    }
