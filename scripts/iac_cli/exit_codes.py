"""The one table of exit codes shared by every subcommand."""

SUCCESS = 0
USAGE = 1
MISSING_DEPENDENCY = 2
INVALID_INPUT = 3
OPERATION_FAILED = 4

HELP_TEXT = """\
exit codes:
  0  success
  1  usage error (bad arguments, no target configured)
  2  missing dependency (no engine, no micromamba, no curl or tar)
  3  invalid input (bad path, bad tier name, bad config file)
  4  operation failed (an install failed, too little disk space)
"""
