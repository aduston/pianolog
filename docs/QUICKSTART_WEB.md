# Pianolog Web Interface - Quick Start

Get your pianolog web interface up and running in 3 steps!

## Step 1: Install Dependencies

```bash
cd /home/aduston/pianolog
venv/bin/pip install -r requirements.txt
```

## Step 2: Start the Server

```bash
./scripts/start_with_web.sh
```

## Step 3: Open in Browser

### Option A: Direct Access (Easiest)
Open: **http://localhost:5000**

Or from another device on your network: **http://raspberrypi.local:5000**

### Option B: Clean URL via Nginx (Recommended)
Run the setup script:
```bash
./scripts/setup_nginx.sh
```

Then open: **http://raspberrypi.local/pianolog**

## What You'll See

- Current session status (active/inactive)
- Who's practicing (parent/daughter)
- Live session stats (duration, notes played)
- Buttons to change the current user
- Recent practice sessions list

## How It Works

1. **No session active:** Page shows "No active session"
2. **Play piano:** After 3+ notes, session automatically starts
3. **Watch updates:** Duration and note count update in real-time
4. **Stop playing:** After ~30 seconds of silence, session ends
5. **Switch users:** Click "Parent" or "Daughter" button anytime

## Testing Without Piano

You can open the web interface even without a piano connected. It will show "No active session" but you can:
- Change users
- View recent sessions (if any exist in the database)
- See the interface design and layout

## Running as a Service

To have pianolog start automatically on boot:

```bash
./scripts/install_service.sh
```

Check status:
```bash
sudo systemctl status piano-practice-tracker
```

## Troubleshooting

### Can't connect to web interface?
1. Make sure pianolog is running: `ps aux | grep python`
2. Check the port: `sudo netstat -tlnp | grep 5000`
3. Look at logs: `tail -f practice_tracker.log`

### Web interface loads but doesn't update?
- Check browser console (F12) for WebSocket errors
- Make sure JavaScript is enabled
- Try refreshing the page

### Using nginx but getting 502 error?
- Nginx is running but pianolog isn't
- Start pianolog: `./scripts/start_with_web.sh`

## Next Steps

- **Full Setup Guide:** See [SETUP_WEB.md](SETUP_WEB.md)
- **API Documentation:** See [WEB_INTERFACE.md](WEB_INTERFACE.md)
- **General Usage:** See [USAGE.md](USAGE.md)

## Features at a Glance

✅ Real-time session monitoring
✅ Live duration and note count
✅ Switch users from web interface
✅ Recent sessions history
✅ Mobile-friendly design
✅ No page refresh needed
✅ Multiple users can view simultaneously

Enjoy tracking your piano practice! 🎹
