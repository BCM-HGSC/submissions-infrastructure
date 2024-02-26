"""
Testing the sytem we use to test bash functions. (A bit meta.)
"""

from pathlib import Path

from bash_test_helpers import call_bash_function

LIB_PATH = Path("tests/resources/lib.sh")


def test_a():
    result = call_bash_function(LIB_PATH, "func", ["var1", "var2"], "foo\nbar", "spam")
    assert result.stderr == ""
    assert result.function_output == "hello\nMARKER\n-- foo bar spam"
    assert result.namespace == {"var1": "foo\nbar", "var2": "spam"}
    assert result.returncode == 2


def test_b():
    result = call_bash_function(LIB_PATH, "func", "var1 var2", "foobar", "spam")
    assert result.stderr == ""
    assert result.function_output == "hello\nMARKER\n-- foobar spam"
    assert result.namespace == {"var1": "foobar", "var2": "spam"}
    assert result.returncode == 2


def test_c():
    result = call_bash_function(LIB_PATH, "func", "var2", "foo\nbar", "spam")
    assert result.stderr == ""
    assert result.function_output == "hello\nMARKER\n-- foo bar spam"
    assert result.namespace == {"var2": "spam"}
    assert result.returncode == 2


def test_d():
    result = call_bash_function(
        LIB_PATH, "func", "var1 var2 var2", "foo\nbar", "sp''am", "eggs"
    )
    assert result.stderr == ""
    assert result.function_output == "hello\nMARKER\n-- foo bar spam eggs"
    assert result.namespace == {"var1": "foo\nbar", "var2": "spam"}
    assert result.returncode == 2
