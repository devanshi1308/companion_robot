# Baymax family app (everything the family sees is in this folder)

| File | What it does |
|---|---|
| `index.html` | The app screen: sign in, live floor plan with Baymax and her, Baymax's feelings, medicine card, chat, timeline, alerts |
| `server.py` | Local server (127.0.0.1:8765): sign-in, state, events, chat, commands |
| `auth.py` | Sign-in: PBKDF2 password hashes in `config/family_users.json`, lock after 5 wrong tries |
| `feed.py`, `publisher.py` | The link between the simulation and the app (state, events, chat, pictures) |
| `manifest.webmanifest`, `sw.js`, `icon.svg` | Make it installable as an app and let it show system notifications |
| `run_app.sh` | Starts the server and opens the app window |

**Run:** `./family_app/run_app.sh`, then start a simulation in another terminal (`./run_family_demo.sh fall` or `cardiac`). Demo accounts: rohan / rohan-demo, meera / meera-demo, iyer / iyer-demo.

**Notifications:** press "Turn on alerts" once. After that every text Baymax sends that person (heads-up, emergency, tablet report, siren) appears as a banner with a beep, and as a system notification if the browser allows it. In Chrome you can also install it (address bar, install icon) to get a Dock or home-screen icon.

**Honest limits:** this is a simulation demo. Nothing is sent to a real phone: the alerts are shown by the page itself while it is open, there is no push service, SMS or call, and there is no video stream (pictures only on request and only if she agreed). It listens on this computer only and has no HTTPS, so do not expose it to a network.

## Phone app (Expo Go): `family_app/mobile`
Dark-purple mobile app: welcome, sign in, Home (alert card, medicine, history), Live (floor plan, ask Baymax), Talk (chat with voice orb and spoken replies). New texts to the signed-in person arrive as a phone notification with haptics while the app is open.

1. Mac: `./family_app/run_app.sh --lan` (server listens on the Wi-Fi), and in another terminal `./run_family_demo.sh fall` (or `cardiac`).
2. Mac: `cd family_app/mobile && npm install && npx expo start`, then scan the QR code with Expo Go (phone on the same Wi-Fi).
3. In the app, server address `http://<Mac LAN IP>:8765` (find it with `ipconfig getifaddr en0`), then rohan / rohan-demo.

Phone sign-in returns a bearer token (header `X-Client: mobile`); the web page still uses its HttpOnly cookie. Honest limits: notifications are local (shown while the app runs; there is no push service, SMS or call); `--lan` has no HTTPS, so use a trusted network only. Checked: type-check clean, web bundle builds, welcome screen rendered, token login and state/events endpoints tested by curl. NOT yet checked on a real phone or Expo Go.
