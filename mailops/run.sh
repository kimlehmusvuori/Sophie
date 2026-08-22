#!/usr/bin/env bash
# Launch the mail docket. Usage:  ./mailops/run.sh
#
# Reads GRAPH_CLIENT_ID / GRAPH_TENANT_ID from mailops/.env if present, so you
# don't have to export them by hand each time.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$here/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$here/.env"
  set +a
fi

for name in GRAPH_CLIENT_ID GRAPH_TENANT_ID; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing $name. Put it in mailops/.env as ${name}=... (see mailops/README.md)." >&2
    exit 1
  fi
done

exec python3 -m streamlit run "$here/app.py" \
  --server.address 127.0.0.1 \
  --server.port "${MAILOPS_PORT:-8501}" \
  --server.headless false \
  --browser.gatherUsageStats false
