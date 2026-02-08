// Connect to WebSocket
// Detect if we're behind a proxy at /pianolog/
const basePath = window.location.pathname.startsWith('/pianolog') ? '/pianolog' : '';
const socket = io({
    path: basePath + '/socket.io'
});

let currentSession = null;
let durationTimer = null;
let configuredUsers = [];
let midiConnected = false;
let weeklyStats = {};
let statsRefreshInterval = null;
let lastActivityTime = null;
let countdownTimer = null;
let countdownCheckInterval = null;
let sessionTimeout = 30; // Default, will be loaded from config

// Connection status
socket.on('connect', () => {
    console.log('Connected to server');
    document.getElementById('connectionStatus').textContent = 'WebSocket Connected';
    document.getElementById('connectionStatus').className = 'connection-status connected';
    loadConfig();
    loadUsers();
    loadMidiStatus();
    loadStatus();
    loadRecentSessions();
    loadWeeklyStats();
    startStatsRefresh();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    document.getElementById('connectionStatus').textContent = 'Disconnected';
    document.getElementById('connectionStatus').className = 'connection-status disconnected';
});

// Session events
socket.on('session_started', (data) => {
    console.log('Session started:', data);
    currentSession = data;
    lastActivityTime = Date.now();
    startDurationTimer();
    startCountdownCheck();
    updateStatus();
    switchToScreen('practice');
    loadRecentSessions();
});

socket.on('session_ended', (data) => {
    console.log('Session ended:', data);
    currentSession = null;
    lastActivityTime = null;
    stopCountdownCheck();
    updateStatus();
    switchToScreen('stats');
    loadRecentSessions();
    loadWeeklyStats();  // Refresh stats after session ends
});

socket.on('session_activity', (data) => {
    console.log('Session activity:', data);
    if (currentSession) {
        currentSession.note_count = data.note_count;
        currentSession.duration = data.duration;
        updateSessionInfo();

        // Update last activity time and reset countdown
        lastActivityTime = Date.now();
        hideCountdown();
    }
});

socket.on('midi_connected', (data) => {
    console.log('MIDI connected:', data);
    midiConnected = true;
    updateMidiStatus(true, data.device);
});

socket.on('midi_disconnected', (data) => {
    console.log('MIDI disconnected:', data);
    midiConnected = false;
    updateMidiStatus(false, null);
});

socket.on('user_selection_prompt', (data) => {
    console.log('User selection prompt triggered:', data);
    showUserSelection();
});

// Load configuration from server
async function loadConfig() {
    try {
        const response = await fetch(basePath + '/api/config');
        const config = await response.json();
        sessionTimeout = config.session_timeout;
        console.log('Loaded config: session_timeout =', sessionTimeout);
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

// Load configured users from server
async function loadUsers() {
    try {
        const response = await fetch(basePath + '/api/users');
        configuredUsers = await response.json();
        console.log('Loaded users:', configuredUsers);
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Load MIDI status
async function loadMidiStatus() {
    try {
        const response = await fetch(basePath + '/api/midi/status');
        const data = await response.json();
        midiConnected = data.connected;
        updateMidiStatus(data.connected, data.device);
    } catch (error) {
        console.error('Error loading MIDI status:', error);
    }
}

// Update MIDI status display
function updateMidiStatus(connected, deviceName) {
    const midiStatus = document.getElementById('midiStatus');
    const midiStatusText = document.getElementById('midiStatusText');
    const midiDeviceName = document.getElementById('midiDeviceName');
    const retryButton = document.getElementById('retryButton');

    if (connected) {
        midiStatus.className = 'midi-status connected';
        midiStatusText.textContent = 'USB Piano Connected';
        midiDeviceName.textContent = deviceName || '';
        retryButton.style.display = 'none';
        // Reset button state for next time
        retryButton.disabled = false;
        retryButton.textContent = 'Retry Connection';
    } else {
        midiStatus.className = 'midi-status disconnected';
        midiStatusText.textContent = 'USB is disconnected';
        midiDeviceName.textContent = 'Waiting for piano...';
        retryButton.style.display = 'block';
        // Only enable the button if it's not currently processing a retry
        if (retryButton.textContent === 'Retry Connection') {
            retryButton.disabled = false;
        }
    }
}

// Retry MIDI connection
async function retryMidiConnection() {
    const retryButton = document.getElementById('retryButton');
    retryButton.disabled = true;
    retryButton.textContent = 'Power cycling USB...';

    try {
        const response = await fetch(basePath + '/api/midi/reconnect', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            // Connection successful - MIDI status will be updated via WebSocket event
            midiConnected = true;
            updateMidiStatus(true, data.device);
        } else {
            // Connection failed - keep button disabled and wait for connection
            // The button will be re-enabled only when midi_connected event is received
            retryButton.textContent = 'Waiting for piano...';
        }
    } catch (error) {
        console.error('Error retrying MIDI connection:', error);
        // On error, keep button disabled with waiting message
        retryButton.textContent = 'Waiting for piano...';
    }
}

// Load current status
async function loadStatus() {
    try {
        const response = await fetch(basePath + '/api/status');
        const data = await response.json();

        if (data.active) {
            currentSession = data;
            // Don't set lastActivityTime here - wait for actual key press events
            // This ensures countdown only triggers after real inactivity, not on page load
            startDurationTimer();
            startCountdownCheck();
            switchToScreen('practice');
        } else {
            currentSession = null;
            lastActivityTime = null;
            stopDurationTimer();
            stopCountdownCheck();
            switchToScreen('stats');
        }

        updateStatus();
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

// Update status display
function updateStatus() {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const sessionInfo = document.getElementById('sessionInfo');
    const sessionControls = document.getElementById('sessionControls');

    if (currentSession && currentSession.active) {
        // Active session - show practice screen
        statusIndicator.className = 'status-indicator active';
        statusText.textContent = `${currentSession.user} is practicing`;
        sessionInfo.style.display = 'grid';
        updateSessionInfo();

        // Show end session button
        sessionControls.className = 'session-controls active';
    } else {
        // No active session - should be in stats screen, not practice screen
        // The practice screen UI doesn't need to be updated because we switch to stats
        stopDurationTimer();
    }
}

// Update session info
function updateSessionInfo() {
    if (!currentSession || !currentSession.active) return;

    const duration = currentSession.duration || 0;
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    document.getElementById('duration').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('noteCount').textContent = currentSession.note_count || 0;
}

// Start duration timer
function startDurationTimer() {
    stopDurationTimer();
    durationTimer = setInterval(() => {
        if (currentSession && currentSession.active) {
            const elapsed = Date.now() / 1000 - currentSession.start_time;
            currentSession.duration = elapsed;
            updateSessionInfo();
        }
    }, 1000);
}

// Stop duration timer
function stopDurationTimer() {
    if (durationTimer) {
        clearInterval(durationTimer);
        durationTimer = null;
    }
}

// Start countdown check (runs every 100ms to check if we should show countdown)
function startCountdownCheck() {
    stopCountdownCheck();
    countdownCheckInterval = setInterval(() => {
        if (currentSession && currentSession.active && lastActivityTime) {
            const timeSinceActivity = (Date.now() - lastActivityTime) / 1000;

            // Show countdown after 10 seconds of inactivity
            if (timeSinceActivity >= 10) {
                // Calculate seconds remaining until session timeout
                const secondsRemaining = Math.max(0, Math.ceil(sessionTimeout - timeSinceActivity));
                showCountdown(secondsRemaining);

                if (secondsRemaining === 0) {
                    hideCountdown();
                }
            } else {
                hideCountdown();
            }
        }
    }, 100);
}

// Stop countdown check
function stopCountdownCheck() {
    if (countdownCheckInterval) {
        clearInterval(countdownCheckInterval);
        countdownCheckInterval = null;
    }
    hideCountdown();
}

// Show countdown timer with specified seconds
function showCountdown(seconds) {
    const countdownTimer = document.getElementById('countdownTimer');
    const countdownValue = document.getElementById('countdownValue');

    countdownValue.textContent = seconds;
    countdownTimer.classList.add('active');
}

// Hide countdown timer
function hideCountdown() {
    const countdownTimer = document.getElementById('countdownTimer');
    countdownTimer.classList.remove('active');
}

// Set user
async function setUser(userId) {
    try {
        const response = await fetch(basePath + '/api/user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId })
        });

        const data = await response.json();
        console.log('User set:', data);

        // Update button highlighting immediately (case-insensitive comparison)
        document.querySelectorAll('.user-button').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent.toLowerCase() === userId.toLowerCase()) {
                btn.classList.add('active');
            }
        });

        loadStatus();
    } catch (error) {
        console.error('Error setting user:', error);
    }
}

// Load recent sessions
async function loadRecentSessions() {
    try {
        const response = await fetch(basePath + '/api/sessions/recent?limit=5');
        const sessions = await response.json();

        const sessionList = document.getElementById('recentSessions');

        if (sessions.length === 0) {
            sessionList.innerHTML = '<li class="session-item">No recent sessions</li>';
            return;
        }

        sessionList.innerHTML = sessions.map(session => {
            const date = new Date(session.start_timestamp * 1000);
            const duration = Math.round(session.duration_seconds / 60);

            return `
                <li class="session-item">
                    <span class="session-user">${session.user_id}</span>
                    <span class="session-details">
                        ${date.toLocaleDateString()} ${date.toLocaleTimeString()} -
                        ${duration} min, ${session.note_count} notes
                    </span>
                </li>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading recent sessions:', error);
    }
}

// End current session
async function endSession() {
    const endButton = document.getElementById('endSessionButton');
    endButton.disabled = true;
    endButton.textContent = 'Ending...';

    try {
        const response = await fetch(basePath + '/api/session/end', {
            method: 'POST'
        });

        if (response.ok) {
            console.log('Session ended successfully');
            // Status will update via WebSocket event
        } else {
            console.error('Failed to end session');
            alert('Failed to end session');
        }
    } catch (error) {
        console.error('Error ending session:', error);
        alert('Error ending session');
    } finally {
        endButton.disabled = false;
        endButton.textContent = 'End Session';
    }
}

// Load weekly stats for all users
async function loadWeeklyStats() {
    try {
        const response = await fetch(basePath + '/api/stats/weekly');
        weeklyStats = await response.json();
        renderStatsScreen();
    } catch (error) {
        console.error('Error loading weekly stats:', error);
    }
}

// Render the stats screen with weekly bar graphs
function renderStatsScreen() {
    const userStatsGrid = document.getElementById('userStatsGrid');

    if (Object.keys(weeklyStats).length === 0) {
        userStatsGrid.innerHTML = '<p style="color: white; text-align: center;">Loading stats...</p>';
        return;
    }

    // Check if we're in landscape mode on a larger screen
    const isLandscape = window.matchMedia('(min-width: 768px) and (orientation: landscape)').matches;
    const userEntries = Object.entries(weeklyStats);

    if (isLandscape && userEntries.length > 2) {
        // Render with carousel for landscape mode
        renderStatsCarousel(userEntries);
    } else {
        // Render normal grid for portrait or when 2 or fewer users
        renderStatsGrid(userEntries);
    }
}

// Render stats in a simple grid
function renderStatsGrid(userEntries) {
    const userStatsGrid = document.getElementById('userStatsGrid');
    userStatsGrid.innerHTML = userEntries.map(([userId, stats]) => {
        // Calculate summary stats
        const totalMinutes = stats.reduce((sum, day) => sum + day.minutes, 0);
        const daysMetTarget = stats.filter(day => day.met_target).length;
        const avgMinutes = (totalMinutes / stats.length).toFixed(1);
        const targetMinutes = stats[0]?.target_minutes || 15;

        // Generate bar chart
        const maxHeight = 150;
        const bars = stats.map(day => {
            const heightPercentage = Math.min(100, day.percentage);
            const height = Math.max(4, (heightPercentage / 100) * maxHeight);

            let barClass = 'day-bar';
            if (day.minutes === 0) {
                barClass += ' empty';
            } else if (day.met_target) {
                barClass += ' met-target';
            } else {
                barClass += ' partial';
            }

            return `
                <div class="day-bar-container" onclick="showBarPopover(event, '${userId}', '${day.day_name}', ${day.minutes})">
                    <div class="${barClass}" style="height: ${height}px;">
                        <div class="day-value">${day.minutes}m</div>
                    </div>
                    <div class="day-label">${day.day_name}</div>
                </div>
            `;
        }).join('');

        return `
            <div class="user-stats-card">
                <div class="user-stats-header">
                    <div class="user-stats-name">${userId}</div>
                    <div class="user-stats-target">Goal: ${targetMinutes} min/day</div>
                </div>
                <div class="weekly-chart">
                    ${bars}
                </div>
                <div class="stats-summary">
                    <div class="stats-summary-item">
                        <div class="stats-summary-value">${daysMetTarget}/7</div>
                        <div class="stats-summary-label">Days on track</div>
                    </div>
                    <div class="stats-summary-item">
                        <div class="stats-summary-value">${totalMinutes.toFixed(0)}m</div>
                        <div class="stats-summary-label">This week</div>
                    </div>
                    <div class="stats-summary-item">
                        <div class="stats-summary-value">${avgMinutes}m</div>
                        <div class="stats-summary-label">Daily avg</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

let currentCarouselPage = 0;

// Render stats with carousel for landscape mode
function renderStatsCarousel(userEntries) {
    const userStatsGrid = document.getElementById('userStatsGrid');
    const totalPages = Math.ceil(userEntries.length / 2);

    // Build carousel HTML
    let carouselHTML = '<div class="stats-carousel-container"><div class="stats-carousel" id="statsCarousel">';

    for (let page = 0; page < totalPages; page++) {
        const startIdx = page * 2;
        const pageUsers = userEntries.slice(startIdx, startIdx + 2);

        carouselHTML += '<div class="stats-carousel-page">';

        pageUsers.forEach(([userId, stats]) => {
            const totalMinutes = stats.reduce((sum, day) => sum + day.minutes, 0);
            const daysMetTarget = stats.filter(day => day.met_target).length;
            const avgMinutes = (totalMinutes / stats.length).toFixed(1);
            const targetMinutes = stats[0]?.target_minutes || 15;

            const maxHeight = 150;
            const bars = stats.map(day => {
                const heightPercentage = Math.min(100, day.percentage);
                const height = Math.max(4, (heightPercentage / 100) * maxHeight);

                let barClass = 'day-bar';
                if (day.minutes === 0) {
                    barClass += ' empty';
                } else if (day.met_target) {
                    barClass += ' met-target';
                } else {
                    barClass += ' partial';
                }

                return `
                    <div class="day-bar-container" onclick="showBarPopover(event, '${userId}', '${day.day_name}', ${day.minutes})">
                        <div class="${barClass}" style="height: ${height}px;">
                            <div class="day-value">${day.minutes}m</div>
                        </div>
                        <div class="day-label">${day.day_name}</div>
                    </div>
                `;
            }).join('');

            carouselHTML += `
                <div class="user-stats-card">
                    <div class="user-stats-header">
                        <div class="user-stats-name">${userId}</div>
                        <div class="user-stats-target">Goal: ${targetMinutes} min/day</div>
                    </div>
                    <div class="weekly-chart">
                        ${bars}
                    </div>
                    <div class="stats-summary">
                        <div class="stats-summary-item">
                            <div class="stats-summary-value">${daysMetTarget}/7</div>
                            <div class="stats-summary-label">Days on track</div>
                        </div>
                        <div class="stats-summary-item">
                            <div class="stats-summary-value">${totalMinutes.toFixed(0)}m</div>
                            <div class="stats-summary-label">This week</div>
                        </div>
                        <div class="stats-summary-item">
                            <div class="stats-summary-value">${avgMinutes}m</div>
                            <div class="stats-summary-label">Daily avg</div>
                        </div>
                    </div>
                </div>
            `;
        });

        carouselHTML += '</div>';
    }

    carouselHTML += '</div></div>';

    userStatsGrid.innerHTML = carouselHTML;

    // Add navigation buttons if more than 1 page (insert into placeholder)
    const navPlaceholder = document.getElementById('carouselNavPlaceholder');

    if (totalPages > 1) {
        navPlaceholder.innerHTML = `
            <div id="carouselNavContainer" class="carousel-nav">
                <button class="carousel-button" id="prevButton" onclick="navigateCarousel(-1)">← Previous</button>
                <button class="carousel-button" id="nextButton" onclick="navigateCarousel(1)">Next →</button>
            </div>
        `;
    } else {
        navPlaceholder.innerHTML = '';
    }

    // Reset to first page
    currentCarouselPage = 0;
    updateCarousel();
}

// Navigate carousel
function navigateCarousel(direction) {
    const userEntries = Object.entries(weeklyStats);
    const totalPages = Math.ceil(userEntries.length / 2);

    currentCarouselPage += direction;

    if (currentCarouselPage < 0) {
        currentCarouselPage = 0;
    } else if (currentCarouselPage >= totalPages) {
        currentCarouselPage = totalPages - 1;
    }

    updateCarousel();
}

// Update carousel position
function updateCarousel() {
    const carousel = document.getElementById('statsCarousel');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const userEntries = Object.entries(weeklyStats);
    const totalPages = Math.ceil(userEntries.length / 2);

    if (carousel) {
        carousel.style.transform = `translateX(-${currentCarouselPage * 100}%)`;
    }

    if (prevButton) {
        prevButton.disabled = currentCarouselPage === 0;
    }

    if (nextButton) {
        nextButton.disabled = currentCarouselPage === totalPages - 1;
    }
}

// Switch between screens
function switchToScreen(screenName) {
    const statsScreen = document.getElementById('statsScreen');
    const practiceScreen = document.getElementById('practiceScreen');
    const userMgmtScreen = document.getElementById('userMgmtScreen');
    const userSelectionScreen = document.getElementById('userSelectionScreen');

    if (screenName === 'stats') {
        statsScreen.classList.add('active');
        practiceScreen.classList.remove('active');
        userMgmtScreen.classList.remove('active');
        userSelectionScreen.classList.remove('active');
    } else if (screenName === 'user-selection') {
        statsScreen.classList.remove('active');
        practiceScreen.classList.remove('active');
        userMgmtScreen.classList.remove('active');
        userSelectionScreen.classList.add('active');
    } else if (screenName === 'practice') {
        statsScreen.classList.remove('active');
        practiceScreen.classList.add('active');
        userMgmtScreen.classList.remove('active');
        userSelectionScreen.classList.remove('active');
    } else if (screenName === 'user-mgmt') {
        statsScreen.classList.remove('active');
        practiceScreen.classList.remove('active');
        userMgmtScreen.classList.add('active');
        userSelectionScreen.classList.remove('active');
    }
}

// Show user selection screen
function showUserSelection() {
    renderUserSelectionButtons();
    switchToScreen('user-selection');
}

// Render user selection buttons
function renderUserSelectionButtons() {
    const container = document.getElementById('userSelectionButtons');

    if (configuredUsers.length === 0) {
        container.innerHTML = '<p style="color: #666;">No users configured</p>';
        return;
    }

    container.innerHTML = configuredUsers.map(user => {
        const noteName = midiNoteToName(user.note);
        return `
            <button class="user-select-button" onclick="selectUserForPractice('${user.name}')">
                <span class="user-name">${user.name}</span>
                <span class="trigger-note">or play ${noteName}</span>
            </button>
        `;
    }).join('');
}

// Select user for practice (via button click)
async function selectUserForPractice(userName) {
    try {
        const response = await fetch(basePath + '/api/user/activate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userName })
        });

        const data = await response.json();

        // The session_started event from WebSocket will handle switching to practice screen
    } catch (error) {
        console.error('Error activating user:', error);
        alert('Error activating user. Please try again.');
    }
}

// Show user management screen
function showUserManagement() {
    switchToScreen('user-mgmt');
    loadUserList();
}

// Back to stats screen
function backToStats() {
    switchToScreen('stats');
    loadWeeklyStats();  // Refresh stats in case users were changed
}

// Load user list for management screen
async function loadUserList() {
    try {
        const response = await fetch(basePath + '/api/users');
        const users = await response.json();

        const userList = document.getElementById('userList');

        if (users.length === 0) {
            userList.innerHTML = '<li class="user-item">No users configured</li>';
            return;
        }

        userList.innerHTML = users.map(user => `
            <li class="user-item">
                <div class="user-info">
                    <div class="user-info-name">${user.name}</div>
                    <div class="user-info-note">MIDI Note: ${user.note} (${midiNoteToName(user.note)})</div>
                </div>
                <button class="delete-user-button" onclick="deleteUser(${user.id}, '${user.name}')">Delete</button>
            </li>
        `).join('');
    } catch (error) {
        console.error('Error loading user list:', error);
    }
}

// Convert MIDI note to note name
function midiNoteToName(noteNumber) {
    const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const octave = Math.floor(noteNumber / 12) - 1;
    const note = noteNames[noteNumber % 12];
    return `${note}${octave}`;
}

// Add new user
async function addUser(event) {
    event.preventDefault();

    const userName = document.getElementById('userName').value;
    const userNote = parseInt(document.getElementById('userNote').value);
    const submitButton = document.getElementById('addUserSubmit');

    submitButton.disabled = true;
    submitButton.textContent = 'Adding...';

    try {
        const response = await fetch(basePath + '/api/users/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: userName,
                trigger_note: userNote
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Clear form
            document.getElementById('addUserForm').reset();
            // Reload user list
            loadUserList();
            // Reload users for practice screen
            loadUsers();
            alert(`User "${userName}" added successfully!`);
        } else {
            alert(`Error adding user: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error adding user:', error);
        alert('Error adding user. Please try again.');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Add User';
    }
}

// Delete user
async function deleteUser(userId, userName) {
    if (!confirm(`Are you sure you want to delete user "${userName}"? Their practice data will be preserved.`)) {
        return;
    }

    try {
        const response = await fetch(basePath + `/api/users/${userId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Reload user list
            loadUserList();
            // Reload users for practice screen
            loadUsers();
            alert(`User "${userName}" has been deleted.`);
        } else {
            alert(`Error deleting user: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Error deleting user. Please try again.');
    }
}

// Start periodic stats refresh (every 5 minutes)
function startStatsRefresh() {
    if (statsRefreshInterval) {
        clearInterval(statsRefreshInterval);
    }
    statsRefreshInterval = setInterval(() => {
        loadWeeklyStats();
    }, 5 * 60 * 1000);
}

// Update status display (modified to handle screen switching)
function updateStatusAndScreen() {
    updateStatus();

    // Switch screens based on session state
    if (currentSession && currentSession.active) {
        switchToScreen('practice');
    } else {
        switchToScreen('stats');
    }
}

// Initialize KioskBoard for kiosk mode
document.addEventListener('DOMContentLoaded', async function() {
    // Check if we're in kiosk mode via URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const isKioskMode = urlParams.get('kiosk') === 'true';

    if (isKioskMode) {
        // Wait for KioskBoard to load before initializing
        try {
            await window.kioskBoardLoaded;
        } catch (error) {
            console.error('Failed to load KioskBoard:', error);
            return;
        }

        // Initialize KioskBoard with light theme and default QWERTY layout
        KioskBoard.init({
            keysArrayOfObjects: [
                {"0": "Q", "1": "W", "2": "E", "3": "R", "4": "T", "5": "Y", "6": "U", "7": "I", "8": "O", "9": "P"},
                {"0": "A", "1": "S", "2": "D", "3": "F", "4": "G", "5": "H", "6": "J", "7": "K", "8": "L"},
                {"0": "Z", "1": "X", "2": "C", "3": "V", "4": "B", "5": "N", "6": "M"}
            ],
            keysArrayOfNumbers: [
                {"0": "7", "1": "8", "2": "9"},
                {"0": "4", "1": "5", "2": "6"},
                {"0": "1", "1": "2", "2": "3"},
                {"0": "0"}
            ],
            theme: 'light',
            capsLockActive: false,
            allowRealKeyboard: true,
            allowMobileKeyboard: false,
            cssAnimations: true,
            cssAnimationsDuration: 360,
            cssAnimationsStyle: 'slide',
            keysAllowSpacebar: true,
            keysSpacebarText: 'Space',
            keysEnterText: 'Close',
            keysEnterCanClose: true,
            keysFontFamily: 'sans-serif',
            keysFontSize: '22px',
            keysFontWeight: 'normal',
            keysIconSize: '25px',
        });

        // Run KioskBoard on all inputs (keyboard type determined by data-kioskboard-type attribute)
        KioskBoard.run('.kioskboard-input');

        // Auto-close keyboard on form submission
        const addUserForm = document.getElementById('addUserForm');
        if (addUserForm) {
            addUserForm.addEventListener('submit', function() {
                // Close KioskBoard after a brief delay to allow form submission
                setTimeout(() => {
                    const activeKeyboard = document.querySelector('.kioskboard-wrapper');
                    if (activeKeyboard) {
                        activeKeyboard.remove();
                    }
                }, 100);
            });
        }
    }
});

// Show bar popover with total practice time
function showBarPopover(event, userId, dayName, minutes) {
    event.stopPropagation();

    // Remove any existing popover
    hideBarPopover();

    // Create popover element
    const popover = document.createElement('div');
    popover.className = 'bar-popover';
    popover.id = 'barPopover';

    // Format the time nicely
    const roundedMinutes = Math.round(minutes);
    let timeDisplay;
    if (roundedMinutes >= 60) {
        const hours = Math.floor(roundedMinutes / 60);
        const mins = roundedMinutes % 60;
        timeDisplay = mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    } else {
        timeDisplay = `${roundedMinutes}m`;
    }

    popover.innerHTML = `
        <div class="bar-popover-title">${userId} - ${dayName}</div>
        <div class="bar-popover-value">${timeDisplay}</div>
        <div class="bar-popover-label">total practice time</div>
    `;

    document.body.appendChild(popover);

    // Position the popover near the clicked bar
    const rect = event.currentTarget.getBoundingClientRect();
    const popoverRect = popover.getBoundingClientRect();

    let left = rect.left + (rect.width / 2) - (popoverRect.width / 2);
    let top = rect.top - popoverRect.height - 10;

    // Keep within viewport
    if (left < 10) left = 10;
    if (left + popoverRect.width > window.innerWidth - 10) {
        left = window.innerWidth - popoverRect.width - 10;
    }
    if (top < 10) {
        top = rect.bottom + 10;
    }

    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;

    // Add click listener to close popover
    setTimeout(() => {
        document.addEventListener('click', hideBarPopover);
    }, 0);
}

// Hide bar popover
function hideBarPopover() {
    const popover = document.getElementById('barPopover');
    if (popover) {
        popover.remove();
    }
    document.removeEventListener('click', hideBarPopover);
}

// Initial load
loadConfig();
loadUsers();
loadMidiStatus();
loadStatus();
loadRecentSessions();
loadWeeklyStats();
startStatsRefresh();
