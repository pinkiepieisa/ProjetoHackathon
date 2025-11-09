#!/usr/bin/env python
import asyncio
import json
import websockets
import os
import sys
from vosk import Model, KaldiRecognizer

# Auto-detect model path inside BackEnd/models/pt
BASE_DIR = os.path.dirname(__file__)
MODEL_BASE = os.path.join(BASE_DIR, 'models', 'pt')
SAMPLE_RATE = 16000

def find_model_path(base):
    if not os.path.isdir(base):
        return None
    entries = [e for e in os.listdir(base) if os.path.isdir(os.path.join(base, e))]
    # If base itself looks like a model (contains typical files), use it.
    # Look for common Vosk/Kaldi model indicators: .mdl files, .fst files, mfcc.conf, model.conf
    base_contents = set(os.listdir(base))
    has_mdl = any(name.endswith('.mdl') for name in base_contents)
    has_fst = any(name.endswith('.fst') for name in base_contents)
    if has_mdl or has_fst or 'mfcc.conf' in base_contents or 'model.conf' in base_contents:
        return base

    # Prefer a subdirectory that looks like a model (contains model indicators)
    for sub in entries:
        subpath = os.path.join(base, sub)
        try:
            contents = set(os.listdir(subpath))
        except Exception:
            contents = set()
        # Check subfolder for model indicators as well
        sub_has_mdl = any(name.endswith('.mdl') for name in contents)
        sub_has_fst = any(name.endswith('.fst') for name in contents)
        if sub_has_mdl or sub_has_fst or 'mfcc.conf' in contents or 'model.conf' in contents:
            return subpath

    # If none of the subfolders look like a model, try common model-named folders
    for sub in entries:
        if sub.lower().startswith('vosk-model') or sub.lower().startswith('model'):
            return os.path.join(base, sub)

    # Fallback: pick first subdirectory if available
    if entries:
        return os.path.join(base, entries[0])
    return None

MODEL_PATH = find_model_path(MODEL_BASE)
if not MODEL_PATH:
    print(f"ERROR: Vosk model not found. Expected files under: {MODEL_BASE}")
    print("Please download a Vosk model (e.g. vosk-model-small-pt) and extract it under BackEnd/models/pt")
    sys.exit(1)
def _to_short_path_if_windows(path):
    """Convert a long/unicode Windows path to its short (8.3) form to avoid
    potential issues in native libraries that don't handle wide unicode paths.
    If not on Windows or conversion fails, returns the original path.
    """
    try:
        if os.name == 'nt':
            # Use GetShortPathNameW to get an ASCII-safe short path
            from ctypes import create_unicode_buffer, windll
            buf = create_unicode_buffer(260)
            res = windll.kernel32.GetShortPathNameW(path, buf, 260)
            if res and buf.value:
                return buf.value
    except Exception as e:
        print('Warning: short-path conversion failed:', e)
    return path

print("Loading Vosk model from:", MODEL_PATH)
MODEL_PATH_SHORT = _to_short_path_if_windows(os.path.abspath(MODEL_PATH))
if MODEL_PATH_SHORT != os.path.abspath(MODEL_PATH):
    print("Using short path for model (Windows):", MODEL_PATH_SHORT)
try:
    model = Model(MODEL_PATH_SHORT)
except Exception as e:
    # Provide more diagnostics: list model dir contents and retry with original path
    print("Failed to create model using:", MODEL_PATH_SHORT)
    try:
        print("Directory listing:", os.listdir(MODEL_PATH))
    except Exception:
        pass
    # Final attempt with original path (may raise same error)
    model = Model(MODEL_PATH)

async def handler(websocket, path=None):
    # websockets library changed handler signature in newer versions and may pass
    # a single 'connection' argument. Support both signatures by accepting an
    # optional path and extracting it if necessary.
    if path is None:
        path = getattr(websocket, 'path', None)
    print("Client connected")
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    rec.SetWords(True)

    try:
        async for message in websocket:
            # texto de controle
            if isinstance(message, str):
                try:
                    msg = json.loads(message)
                except Exception:
                    continue
                if msg.get("command") == "reset":
                    rec.Reset()
                    await websocket.send(json.dumps({"type":"reset"}))
                continue

            # mensagem binária: PCM16 little-endian
            data = message
            if not data:
                continue
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                await websocket.send(json.dumps({"type":"final","text":res.get("text","")}))
            else:
                pres = json.loads(rec.PartialResult())
                await websocket.send(json.dumps({"type":"partial","partial":pres.get("partial","")}))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "127.0.0.1", 2700):
        print("Vosk WS server running on ws://127.0.0.1:2700")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
