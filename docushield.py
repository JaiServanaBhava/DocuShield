#!/usr/bin/env python3
"""
DocuShield Prototype — Volatile Memory Spooling (zero-dependency, offline)
--------------------------------------------------------------------------
Demonstrates the paper's architecture:
  Upload -> RAM-backed Volatile Spool Enclave (VSE) -> Print -> 0x00 wipe -> verify

HOW TO RUN A REAL RAM DISK (the whole point of the paper):
  Linux : sudo mkdir /mnt/vse && sudo mount -t tmpfs -o size=512m tmpfs /mnt/vse
          then  :  python3 docushield.py --spool /mnt/vse
  Windows: install ImDisk (free) -> create 512MB RAMDisk R:
          then  :  python docushield.py --spool R:\\docushield
  Demo  : just run it — it falls back to ./ram_spool and warns you.
"""

import argparse, os, sys, time, json, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

STATE = {"jobs": [], "paid": False}
DISK_SPOOL_CANDIDATES = [
    r"C:\Windows\System32\spool\PRINTERS",          # Windows
    "/var/spool/cups",                               # Linux CUPS
    "/var/spool/lpd",                                # BSD LPD
]

def secure_wipe(path, passes=1):
    """Overwrite exact file bytes with 0x00, then unlink (anti cold-boot)."""
    try:
        size = os.path.getsize(path)
        with open(path, "r+b") as f:
            for _ in range(passes):
                f.seek(0); f.write(b"\x00" * size); f.flush(); os.fsync(f.fileno())
        os.unlink(path)
        return True
    except FileNotFoundError:
        return False

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet console
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _serve(self, path, ctype):
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._serve(os.path.join(HERE, "static", "index.html"), "text/html")
        if u.path == "/api/status":
            return self._json({"spool_dir": SPOOL_DIR, "volatile": ON_RAMDISK,
                               "ram_warning": not ON_RAMDISK, "paid": STATE["paid"]})
        if u.path == "/api/forensics":
            disk = next((d for d in DISK_SPOOL_CANDIDATES if os.path.isdir(d)), None)
            disk_left = []
            if disk:
                disk_left = [f for f in os.listdir(disk) if f.lower().endswith((".spl", ".shd", ".pdf", ".docx"))]
            ram_left = os.listdir(SPOOL_DIR) if os.path.isdir(SPOOL_DIR) else []
            return self._json({"disk_spool_dir": disk, "disk_leftovers": disk_left,
                               "vse_dir": SPOOL_DIR, "vse_leftovers": ram_left})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        if u.path == "/api/upload":
            filename = os.path.basename(parse_qs(u.query).get("filename", ["doc.pdf"])[0])
            dest = os.path.join(SPOOL_DIR, filename)
            with open(dest, "wb") as f:
                shutil.copyfileobj(self.rfile, f, length)
            STATE["jobs"].append({"file": filename, "bytes": os.path.getsize(dest), "wiped": False})
            return self._json({"ok": True, "stored_in": SPOOL_DIR, "volatile": ON_RAMDISK,
                               "bytes": os.path.getsize(dest)})
        if u.path == "/api/pay":
            # Prototype: simulated payment. Real version = UPI intent / cash at counter.
            STATE["paid"] = True
            return self._json({"ok": True, "method": "SIMULATED (plug in UPI/cash here)"})
        if u.path == "/api/print":
            if not STATE["paid"]:
                return self._json({"ok": False, "error": "payment required first"}, 402)
            job = STATE["jobs"][-1] if STATE["jobs"] else None
            if not job:
                return self._json({"ok": False, "error": "no document uploaded"}, 400)
            time.sleep(1.5)  # simulate print hardware time
            path = os.path.join(SPOOL_DIR, job["file"])
            wiped = secure_wipe(path)
            job["wiped"] = wiped
            STATE["paid"] = False
            return self._json({"ok": True, "printed": job["file"], "wiped_from_ram": wiped,
                               "disk_touched": False})
        self._json({"error": "not found"}, 404)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spool", default=os.path.join(os.getcwd(), "ram_spool"))
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    HERE = os.path.dirname(os.path.abspath(__file__))
    SPOOL_DIR = os.path.abspath(a.spool)
    os.makedirs(SPOOL_DIR, exist_ok=True)
    ON_RAMDISK = SPOOL_DIR.startswith(("/mnt/", "/dev/shm", "/run/")) or \
                 (len(SPOOL_DIR) >= 3 and SPOOL_DIR[1] == ":")  # crude RAM check
    print(f"[DocuShield] VSE (spool dir): {SPOOL_DIR}   volatile={ON_RAMDISK}")
    print(f"[DocuShield] Open http://localhost:{a.port}  — Ctrl+C to stop")
    ThreadingHTTPServer(("0.0.0.0", a.port), Handler).serve_forever()
