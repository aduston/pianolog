# Pianolog Web Interface

The pianolog web interface provides real-time monitoring and control of piano practice sessions through your browser.

## Features

- **Real-time Session Monitoring**: View active practice sessions with live updates
- **User Management**: Switch between users (parent/daughter) from the web interface
- **Session Statistics**: See duration and note count for active sessions
- **Recent Sessions**: View the 5 most recent practice sessions
- **Automatic Updates**: Page automatically updates when sessions start/end or user changes

## Setup

### 1. Install Dependencies

The web server dependencies are included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Run with Web Server (Default)

The web server is enabled by default when you run pianolog:

```bash
python main.py --user parent
```

The web interface will be available at: **http://localhost:5000**

### 3. Configure Nginx (Optional)

To access the web interface at `http://raspberrypi.local/pianolog`:

```bash
./scripts/setup_nginx.sh
```

This will:
- Install nginx
- Configure it to proxy requests from `/pianolog` to the Flask server
- Enable WebSocket support for real-time updates
- Start nginx and enable it on boot

After setup, access the interface at: **http://raspberrypi.local/pianolog**

### 4. Update Systemd Service (If Using)

If you're running pianolog as a systemd service, make sure the service file passes the web port:

```ini
[Service]
ExecStart=/home/aduston/pianolog/venv/bin/python /home/aduston/pianolog/main.py --prompt-each-session
```

The web server runs on port 5000 by default.

## Usage

### Viewing the Interface

Open your browser and navigate to:
- Local: `http://localhost:5000`
- Network (with nginx): `http://raspberrypi.local/pianolog`

### Changing Users

Click the "Parent" or "Daughter" button to set who is currently practicing. This change takes effect immediately and will be used for the next practice session.

### Real-time Updates

The interface uses WebSocket connections to receive real-time updates:
- Session starts/ends
- User changes
- Note count updates during active sessions
- Duration timer updates every second

## API Endpoints

The web server provides the following REST API endpoints:

### GET /api/status

Get current session status.

**Response:**
```json
{
  "active": true,
  "user": "parent",
  "start_time": 1698765432.0,
  "duration": 125.5,
  "note_count": 450
}
```

### POST /api/user

Set the current user.

**Request:**
```json
{
  "user_id": "parent"
}
```

**Response:**
```json
{
  "success": true,
  "user": "parent"
}
```

### GET /api/sessions/recent

Get recent practice sessions.

**Parameters:**
- `limit` (optional): Number of sessions to return (default: 10)

**Response:**
```json
[
  {
    "id": 1,
    "user_id": "parent",
    "start_timestamp": 1698765432,
    "end_timestamp": 1698765682,
    "duration_seconds": 250,
    "note_count": 450,
    "session_date": "2024-10-31",
    "created_at": "2024-10-31 14:30:32"
  }
]
```

### GET /api/sessions/summary

Get daily practice summary.

**Parameters:**
- `days` (optional): Number of days to include (default: 7)
- `user_id` (optional): Filter by user

**Response:**
```json
[
  {
    "session_date": "2024-10-31",
    "user_id": "parent",
    "session_count": 3,
    "total_seconds": 1200,
    "total_notes": 2500
  }
]
```

## WebSocket Events

The server emits the following WebSocket events:

### session_started

Emitted when a practice session begins.

```json
{
  "user": "parent",
  "start_time": 1698765432.0,
  "timestamp": 1698765432.0
}
```

### session_ended

Emitted when a practice session ends.

```json
{
  "user": "parent",
  "start_time": 1698765432.0,
  "end_time": 1698765682.0,
  "duration": 250.0,
  "note_count": 450,
  "timestamp": 1698765682.0
}
```

### session_activity

Emitted periodically during an active session (on each note).

```json
{
  "user": "parent",
  "note_count": 450,
  "duration": 125.5,
  "timestamp": 1698765557.5
}
```

### user_changed

Emitted when the current user is changed.

```json
{
  "user": "daughter",
  "timestamp": 1698765600.0
}
```

## Troubleshooting

### Web interface doesn't load

1. Check that the web server is running:
   ```bash
   ps aux | grep "python.*main.py"
   ```

2. Verify the port is listening:
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

3. Check the logs:
   ```bash
   tail -f practice_tracker.log
   ```

### WebSocket not connecting

1. Make sure you're not behind a proxy that blocks WebSocket connections
2. Check browser console for errors
3. Verify nginx configuration if using reverse proxy

### Can't access from network

1. Check firewall settings:
   ```bash
   sudo ufw status
   ```

2. If using nginx, verify it's running:
   ```bash
   sudo systemctl status nginx
   ```

3. Test local access first before network access

## Architecture

```
┌─────────────────┐
│   Web Browser   │
│  (JavaScript)   │
└────────┬────────┘
         │ HTTP / WebSocket
         │
┌────────▼────────┐
│  Flask Server   │
│  (port 5000)    │
└────────┬────────┘
         │
┌────────▼────────┐
│ PracticeTracker │
│  (main.py)      │
└────────┬────────┘
         │
┌────────▼────────┐
│  SQLite DB      │
│  (sessions)     │
└─────────────────┘
```

The web server runs in a background thread alongside the MIDI monitoring. When events occur (session start/end, notes played), the PracticeTracker notifies the web server, which broadcasts updates to all connected clients via WebSocket.

## Security Notes

- The web server is configured for local network access
- No authentication is implemented by default
- If exposing to the internet, add authentication and use HTTPS
- Consider firewall rules to restrict access to trusted networks
