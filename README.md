# Pianolog (Piano Practice Tracker)

Track piano practice sessions via USB-MIDI, with a real-time web interface (Flask + Socket.IO).

This is designed to run on a Raspberry Pi as a “kiosk” appliance:

- `pianolog` runs as a `systemd` service
- Chromium runs fullscreen (`--kiosk`) and displays the web UI
- Optional nginx reverse proxy serves the UI at `/pianolog`

## Repo Layout

- `pianolog/` – Python package (core app code)
- `templates/` – Flask HTML templates
- `static/` – Frontend assets (CSS/JS)
- `scripts/` – Raspberry Pi / system scripts (systemd, nginx, kiosk)
- `tools/` – Local utilities and test scripts
- `docs/` – Setup and usage docs

## Setup (Dev / Local)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

Run the tracker directly:

```bash
source venv/bin/activate
python main.py --prompt-each-session
```

Or start the web-friendly wrapper script:

```bash
./scripts/start_with_web.sh
```

Web UI:

- Local: `http://localhost:5000`
- If nginx reverse-proxy is configured: `http://raspberrypi.local/pianolog`

## React Pilot UI (Incremental Migration)

The legacy UI is still the default at `/`. A React pilot app now lives in `frontend/` and is served at `/react` after you build it.

Install frontend deps:

```bash
cd frontend
npm install
```

Run React in development mode (with API and Socket.IO proxy to Flask on `:5000`):

```bash
npm run dev
```

Build React assets for Flask to serve:

```bash
npm run build
```

Then open:

- Legacy UI: `http://localhost:5000/`
- React pilot UI: `http://localhost:5000/react`

## Configure

Edit `pianolog/config.py`:

- `USERS` – MIDI note → user name mapping (used for initial migration into the DB)
- `MIDI_DEVICE_KEYWORD` – device name match (for auto-connect)
- `ACTIVITY_THRESHOLD`, `ACTIVITY_WINDOW`, `MIN_PRACTICE_DURATION`, `SESSION_TIMEOUT`
- `WEB_PORT`

## Service / Pi Setup

- Install/update systemd service: `./scripts/install_service.sh`
- Uninstall systemd service: `./scripts/uninstall_service.sh`
- Set up nginx reverse proxy: `./scripts/setup_nginx.sh`
- Kiosk browser: `./scripts/start_kiosk.sh`
- Restart kiosk browser: `./scripts/restart_kiosk.sh`
- USB autoreset udev rules: `./scripts/setup_usb_autoreset.sh`

## Data + Logs

- SQLite DB: `practice_sessions.db` (in the repo working directory by default)
- Log file: `practice_tracker.log`

## Docs

Start with:

- `docs/QUICKSTART_WEB.md`
- `docs/SETUP_WEB.md`
- `docs/USAGE.md`
- `docs/WEB_INTERFACE.md`

Coming soon...
