#!/bin/bash
# pull-signups.sh — pull signups from the nest box to the Mac.
# Safe to run any time; merges by timestamp, so re-runs never duplicate.
# Destination: ~/Documents/fair-signups.jsonl (change DEST below if you prefer).
set -euo pipefail

BOX="duck@hackclub.app"
SRC="/opt/fair/data/signups.jsonl"
DEST="${HOME}/Documents/fair-signups.jsonl"

mkdir -p "$(dirname "$DEST")"
touch "$DEST"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

for attempt in 1 2 3 4; do
  if ssh -o BatchMode=yes -o ConnectTimeout=15 "$BOX" "cat $SRC" > "$TMP" 2>/dev/null; then
    break
  fi
  if [ "$attempt" -eq 4 ]; then
    echo "pull failed after 4 tries — is the box reachable? (ssh duck@hackclub.app)" >&2
    exit 1
  fi
  sleep 3
done

python3 - "$TMP" "$DEST" <<'EOF'
import json, sys
tmp, dest = sys.argv[1], sys.argv[2]
seen = set()
out = []

def add(path):
    try:
        with open(path) as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                try:
                    key = json.loads(line)["ts"]
                except Exception:
                    key = line
                if key in seen:
                    continue
                seen.add(key)
                out.append(line)
    except FileNotFoundError:
        pass

add(dest)
add(tmp)

with open(dest, "w") as f:
    f.write("\n".join(out) + ("\n" if out else ""))

print(f"synced {len(out)} entries -> {dest}")
EOF