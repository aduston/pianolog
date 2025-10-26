# Building a Piano Practice Tracker: Complete Hardware & System Design Guide

Your piano practice tracker is entirely feasible on a budget under $100. The **Raspberry Pi 4 (2GB) at $88-97 total** provides the sweet spot for on-device facial recognition and audio detection, while cheaper alternatives like ESP32-CAM cannot reliably handle facial recognition without costly cloud services.

## Hardware recommendations: the budget-conscious build

The Raspberry Pi ecosystem offers the most viable path for your requirements. After extensive market analysis, **no genuinely cheaper alternative exists** that can handle on-device facial recognition reliably. The ESP32-CAM at $7-10 seems attractive but requires cloud processing at $360+/year, making it far more expensive long-term. Other single-board computers like Orange Pi 5 ($90-100) and Banana Pi M5 Pro ($130-145) are actually more expensive than Raspberry Pi while offering worse software ecosystems.

### Recommended complete build ($88-97)

**Core components for production-ready device:**

**Raspberry Pi 4 Model B (2GB RAM)** - $35
- Quad-core ARM Cortex-A72 @ 1.5GHz processor handles real-time facial recognition
- 2GB RAM sufficient for face_recognition library (4GB at $55 provides headroom)
- Dual-band Wi-Fi and multiple USB ports eliminate need for hubs
- Achieves 3-5 FPS for full facial recognition pipeline with optimization
- Available from Adafruit, CanaKit, Amazon, or official resellers

**Raspberry Pi Camera Module 3** - $25
- Sony IMX708 12MP sensor with autofocus via Phase Detection
- 75° field of view ideal for close-range facial recognition
- 1080p @ 50fps video capability
- Autofocus is critical advantage over older Module 2 for varying distances
- Note: Requires standard 15-pin cable (included) for Pi 4

**USB Mini Microphone** - $5-7
- SunFounder or generic plug-and-play USB microphones
- Omnidirectional, adequate for piano audio detection within 2-3 feet
- No drivers needed, lowest complexity for beginners
- Consumes minimal power (50-100mA)

**Official Raspberry Pi USB-C Power Supply (5V/3A, 15W)** - $10-12
- Required for stable Pi 4 operation under load
- Insufficient power causes throttling and instability

**32GB microSD Card (Class 10)** - $8-10
- Storage for OS, recordings buffer, and Python code

**Basic case** - $5-8 (optional but recommended)
- Protects board and improves aesthetics

**Total: $88-97** for complete working system

### Budget alternative: Pi Zero 2 W build ($63-77)

If you need absolute minimum cost, the **Raspberry Pi Zero 2 W at $15-19** can technically run facial recognition, but expect significant limitations. Performance drops to 0.1-0.5 FPS (approximately 10 seconds per frame) for facial recognition, making real-time detection challenging. The 512MB RAM struggles with complex models. This works for initial prototyping but may frustrate in production use.

Components: Pi Zero 2 W ($15-19) + Camera Module 3 ($25) + 22-pin camera cable ($5-8) + USB Mini Mic ($5-7) + Micro USB power supply ($8-10) + 16GB microSD ($5-8) = $63-77 total.

### Power options: plugged vs battery

**Wall adapter (recommended)**: Use the official power supply for permanent installation on your piano. Provides unlimited runtime, reliable power delivery, and eliminates battery maintenance. The Pi 4 consumes 2.5-7W during operation.

**Battery option**: For portable scenarios or as backup power, the **Adafruit 10,000mAh USB battery pack ($25-30)** provides approximately 15 hours of Pi 4 runtime in headless mode. However, most battery packs aren't true UPS devices and experience brief power flickers when switching between charging and discharging modes. The PiSugar2 Pro ($32-40) offers genuine UPS functionality if needed.

For a stationary piano tracker, stick with the wall adapter - it's simpler, more reliable, and cheaper.

### Camera and microphone deep dive

The Camera Module 3's autofocus feature justifies its $25 price over the older Module 2 ($20). When tracking piano practice, users move closer and farther from the camera, and autofocus automatically adjusts for accurate facial recognition at varying distances. The standard 75° FOV works well for single-user tracking; upgrade to the wide-angle 120° version ($35) only if monitoring multiple people simultaneously.

For microphones, the $5-7 USB option provides remarkable value. While the ReSpeaker 2-Mic Pi HAT ($12-25) offers superior dual-microphone audio and speaker output, it consumes GPIO pins and requires more complex setup. As a software engineer new to hardware, start with USB simplicity and upgrade later if audio quality becomes limiting.

## Software libraries: your Python toolkit

Your comfort with Python translates directly to Raspberry Pi development. The ecosystem offers mature, well-documented libraries that handle hardware abstraction.

### Facial recognition: three approaches

**Option 1: face_recognition library (recommended for accuracy)**

This dlib-based library achieves 97%+ accuracy with remarkably simple APIs. Installation requires patience - dlib compilation takes 30-60 minutes on Pi - but the payoff is substantial.

```bash
pip install dlib
pip install face_recognition
pip install imutils
```

Critical performance note: **Always use `model="hog"` for detection on Raspberry Pi**, not CNN. The HOG (Histogram of Oriented Gradients) model runs at 423±64ms per frame, while CNN is prohibitively slow. Pre-compute facial encodings on a desktop computer and load them on the Pi for recognition - computing encodings takes 105±8ms per face, which is acceptable for periodic identification.

Basic recognition workflow:
```python
import face_recognition
import pickle
import cv2

# Load pre-computed encodings
data = pickle.loads(open("encodings.pickle", "rb").read())

# Detect faces using HOG
rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
boxes = face_recognition.face_locations(rgb, model="hog")

# Compute encodings for detected faces
encodings = face_recognition.face_encodings(rgb, boxes)

# Match against known faces
for encoding in encodings:
    matches = face_recognition.compare_faces(data["encodings"], encoding)
    if True in matches:
        # Identify person via voting
        matchedIdxs = [i for (i, b) in enumerate(matches) if b]
        counts = {}
        for i in matchedIdxs:
            name = data["names"][i]
            counts[name] = counts.get(name, 0) + 1
        name = max(counts, key=counts.get)
```

Expected performance on Pi 4: 1-2 FPS for complete detection and recognition pipeline.

**Option 2: OpenCV with Haar Cascades (recommended for older Pi models)**

For Pi Zero 2 W or when maximum speed is essential, Haar Cascade classifiers provide 85-90% accuracy at significantly faster speeds. This works well for the piano tracker use case where you can process periodically rather than requiring real-time.

```bash
sudo apt install python3-opencv opencv-data
```

The trade-off: lower accuracy and sensitivity to lighting conditions, but 10-20x faster processing.

**Option 3: MobileNetV2 (recommended for custom training)**

Recent 2024 research demonstrates MobileNetV2 achieves 97.67% accuracy on Raspberry Pi 4 with 15-17 FPS performance - the best balance for edge devices. Training takes 102 minutes on Pi 4. Use this if you need to train custom models or want maximum performance.

### Audio detection and sound activation

**sounddevice + webrtcvad (recommended stack)**

This combination provides modern APIs with battle-tested voice activity detection. sounddevice replaces the older PyAudio with cleaner non-blocking APIs and better NumPy integration. webrtcvad offers \u003c1ms latency per 30ms audio frame for detecting speech/sound.

```bash
pip install sounddevice soundfile numpy
pip install webrtcvad-wheels
```

Sound-activated recording implementation:
```python
import sounddevice as sd
import webrtcvad
import numpy as np
from collections import deque

class SoundActivatedRecorder:
    def __init__(self, rate=16000):
        self.rate = rate
        self.vad = webrtcvad.Vad(2)  # Aggressiveness 0-3
        self.buffer = deque(maxlen=20)  # Pre-trigger buffer
        
    def is_speech(self, frame):
        # Convert float to int16 for VAD
        audio_int16 = (frame * 32767).astype('int16')
        return self.vad.is_speech(audio_int16.tobytes(), self.rate)
    
    def audio_callback(self, indata, frames, time, status):
        self.buffer.append(indata.copy())
        
        if self.is_speech(indata[:, 0]):
            # Trigger recording with pre-buffer
            self.start_recording()

# Start monitoring
stream = sd.InputStream(
    callback=recorder.audio_callback,
    channels=1,
    samplerate=16000,
    blocksize=int(16000 * 0.03)  # 30ms frames
)
```

The webrtcvad library requires 16-bit mono PCM at specific sample rates (8kHz, 16kHz, 32kHz, 48kHz). Use 16kHz as the sweet spot for piano audio - high enough quality while minimizing processing overhead.

### Camera interfacing with picamera2

Picamera2 is the official, hardware-accelerated camera library for Raspberry Pi. It comes pre-installed on Raspberry Pi OS and provides dramatically lower CPU usage than USB webcams.

```python
from picamera2 import Picamera2
import time

# Initialize camera
picam2 = Picamera2()

# Configure for 640x480 RGB (optimal for face detection)
config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)

picam2.configure(config)
picam2.start()

time.sleep(2)  # Camera warmup

# Capture as NumPy array (works directly with OpenCV)
frame = picam2.capture_array()

# Or capture as PIL Image
image = picam2.capture_image()

# Or save directly to file
picam2.capture_file("photo.jpg")
```

**Critical tip**: Use 640x480 resolution for facial recognition rather than full 1080p. The lower resolution provides 3-4x faster processing with negligible accuracy loss for face detection at close range. Hardware-accelerated H.264 encoding reduces CPU usage by 80% compared to software encoding.

### USB microphone setup

USB microphones are genuinely plug-and-play on Raspberry Pi. Verify detection:

```bash
# List audio devices
arecord -l

# Test in Python
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

If your USB microphone doesn't appear as the default, specify it explicitly:

```python
import sounddevice as sd

# List all devices to find your microphone
print(sd.query_devices())

# Use specific device by index
sd.default.device = 1  # Replace with your device index
```

Most USB microphones work immediately without driver installation or configuration files.

## System architecture: state machine and processing flow

The motion/sound-activated architecture provides 60-90% storage reduction compared to continuous recording by focusing exclusively on practice sessions.

### State machine design for session tracking

Implement a behavioral state machine with seven core states managing the complete session lifecycle:

**1. IDLE**: System armed, minimal processing (CPU \u003c10%), sensors monitoring for triggers

**2. DETECTION**: Motion or sound threshold exceeded, validating trigger to filter spurious events

**3. PRE_RECORDING**: Saving 3-5 second pre-trigger buffer to capture session start context

**4. ACTIVE_RECORDING**: Main recording phase with concurrent audio, video, and periodic facial recognition

**5. POST_RECORDING**: Continue recording 5-10 seconds after silence/stillness detected to ensure complete phrase capture

**6. PROCESSING**: Finalize recording, merge audio/video, extract metadata, compress files

**7. COOLDOWN**: 30-second prevention of immediate re-trigger to avoid session fragmentation

Transitions follow trigger events:
- IDLE → DETECTION when audio exceeds threshold AND motion detected (dual confirmation reduces false positives)
- DETECTION → PRE_RECORDING after 1-2 second validation period
- ACTIVE_RECORDING → POST_RECORDING after 60 seconds of silence/no motion
- PROCESSING → COOLDOWN after file successfully saved
- COOLDOWN → IDLE after timer expires

This state machine encapsulates session logic cleanly and supports hierarchical states for complex workflows like handling multiple simultaneous users.

### Processing architecture: multiprocessing for concurrency

Python's Global Interpreter Lock (GIL) limits threading effectiveness for CPU-bound tasks. Use multiprocessing for parallel execution of computationally intensive operations:

**Process 1: Audio Recording** - Captures and encodes audio stream, manages circular buffer for pre-trigger recording

**Process 2: Video Recording** - Interfaces with picamera2, handles H.264 hardware encoding, manages frame buffers

**Process 3: Facial Recognition** - Processes frames every 1-2 seconds (every 30-60 frames), builds confidence scores over time

**Thread 1: Cloud Uploader** - I/O-bound network operations upload completed sessions in background

**Thread 2: Event Monitor** - Lightweight coordination of GPIO sensors and trigger thresholds

**Main Process: State Machine Controller** - Coordinates all processes, manages state transitions, handles error recovery

Inter-process communication uses multiprocessing.Queue for data passing and multiprocessing.Pipe for command signaling. This architecture achieves concurrent audio and video recording while performing periodic facial recognition without blocking.

### Trigger-based recording best practices

**Dual-trigger confirmation**: Require both audio above threshold AND camera motion detection to start recording. This dramatically reduces false positives from ambient noise or non-practice movement.

**Pre/post-trigger buffering**: Maintain a 3-5 second circular buffer continuously. When triggered, save the pre-buffer to capture the session start naturally. Continue recording for 5-10 seconds after triggers cease to ensure complete musical phrases are captured.

**Session boundary detection**: Define session end as 60 seconds of no motion and no audio above threshold. Implement minimum session duration filter of 30 seconds to eliminate spurious triggers.

**Cascaded activation for power efficiency**:
1. Low-power motion sensor (PIR on GPIO) wakes system from idle
2. Audio threshold detection activates camera
3. Motion detection in camera frames confirms ongoing activity  
4. Facial recognition runs only when motion/audio confirmed

This cascade reduces average power consumption by 40-60% compared to continuous processing.

### Performance optimization techniques

**1. Frame skipping**: Process every 2nd or 3rd frame for facial recognition rather than every frame. At 30 FPS, processing every 30 frames (once per second) provides adequate identification accuracy while achieving 30x speedup.

**2. Resolution scaling**: Capture video at 1080p for recording quality, but downscale to 640x480 for facial recognition. Face detection works excellently at this resolution while providing 6x faster processing.

**3. ROI (Region of Interest) processing**: After initial face detection, track the face location and only process that region in subsequent frames. This 4-10x speedup maintains tracking while reducing computational load.

**4. Model pre-loading**: Load facial recognition models during initialization rather than per-frame. Model loading is expensive (2-5 seconds), so amortize across the application lifetime.

**5. Hardware acceleration**: Enable VideoCore GPU for H.264 encoding (automatic with picamera2). This offloads video compression from CPU, preventing thermal throttling during long sessions.

Expected performance on Pi 4 with optimization: 60-80% CPU utilization during active recording, \u003c1.5GB memory usage, sustained operation without throttling with heatsink/fan.

## Google Cloud integration: storage and reporting

Google Cloud provides serverless, scalable infrastructure at remarkably low cost for IoT devices.

### Recommended service architecture

**Cloud Storage** - Store raw audio/video recordings at $0.02/GB/month. The Standard storage class works well for recent data; Archive class ($0.0012/GB/month) for old recordings.

**Firestore** - NoSQL database for session metadata (who practiced, when, duration). Free tier covers 50,000 reads and 20,000 writes per day - sufficient for hobbyist use.

**Cloud Functions** - Serverless processing triggered by file uploads. Generate thumbnails, extract audio features, update analytics. Free tier provides 2 million invocations per month.

**BigQuery** - Analytics and reporting engine for practice statistics. Free tier includes 10GB storage and 1TB query processing monthly.

Total monthly cost: **$1-2 for 100 sessions**, **$10-15 for 1000 sessions**. No upfront infrastructure costs or server management.

### Raspberry Pi upload implementation

Install Google Cloud libraries and configure authentication:

```bash
pip3 install google-cloud-storage google-cloud-firestore

# Create service account key in GCP Console, download JSON
export GOOGLE_APPLICATION_CREDENTIALS="/home/pi/.config/gcloud/piano-key.json"
```

Complete upload implementation with retry logic:

```python
from google.cloud import storage, firestore
from google.oauth2 import service_account
from datetime import datetime
import os
import time

class PracticeTracker:
    def __init__(self, project_id, bucket_name, credentials_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        self.storage_client = storage.Client(project=project_id, credentials=credentials)
        self.db = firestore.Client(project=project_id, credentials=credentials)
        self.bucket = self.storage_client.bucket(bucket_name)
    
    def upload_session(self, audio_file, video_file, metadata):
        """Upload session files and metadata to GCP"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Upload audio to Cloud Storage
        audio_blob = self.bucket.blob(f"sessions/{timestamp}/audio.wav")
        audio_blob.upload_from_filename(audio_file)
        
        # Upload video if exists
        if video_file:
            video_blob = self.bucket.blob(f"sessions/{timestamp}/video.mp4")
            video_blob.upload_from_filename(video_file)
        
        # Store metadata in Firestore
        session_doc = {
            'timestamp': firestore.SERVER_TIMESTAMP,
            'user_id': metadata['user_id'],  # From facial recognition
            'duration_seconds': metadata['duration'],
            'audio_path': audio_blob.name,
            'video_path': video_blob.name if video_file else None,
            'device_id': 'piano-pi-001'
        }
        
        doc_ref = self.db.collection('practice_sessions').add(session_doc)
        print(f"Uploaded session: {doc_ref[1].id}")
        
        # Clean up local files after successful upload
        os.remove(audio_file)
        if video_file:
            os.remove(video_file)
    
    def upload_with_retry(self, audio_file, video_file, metadata, max_retries=3):
        """Retry upload with exponential backoff"""
        for attempt in range(max_retries):
            try:
                self.upload_session(audio_file, video_file, metadata)
                return True
            except Exception as e:
                print(f"Upload failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
        return False

# Usage
tracker = PracticeTracker(
    project_id="your-project-id",
    bucket_name="piano-practice-data",
    credentials_path="/home/pi/.config/gcloud/piano-key.json"
)

session = {
    'user_id': 'daughter',  # From facial recognition
    'duration': 2700  # 45 minutes in seconds
}

tracker.upload_with_retry('session_audio.wav', 'session_video.mp4', session)
```

### Handling intermittent connectivity

Network reliability varies in home environments. Implement a local queue for failed uploads:

```python
import sqlite3
import json

class OfflineQueue:
    def __init__(self, db_path='/home/pi/upload_queue.db'):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS upload_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_path TEXT,
                video_path TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def add_to_queue(self, audio_path, video_path, metadata):
        """Queue failed upload for later retry"""
        self.conn.execute(
            'INSERT INTO upload_queue (audio_path, video_path, metadata) VALUES (?, ?, ?)',
            (audio_path, video_path, json.dumps(metadata))
        )
        self.conn.commit()
    
    def process_queue(self, tracker):
        """Attempt to upload queued sessions"""
        cursor = self.conn.execute('SELECT * FROM upload_queue ORDER BY id')
        for row in cursor:
            upload_id, audio_path, video_path, metadata_json, _ = row
            metadata = json.loads(metadata_json)
            
            if tracker.upload_session(audio_path, video_path, metadata):
                # Successful upload - remove from queue
                self.conn.execute('DELETE FROM upload_queue WHERE id = ?', (upload_id,))
                self.conn.commit()
```

Run queue processing every 15-30 minutes in a background thread to automatically upload when connectivity returns.

### Weekly metrics and reporting

BigQuery scheduled queries automatically generate weekly reports without server management:

```sql
-- Create weekly summary table with scheduled query
CREATE TABLE `project.piano_analytics.weekly_summary` AS
SELECT
  DATE_TRUNC(timestamp, WEEK) as week_start,
  user_id,
  COUNT(*) as total_sessions,
  SUM(duration_seconds) / 60 as total_minutes,
  AVG(duration_seconds) / 60 as avg_session_minutes,
  MIN(timestamp) as first_practice,
  MAX(timestamp) as last_practice
FROM `project.piano_analytics.practice_sessions`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY week_start, user_id
ORDER BY week_start DESC;
```

Schedule this query to run every Sunday at midnight. Access results via Cloud Functions REST API:

```python
from google.cloud import bigquery

def get_weekly_report(request):
    """Cloud Function to serve weekly report"""
    client = bigquery.Client()
    
    query = """
    SELECT * FROM `project.piano_analytics.weekly_summary`
    WHERE week_start = DATE_TRUNC(CURRENT_DATE(), WEEK)
    """
    
    results = client.query(query).to_dataframe()
    return results.to_json(orient='records')
```

Deploy this function and access reports from your iPhone app or web dashboard via HTTPS endpoint.

## Complete implementation example

Bringing all components together into a functional practice tracker:

```python
import cv2
import face_recognition
import sounddevice as sd
import webrtcvad
from picamera2 import Picamera2
import numpy as np
import pickle
from datetime import datetime
from collections import deque
import threading
import multiprocessing

class PianoPracticeTracker:
    def __init__(self):
        # Initialize camera
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        # Initialize VAD for sound detection
        self.vad = webrtcvad.Vad(2)  # Aggressiveness 0-3
        self.sample_rate = 16000
        
        # Load known face encodings
        with open("face_encodings.pkl", "rb") as f:
            self.known_faces = pickle.load(f)
        
        # Session state
        self.current_user = None
        self.session_start = None
        self.audio_buffer = deque(maxlen=50)  # 50 frames buffer
        self.recording = False
        
    def audio_callback(self, indata, frames, time, status):
        """Process incoming audio in real-time"""
        # Convert to int16 for VAD
        audio_int16 = (indata[:, 0] * 32767).astype('int16')
        
        # Detect speech/sound
        is_sound = self.vad.is_speech(audio_int16.tobytes(), self.sample_rate)
        
        if is_sound:
            self.audio_buffer.append(indata.copy())
            
            # Start recording if not already
            if not self.recording:
                self.start_session()
            
            # Identify user if unknown
            if self.current_user is None:
                self.identify_user()
    
    def identify_user(self):
        """Identify user from camera"""
        frame = self.picam2.capture_array()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces with HOG
        boxes = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, boxes)
        
        for encoding in encodings:
            matches = face_recognition.compare_faces(
                self.known_faces["encodings"],
                encoding
            )
            
            if True in matches:
                # Find most common match
                matched_idxs = [i for i, b in enumerate(matches) if b]
                counts = {}
                for i in matched_idxs:
                    name = self.known_faces["names"][i]
                    counts[name] = counts.get(name, 0) + 1
                
                self.current_user = max(counts, key=counts.get)
                print(f"User identified: {self.current_user}")
                return
    
    def start_session(self):
        """Begin practice session recording"""
        self.recording = True
        self.session_start = datetime.now()
        print(f"Session started: {self.session_start}")
        # Initialize video/audio recording processes here
    
    def end_session(self):
        """End and save practice session"""
        if self.session_start and self.current_user:
            duration = (datetime.now() - self.session_start).total_seconds()
            
            session_data = {
                'user_id': self.current_user,
                'start_time': self.session_start,
                'duration_seconds': duration,
                'timestamp': datetime.now()
            }
            
            print(f"Session ended: {duration/60:.1f} minutes")
            # Upload to cloud, save locally, etc.
            
        # Reset state
        self.recording = False
        self.session_start = None
        self.current_user = None
    
    def run(self):
        """Main tracker loop"""
        print("Piano Practice Tracker started...")
        
        stream = sd.InputStream(
            callback=self.audio_callback,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=int(self.sample_rate * 0.03)  # 30ms frames
        )
        
        try:
            with stream:
                last_activity = datetime.now()
                
                while True:
                    sd.sleep(1000)  # Check every second
                    
                    # Check for session timeout (60 seconds silence)
                    if self.recording:
                        if len(self.audio_buffer) == 0:
                            idle_time = (datetime.now() - last_activity).total_seconds()
                            if idle_time > 60:
                                self.end_session()
                        else:
                            last_activity = datetime.now()
                            
        except KeyboardInterrupt:
            print("\nStopping tracker...")
            if self.recording:
                self.end_session()

if __name__ == "__main__":
    tracker = PianoPracticeTracker()
    tracker.run()
```

This example demonstrates the core logic. A production implementation would separate audio/video recording into dedicated processes and add robust error handling.

## Setup roadmap for software engineers

Your software engineering background provides a strong foundation. Here's the learning path from hardware novice to working tracker:

**Week 1-2: Hardware setup and basics**
- Order Raspberry Pi 4 kit, Camera Module 3, USB microphone
- Flash Raspberry Pi OS to SD card using Raspberry Pi Imager
- Initial boot, configure SSH for headless operation, update system
- Test camera with `libcamera-hello`, test microphone with `arecord`
- Run basic Python camera and audio capture scripts

**Week 3-4: Individual component testing**
- Implement motion detection with OpenCV
- Implement audio threshold detection with sounddevice
- Capture facial images of yourself and daughter (3-5 images each)
- Generate facial encodings using face_recognition library
- Test identification accuracy with various lighting conditions

**Week 5-6: Integration and state machine**
- Build state machine controller for session lifecycle
- Integrate motion + audio triggers with dual confirmation
- Implement pre/post-trigger buffering
- Test session boundary detection with simulated practice sessions
- Add session metadata tracking

**Week 7-8: Cloud integration and refinement**
- Set up Google Cloud project and service account
- Implement Cloud Storage upload with retry logic
- Configure Firestore for metadata storage
- Create BigQuery tables and scheduled queries
- Build simple web dashboard or iOS app to view reports

**Week 9+: Polish and optimization**
- Optimize performance (frame skipping, resolution tuning)
- Implement offline queue for connectivity issues
- Add error handling and automatic recovery
- Create user enrollment interface
- Document system and create backup strategy

Expected total development time: 40-60 hours spread over 8-10 weeks for a software engineer with no prior hardware experience.

## Critical success factors

**1. Start with wired power, not battery**: Eliminate power management complexity during development. Battery operation is a future enhancement after core functionality works.

**2. Process every Nth frame, not every frame**: Facial recognition at 30 FPS is unnecessary and impossible on Pi. Processing every 30-60 frames (once per 1-2 seconds) provides adequate identification while achieving sustainable performance.

**3. Use HOG, not CNN, for face detection**: The CNN model in face_recognition is 5-10x slower. Always specify `model="hog"` for Raspberry Pi deployment.

**4. Test incrementally**: Get each component working individually before integration. Debugging concurrent multiprocessing with hardware interfaces is challenging - ensure each piece functions correctly in isolation first.

**5. Monitor temperature**: Raspberry Pi 4 throttles at 80°C. Add heatsink or fan for sustained performance during long practice sessions. Check temperature with `vcgencmd measure_temp`.

**6. Plan for SD card failure**: SD cards wear out with extensive writes. Use tmpfs (RAM disk) for temporary buffers, write only completed sessions to SD card, and maintain backups in cloud.

Your piano practice tracker is entirely achievable with the Raspberry Pi 4 at under $100 total cost. The combination of on-device facial recognition, sound-activated recording, and cloud analytics provides a professional-grade solution without ongoing subscription costs. The Python ecosystem offers mature libraries that abstract hardware complexity, letting you leverage your software engineering skills effectively.

Start with the recommended $88-97 build, follow the incremental development roadmap, and you'll have a working tracker within 8-10 weeks. The system will reliably track who practices and for how long, upload data to Google Cloud, and generate weekly reports accessible from your iPhone - exactly what you need to monitor piano practice progress.