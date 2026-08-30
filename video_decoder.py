#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeTheBird — Video decoder (separate process).

Decodes X/Twitter HLS (.m3u8) streams using a local ffmpeg and plays them
in a small Qt player window. Keeps freethebird.py clean of any decoding.

Usage:
    python video_decoder.py <video_url> [--ffmpeg PATH] [--save PATH]

The main app (freethebird.py) launches this script with the captured
video.twimg.com m3u8/mp4 URL.
"""

import os
import re
import sys
import json
import shutil
import argparse
import subprocess
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from PyQt6.QtCore import QUrl, Qt
    from PyQt6.QtGui import QDesktopServices, QAction, QKeySequence, QShortcut
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QMessageBox, QFileDialog,
        QSlider, QMenu, QToolButton,
    )
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except Exception:
    HAS_MULTIMEDIA = False

CONFIG_PATH = os.path.expanduser("~/.config/freethebird/config.json")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def find_ffmpeg(cli_path):
    """ffmpeg path: CLI arg > config > PATH."""
    for p in (cli_path, load_config().get("ffmpeg_path", "")):
        if p and os.path.isfile(p):
            return p
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or "ffmpeg"


def decode(url, ffmpeg, out, on_status=None):
    """Download/transcode url (m3u8 or mp4) to a local mp4 using ffmpeg.
    Tries: copy remux -> libx264/aac transcode -> plain copy -> plain transcode.
    Returns (ok, error_tail)."""
    hdr = (
        "Referer: https://x.com\r\n"
        "Origin: https://x.com\r\n"
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Chrome/133.0.0.0 Safari/537.36\r\n"
    )
    base = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-headers", hdr]
    attempts = [
        base + ["-i", url, "-c", "copy", "-movflags", "+faststart", out],
        base + ["-i", url, "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac", "-movflags", "+faststart", out],
        [ffmpeg, "-y", "-i", url, "-c", "copy", out],
        [ffmpeg, "-y", "-i", url, "-c:v", "libx264", "-preset", "veryfast",
         "-c:a", "aac", out],
    ]
    last_err = ""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for i, cmd in enumerate(attempts, 1):
        if on_status:
            on_status(f"Decoding with ffmpeg ({i}/{len(attempts)})…")
        try:
            r = subprocess.run(cmd, timeout=180, check=False,
                               capture_output=True, text=True, creationflags=flags)
            last_err = (r.stderr or "")[-500:]
        except subprocess.TimeoutExpired:
            last_err = "timeout"
        except Exception as e:
            last_err = str(e)
        if os.path.exists(out) and os.path.getsize(out) > 8000:
            return True, ""
    return False, last_err


def output_path(url):
    """Temp mp4 path derived from url (stable per URL)."""
    base = os.path.basename(urllib.parse.urlparse(url).path) or "video"
    base = re.sub(r"[^\w.\-]", "_", base)
    if not base.lower().endswith((".mp4", ".mkv", ".webm")):
        base += ".mp4"
    return os.path.join(tempfile.gettempdir(),
                        f"freethebird_{abs(hash(url)) % 100000000}{os.path.splitext(base)[1]}")


def stream_headers(url):
    return (
        "Referer: https://x.com\r\n"
        "Origin: https://x.com\r\n"
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Chrome/133.0.0.0 Safari/537.36\r\n"
    )


def serve(url, ffmpeg, port):
    """Decode url (m3u8) with ffmpeg into a fragmented MP4 file, then serve that
    file over HTTP on 127.0.0.1:port with byte-range support so the browser's
    <video> can play it natively as it grows."""
    out = output_path(url)
    if os.path.exists(out):
        try:
            os.remove(out)
        except Exception:
            pass
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    hdr = stream_headers(url)

    def start_ffmpeg(copy=True):
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-headers", hdr,
               "-i", url]
        if copy:
            cmd += ["-c", "copy"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"]
        cmd += ["-movflags", "frag_keyframe+empty_moov", "-f", "mp4", out]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=flags)

    proc = start_ffmpeg(copy=True)
    # if copy can't produce output, fall back to transcode
    import time
    waited = 0
    while waited < 12:
        time.sleep(2)
        waited += 2
        if os.path.exists(out) and os.path.getsize(out) > 8000:
            break
        if proc.poll() is not None:  # ffmpeg exited → copy failed
            try:
                proc.kill()
            except Exception:
                pass
            proc = start_ffmpeg(copy=False)
            waited = 0
            break
    if not (os.path.exists(out) and os.path.getsize(out) > 8000):
        # give transcode a chance if we just switched
        time.sleep(3)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _serve(self):
            if not os.path.exists(out) or os.path.getsize(out) < 1000:
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            size = os.path.getsize(out)
            rng = self.headers.get("Range")
            start, end = 0, size - 1
            partial = False
            if rng:
                m = re.match(r"bytes=(\d*)-(\d*)", rng)
                if m:
                    partial = True
                    start = int(m.group(1) or 0)
                    req_end = m.group(2)
                    end = int(req_end) if req_end else size - 1
                    end = min(end, size - 1)
            if start > end:
                start = end
            length = end - start + 1
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Access-Control-Allow-Origin", "*")
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(length))
            self.end_headers()
            try:
                with open(out, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except Exception:
                            break
                        remaining -= len(chunk)
            except Exception:
                pass

        def do_GET(self):
            self._serve()

        def do_HEAD(self):
            if not os.path.exists(out):
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            size = os.path.getsize(out)
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(size))
            self.end_headers()

    try:
        srv = HTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print(f"FreeTheBird: could not bind port {port}: {e}", file=sys.stderr)
        try:
            proc.kill()
        except Exception:
            pass
        sys.exit(3)
    print(f"FreeTheBird: streaming decoded video on http://127.0.0.1:{port}/stream.mp4")
    try:
        srv.serve_forever()
    finally:
        srv.server_close()
        try:
            proc.kill()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="FreeTheBird video decoder")
    ap.add_argument("url", help="X video URL (m3u8 or mp4)")
    ap.add_argument("--ffmpeg", default=None, help="path to ffmpeg binary")
    ap.add_argument("--save", default=None, help="also save decoded mp4 to this path")
    ap.add_argument("--serve", action="store_true",
                    help="serve decoded stream over local HTTP back to the browser")
    ap.add_argument("--port", type=int, default=0,
                    help="local port for --serve")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg(args.ffmpeg)
    has_ff = bool(shutil.which(ffmpeg) or os.path.isfile(ffmpeg))
    if not has_ff:
        print(f"FreeTheBird: ffmpeg not found ({ffmpeg})", file=sys.stderr)
        if HAS_MULTIMEDIA and not args.serve:
            app = QApplication(sys.argv)
            QMessageBox.information(
                None, "FreeTheBird Video",
                "ffmpeg not found.\n\n"
                "X serves videos as HLS (.m3u8), which needs ffmpeg to decode.\n"
                "Install ffmpeg and put it on PATH, or pass --ffmpeg <path>.",
            )
        sys.exit(2)

    if args.serve:
        # streaming mode: decode and serve back to the browser
        serve(args.url, ffmpeg, args.port)
        sys.exit(0)

    out = args.save or output_path(args.url)

    if not HAS_MULTIMEDIA:
        # No QtMultimedia: decode then open the mp4 in the system player.
        def _status(s):
            print("FreeTheBird:", s)
        ok, err = decode(args.url, ffmpeg, out, on_status=_status)
        if ok:
            print("FreeTheBird: saved", out)
            subprocess.Popen(["cmd", "/c", "start", "", out])
        else:
            print("FreeTheBird: decode failed:\n" + err, file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName("FreeTheBird Video")

    dlg = QDialog()
    dlg.setWindowTitle("FreeTheBird Video")
    dlg.resize(900, 600)
    lay = QVBoxLayout(dlg)

    status = QLabel("Decoding video via ffmpeg…")
    status.setStyleSheet("color:#888; font-size:12px;")
    status.setWordWrap(True)
    lay.addWidget(status)

    video = QVideoWidget()
    video.setStyleSheet("background:#000;")
    video.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    lay.addWidget(video, stretch=1)

    # --- Twitter-like controls ---
    # seek bar (thin like X)
    pos_slider = QSlider(Qt.Orientation.Horizontal)
    pos_slider.setRange(0, 0)
    pos_slider.setStyleSheet(
        "QSlider::groove:horizontal{height:3px;background:#2f3336;border-radius:1px}"
        "QSlider::sub-page:horizontal{background:#1da1f2;border-radius:1px}"
        "QSlider::handle:horizontal{width:10px;height:10px;background:#fff;border-radius:5px;margin:-4px 0}"
    )
    lay.addWidget(pos_slider)

    # controls row: [play/pause] [time] --- [vol icon+slider] [gear(speed)] [fullscreen]
    ctrl_row = QHBoxLayout()
    ctrl_row.setContentsMargins(2, 2, 2, 2)
    play_btn = QToolButton()
    play_btn.setText("⏸")
    play_btn.setToolTip("Play/Pause (Space)")
    play_btn.setFixedSize(32, 28)
    play_btn.setStyleSheet("QToolButton{background:#15202b;color:#fff;border:1px solid #333;border-radius:14px;font-size:13px}")

    time_label = QLabel("0:00 / 0:00")
    time_label.setStyleSheet("color:#e7e9ea; font-size:12px; min-width:110px;")
    time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    vol_btn = QToolButton()
    vol_btn.setText("🔊")
    vol_btn.setToolTip("Mute (M)")
    vol_btn.setFixedSize(28, 28)
    vol_btn.setStyleSheet("QToolButton{background:transparent;color:#e7e9ea;border:0;font-size:14px}")
    vol_slider = QSlider(Qt.Orientation.Horizontal)
    vol_slider.setRange(0, 100)
    vol_slider.setValue(50)
    vol_slider.setFixedWidth(90)
    vol_slider.setToolTip("Volume")
    vol_slider.setStyleSheet("QSlider::groove:horizontal{height:3px;background:#333} QSlider::handle:horizontal{width:8px;background:#fff}")

    # settings gear -> speed menu (like X's Playback speed)
    settings_btn = QToolButton()
    settings_btn.setText("⚙")
    settings_btn.setToolTip("Playback speed")
    settings_btn.setFixedSize(28, 28)
    settings_btn.setStyleSheet("QToolButton{background:transparent;color:#e7e9ea;border:0;font-size:14px}")
    settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    speed_menu = QMenu(settings_btn)
    speed_menu.setStyleSheet(
        "QMenu{background:#15202b;color:#e7e9ea;border:1px solid #2f3336;padding:4px}"
        "QMenu::item:selected{background:#1da1f2}"
        "QMenu::separator{height:1px;background:#2f3336;margin:4px 0}"
    )
    speed_menu.addAction("Playback speed", lambda: None).setEnabled(False)
    speed_menu.addSeparator()
    speed_actions = []
    for s in ["0.25x", "0.5x", "0.75x", "1x", "1.25x", "1.5x", "1.75x", "2x"]:
        act = speed_menu.addAction(s)
        act.setCheckable(True)
        act.setChecked(s == "1x")
        speed_actions.append(act)
    settings_btn.setMenu(speed_menu)

    fs_btn = QToolButton()
    fs_btn.setText("⛶")
    fs_btn.setToolTip("Fullscreen (F)")
    fs_btn.setFixedSize(28, 28)
    fs_btn.setStyleSheet("QToolButton{background:transparent;color:#e7e9ea;border:0;font-size:15px}")

    ctrl_row.addWidget(play_btn)
    ctrl_row.addWidget(time_label)
    ctrl_row.addStretch(1)
    ctrl_row.addWidget(vol_btn)
    ctrl_row.addWidget(vol_slider)
    ctrl_row.addWidget(settings_btn)
    ctrl_row.addWidget(fs_btn)
    lay.addLayout(ctrl_row)

    # bottom row: Close / Open externally
    bottom_row = QHBoxLayout()
    close_btn = QPushButton("Close")
    ext_btn = QPushButton("Open in browser")
    bottom_row.addWidget(close_btn)
    bottom_row.addWidget(ext_btn)
    lay.addLayout(bottom_row)

    player = QMediaPlayer(dlg)
    audio = QAudioOutput(dlg)
    player.setAudioOutput(audio)
    player.setVideoOutput(video)
    audio.setVolume(0.5)

    def set_status(s):
        status.setText(s)

    def fmt(ms):
        s = int(ms / 1000)
        m, sec = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

    prev_vol = {"v": 50}

    def toggle_play():
        if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            player.pause()
        else:
            player.play()

    def toggle_mute():
        if audio.volume() > 0:
            prev_vol["v"] = vol_slider.value()
            vol_slider.setValue(0)
        else:
            vol_slider.setValue(prev_vol["v"] or 50)

    def toggle_fs():
        if dlg.isFullScreen():
            dlg.showNormal()
        else:
            dlg.showFullScreen()

    # wire controls
    def on_state_changed(state):
        play_btn.setText("⏸" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")
    player.playbackStateChanged.connect(on_state_changed)

    play_btn.clicked.connect(toggle_play)
    vol_btn.clicked.connect(toggle_mute)
    fs_btn.clicked.connect(toggle_fs)

    # click on video toggles play (Twitter-like)
    video.mousePressEvent = lambda e: toggle_play()

    pos_slider.sliderMoved.connect(lambda v: player.setPosition(v))
    player.positionChanged.connect(lambda v: (pos_slider.setValue(v), time_label.setText(f"{fmt(v)} / {fmt(player.duration())}")) if not pos_slider.isSliderDown() else None)
    player.durationChanged.connect(lambda d: (pos_slider.setRange(0, d), time_label.setText(f"{fmt(player.position())} / {fmt(d)}")))
    vol_slider.valueChanged.connect(lambda v: (audio.setVolume(v / 100), vol_btn.setText("🔇" if v == 0 else "🔊")))
    for act in speed_actions:
        act.triggered.connect(lambda checked, a=act: (player.setPlaybackRate(float(a.text().replace("x", ""))), [x.setChecked(x is a) for x in speed_actions]))

    # shortcuts: Space pause, M mute, F fullscreen
    QShortcut(QKeySequence("Space"), dlg, toggle_play)
    QShortcut(QKeySequence("M"), dlg, toggle_mute)
    QShortcut(QKeySequence("F"), dlg, toggle_fs)
    QShortcut(QKeySequence("Escape"), dlg, lambda: dlg.showNormal() if dlg.isFullScreen() else None)
    # double-click fullscreen
    orig_dbl = video.mouseDoubleClickEvent
    video.mouseDoubleClickEvent = lambda e: toggle_fs()

    ok, err = decode(args.url, ffmpeg, out, on_status=set_status)
    if not ok:
        QMessageBox.critical(
            dlg, "Decode failed",
            "ffmpeg could not decode this video.\n\n"
            "Common causes:\n"
            "- X session expired (re-import cookies / open the tweet first)\n"
            "- ffmpeg build missing HLS/h264 support\n"
            "- URL expired\n\n" + (err or ""),
        )
        dlg.reject()
    else:
        set_status("Playing…")
        player.setSource(QUrl.fromLocalFile(out))
        player.play()

    close_btn.clicked.connect(dlg.accept)
    ext_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(args.url)))

    dlg.exec()


if __name__ == "__main__":
    main()
