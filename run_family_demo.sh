#!/bin/zsh
# Family-platform demo WITH the live MuJoCo window. Usage: ./run_family_demo.sh [medicine|cardiac|fall] [--no-view]
# Opens the page in your browser: sign in as rohan / rohan-demo (or meera / meera-demo, iyer / iyer-demo) and chat with Baymax while the robot moves.
cd "$(dirname "$0")" || exit 1
source .venv/bin/activate || { echo "no .venv here"; exit 1; }
export MUJOCO_GL=glfw
SCEN=${1:-medicine}
VIEW="--view"; [ "$2" = "--no-view" ] && VIEW=""
pkill -f run_platform_demo.py 2>/dev/null; sleep 1
echo "Starting the $SCEN demo (about 20 s before the page has data)..."
( for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:8765/ && { open http://127.0.0.1:8765/; break; }; sleep 1; done ) &
if [ -n "$VIEW" ]; then
  MUJOCO_GL=cgl mjpython src/sim/run_platform_demo.py --scenario "$SCEN" --agent --consent --voice --view --until-closed
else
  python src/sim/run_platform_demo.py --scenario "$SCEN" --agent --consent --voice --until-closed
fi
