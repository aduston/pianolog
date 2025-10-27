# Test 1

1. Turn the piano off
2. Turn the piano back on. At this point we expect `lsusb` to not see the CA49 due to the USB issue described in USAGE.md.
3. At this point the main webpage (served from web_server.py) should say that the USB is disconnected, and show a retry button. A note should say that the solution is to unplug and re-plug in the USB cable.
4. After the USB cable is unplugged and re-plugged in, we expect `lsusb` to show the CA49. The web page should either refresh on its own, or hitting the "retry" button should show that it's now connected again.

# Test 2

1. A person walks up the piano. More than 1 minute has elapsed since the last session ended. The person hits a key.
2. The C-E-G sequence plays.
3. The user hits "C" (currently mapped to "Dad").
4. The web page now shows there is an active session, and that "Dad" is practicing. The web page allows Dad to end his session, or switch to Alex.

# Test 3

1. A person walks up the piano and hits a key.
2. The C-E-G sequence plays.
3. The user hits "C" (currently mapped to "Dad").
4. The web page now shows there is an active session, and that "Dad" is practicing. The web page allows Dad to end his session, or switch to Alex.
5. The person stops playing before 30 seconds is up.
6. This does not show up in "Recent Sessions" as a session, or count toward Dad's time for the week.
7. As soon as a timeout elapses, the webpage again shows there's no active session.

# Test 4

1. A person views the webpage when nobody is practicing.
2. The webpage says "No active session". It does not say "No active session (unknown)", and it doesn't have a button to indicate who's practicing.