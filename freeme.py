#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

"""
Simplified Flask-based Windows site blocker.
- Automatically elevates to administrator using a UAC prompt.
- Blocks distracting sites by adding entries to the hosts file.
- Unblocks YouTube for 30 minutes by removing lines matching 'youtube.com'.
- Re-blocks YouTube after 30 minutes.
- Backs up and restores hosts on shutdown.
- 2 unblocks allowed per 10-hour window.

Requires:
  pip install flask

Usage:
  pythonw simple_blocker.py
  (UAC prompt will appear if not already elevated)
"""

import os
import sys
import time
import threading
import signal
import ctypes
import webbrowser
import atexit
import tempfile

from datetime import datetime, timedelta
from flask import Flask, Response, request

##############################################################################
# 1) Check / request admin privileges (UAC)
##############################################################################

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

# If not admin, re-launch with admin privileges
if not is_admin():
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    # "runas" -> triggers UAC
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)

##############################################################################
# 2) Configuration
##############################################################################

app = Flask(__name__)

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

BLOCKED_DOMAINS = [
    "youtube.com", "www.youtube.com",
    "reddit.com", "www.reddit.com",
    "4chan.org", "www.4chan.org",
    "steampowered.com", "store.steampowered.com",
    "instagram.com", "www.instagram.com",
    "x.com", "www.x.com",
    "twitter.com", "www.twitter.com",
    "facebook.com", "www.facebook.com",
    "tiktok.com", "www.tiktok.com",
    "netflix.com", "www.netflix.com",
    "hulu.com", "www.hulu.com",
    "amazon.com", "www.amazon.com",
    "ebay.com", "www.ebay.com",
    "pinterest.com", "www.pinterest.com",
    "snapchat.com", "www.snapchat.com",
    "tumblr.com", "www.tumblr.com"
]

# Unblock logic
MAX_UNBLOCKS_IN_10H = 2
UNBLOCK_DURATION_MINUTES = 30
UNBLOCK_WINDOW_HOURS = 10

# Global in-memory state
original_hosts_content = ""
youtube_blocked = True
unblock_window_active = False
unblocks_used_in_window = 0
unblock_window_start = datetime.now()

##############################################################################
# 3) Utility functions
##############################################################################

def hide_console():
    """Hides the console window, if any."""
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)

def ignore_ctrl_c():
    """Ignore Ctrl+C signals (if console is present)."""
    signal.signal(signal.SIGINT, lambda sig, frame: None)

def flush_dns_cache():
    """Flush DNS cache after modifying hosts file."""
    os.system("ipconfig /flushdns")

def read_hosts() -> str:
    """Return the entire contents of the hosts file."""
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Unable to read hosts file: {e}")
        return ""

def write_hosts(contents: str):
    """Overwrite the hosts file with given contents, then flush DNS."""
    try:
        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.write(contents)
    except Exception as e:
        print(f"[ERROR] Unable to write hosts file: {e}")
    flush_dns_cache()

def backup_original_hosts():
    """Backup the original hosts file content to memory and a temp file."""
    global original_hosts_content
    original_hosts_content = read_hosts() or "# (Hosts file empty/unreadable)\n"

    backup_path = os.path.join(tempfile.gettempdir(), f"hosts_backup_{int(time.time())}.bak")
    try:
        with open(backup_path, "w", encoding="utf-8") as bf:
            bf.write(original_hosts_content)
        print(f"[INFO] Original hosts backed up to {backup_path}")
    except Exception as e:
        print(f"[WARN] Could not write backup file: {e}")

def restore_original_hosts():
    """Restore hosts file to original content if available."""
    global original_hosts_content
    if original_hosts_content:
        print("[INFO] Restoring original hosts file...")
        write_hosts(original_hosts_content)

def block_sites(domains):
    """Add lines for each domain (if missing) and flush DNS."""
    current_content = read_hosts() or "# (Hosts file empty)\n"
    lines = current_content.splitlines()
    changed = False
    line_set = set(lines)

    for domain in domains:
        block_line = f"127.0.0.1 {domain}"
        if block_line not in line_set:
            lines.append(block_line)
            line_set.add(block_line)
            changed = True

    if changed:
        new_content = "\n".join(lines) + "\n"
        write_hosts(new_content)

def unblock_youtube_entries():
    """Remove lines containing 'youtube.com' once."""
    current_content = read_hosts()
    if not current_content:
        return
    lines = current_content.splitlines()
    changed = False
    new_lines = []
    for line in lines:
        # If line references youtube.com, skip it
        if "youtube.com" in line.lower():
            changed = True
            continue
        new_lines.append(line)
    if changed:
        write_hosts("\n".join(new_lines) + "\n")

def schedule_reblock_youtube():
    """Spawn a thread that waits 30 min, then re-blocks YouTube."""
    def worker():
        time.sleep(UNBLOCK_DURATION_MINUTES * 60)  # e.g. 30 * 60
        block_sites(["youtube.com", "www.youtube.com"])
        global youtube_blocked
        youtube_blocked = True
        print("[INFO] YouTube re-blocked automatically after 30 minutes.")

    t = threading.Thread(target=worker, daemon=True)
    t.start()

##############################################################################
# 4) Flask Routes
##############################################################################

app = Flask(__name__)

def _layout(body: str) -> str:
    return f"""HTTP/1.1 200 OK\r
Content-Type: text/html\r
\r
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Simple Blocker</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background: #f0f0f0;
      margin: 0; padding: 0;
    }}
    header {{
      background-color: #333;
      color: #fff;
      padding: 1em;
      text-align: center;
    }}
    main {{
      margin: 2em auto;
      padding: 2em;
      max-width: 600px;
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }}
    button {{
      padding: 0.6em 1.2em;
      font-size: 1em;
      background-color: #007BFF;
      color: #fff;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }}
    button:hover {{
      background-color: #0056b3;
    }}
    p {{
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <header><h1>Simple Blocker</h1></header>
  <main>
    {body}
  </main>
</body>
</html>
"""

@app.route("/")
def home():
    global unblocks_used_in_window

    items = []
    items.append("<h2>Distracting Sites Blocked</h2>")
    items.append("<p>Sites like YouTube, Reddit, 4chan, etc. have been added to the hosts file.</p>")
    items.append(f"<p>You have used <strong>{unblocks_used_in_window}</strong> / <strong>{MAX_UNBLOCKS_IN_10H}</strong> YouTube unblocks in this 10-hour window.</p>")
    if unblocks_used_in_window < MAX_UNBLOCKS_IN_10H:
        items.append('''
            <form action="/unblock_youtube" method="post">
              <button type="submit">Unblock YouTube for 30 minutes</button>
            </form>
        ''')
    else:
        items.append("<p><strong>You have reached the limit of YouTube unblocks in this 10-hour window.</strong></p>")

    html = _layout("\n".join(items))
    return html

@app.route("/unblock_youtube", methods=["POST"])
def do_unblock():
    global youtube_blocked
    global unblock_window_active
    global unblocks_used_in_window
    global unblock_window_start

    now = datetime.now()
    # Start or continue the 10-hour window
    if not unblock_window_active:
        unblock_window_active = True
        unblock_window_start = now
        unblocks_used_in_window = 0

    # If 10 hours have passed, reset
    if now - unblock_window_start > timedelta(hours=UNBLOCK_WINDOW_HOURS):
        unblock_window_start = now
        unblocks_used_in_window = 0

    if unblocks_used_in_window < MAX_UNBLOCKS_IN_10H:
        # Unblock by removing lines
        unblock_youtube_entries()
        youtube_blocked = False
        unblocks_used_in_window += 1

        # After 30 min, re-block
        schedule_reblock_youtube()

        msg = """
        <h2>YouTube unblocked for 30 minutes!</h2>
        <p>We'll remove hosts entries for youtube.com. After 30 minutes, they're added back automatically.</p>
        <p><a href="/">Return to main page</a></p>
        """
    else:
        msg = """
        <h2>Unblock limit reached!</h2>
        <p>You have reached the limit of unblocks in this 10-hour window.</p>
        <p><a href="/">Return to main page</a></p>
        """
    return _layout(msg)

##############################################################################
# 5) Cleanup on Exit
##############################################################################

def on_exit():
    restore_original_hosts()

def windows_event_handler(dw_ctrl_type):
    # On shutdown, close event, etc., restore the hosts
    if dw_ctrl_type in (0, 1, 2, 5, 6):
        restore_original_hosts()
    return True

##############################################################################
# MAIN
##############################################################################

def main():
    hide_console()
    ignore_ctrl_c()

    # Backup
    backup_original_hosts()

    # Register normal exit cleanup
    atexit.register(on_exit)

    # Console event handler if running in console
    if ctypes.windll.kernel32.GetConsoleWindow() != 0:
        PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        handler = PHANDLER_ROUTINE(windows_event_handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)

    # Block distracting domains
    print("[INFO] Blocking distracting sites...")
    block_sites(BLOCKED_DOMAINS)

    # Launch Flask
    url = "http://localhost:8080/"
    webbrowser.open(url)
    print(f"[INFO] Opening {url}. Starting server on port 8080...")

    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
