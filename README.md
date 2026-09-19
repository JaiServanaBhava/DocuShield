# DocuShield — Prototype (matches the research paper)

## Run it
    python3 docushield.py                # demo (spool in ./ram_spool — warns you)
    python3 docushield.py --port 8080

Open http://localhost:8080 — the QR code on the page encodes that URL,
so a customer phone on the same Wi-Fi scans it and uploads directly.

## Make the spool TRULY volatile (the core of the paper)
Linux (tmpfs RAM disk, built into the kernel — no install, free):
    sudo mkdir /mnt/vse
    sudo mount -t tmpfs -o size=512m tmpfs /mnt/vse
    python3 docushield.py --spool /mnt/vse

Windows (free ImDisk):
    Install ImDisk -> create 512 MB RAMDisk (drive R:) ->
    python docushield.py --spool R:\docushield

/tmpfs lives in RAM: unplug the PC mid-print and every customer file
vanishes instantly. After each job, /api/print 0x00-overwrites the exact
bytes and unlinks — the anti-cold-boot step from the paper.

## "But how do we do this WITHOUT a server?" (honest answer)
You can't have *zero* software running — a browser alone cannot accept
uploads, talk to the printer, or wipe RAM. What you CAN avoid is a
CLOUD/central server. Realistic architectures, cheapest first:

1. SAME-PC KIOSK (what this prototype does — recommended for the paper):
   The tiny Python process runs on the shop PC itself, listening only on
   localhost/LAN. It is not "a server" in the cloud sense — no internet,
   no data ever leaves the building. This is the honest interpretation of
   "serverless" for your threat model.

2. COMPILED BACKGROUND AGENT (the paper's "future work"):
   Package docushield.py with PyInstaller into a Windows service that
   starts with the PC. Customer flow stays: scan QR -> upload -> pay ->
   print -> wipe. Nothing to install, nothing visible to tamper with.

3. PWA + LOCAL AGENT: browser UI (this React page, installed as a PWA)
   talks only to 127.0.0.1 agent. No internet needed after first load.

## What is intentionally faked in this prototype
- Payment: /api/pay is a stub. Real version: UPI deep-link (upi://pay?...)
  or cash at counter; a UPI QR on screen is enough for a Xerox shop.
- Print: /api/print sleeps 1.5s. Real version: send the file to the
  printer queue (CUPS `lp` on Linux, Win32 print API on Windows) or just
  open it in the default viewer on the shop PC.
- RAM detection is a crude path check — for the paper, verify tmpfs with
  `df -T /mnt/vse` (should say tmpfs) and screenshot it for Section 4.

## For your paper (Section 4 evidence)
1. Run the control test: print 50 PDFs normally, screenshot FTK Imager
   finding .SPL/.SHD in C:\Windows\System32\spool\PRINTERS.
2. Run DocuShield: screenshot `df -T` showing tmpfs, the upload step,
   and FTK/Autopsy showing the drive empty afterwards.
3. The /api/forensics endpoint automates the leftover scan.
