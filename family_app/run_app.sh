#!/bin/zsh
# Baymax family app: starts the server and opens it in its own app window (Chrome app mode), or in the browser.
# ./family_app/run_app.sh --lan   lets the phone app (family_app/mobile, Expo Go) connect over your Wi-Fi.
# The app shows the simulation LIVE; start a simulation in another terminal, for example ./run_family_demo.sh fall
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || { echo "no .venv here"; exit 1; }
pkill -f "family_app/server.py" 2>/dev/null; sleep 1
if [ "$1" = "--lan" ]; then python family_app/server.py --lan & else python family_app/server.py & fi
for i in $(seq 1 20); do curl -s -o /dev/null http://127.0.0.1:8765/ && break; sleep 1; done
if [ -d "/Applications/Google Chrome.app" ]; then open -na "Google Chrome" --args --app=http://127.0.0.1:8765 --user-data-dir="$HOME/.baymax_app_profile"; else open http://127.0.0.1:8765; fi
echo "Baymax family app running. Sign in as rohan / rohan-demo (or meera / meera-demo, iyer / iyer-demo). Ctrl-C stops the server."
wait
