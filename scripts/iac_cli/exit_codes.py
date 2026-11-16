"""The one table of exit codes shared by every subcommand."""

SUCCESS = 0
USAGE = 1
MISSING_DEPENDENCY = 2
INVALID_STATE = 3
OPERATION_FAILED = 4

HELP_TEXT = """\
exit codes:
  0  success
  1  usage error (bad arguments, no target configured)
  2  missing dependency (no engine, no micromamba, no curl)
  3  invalid input or state (bad tier name, bad config file, broken links,
     promoting a tier that was never deployed)
  4  operation failed (an install failed, too little disk space)
"""
