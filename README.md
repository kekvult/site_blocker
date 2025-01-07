Overview
site_blocker.py is a Python script designed to block distracting websites by modifying the Windows hosts file. The script provides a web-based interface to control blocking and includes features like unblocking YouTube temporarily. It automatically restores the original hosts file when terminated and limits the number of unblocks to help maintain focus.

Features
Automatic Elevation: Automatically requests admin privileges (UAC prompt) when needed.
Site Blocking: Blocks an extended list of distracting websites (e.g., YouTube, Reddit, Instagram, etc.).
Temporary Unblocking: Unblocks YouTube for a configurable duration (default: 30 minutes) and re-blocks it afterward.
Web Interface: Access the control panel via http://localhost:8080/.
Backup and Restore: Backs up the original hosts file and restores it on shutdown.
DNS Flushing: Ensures immediate application of changes by flushing the DNS cache.
Unblock Limits: Limits YouTube unblocking to 2 times per 10-hour window.
Requirements
Python 3.6+
Flask library:
bash
Code kopieren
pip install flask
Usage
Run the Script:

bash
Code kopieren
pythonw site_blocker.py
The script will prompt for admin privileges (UAC popup) if not already elevated.
A web interface will open automatically at http://localhost:8080/.
Control Blocking:

Blocking starts automatically on script launch.
To temporarily unblock YouTube, click the "Unblock YouTube for 30 minutes" button in the web interface.
Stop the Script:

When the script is terminated, the original hosts file is restored automatically.
Notes
Run the script as Administrator to allow modifications to the hosts file.
If any issues arise, verify the script's DNS flushing or check the hosts file directly.
Contribution
Feel free to fork the repository, open issues, or submit pull requests to improve the script.
