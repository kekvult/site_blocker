# Site Blocker

## Overview
`freeme.py` is a Python script designed to block distracting websites by modifying the Windows `hosts` file. The script provides a web-based interface to control blocking and includes features like unblocking YouTube temporarily. It automatically restores the original `hosts` file when terminated and limits the number of unblocks to help maintain focus.

## Install and Run
Run the following command in **PowerShell** or **Command Prompt** to install dependencies, clone the repository, and run the script:

```powershell
winget install --id Python.Python.3 -e --source winget; winget install --id Git.Git -e --source winget; python -m pip install flask --quiet; git clone https://github.com/kekvult/site_blocker.git; cd site_blocker; pythonw site_blocker.py

