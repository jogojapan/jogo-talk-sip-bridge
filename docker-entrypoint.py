#!/usr/bin/env python3
"""talk-sip-bridge container entrypoint.

Starts the bridge daemon as a child, then - once the daemon's control API
is up - checks each line's registration and toggles any unregistered line
on. This makes dial-in work on a fresh/cleared state dir, where the daemon
would otherwise stay off until someone POSTs /toggle by hand. On later
restarts the daemon's own persisted-state resume (see sip_registrar's state
file) has already registered the line, so the check sees registered=true and
does nothing.

Toggling is state-aware: /toggle flips (it would deregister an already-
registered line), so we only fire it at lines that report registered=false.

Signals (SIGTERM/SIGINT) are forwarded to the daemon so it can run its
clean shutdown - hang up calls and deregister - before we exit.
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DAEMON = [sys.executable, "-u", "/opt/talk-sip-bridge/daemon.py"]

# Confirmed by default: turns itself on to make dial-in work out of the
# box. Set BRIDGE_AUTO_REGISTER=false to keep the upstream behaviour of
# leaving the line off until it is toggled explicitly.
AUTO_REGISTER = os.environ.get("BRIDGE_AUTO_REGISTER", "true").strip().lower() != "false"


def _control_base():
    bind = os.environ.get("BRIDGE_CONTROL_BIND", "127.0.0.1")
    port = os.environ.get("BRIDGE_CONTROL_PORT", "8765")
    # Connect to localhost when the daemon binds a loopback/all-interfaces
    # address; otherwise use the configured bind (e.g. a container IP the
    # daemon is reachable on from inside this host).
    host = bind if bind not in ("", "0.0.0.0", "127.0.0.1", "::1", "[::1]") else "127.0.0.1"
    return f"http://{host}:{port}"


def _request(base, path, method="GET", timeout=15):
    req = urllib.request.Request(base + path, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        # The control API's error responses (e.g. 502 from a failed toggle)
        # carry the full status JSON in the body - keep it so the caller can
        # surface registered/last_error instead of just the status code.
        body = e.read().decode() or "{}"
        data = json.loads(body) if body.strip() else {"error": str(e)}
        data["_http_status"] = e.code
        return data


def _ensure_registered(base, daemon: subprocess.Popen, wait=90):
    """Waits for the control API, then turns on any unregistered line."""
    deadline = time.time() + wait
    status = None
    while time.time() < deadline:
        if daemon.poll() is not None:
            return  # daemon exited; nothing to check
        try:
            status = _request(base, "/status")
            break
        except Exception:
            time.sleep(1)
    if status is None:
        print("[bootstrap] control API not reachable in time; "
              "skipping registration check", flush=True)
        return

    lines = status.get("lines", [])
    print("[bootstrap] startup lines: "
          + ", ".join(f"{l.get('line')}={l.get('registered')}" for l in lines), flush=True)
    for line in lines:
        line_id = line.get("line")
        if line.get("registered"):
            continue
        qid = urllib.parse.quote(line_id)
        print(f"[bootstrap] line {line_id!r} not registered - toggling on", flush=True)
        try:
            resp = _request(base, f"/toggle?line={qid}", "POST")
            after = next((l for l in resp.get("lines", []) if l.get("line") == line_id), resp)
            print(f"[bootstrap] line {line_id!r} after toggle: "
                  f"registered={after.get('registered')} "
                  f"last_error={after.get('last_error')}", flush=True)
        except Exception as e:
            print(f"[bootstrap] toggle {line_id!r} failed: {e!r}", flush=True)


def main():
    base = _control_base()
    prop = subprocess.Popen(DAEMON)

    def _forward(signum, frame):
        if prop.poll() is None:
            prop.send_signal(signum)

    signal.signal(signal.SIGTERM, _forward)
    signal.signal(signal.SIGINT, _forward)

    try:
        if AUTO_REGISTER:
            _ensure_registered(base, prop)
        else:
            print("[bootstrap] BRIDGE_AUTO_REGISTER=false - "
                  "leaving registration to the operator", flush=True)
    except Exception as e:
        print(f"[bootstrap] registration check failed: {e!r}", flush=True)

    rc = prop.wait()
    sys.exit(rc)


if __name__ == "__main__":
    main()