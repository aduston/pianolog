# Pianolog Web Interface - Connection Information

## ✅ Setup Complete!

Your pianolog web interface is now fully configured and running.

## Access URLs

You can access the web interface using any of these URLs:

### From the Raspberry Pi itself:
- http://localhost:5000
- http://localhost/pianolog
- http://127.0.0.1:5000

### From other devices on your network:
- **http://raspberrypi.local/pianolog** ← Recommended
- http://raspberrypi.local:5000
- http://192.168.86.59:5000
- http://192.168.86.59/pianolog

## Current Status

✅ **Pianolog Service**: Running (port 5000)
✅ **Nginx Reverse Proxy**: Running (port 80)
✅ **MIDI Device**: Connected
✅ **Database**: Working

## Testing the Connection

### From your other machine:

Open your web browser and try these URLs in order:

1. **http://raspberrypi.local/pianolog** (cleanest URL)
2. **http://192.168.86.59/pianolog** (if the above doesn't work)
3. **http://192.168.86.59:5000** (direct connection)

### What you should see:

- A purple gradient background
- "Pianolog - Piano Practice Tracker" title
- Current session status
- Buttons to select "Parent" or "Daughter"
- Recent sessions list (if any sessions exist)
- Connection status in the top-right corner (should show "Connected")

## Troubleshooting

### Can't connect from other machine?

**Issue**: Browser shows "Can't connect" or times out

**Solutions**:

1. **Check firewall on Raspberry Pi**:
   ```bash
   sudo ufw status
   ```
   If active, allow ports:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 5000/tcp
   ```

2. **Try the IP address directly**: http://192.168.86.59/pianolog

3. **Check if mDNS is working**:
   From your other machine, try:
   ```bash
   ping raspberrypi.local
   ```
   If this fails, use the IP address instead.

4. **Verify both services are running**:
   On the Raspberry Pi:
   ```bash
   sudo systemctl status piano-practice-tracker
   sudo systemctl status nginx
   ```

### Browser shows "502 Bad Gateway"?

This means nginx is running but can't connect to pianolog.

**Solution**: Restart the pianolog service:
```bash
sudo systemctl restart piano-practice-tracker
```

### Page loads but doesn't update?

**Solution**: Check the browser console (F12) for WebSocket errors. Refresh the page.

## Service Management

### View logs:
```bash
# Pianolog logs
tail -f /home/aduston/pianolog/practice_tracker.log

# Or systemd logs
sudo journalctl -u piano-practice-tracker -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Restart services:
```bash
sudo systemctl restart piano-practice-tracker
sudo systemctl restart nginx
```

### Stop services:
```bash
sudo systemctl stop piano-practice-tracker
sudo systemctl stop nginx
```

## Network Information

- **Raspberry Pi IP**: 192.168.86.59
- **Hostname**: raspberrypi.local
- **Flask Port**: 5000
- **Nginx Port**: 80 (HTTP)

## Features Working

✅ Real-time session monitoring
✅ Live duration and note count updates
✅ User switching from web interface
✅ Recent sessions history
✅ WebSocket automatic updates
✅ Multi-device access
✅ Mobile-friendly responsive design

## What to do now

1. **Open the web interface** on your other device
2. **Click a user button** (Parent or Daughter) to set who's practicing
3. **Play some notes** on the piano
4. **Watch the interface update** in real-time as the session starts

The page will automatically update when:
- A session starts (after playing 3+ notes)
- Notes are played during the session
- A session ends (after 15 seconds of silence)
- The user is changed

Enjoy your piano practice tracking! 🎹

---

## Quick Commands Reference

```bash
# Check if everything is running
sudo systemctl status piano-practice-tracker nginx

# View real-time logs
tail -f /home/aduston/pianolog/practice_tracker.log

# Restart everything
sudo systemctl restart piano-practice-tracker nginx

# Check what ports are listening
sudo netstat -tlnp | grep -E ":(80|5000)"
```
