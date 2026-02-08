# Pianolog Web Interface Setup Guide

This guide will help you set up and test the web interface for pianolog.

## Quick Start

### 1. Install Dependencies

```bash
cd /home/aduston/pianolog
venv/bin/pip install -r requirements.txt
```

### 2. Start Pianolog with Web Server

```bash
./scripts/start_with_web.sh
```

Or manually:

```bash
source venv/bin/activate
python main.py --prompt-each-session
```

### 3. Access the Web Interface

Open your browser and go to:
- **http://localhost:5000** (from the same machine)
- **http://raspberrypi.local:5000** (from any device on your network)

## Setup for http://raspberrypi.local/pianolog

If you want to access the interface at the cleaner URL `http://raspberrypi.local/pianolog`, follow these steps:

### 1. Install and Configure Nginx

```bash
./scripts/setup_nginx.sh
```

This script will:
- Install nginx if not already installed
- Create a reverse proxy configuration
- Enable WebSocket support
- Configure the server to listen on port 80
- Start and enable nginx

### 2. Verify Nginx is Running

```bash
sudo systemctl status nginx
```

### 3. Test the Configuration

Open your browser and navigate to:
- **http://raspberrypi.local/pianolog**

You should see the pianolog web interface.

## Running as a Service

The systemd service has been updated to work with the web interface.

### Install/Update the Service

```bash
./scripts/install_service.sh
```

### Check Service Status

```bash
sudo systemctl status piano-practice-tracker
```

### View Logs

```bash
sudo journalctl -u piano-practice-tracker -f
```

Or check the local log file:

```bash
tail -f practice_tracker.log
```

## Testing the Web Interface

### Test 1: View Current Status

1. Open the web interface in your browser
2. You should see "No active session" initially
3. The current user should be displayed

### Test 2: Change User

1. Click the "Parent" button
2. The button should highlight
3. The status should update to show the new user
4. Check the console logs - you should see a "User changed" message

### Test 3: Simulate a Practice Session

**Note:** This requires a MIDI piano to be connected.

1. Open the web interface
2. Play some notes on the piano
3. After playing 3+ notes within 10 seconds, a session should start
4. The interface should automatically update to show:
   - "parent is practicing" (or "daughter")
   - Duration counter (updating every second)
   - Note count (increasing as you play)

5. Stop playing for 15 seconds
6. The session should end automatically
7. The interface should update to show "No active session"
8. The session should appear in the "Recent Sessions" list

### Test 4: Real-time Updates

Open the web interface in two different browser windows or tabs:

1. In window 1: Click "Parent"
2. In window 2: Should automatically update to show "Parent" is selected
3. Play notes on the piano
4. Both windows should show the session start simultaneously
5. Both windows should show live note count and duration updates

### Test 5: Check Recent Sessions

1. Complete a practice session (30+ seconds)
2. Scroll down to "Recent Sessions"
3. Your session should appear in the list with:
   - User name
   - Date and time
   - Duration in minutes
   - Note count

## Troubleshooting

### Web Server Won't Start

**Error:** "Address already in use"

**Solution:** Check if port 5000 is already in use:

```bash
sudo netstat -tlnp | grep 5000
```

Kill the process or change the port in `pianolog/config.py`.

---

**Error:** "ModuleNotFoundError: No module named 'flask'"

**Solution:** Install dependencies:

```bash
venv/bin/pip install -r requirements.txt
```

### Can't Access from Network

**Problem:** `http://raspberrypi.local:5000` doesn't work from another device

**Solutions:**

1. Check firewall settings:
   ```bash
   sudo ufw status
   ```

2. Allow port 5000:
   ```bash
   sudo ufw allow 5000/tcp
   ```

3. Verify the server is listening on all interfaces:
   ```bash
   sudo netstat -tlnp | grep 5000
   ```
   Should show `0.0.0.0:5000` not `127.0.0.1:5000`

4. Try accessing by IP address instead:
   ```bash
   hostname -I
   ```
   Then try `http://<IP_ADDRESS>:5000`

### Nginx Returns 502 Bad Gateway

**Problem:** `http://raspberrypi.local/pianolog` shows "502 Bad Gateway"

**Solution:** The Flask server is not running. Check:

```bash
# Is pianolog running?
ps aux | grep "python.*main.py"

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

Start pianolog:
```bash
./scripts/start_with_web.sh
```

### WebSocket Not Connecting

**Problem:** Page loads but doesn't update in real-time

**Solution:**

1. Open browser developer console (F12)
2. Look for WebSocket connection errors
3. Check if nginx WebSocket proxy is configured correctly:
   ```bash
   sudo nginx -t
   cat /etc/nginx/sites-available/pianolog
   ```

4. Verify the WebSocket connection in the browser console:
   ```javascript
   // Should see: "Connected to server"
   ```

### MIDI Device Not Detected

**Problem:** Web interface works but sessions never start

**Solution:**

1. Check if MIDI device is connected:
   ```bash
   lsusb | grep -i midi
   ```

2. Check if mido can see it:
   ```bash
   venv/bin/python -c "import mido; print(mido.get_input_names())"
   ```

3. Check the logs:
   ```bash
   tail -f practice_tracker.log
   ```

## Configuration Options

### Change Web Server Port

Edit `pianolog/config.py` to change the default port:

```python
WEB_PORT = 8080
```

Or pass it as a parameter when creating PracticeTracker.

### Disable Web Server

To run without the web interface:

```python
tracker = PracticeTracker(enable_web_server=False)
```

Or instantiate `PracticeTracker(enable_web_server=False)`.

### Change Session Detection Thresholds

Edit the detector settings in `pianolog/config.py`:

```python
ACTIVITY_THRESHOLD = 3
ACTIVITY_WINDOW = 10.0
MIN_PRACTICE_DURATION = 30.0
SESSION_TIMEOUT = 30.0
```

## Performance Notes

- The web server runs in a background thread and has minimal impact on MIDI monitoring
- WebSocket updates are throttled to avoid overwhelming the network
- The interface is optimized for mobile and desktop browsers
- Multiple clients can connect simultaneously without performance degradation

## Security Considerations

- The web interface has **no authentication** by default
- It's designed for local network use only
- If exposing to the internet:
  1. Add authentication (Flask-Login, OAuth, etc.)
  2. Use HTTPS with proper SSL certificates
  3. Consider rate limiting
  4. Restrict access with firewall rules

## Browser Compatibility

Tested and working on:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

Requires:
- JavaScript enabled
- WebSocket support
- Modern CSS (flexbox, grid)

## Next Steps

- See [WEB_INTERFACE.md](WEB_INTERFACE.md) for API documentation
- Check [USAGE.md](USAGE.md) for general pianolog usage
- Read [README.md](README.md) for project overview
