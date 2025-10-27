# Piano Practice Tracker - Usage Guide

## Quick Start

The Piano Practice Tracker is now installed and running as a service! It will automatically start when your Raspberry Pi boots.

## How to Use

1. **Turn on your piano** - The tracker will detect it automatically
2. **Start playing** - On the first note, you'll hear a prompt melody (C-E-G)
3. **Identify yourself**:
   - Press **C** (middle C) for Dad
   - Press **D** for Alex
4. **Hear confirmation** - The piano plays a chord to confirm
5. **Practice!** - Your session is now being tracked
6. **When done** - Stop playing for 15 seconds and the session auto-saves

## Viewing Your Practice Data

```bash
# Activate the virtual environment
cd /home/aduston/practicetracker
source venv/bin/activate

# Show recent practice sessions
python main.py --show-sessions

# Show daily summary for the last 7 days
python main.py --show-summary
```

## Service Management

```bash
# Check if the service is running
sudo systemctl status piano-practice-tracker

# View live logs (press Ctrl+C to exit)
sudo journalctl -u piano-practice-tracker -f

# Restart the service
sudo systemctl restart piano-practice-tracker

# Stop the service
sudo systemctl stop piano-practice-tracker

# Start the service
sudo systemctl start piano-practice-tracker
```

## Troubleshooting

### Piano not responding
- Make sure the piano is powered on
- Check USB cable is connected
- Restart the service: `sudo systemctl restart piano-practice-tracker`

### Piano power-cycled (turned off then on)
**IMPORTANT:** If you turn the piano off and back on, the USB connection will NOT re-establish automatically.

**Root Cause:** The Kawai CA49's USB firmware does not properly re-initialize when the piano is power-cycled. This is a limitation of the piano itself, not the Raspberry Pi.

**Solutions (choose one):**

1. **Recommended: Leave piano on 24/7**
   - Disable Auto Power Off in piano settings (Settings → Auto Power Off → Off)
   - The tracker is designed for always-on operation
   - Minimal power consumption when idle

2. **Manual USB unplug/replug**
   - Unplug USB cable from Raspberry Pi
   - Wait 2 seconds
   - Plug it back in
   - Device reconnects immediately

3. **Optional: USB power switch** (~$15-20)
   - Install a physical USB switch between piano and Pi
   - Press switch to power-cycle USB without unplugging
   - Search for "USB power switch" online

4. **Optional: Smart USB hub** (~$30-40)
   - USB hub with software-controlled power (uhubctl compatible)
   - Allows programmatic port power cycling
   - More complex setup

**Note:** We attempted automatic USB reset via udev rules, but the piano's USB controller fails to enumerate properly after power-cycling, making software-only solutions ineffective.

### No prompt melody
- Check piano volume
- Verify Local Control is ON in piano settings
- Check logs: `sudo journalctl -u piano-practice-tracker -n 50`

### Service not running
- Check status: `sudo systemctl status piano-practice-tracker`
- View errors: `sudo journalctl -u piano-practice-tracker -n 50`
- Restart: `sudo systemctl restart piano-practice-tracker`

## Configuration

### Session Detection Settings
Located in `main.py`, line 39-43:
- **activity_threshold**: 3 (notes needed to start session)
- **activity_window**: 10.0 (seconds to detect activity)
- **min_practice_duration**: 30.0 (minimum seconds to save)
- **session_timeout**: 15.0 (seconds of silence to end session)

### User Mapping
Located in `main.py`, line 53-56:
- C (MIDI note 60) = parent
- D (MIDI note 62) = daughter

To add more users, edit these lines and restart the service.

## Auto-Start on Boot

The service is configured to start automatically when the Raspberry Pi boots. No manual intervention needed!

To disable auto-start:
```bash
sudo systemctl disable piano-practice-tracker
```

To re-enable:
```bash
sudo systemctl enable piano-practice-tracker
```

## Database Location

All practice data is stored in: `/home/aduston/practicetracker/practice_sessions.db`

## Logs

Application logs: `/home/aduston/practicetracker/practice_tracker.log`
System logs: `sudo journalctl -u piano-practice-tracker`
