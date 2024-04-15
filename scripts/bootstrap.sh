# Starting with just bash, bootstrap our infrastructure.

set -Eeuo pipefail

MY_DIR="$(dirname "${BASH_SOURCE[0]}")"

source "${MY_DIR}/bootstrap_lib.sh"

main "$@"
