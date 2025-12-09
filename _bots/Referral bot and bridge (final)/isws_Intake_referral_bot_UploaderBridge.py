# isws_Intake_referral_bot_UploaderBridge.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Referral Uploader Bridge
- Place this file as: referral_uploader_bot.py
- Put it in the SAME FOLDER as your base bot AND your new uploader app.
- It will try to launch a packaged EXE first, then a Python script.
- Completely detached (does not block your base bot).
"""

import os, sys, subprocess, time, traceback

# Candidate filenames for your new uploader app (edit if you use a different name)
EXE_CANDIDATES = [
    "ReferralFormUploader.exe",
    "ReferralUploaderBot.exe",
    "Uploader.exe",
]
PY_CANDIDATES = [
    "ReferralFormUploader.py",
    "ReferralUploaderBot_main.py",
    "uploader_main.py",
]

LOG_NAME = "ReferralUploaderBridge.log"


def _here():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def _write_log(msg: str):
    try:
        base = _here()
        p = os.path.join(base, LOG_NAME)
        ts = time.strftime("[%Y-%m-%d %H:%M:%S] ")
        with open(p, "a", encoding="utf-8") as f:
            f.write(ts + msg.rstrip() + "\n")
    except Exception:
        pass


def _launch_exe(path: str):
    # Launch EXE detached so this bridge exits immediately
    _write_log(f"Launching EXE: {path}")
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        subprocess.Popen([path], cwd=os.path.dirname(path),
                         creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                         close_fds=True)
    else:
        subprocess.Popen([path], cwd=os.path.dirname(path),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)


def _launch_py(path: str):
    # Launch .py via the same Python the base bot is using, detached
    _write_log(f"Launching PY: {path}")
    py = sys.executable or "python"
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        subprocess.Popen([py, path], cwd=os.path.dirname(path),
                         creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                         close_fds=True)
    else:
        subprocess.Popen([py, path], cwd=os.path.dirname(path),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)


def main():
    base = _here()
    _write_log("Bridge invoked.")

    # 1) Prefer an EXE (fastest path for end users)
    for name in EXE_CANDIDATES:
        p = os.path.join(base, name)
        if os.path.isfile(p):
            try:
                _launch_exe(p)
                _write_log(f"SUCCESS: started {name}")
                return
            except Exception as e:
                _write_log(f"ERROR launching {name}: {e}\n{traceback.format_exc()}")

    # 2) Fallback to a Python entrypoint
    for name in PY_CANDIDATES:
        p = os.path.join(base, name)
        if os.path.isfile(p):
            try:
                _launch_py(p)
                _write_log(f"SUCCESS: started {name}")
                return
            except Exception as e:
                _write_log(f"ERROR launching {name}: {e}\n{traceback.format_exc()}")

    # 3) Nothing found — write guidance for you
    msg = ("No uploader app found. Place one of these next to this file:\n"
           f"  EXE: {', '.join(EXE_CANDIDATES)}\n"
           f"  PY : {', '.join(PY_CANDIDATES)}\n")
    _write_log(msg)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _write_log(f"FATAL: {e}\n{traceback.format_exc()}")
