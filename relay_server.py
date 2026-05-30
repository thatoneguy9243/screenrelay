"""
relay_server.py
---------------
Tiny cloud relay. Python pushes frames here, Roblox polls here.
Deploy free on Railway: https://railway.app

Endpoints:
  POST /push          ← Python pushes raw RGBA + width/height headers
  GET  /frame/raw     ← Roblox polls this (raw RGBA bytes)
  GET  /frame/meta    ← Roblox gets { width, height }
  GET  /ping          ← health check
"""

import os
import threading
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

_lock    = threading.Lock()
_frame   = None   # raw RGBA bytes
_width   = 0
_height  = 0

# Optional: shared secret so randos can't push fake frames
PUSH_SECRET = os.environ.get("PUSH_SECRET", "")

@app.route("/push", methods=["POST"])
def push():
    global _frame, _width, _height
    if PUSH_SECRET and request.headers.get("X-Secret") != PUSH_SECRET:
        return "unauthorized", 401
    w = int(request.headers.get("X-Width",  0))
    h = int(request.headers.get("X-Height", 0))
    if w == 0 or h == 0:
        return "missing dimensions", 400
    data = request.get_data()
    if len(data) != w * h * 4:
        return f"bad size: got {len(data)}, expected {w*h*4}", 400
    with _lock:
        _frame  = data
        _width  = w
        _height = h
    return "ok"

@app.route("/frame/raw")
def frame_raw():
    with _lock:
        frame, w, h = _frame, _width, _height
    if frame is None:
        return "no frame yet", 503
    resp = Response(frame, mimetype="application/octet-stream")
    resp.headers["X-Width"]  = str(w)
    resp.headers["X-Height"] = str(h)
    return resp

@app.route("/frame/meta")
def frame_meta():
    with _lock:
        w, h = _width, _height
    return jsonify({"width": w, "height": h})

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Relay running on port {port}")
    app.run(host="0.0.0.0", port=port)
