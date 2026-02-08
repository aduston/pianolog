"""
Web server for pianolog - provides a web interface for viewing and managing practice sessions.
"""
import logging
import threading
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request, make_response
from flask_socketio import SocketIO, emit
import time
import pianolog.config as config

logger = logging.getLogger(__name__)


class PianologWebServer:
    """Web server for pianolog with real-time updates via WebSocket."""

    def __init__(self, practice_tracker, host='0.0.0.0', port=5000):
        """
        Initialize web server.

        Args:
            practice_tracker: Reference to PracticeTracker instance
            host: Host to bind to
            port: Port to bind to
        """
        self.practice_tracker = practice_tracker
        self.host = host
        self.port = port

        # Create Flask app
        repo_root = Path(__file__).resolve().parent.parent
        self.app = Flask(
            __name__,
            template_folder=str(repo_root / "templates"),
            static_folder=str(repo_root / "static"),
            static_url_path="/static",
        )
        self.app.config['SECRET_KEY'] = 'pianolog-secret-key-change-in-production'
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates

        # Create SocketIO instance
        self.socketio = SocketIO(self.app, cors_allowed_origins='*')

        # Setup routes
        self._setup_routes()

        # Thread for running server
        self.server_thread = None
        self.running = False

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            """Serve the main page."""
            response = make_response(render_template('index.html'))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        @self.app.route('/api/status')
        def get_status():
            """Get current session status."""
            session_info = self.practice_tracker.detector.get_session_info()

            if session_info:
                response = {
                    'active': True,
                    'user': self.practice_tracker.current_user,
                    'start_time': session_info['start_time'],
                    'duration': session_info['duration'],
                    'note_count': session_info['note_count']
                }
            else:
                response = {
                    'active': False,
                    'user': self.practice_tracker.current_user
                }

            return jsonify(response)

        @self.app.route('/api/user', methods=['POST'])
        def set_user():
            """Set the current user."""
            data = request.get_json()
            user_id = data.get('user_id')

            if not user_id:
                return jsonify({'error': 'user_id is required'}), 400

            self.practice_tracker.set_user(user_id)

            return jsonify({'success': True, 'user': user_id})

        @self.app.route('/api/user/activate', methods=['POST'])
        def activate_user():
            """Activate a user and start their practice session (button-based activation)."""
            data = request.get_json()
            user_id = data.get('user_id')

            if not user_id:
                return jsonify({'error': 'user_id is required'}), 400

            # Set the user
            self.practice_tracker.set_user(user_id)

            # Clear waiting_for_user flag BEFORE starting session
            # This ensures _on_session_start callback sees the correct state
            self.practice_tracker.waiting_for_user = False

            # Play confirmation chord
            self.practice_tracker._play_confirmation()

            # Force start the session (this will trigger _on_session_start callback)
            self.practice_tracker.detector.force_start_session()

            return jsonify({'success': True, 'user': user_id})

        @self.app.route('/api/sessions/recent')
        def get_recent_sessions():
            """Get recent practice sessions."""
            limit = request.args.get('limit', 10, type=int)
            sessions = self.practice_tracker.db.get_recent_sessions(limit=limit)
            return jsonify(sessions)

        @self.app.route('/api/sessions/summary')
        def get_summary():
            """Get daily summary of practice sessions."""
            days = request.args.get('days', 7, type=int)
            user_id = request.args.get('user_id', None)
            summary = self.practice_tracker.db.get_daily_summary(user_id=user_id, days=days)
            return jsonify(summary)

        @self.app.route('/api/users')
        def get_users():
            """Get configured users for the web interface."""
            # Get users from database instead of config
            users = self.practice_tracker.db.get_users()
            users_list = [
                {'id': user['id'], 'note': user['trigger_note'], 'name': user['name']}
                for user in users
            ]
            return jsonify(users_list)

        @self.app.route('/api/users/add', methods=['POST'])
        def add_user():
            """Add a new user."""
            data = request.get_json()
            name = data.get('name')
            trigger_note = data.get('trigger_note')

            if not name or trigger_note is None:
                return jsonify({'error': 'name and trigger_note are required'}), 400

            try:
                user_id = self.practice_tracker.db.add_user(name, trigger_note)
                # Reload user notes mapping in main tracker
                self.practice_tracker._load_user_notes()
                return jsonify({'success': True, 'user_id': user_id, 'name': name, 'trigger_note': trigger_note})
            except Exception as e:
                return jsonify({'error': str(e)}), 400

        @self.app.route('/api/users/<int:user_id>', methods=['DELETE'])
        def delete_user(user_id):
            """Tombstone a user."""
            try:
                self.practice_tracker.db.delete_user(user_id)
                # Reload user notes mapping in main tracker
                self.practice_tracker._load_user_notes()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 400

        @self.app.route('/api/config')
        def get_config():
            """Get configuration values for the web interface."""
            return jsonify({
                'session_timeout': config.SESSION_TIMEOUT
            })

        @self.app.route('/api/midi/status')
        def get_midi_status():
            """Get MIDI device connection status."""
            midi_monitor = self.practice_tracker.midi_monitor
            return jsonify({
                'connected': midi_monitor.is_connected,
                'device': midi_monitor.last_connected_device,
                'searching_for': midi_monitor.device_keyword
            })

        @self.app.route('/api/midi/reconnect', methods=['POST'])
        def reconnect_midi():
            """Trigger MIDI reconnection attempt with automatic power cycling."""
            midi_monitor = self.practice_tracker.midi_monitor
            # Use force_reconnect_with_power_cycle to bypass cooldown and force power cycle
            success = midi_monitor.force_reconnect_with_power_cycle()
            return jsonify({
                'success': success,
                'connected': midi_monitor.is_connected,
                'device': midi_monitor.last_connected_device
            })

        @self.app.route('/api/session/end', methods=['POST'])
        def end_session():
            """Manually end the current practice session."""
            detector = self.practice_tracker.detector
            if detector.practice_session_active:
                detector.force_end_session()
                return jsonify({'success': True, 'message': 'Session ended'})
            else:
                return jsonify({'success': False, 'message': 'No active session'}), 400

        @self.app.route('/api/stats/weekly')
        def get_weekly_stats():
            """Get weekly practice stats for all users, sorted by practice time."""
            from collections import OrderedDict

            # Get all users from database
            users = self.practice_tracker.db.get_users()
            all_stats = {}
            user_totals = []

            for user in users:
                user_name = user['name']
                stats = self.practice_tracker.db.get_weekly_stats(user_name)
                all_stats[user_name] = stats

                # Calculate total practice minutes for sorting
                total_minutes = sum(day['minutes'] for day in stats)
                user_totals.append((user_name, total_minutes))

            # Sort users by total practice minutes (descending)
            user_totals.sort(key=lambda x: x[1], reverse=True)

            # Return stats in sorted order using OrderedDict to preserve order
            sorted_stats = OrderedDict((user_name, all_stats[user_name]) for user_name, _ in user_totals)

            # Use json.dumps with ensure_ascii=False to preserve key order
            response = make_response(json.dumps(sorted_stats, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/json'
            return response

        @self.app.route('/api/target/<user_id>', methods=['GET'])
        def get_user_target(user_id):
            """Get practice target for a specific user."""
            target = self.practice_tracker.db.get_user_target(user_id)
            return jsonify({'user_id': user_id, 'target_minutes': target})

        @self.app.route('/api/target/<user_id>', methods=['POST'])
        def set_user_target(user_id):
            """Set practice target for a specific user."""
            data = request.get_json()
            target_minutes = data.get('target_minutes')

            if target_minutes is None or target_minutes < 0:
                return jsonify({'error': 'target_minutes must be >= 0'}), 400

            self.practice_tracker.db.set_user_target(user_id, target_minutes)
            return jsonify({'success': True, 'user_id': user_id, 'target_minutes': target_minutes})

    def notify_session_start(self):
        """Notify clients that a session has started."""
        session_info = self.practice_tracker.detector.get_session_info()
        if session_info:
            self.socketio.emit('session_started', {
                'user': self.practice_tracker.current_user,
                'start_time': session_info['start_time'],
                'active': True,
                'note_count': session_info['note_count'],
                'duration': session_info['duration'],
                'timestamp': time.time()
            })

    def notify_session_end(self, start_time, end_time, note_count):
        """Notify clients that a session has ended."""
        self.socketio.emit('session_ended', {
            'user': self.practice_tracker.current_user,
            'start_time': start_time,
            'end_time': end_time,
            'duration': end_time - start_time,
            'note_count': note_count,
            'timestamp': time.time()
        })

    def notify_session_activity(self):
        """Notify clients of session activity (note played)."""
        session_info = self.practice_tracker.detector.get_session_info()
        if session_info:
            self.socketio.emit('session_activity', {
                'user': self.practice_tracker.current_user,
                'note_count': session_info['note_count'],
                'duration': session_info['duration'],
                'timestamp': time.time()
            })

    def notify_midi_connected(self, device_name: str):
        """Notify clients that MIDI device connected."""
        logger.info(f"Notifying clients: MIDI connected to {device_name}")
        self.socketio.emit('midi_connected', {
            'device': device_name,
            'timestamp': time.time()
        })

    def notify_midi_disconnected(self):
        """Notify clients that MIDI device disconnected."""
        logger.info("Notifying clients: MIDI disconnected")
        self.socketio.emit('midi_disconnected', {
            'timestamp': time.time()
        })

    def notify_user_selection_prompt(self):
        """Notify clients to show user selection screen."""
        logger.info("Notifying clients: User selection prompt")
        self.socketio.emit('user_selection_prompt', {
            'timestamp': time.time()
        })

    def start(self):
        """Start the web server in a background thread."""
        if self.running:
            logger.warning("Web server already running")
            return

        self.running = True

        def run_server():
            logger.info(f"Starting web server on {self.host}:{self.port}")
            self.socketio.run(self.app, host=self.host, port=self.port,
                            allow_unsafe_werkzeug=True, debug=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info("Web server started in background thread")

    def stop(self):
        """Stop the web server."""
        self.running = False
        logger.info("Web server stopped")
