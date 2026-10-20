#!/bin/bash
PATTERNS="gz sim|ruby.*gz|arducopter|mavproxy|QGroundControl"
PORTS="5760 9002 14550"

pkill -f "$PATTERNS" 2>/dev/null
for i in $(seq 1 10); do
    pgrep -f "$PATTERNS" >/dev/null 2>&1 || break
    sleep 1
done
pgrep -f "$PATTERNS" >/dev/null 2>&1 && { pkill -9 -f "$PATTERNS"; sleep 2; }

for i in $(seq 1 30); do
    BUSY=""
    for P in $PORTS; do
        ss -lntu 2>/dev/null | grep -qE "[:.]$P\b" && BUSY="$BUSY $P"
    done
    [ -z "$BUSY" ] && { echo "Lab 7 stopped, ports are free."; exit 0; }
    sleep 1
done
echo "WARNING: ports still busy:$BUSY"
exit 1
