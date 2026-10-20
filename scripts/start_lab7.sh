#!/bin/bash
set -e
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPTS/stop_lab7.sh"
source "$SCRIPTS/setup_env.sh"

RUN_DIR=$HOME/lab7/run
mkdir -p "$RUN_DIR" "$HOME/lab7/logs"
cd "$RUN_DIR"

echo "[1/3] Gazebo Sim: iris_runway.sdf"
gz sim -v4 -s -r iris_runway.sdf > "$RUN_DIR/gazebo.log" 2>&1 &
sleep 10

echo "[2/3] QGroundControl"
"$SCRIPTS/run_qgc.sh" > "$RUN_DIR/qgc.log" 2>&1 &
sleep 5

echo "[3/3] ArduPilot SITL (ArduCopter, frame gazebo-iris, JSON backend)"
echo "Leave this terminal open. Ctrl+C here, then ./stop_lab7.sh to stop all."
PARAMS=$ARDUPILOT_DIR/Tools/autotest/default_params
exec sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --no-rebuild \
    --add-param-file=$PARAMS/copter.parm \
    --add-param-file=$PARAMS/gazebo-iris.parm \
    --out=udp:127.0.0.1:14550 --console "$@"
