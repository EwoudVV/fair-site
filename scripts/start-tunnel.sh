#!/bin/bash
# Starts the Cloudflare quick tunnel for the fair site, captures the URL,
# and regenerates the QR code. If the tunnel dies, run this again and
# print the new QR (/opt/fair/qr.png or /opt/fair/table-sign.html).
set -e

FAIR=/opt/fair
LOG=$FAIR/cloudflared.log
URLFILE=$FAIR/tunnel-url.txt

# old instance must be gone before we start a new one (else new URL is a race)
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

: > "$LOG"
cloudflared tunnel --url http://127.0.0.1:80 --no-autoupdate > "$LOG" 2>&1 &
CF_PID=$!
trap 'kill $CF_PID 2>/dev/null || true' EXIT

URL=""
for _ in $(seq 1 90); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" 2>/dev/null | head -1)
  if [ -n "$URL" ]; then break; fi
  if ! kill -0 "$CF_PID" 2>/dev/null; then
    echo "cloudflared died:" >&2
    tail -20 "$LOG" >&2
    exit 1
  fi
  sleep 1
done

if [ -z "$URL" ]; then
  echo "no tunnel URL found after 90s — check $LOG" >&2
  tail -20 "$LOG" >&2
  exit 1
fi

echo "$URL" > "$URLFILE"
python3 "$FAIR/make_qr.py" "$URL" "$FAIR/qr.png"
python3 "$FAIR/make_sign.py" "$URL" "$FAIR/table-sign.html"

echo "=============================================="
echo "TUNNEL URL : $URL"
echo "QR code    : $FAIR/qr.png"
echo "Print sign : $FAIR/table-sign.html  (open in browser, print)"
echo "=============================================="

# keep running in foreground so systemd tracks the process
wait "$CF_PID"
trap - EXIT
