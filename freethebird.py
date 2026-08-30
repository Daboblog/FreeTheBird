#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  FreeTheBird — A privacy-first, lightweight X (Twitter) client for GNU/Linux ║
║                                                                               ║
║  Version:    1.2.0                                                              ║
║  License:    GPL v3 (GNU General Public License)                              ║
║  Author:     David Hernández (@daboblog)                                      ║
║  Website:    https://davidhernandez.es | https://daboblog.com                 ║
║  GitHub:     https://github.com/daboblog/FreeTheBird                          ║
║  X:          https://x.com/daboblog                                           ║
║  Bluesky:    https://bsky.app/profile/daboblog.bsky.social                    ║
║                                                                               ║
║  Built with PyQt6 + QtWebEngine. No Electron. No bloat. No tracking.          ║
║  Just 50KB of Python that respects your freedom and your RAM.                 ║
║                                                                               ║
║  Dependencies:                                                                ║
║    sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine python3-pyqt6.qtsvg║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
import os
import re
import signal
import argparse
import json
import shutil
import subprocess
import tempfile
import threading
import ssl
import urllib.request
import urllib.parse

from PyQt6.QtCore import Qt, QTimer, QUrl, QSize, QByteArray, QDateTime
from PyQt6.QtGui import (
    QIcon, QAction, QPixmap, QPainter, QColor,
    QShortcut, QKeySequence, QDesktopServices,
)
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QMenu,
    QMessageBox, QToolBar, QLabel, QSpinBox, QLineEdit,
    QWidgetAction, QHBoxLayout, QWidget, QDialog, QTextEdit,
    QVBoxLayout, QPushButton, QDialogButtonBox, QFileDialog,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineUrlRequestInterceptor,
    QWebEngineScript, QWebEngineSettings,
)
from PyQt6.QtSvg import QSvgRenderer

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

APP_NAME = "FreeTheBird"
APP_VERSION = "1.3.0"
APP_AUTHOR = "@daboblog"
APP_GITHUB = "https://github.com/daboblog/FreeTheBird"
APP_DESKTOP_NAME = "freethebird"

CONFIG_PATH = os.path.expanduser("~/.config/freethebird/config.json")

# Paths to purge when QtWebEngine cache becomes corrupted
PURGE_PATHS = [
    os.path.expanduser("~/.local/share/QtWebEngine"),
    os.path.expanduser("~/.local/share/freethebird"),
    os.path.expanduser("~/.cache/QtWebEngine"),
    os.path.expanduser("~/.config/freethebird"),
]

# Default configuration values
DEFAULT_CONFIG = {
    "zoom": 1.0,
    "width": 1200,
    "height": 800,
    "dark_mode": True,
    "lang": "es",
    "refresh_interval": 120,
    "tray_enabled": True,
    "sponsor_block": True,
}

# =============================================================================
# INTERNATIONALISATION (i18n) — Spanish & English
# =============================================================================

STRINGS = {
    "es": {
        # Navigation & actions
        "home": "Inicio",
        "refresh": "Refrescar",
        "quit": "Salir",
        # View & theme
        "view": "Vista",
        "dark_mode": "Modo oscuro",
        "light_mode": "Modo claro",
        # Auto-refresh
        "auto_on": "Auto-refresco: ON",
        "auto_off": "Auto-refresco: OFF",
        "auto_each": "Auto-refresco cada {}s",
        "auto_disabled": "Auto-refresco desactivado",
        "refreshed": "Refrescado",
        "interval": " Intervalo:",
        # System tray
        "show_hide": "Mostrar/Ocultar",
        "refresh_now": "Refrescar ahora",
        "tray_title": APP_NAME,
        "tray_msg": "Sigue en la bandeja. Clic derecho > Salir para cerrar.",
        "new_notif": "Tienes nuevas notificaciones en X",
        # Privacy
        "privacy_on": "Privacidad: ON",
        "privacy_title": "Privacidad",
        "privacy_body": (
            "{app} protege tu privacidad bloqueando conexiones "
            "a dominios de rastreo y publicidad de terceros.\n\n"
            "Dominios bloqueados:\n"
            "- Google Ads, Analytics, Tag Manager\n"
            "- Twitter/X Ads y Analytics\n"
            "- Facebook tracking\n"
            "- Criteo, Taboola, Outbrain\n"
            "- Hotjar, Mixpanel, FullStory\n"
            "- Y {count} dominios mas\n\n"
            "Peticiones bloqueadas en esta sesi\u00f3n: {blocked}\n\n"
            "Los anuncios nativos de X (tweets promocionados) se sirven "
            "desde el propio dominio de X y no pueden bloquearse a nivel de red."
        ),
        # Translator
        "translate": "Traducir",
        "translate_title": "Traducci\u00f3n",
        "translate_original": "Original",
        "translate_error": "Error al traducir",
        # Tray
        "tray_toggle": "Minimizar a bandeja",
        "tray_enabled": "Bandeja: ON",
        "tray_disabled": "Bandeja: OFF",
        "sponsor_block": "Bloquear patrocinados",
        # Language switcher
        "switch_to": "Cambiar a English",
        # Connection info
        "conn_details": "Ver detalles de conexi\u00f3n",
        "conn_title": "Conexi\u00f3n",
        "conn_ip": "IP p\u00fablica",
        "conn_isp": "Proveedor",
        "conn_org": "Organizaci\u00f3n",
        "conn_country": "Pa\u00eds",
        "conn_region": "Regi\u00f3n",
        "conn_city": "Ciudad",
        "conn_zip": "C\u00f3digo postal",
        "conn_tz": "Zona horaria",
        "conn_lat": "Latitud",
        "conn_lon": "Longitud",
        "conn_error": "No se pudo obtener informaci\u00f3n adicional.",
        "loading": "Cargando...",
        "session_menu": "Sesi\u00f3n",
        "import_session": "Importar sesi\u00f3n de X",
        "import_title": "Importar sesi\u00f3n",
        "import_instructions": (
            "X bloquea el login dentro de navegadores embebidos.\n"
            "Soluci\u00f3n fiable: inicia sesi\u00f3n en Chrome/Edge real y pega las cookies aqu\u00ed.\n\n"
            "En tu navegador real:\n"
            "1) Entra a https://x.com y logu\u00e9ate (ah\u00ed s\u00ed funciona)\n"
            "2) Pulsa F12 > Application > Cookies > https://x.com\n"
            "3) Copia auth_token y ct0 (o todas las cookies como 'auth_token=...; ct0=...')\n"
            "4) P\u00e9galas abajo y pulsa Importar. Tambi\u00e9n acepta JSON o cookies.txt\n\n"
            "Pega aqu\u00ed:"
        ),
        "import_ok": "Sesi\u00f3n importada. Recargando...",
        "import_fail": "No se detectaron cookies v\u00e1lidas. Pega 'auth_token=...; ct0=...' o JSON o cookies.txt",
        "open_browser_login": "Abrir login en navegador real",
    },
    "en": {
        "home": "Home",
        "refresh": "Refresh",
        "quit": "Quit",
        "view": "View",
        "dark_mode": "Dark mode",
        "light_mode": "Light mode",
        "auto_on": "Auto-refresh: ON",
        "auto_off": "Auto-refresh: OFF",
        "auto_each": "Auto-refresh every {}s",
        "auto_disabled": "Auto-refresh disabled",
        "refreshed": "Refreshed",
        "interval": " Interval:",
        "show_hide": "Show/Hide",
        "refresh_now": "Refresh now",
        "tray_title": APP_NAME,
        "tray_msg": "Still in system tray. Right click > Quit to close.",
        "new_notif": "You have new notifications on X",
        "privacy_on": "Privacy: ON",
        "privacy_title": "Privacy",
        "privacy_body": (
            "{app} protects your privacy by blocking connections "
            "to third-party tracking and advertising domains.\n\n"
            "Blocked domains:\n"
            "- Google Ads, Analytics, Tag Manager\n"
            "- Twitter/X Ads & Analytics\n"
            "- Facebook tracking\n"
            "- Criteo, Taboola, Outbrain\n"
            "- Hotjar, Mixpanel, FullStory\n"
            "- And {count} more domains\n\n"
            "Requests blocked this session: {blocked}\n\n"
            "Native X ads (promoted tweets) are served from X's own domain "
            "and cannot be blocked at the network level."
        ),
        "translate": "Translate",
        "translate_title": "Translation",
        "translate_original": "Original",
        "translate_error": "Translation error",
        "switch_to": "Cambiar a Espanol",
        "tray_toggle": "Minimize to tray",
        "tray_enabled": "Tray: ON",
        "tray_disabled": "Tray: OFF",
        "sponsor_block": "Block sponsors",
        "conn_details": "View connection details",
        "conn_title": "Connection",
        "conn_ip": "Public IP",
        "conn_isp": "ISP",
        "conn_org": "Organization",
        "conn_country": "Country",
        "conn_region": "Region",
        "conn_city": "City",
        "conn_zip": "Postal code",
        "conn_tz": "Timezone",
        "conn_lat": "Latitude",
        "conn_lon": "Longitude",
        "conn_error": "Could not retrieve additional information.",
        "loading": "Loading...",
        "session_menu": "Session",
        "import_session": "Import X session",
        "import_title": "Import session",
        "import_instructions": (
            "X blocks login inside embedded browsers.\n"
            "Reliable workaround: log in on real Chrome/Edge and paste cookies here.\n\n"
            "In your real browser:\n"
            "1) Go to https://x.com and log in (works there)\n"
            "2) Press F12 > Application > Cookies > https://x.com\n"
            "3) Copy auth_token and ct0 (or all cookies as 'auth_token=...; ct0=...')\n"
            "4) Paste below and click Import. Also accepts JSON or cookies.txt\n\n"
            "Paste here:"
        ),
        "import_ok": "Session imported. Reloading...",
        "import_fail": "No valid cookies detected. Paste 'auth_token=...; ct0=...' or JSON or cookies.txt",
        "open_browser_login": "Open login in system browser",
    },
}

# =============================================================================
# PRIVACY — Ad & tracker domain blocklist
# Intercepted at the network level before any request leaves the app.
# These domains are blocked regardless of the page content.
# =============================================================================

AD_DOMAINS = {
    # Google advertising & analytics
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "google-analytics.com", "googletagmanager.com", "googletagservices.com",
    "adservice.google.com", "pagead2.googlesyndication.com",
    # Twitter/X advertising & analytics
    "ads-twitter.com", "ads-api.twitter.com", "analytics.twitter.com",
    "ads.twitter.com", "ads-bidder.twitter.com",
    "ads-api.x.com", "ads.x.com", "analytics.x.com",
    # Facebook tracking
    "facebook.net",
    # Ad networks
    "amazon-adsystem.com", "media.net", "outbrain.com", "taboola.com",
    "criteo.com", "criteo.net", "scorecardresearch.com",
    "quantserve.com", "adsrvr.org", "adnxs.com", "rubiconproject.com",
    "pubmatic.com", "openx.net", "casalemedia.com", "sharethrough.com",
    # Verification & measurement
    "moatads.com", "doubleverify.com", "adsafeprotected.com",
    # Data management & tracking platforms
    "serving-sys.com", "eyeota.net", "mathtag.com", "bluekai.com",
    "demdex.net", "krxd.net", "exelator.com", "agkn.com",
    # Analytics & session recording
    "hotjar.com", "fullstory.com", "mixpanel.com", "segment.io",
    # Attribution & deep linking
    "branch.io", "app.link", "appsflyer.com", "adjust.com",
}

# =============================================================================
# WHITELISTED DOMAINS — Only these domains load inside the app.
# Everything else opens in the system browser.
# =============================================================================

ALLOWED_HOSTS = {
    "x.com", "twitter.com", "www.x.com", "www.twitter.com",
    "mobile.x.com", "mobile.twitter.com",
    "api.x.com", "api.twitter.com",
    "capi.x.com", "capi.twitter.com",
    "internal-api.x.com", "internal-api.twitter.com",
    "i.x.com", "i.twitter.com",
    "upload.twitter.com",
    # twimg media CDNs — X videos/thumbnails/GIFs use many subdomains
    "twimg.com", "abs.twimg.com", "pbs.twimg.com", "video.twimg.com",
    "ton.twimg.com", "cdn.syndication.twimg.com", "syndication.twimg.com",
    "t.co",
    # HLS.js CDN for m3u8 fallback (X serves m3u8, not mp4)
    "cdn.jsdelivr.net", "jsdelivr.net",
    # Local ffmpeg stream server (decoded video is served back to the page)
    "127.0.0.1", "localhost",
    # Verification providers required for login (ArkoseLabs + reCAPTCHA)
    "client-api.arkoselabs.com", "api.arkoselabs.com", "arkoselabs.com",
    "funcaptcha.com", "api.funcaptcha.com",
    "recaptcha.net", "www.recaptcha.net",
    "www.gstatic.com", "www.google.com", "apis.google.com",
}

# Verification hosts that must stay inside the app (not opened in system browser)
# Used by createWindow to avoid breaking Arkose/reCAPTCHA challenges
VERIFICATION_HOSTS = {
    "client-api.arkoselabs.com", "api.arkoselabs.com", "arkoselabs.com",
    "funcaptcha.com", "api.funcaptcha.com",
    "recaptcha.net", "www.recaptcha.net",
    "www.gstatic.com", "www.google.com", "apis.google.com",
}

# Authentication providers allowed to load inside the app
AUTH_HOSTS = {"accounts.google.com", "appleid.apple.com"}

# =============================================================================
# UI — Embedded SVG icon (no external files needed)
# =============================================================================

APP_ICON_SVG = (
    b'<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
    b'<rect width="64" height="64" rx="12" fill="#1a1a2e"/>'
    b'<rect x="14" y="18" width="2.5" height="34" rx="1" fill="#555" opacity="0.8"/>'
    b'<rect x="22" y="18" width="2.5" height="34" rx="1" fill="#555" opacity="0.8"/>'
    b'<rect x="29" y="18" width="2.5" height="16" rx="1" fill="#555" opacity="0.6" transform="rotate(15,30,26)"/>'
    b'<rect x="30" y="38" width="2.5" height="14" rx="1" fill="#555" opacity="0.6" transform="rotate(-8,31,45)"/>'
    b'<rect x="38" y="18" width="2.5" height="34" rx="1" fill="#555" opacity="0.4"/>'
    b'<path d="M12 20Q12 10 27 10Q42 10 42 20" stroke="#555" stroke-width="2.5" fill="none" opacity="0.7"/>'
    b'<rect x="12" y="50" width="32" height="2.5" rx="1" fill="#555" opacity="0.7"/>'
    b'<g transform="translate(38,14)">'
    b'<ellipse cx="10" cy="12" rx="7" ry="5.5" fill="#1da1f2"/>'
    b'<circle cx="16" cy="8" r="4.5" fill="#1da1f2"/>'
    b'<polygon points="20,7 25,8.5 20,10" fill="#ffcc00"/>'
    b'<circle cx="17.5" cy="7" r="1.2" fill="white"/>'
    b'<circle cx="18" cy="7" r="0.6" fill="#1a1a2e"/>'
    b'<path d="M6 11Q2 3 8 1Q14-1 13 7Z" fill="#0d8ecf"/>'
    b'<path d="M3 13Q-2 10-1 15Q0 17 4 15Z" fill="#0d8ecf"/>'
    b'</g>'
    b'<circle cx="52" cy="8" r="1.5" fill="#ffcc00" opacity="0.9"/>'
    b'<circle cx="56" cy="14" r="1" fill="#ffcc00" opacity="0.7"/>'
    b'<circle cx="48" cy="5" r="1" fill="#ffcc00" opacity="0.6"/>'
    b'</svg>'
)

# =============================================================================
# UI — Qt stylesheets for dark and light themes
# =============================================================================

DARK_STYLE = (
    "QMainWindow { background-color: #15202b; }"
    "QMenuBar { background-color: #1a1a2e; color: #e0e0e0; }"
    "QMenuBar::item:selected { background-color: #1da1f2; }"
    "QMenu { background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #333; }"
    "QMenu::item:selected { background-color: #1da1f2; }"
    "QToolBar { background-color: #1a1a2e; color: #e0e0e0; border: none; }"
    "QLabel { color: #e0e0e0; }"
    "QSpinBox { background-color: #2a2a3e; color: #e0e0e0; border: 1px solid #444; }"
    "QToolButton { color: #e0e0e0; }"
    "QToolButton:hover { background-color: #1da1f2; border-radius: 4px; }"
)

LIGHT_STYLE = (
    "QMainWindow { background-color: #fff; }"
    "QMenuBar { background-color: #f5f5f5; color: #333; }"
    "QMenuBar::item:selected { background-color: #1da1f2; color: white; }"
    "QMenu { background-color: #fff; color: #333; border: 1px solid #ccc; }"
    "QMenu::item:selected { background-color: #1da1f2; color: white; }"
    "QToolBar { background-color: #f5f5f5; color: #333; border: none; }"
    "QLabel { color: #333; }"
    "QSpinBox { background-color: #fff; color: #333; border: 1px solid #ccc; }"
    "QToolButton { color: #333; }"
    "QToolButton:hover { background-color: #1da1f2; color: white; border-radius: 4px; }"
)

# Dialog style for dark mode message boxes
DARK_DIALOG = "QLabel { color: #e0e0e0; } QMessageBox { background: #1a1a2e; }"

# Fingerprint hardening — run in MainWorld at DocumentCreation so page JS
# sees a real-Chrome-like navigator/window.chrome. QtWebEngine otherwise
# exposes webdriver/plugins gaps that X's ArkoseLabs check flags as bot.
# Also patches media APIs so QtWebEngine's H.264/AAC support is advertised
# correctly — without this X's player picks a codec Qt cannot decode and
# shows "The media could not be played".
FINGERPRINT_JS = r"""
(function() {
  try { Object.defineProperty(navigator, 'webdriver', {get: () => false, configurable: true}); } catch(e) {}
  try {
    const fakePlugins = [
      {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
      {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
      {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''},
    ];
    Object.defineProperty(navigator, 'plugins', {get: () => {
      const arr = fakePlugins.slice();
      arr.item = function(i){ return this[i] || null; };
      arr.namedItem = function(n){ return this.find(p=>p.name===n) || null; };
      arr.refresh = function(){};
      return arr;
    }, configurable: true});
  } catch(e) {}
  try { Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en'], configurable: true}); } catch(e) {}
  try { Object.defineProperty(navigator, 'platform', {get: () => 'Win32', configurable: true}); } catch(e) {}
  try { Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.', configurable: true}); } catch(e) {}
  try { Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8, configurable: true}); } catch(e) {}
  try { Object.defineProperty(navigator, 'deviceMemory', {get: () => 8, configurable: true}); } catch(e) {}
  try {
    if (!window.chrome) window.chrome = {};
    if (!window.chrome.runtime) window.chrome.runtime = {};
    if (!window.chrome.loadTimes) window.chrome.loadTimes = function(){};
    if (!window.chrome.csi) window.chrome.csi = function(){};
  } catch(e) {}
  try {
    const origQuery = navigator.permissions && navigator.permissions.query;
    if (origQuery) {
      navigator.permissions.query = function(p){ return origQuery.call(this, p).catch(()=>({state:'granted', onchange:null})); };
    }
  } catch(e) {}
})();
"""

# Lightweight sponsor block — hides "Promoted by" trends and sponsored posts.
# Efficient: MutationObserver on added nodes only + exact markers so body text
# containing the word "promoted" is never hidden. Toggleable via window._ftbSponsorBlockEnabled.
SPONSOR_BLOCK_JS = r"""
(function(){
  window._ftbSponsorBlockEnabled = true;
  // exact markers — avoids hiding normal tweets that mention "promoted"
  function isSponsoredTrend(el){
    // X's promoted trend has a small line that starts with "Promoted by "
    // It's a distinct span/div, not the title. Check direct text.
    try{
      var spans = el.querySelectorAll('span, div');
      for(var i=0;i<spans.length;i++){
        var t = (spans[i].textContent||'').trim();
        if(/^Promoted by\s+/i.test(t)) return true;
      }
      // fallback: aria
      if(el.querySelector('[aria-label*="Promoted"]')) return true;
    }catch(e){}
    return false;
  }
  function isSponsoredPost(article){
    try{
      // definitive marker X uses for ads
      if(article.querySelector('[data-testid="placementTracking"]')) return true;
      if(article.querySelector('[aria-label*="Promoted"]')) return true;
      // exact label spans (not tweetText)
      var spans = article.querySelectorAll('span, div');
      for(var i=0;i<spans.length;i++){
        var c = spans[i];
        var t = (c.textContent||'').trim();
        if(/^Promoted by\s+/i.test(t)) return true;
        if(t === 'Promoted' && c.childElementCount === 0){
          if(!c.closest('[data-testid="tweetText"]')) return true;
        }
      }
    }catch(e){}
    return false;
  }
  function hide(el){
    if(!window._ftbSponsorBlockEnabled) return;
    if(!el || el.dataset.ftbHidden) return;
    el.dataset.ftbHidden = '1';
    el.style.display = 'none';
  }
  function unhideAll(){
    document.querySelectorAll('[data-ftb-hidden]').forEach(function(el){
      el.style.display = '';
      delete el.dataset.ftbHidden;
    });
  }
  window._ftbSponsorUnhide = unhideAll;
  function scan(root){
    if(!window._ftbSponsorBlockEnabled) return;
    if(!root || !root.querySelectorAll) return;
    // trends: each [data-testid="trend"]
    var trends = root.matches && root.matches('[data-testid="trend"]') ? [root] : [];
    var q1 = root.querySelectorAll('[data-testid="trend"]');
    for(var i=0;i<q1.length;i++) trends.push(q1[i]);
    for(var i=0;i<trends.length;i++){
      var tr = trends[i];
      if(tr.dataset.ftbHidden) continue;
      if(isSponsoredTrend(tr)) hide(tr);
    }
    // posts: article
    var arts = root.matches && root.tagName === 'ARTICLE' ? [root] : [];
    var q2 = root.querySelectorAll('article');
    for(var i=0;i<q2.length;i++) arts.push(q2[i]);
    for(var i=0;i<arts.length;i++){
      var a = arts[i];
      if(a.dataset.ftbHidden) continue;
      if(isSponsoredPost(a)){
        var cell = a.closest('[data-testid="cellInnerDiv"]');
        hide(cell || a);
      }
    }
  }
  var obs = new MutationObserver(function(muts){
    muts.forEach(function(m){
      m.addedNodes.forEach(function(n){
        if(n.nodeType !== 1) return;
        scan(n);
      });
    });
  });
  obs.observe(document.documentElement, {childList:true, subtree:true});
  scan(document.documentElement);
  // expose toggle for Python
  window._ftbSponsorSet = function(enabled){
    window._ftbSponsorBlockEnabled = enabled;
    if(enabled) scan(document.documentElement);
    else unhideAll();
  };
})();
"""


# =============================================================================
# CONFIGURATION — Load & save user preferences
# =============================================================================

def load_config():
    """Load configuration from disk, falling back to defaults.

    Only accepts keys present in DEFAULT_CONFIG and validates that
    each value matches the expected type. Malformed or unexpected
    entries are silently discarded.
    """
    cfg = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for key, default_val in DEFAULT_CONFIG.items():
                if key in raw and isinstance(raw[key], type(default_val)):
                    cfg[key] = raw[key]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg):
    """Persist configuration to disk. Silently fails on I/O errors."""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


# =============================================================================
# MAINTENANCE — Cache purge for development/troubleshooting
# =============================================================================

def do_purge(verbose=True):
    """Remove all local state that may keep QtWebEngine/X sessions corrupted."""
    removed = []

    for path in PURGE_PATHS:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path)
            if verbose:
                print(f"[purge] Removed: {path}")

    tmp_dir = tempfile.gettempdir()
    for name in os.listdir(tmp_dir):
        if "QtWebEngine" in name or "freethebird" in name.lower():
            path = os.path.join(tmp_dir, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                removed.append(path)
                if verbose:
                    print(f"[purge] Removed temp: {path}")
            except OSError as e:
                if verbose:
                    print(f"[purge] Could not remove {path}: {e}")

    return removed


# =============================================================================
# ICON — Generate app icon from embedded SVG
# =============================================================================

def create_app_icon():
    """Render the embedded SVG into a QIcon. No external files needed."""
    renderer = QSvgRenderer(QByteArray(APP_ICON_SVG))
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# =============================================================================
# PRIVACY ENGINE — Network-level ad & tracker interceptor
# =============================================================================

class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """Intercepts outgoing HTTP requests and blocks known ad/tracker domains.

    This operates at the network level, before any request leaves the app.
    It cannot block native X ads (promoted tweets) because those are served
    from X's own domain (x.com).
    """

    def __init__(self, parent=None, privacy_enabled=True, window=None):
        super().__init__(parent)
        self.blocked_count = 0
        self.privacy_enabled = privacy_enabled
        self.window = window
        self.last_video_url = ""

    def interceptRequest(self, info):
        # 1) NEVER block or mangle media — twimg CDNs 403 if Referer/Client-Hints are wrong
        try:
            url = info.requestUrl()
            scheme = url.scheme().lower()
            host = url.host().lower()
            url_str = url.toString()
            # Capture X video URL so the external decoder script can be launched
            if (".m3u8" in url_str or "/pu/vid/" in url_str or "/ext_tw_video/" in url_str or "/amplify_video/" in url_str):
                self.last_video_url = url_str
                try:
                    win = self.window
                    if win:
                        win._last_video_url = url_str
                        QTimer.singleShot(0, lambda u=url_str, w=win: w._on_video_captured(u))
                except Exception:
                    pass
            if scheme in ("blob", "data", "mediasource"):
                return
            # Local decoder server — always allow (decoded stream back to the page)
            if host in ("127.0.0.1", "localhost"):
                return
            if host == "twimg.com" or host.endswith(".twimg.com"):
                try:
                    info.setHttpHeader(b"Referer", b"https://x.com/")
                    info.setHttpHeader(b"Origin", b"https://x.com")
                except Exception:
                    pass
                return
            # HLS/mp4 chunks are ResourceType Media — never block
            try:
                rt = str(info.resourceType())
                if "Media" in rt:
                    return
            except Exception:
                pass
        except Exception:
            pass
        # 2) Client Hints for fingerprint (skip for media — already returned)
        try:
            info.setHttpHeader(b"sec-ch-ua", b'"Google Chrome";v="133", "Chromium";v="133", "Not-A.Brand";v="99"')
            info.setHttpHeader(b"sec-ch-ua-mobile", b"?0")
            info.setHttpHeader(b"sec-ch-ua-platform", b'"Windows"')
        except Exception:
            pass
        if not self.privacy_enabled:
            return
        host = info.requestUrl().host().lower()
        if not host:
            return
        parts = host.split(".")
        for i in range(len(parts)):
            if ".".join(parts[i:]) in AD_DOMAINS:
                info.block(True)
                self.blocked_count += 1
                return


# =============================================================================
# NAVIGATION ENGINE — Controls which URLs load inside the app
# =============================================================================

class FreeTheBirdPage(QWebEnginePage):
    """Custom web page that enforces domain whitelisting.

    - Allowed domains (X, Twitter, media CDNs) load inside the app
    - Authentication providers (Google, Apple) load inside for login
    - All other clicked links open in the system's default browser
    - Pop-up windows are caught and redirected to the system browser
    """

    def __init__(self, profile, parent=None, privacy_enabled=True):
        super().__init__(profile, parent)
        self.privacy_enabled = privacy_enabled
        self._console_handler = None

    def javaScriptConsoleMessage(self, level, msg, line, sourceId):
        try:
            if self._console_handler:
                self._console_handler(level, msg, line, sourceId)
                # still show video errors in status if handler didn't
        except Exception:
            pass
        try:
            super().javaScriptConsoleMessage(level, msg, line, sourceId)
        except Exception:
            pass

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        # Privacy disabled: let the site navigate freely (fixes blocked login flows)
        if not self.privacy_enabled:
            return True

        host = url.host().lower()
        if not host:
            # blob:, data:, mediasource: — allow (video MSE uses blob:)
            return True

        # Allow whitelisted X/Twitter/media/verification domains (suffix match)
        for h in ALLOWED_HOSTS:
            if host == h or host.endswith("." + h):
                return True

        # Allow authentication providers for login flows (exact match)
        for auth_host in AUTH_HOSTS:
            if host == auth_host or host.endswith("." + auth_host):
                return True

        # Non-whitelisted domains: open links in system browser, block the rest
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
        return False

    def createWindow(self, window_type):
        """Handle pop-up windows. Verification popups (Arkose/reCAPTCHA) stay
        inside the app; all other external popups open in the system browser."""
        page = FreeTheBirdPage(self.profile(), self.parent(), self.privacy_enabled)

        def _on_url_changed(url):
            host = url.host().lower()
            if not host:
                return
            # Keep verification/media/auth challenges inside the app (suffix match)
            for allowed in (VERIFICATION_HOSTS | ALLOWED_HOSTS | AUTH_HOSTS):
                if host == allowed or host.endswith("." + allowed):
                    return
            QDesktopServices.openUrl(url)
            page.deleteLater()

        page.urlChanged.connect(_on_url_changed)
        return page


# =============================================================================
# MAIN WINDOW — The heart of FreeTheBird
# =============================================================================

class FreeTheBirdWindow(QMainWindow):
    """Main application window.

    Architecture:
    - QtWebEngine renders X (Twitter) inside the app
    - AdBlockInterceptor filters requests at the network level
    - FreeTheBirdPage enforces domain whitelisting
    - All UI text updates use setText()/setTitle() in-place to avoid
      widget destruction, which causes segfaults with QtWebEngine+Chrome

    UI structure:
    ┌─────────────────────────────────────────────────────────┐
    │ Menu: Vista │ IP │ ES/EN │ EFF │ @daboblog │ GNU/Linux │
    ├─────────────────────────────────────────────────────────┤
    │                                                         │
    │                   QtWebEngine (X.com)                    │
    │                                                         │
    ├─────────────────────────────────────────────────────────┤
    │ Toolbar: Home │ Refresh │ Auto │ Zoom │ Privacy │ Trad  │
    └─────────────────────────────────────────────────────────┘
    """

    def __init__(self, url, refresh_interval, auto_refresh, width, height,
                 privacy_enabled=True, tray_enabled=True):
        super().__init__()

        # -- Load persisted configuration --
        self.cfg = load_config()
        self.lang = self.cfg.get("lang", "es")
        self.dark_mode = self.cfg.get("dark_mode", True)
        self.refresh_interval = self.cfg.get("refresh_interval", refresh_interval)
        self.auto_refresh_enabled = auto_refresh
        self.privacy_enabled = privacy_enabled
        # Tray: CLI --no-tray overrides config; otherwise use persisted config
        cfg_tray = self.cfg.get("tray_enabled", True)
        self.tray_enabled = False if not tray_enabled else cfg_tray
        self.app_icon = create_app_icon()
        self.last_title = ""
        self.current_ip = "..."
        self.conn_info = None

        # -- Window setup -- start maximized (no left gap on open)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.app_icon)
        self.resize(self.cfg.get("width", width), self.cfg.get("height", height))
        # maximize on open — user requested full window, keep saved size for restore
        try:
            self.setWindowState(Qt.WindowState.WindowMaximized)
        except Exception:
            pass

        # -- WebEngine with isolated profile (persistent across sessions) --
        self.profile = QWebEngineProfile(APP_DESKTOP_NAME, self)
        self.profile.setPersistentStoragePath(os.path.expanduser("~/.local/share/freethebird"))
        try:
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            )
        except Exception:
            pass
        try:
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
            self.profile.setCachePath(os.path.expanduser("~/.cache/freethebird"))
        except Exception:
            pass
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        )
        # Download handling — default to Downloads, always ask where to save
        try:
            dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.isdir(dl_dir):
                self.profile.setDownloadPath(dl_dir)
            self.profile.downloadRequested.connect(self._on_download_requested)
        except Exception:
            pass

        # -- Privacy: attach ad/tracker interceptor (always for Client Hints) --
        self.ad_interceptor = AdBlockInterceptor(self, self.privacy_enabled, window=self)
        # keep python-side last url in sync with JS
        self._last_video_url = ""
        self.profile.setUrlRequestInterceptor(self.ad_interceptor)

        # -- Browser view --
        self.page = FreeTheBirdPage(self.profile, self, self.privacy_enabled)

        # -- Media: allow autoplay + enable every setting X's video player needs --
        # X uses muted autoplay + MSE (blob:) + H.264/AAC. QtWebEngine on Windows
        # ships proprietary codecs, but PlaybackRequiresUserGesture + missing
        # ALLOWED_HOSTS for ton.twimg.com causes "The media could not be played".
        try:
            s = self.profile.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)
            # also apply to the page itself (some Qt versions keep page settings separate)
            self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        except Exception:
            pass

        # -- Fingerprint: spoof navigator/chrome at DocumentCreation (MainWorld) --
        fp = QWebEngineScript()
        fp.setName("fingerprint")
        fp.setSourceCode(FINGERPRINT_JS)
        fp.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        fp.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        fp.setRunsOnSubFrames(True)
        self.profile.scripts().insert(fp)

        # -- Stream patch: if user started a local decoder stream (window._ftbStreamUrl),
        #    point any new <video> with blob/m3u8 src at the decoded stream. --
        STREAM_PATCH_JS = r"""
        (function(){
          var patched = new WeakSet();
          function isStreamSrc(v){
            var s = v.currentSrc || v.src || v.getAttribute('src') || '';
            return s.indexOf('blob:') === 0 || s.indexOf('.m3u8') !== -1 || s.indexOf('video.twimg.com') !== -1;
          }
          function patch(v){
            try{
              var w = window._ftbStreamUrl;
              if(!w || patched.has(v)) return;
              if(!isStreamSrc(v)) return;
              patched.add(v);
              v.muted = true; v.playsInline = true; v.setAttribute('playsinline','');
              v.src = w; v.load();
              var p = v.play(); if(p && p.catch) p.catch(function(){});
            }catch(e){}
          }
          try{
            var obs = new MutationObserver(function(muts){
              muts.forEach(function(m){
                if(m.type === 'attributes' && m.target && m.target.tagName === 'VIDEO'){ patch(m.target); return; }
                m.addedNodes.forEach(function(n){
                  if(n.tagName === 'VIDEO') patch(n);
                  else if(n.querySelectorAll) n.querySelectorAll('video').forEach(patch);
                });
              });
            });
            obs.observe(document.documentElement, {childList:true, subtree:true,
                                                   attributes:true, attributeFilter:['src']});
            document.querySelectorAll('video').forEach(patch);
            setInterval(function(){ document.querySelectorAll('video').forEach(patch); }, 1500);
          }catch(e){}
        })();
        """
        sp = QWebEngineScript()
        sp.setName("stream_patch")
        sp.setSourceCode(STREAM_PATCH_JS)
        sp.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        sp.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        sp.setRunsOnSubFrames(True)
        self.profile.scripts().insert(sp)

        # — Sponsor block: hide "Promoted by" trends and Promoted post cards (exact markers only)
        sponsor = QWebEngineScript()
        sponsor.setName("sponsor_block")
        sponsor.setSourceCode(SPONSOR_BLOCK_JS)
        sponsor.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        sponsor.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        sponsor.setRunsOnSubFrames(True)
        self.profile.scripts().insert(sponsor)

        # — Hijack the tweet's "Reload" button (shown on "The media could not be played")
        #   so it launches the external decoder for *that specific* video's stream.
        RELOAD_JS = r"""
        (function(){
          // only capture URLs when user explicitly clicks Reload — no scroll auto-play noise
          window._ftbLastVideoUrl = window._ftbLastVideoUrl || "";
          window._ftbAllVideoUrls = window._ftbAllVideoUrls || [];
          var _ftbInterceptionEnabled = false;
          window._ftbEnableCapture = function(){ _ftbInterceptionEnabled = true; };
          window._ftbDisableCapture = function(){ _ftbInterceptionEnabled = false; };
          function _ftbCapture(u){
            if(!_ftbInterceptionEnabled) return;
            try{
              var s = String(u||"");
              if(s.indexOf('video.twimg.com')!==-1 || s.indexOf('.m3u8')!==-1 || s.indexOf('/pu/vid/')!==-1 || s.indexOf('/ext_tw_video/')!==-1 || s.indexOf('/amplify_video/')!==-1){
                if(window._ftbAllVideoUrls.indexOf(s)===-1){
                  window._ftbLastVideoUrl = s;
                  window._ftbAllVideoUrls.push(s);
                }
              }
            }catch(e){}
          }
          try{
            var _origFetch = window.fetch;
            window.fetch = function(u){ try{ var s=typeof u==='string'?u:(u&&u.url); if(_ftbInterceptionEnabled) _ftbCapture(s); }catch(e){} return _origFetch.apply(this, arguments); };
          }catch(e){}
          try{
            var _origOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(m,u){ try{ if(_ftbInterceptionEnabled) _ftbCapture(u); }catch(e){} return _origOpen.apply(this, arguments); };
          }catch(e){}
          function _extractUrlsFromContainer(c){
            if(!c) return [];
            try{
              var h = c.innerHTML || "";
              var out = [];
              // m3u8 first (what X actually plays), then mp4
              var reM3u8 = /https:\/\/video\.twimg\.com[^"'\s\\]+\.m3u8[^"'\s\\]*/g;
              var reMp4  = /https:\/\/video\.twimg\.com[^"'\s\\]+\.mp4[^"'\s\\]*/g;
              var m;
              while((m=reM3u8.exec(h))!==null) out.push(m[0].replace(/\\u002F/g,'/').replace(/\\/g,''));
              while((m=reMp4.exec(h))!==null) out.push(m[0].replace(/\\u002F/g,'/').replace(/\\/g,''));
              // also check <meta> tags inside container
              try{
                var metas = c.querySelectorAll('meta[content*="video.twimg.com"]');
                metas.forEach(function(el){ var v=el.getAttribute('content'); if(v) out.push(v); });
              }catch(e){}
              return out;
            }catch(e){ return []; }
          }
          function _findUrlForButton(btn){
            // 1) On-demand DOM search in the tweet that owns this Reload button — ignores scroll captures
            try{
              var tweet = btn.closest('[data-testid="tweet"], article');
              // climb a bit to include video player wrapper
              var c = tweet;
              for(var i=0;i<4 && c; i++){
                var urls = _extractUrlsFromContainer(c);
                if(urls.length) return urls[0]; // first m3u8 in this tweet
                c = c.parentElement;
              }
            }catch(e){}
            // 2) if DOM had no embedded URL (X loads it via JS), briefly enable capture
            //    and try to hit the API by forcing the player to retry — but we already
            //    have Python-side last URL as fallback. Use per-tweet vid id match.
            try{
              var c2 = btn.closest('[data-testid="tweet"], article') || btn.closest('div');
              for(var i=0;i<3 && c2 && !c2.innerHTML.includes('video.twimg.com'); i++) c2 = c2.parentElement;
              var h = c2 ? c2.innerHTML : "";
              var m = h.match(/\/(amplify_video|ext_tw_video)\/(\d+)/);
              var vid = m ? m[2] : "";
              if(!vid){
                var m2 = h.match(/\/(\d{18,19})\//);
                vid = m2 ? m2[1] : "";
              }
              if(vid){
                for(var i=window._ftbAllVideoUrls.length-1;i>=0;i--){
                  if(window._ftbAllVideoUrls[i].indexOf(vid)!==-1) return window._ftbAllVideoUrls[i];
                }
                // also check Python-side via a sync JS var that interceptor mirrors
                // (interceptor sets window._ftbLastVideoUrl even when _ftbInterceptionEnabled is false?
                //  we keep it disabled, so not — fallback to global last)
              }
            }catch(e){}
            if(window._ftbLastVideoUrl) return window._ftbLastVideoUrl;
            return "";
          }
          function hookReload(){
            var candidates = document.querySelectorAll('button, [role="button"], div[role="button"]');
            var found = 0;
            candidates.forEach(function(el){
              if(el.__ftbHooked) return;
              var t=(el.textContent||'').trim().toLowerCase();
              if(t!=='reload') return;
              var p = el;
              var isVideoError = false;
              for(var i=0;i<6 && p; i++){
                p = p.parentElement;
                if(!p) break;
                var txt = (p.textContent||'').toLowerCase();
                if(txt.indexOf('could not be played')!==-1 || txt.indexOf('el medio no se pudo')!==-1){ isVideoError=true; break; }
              }
              if(!isVideoError) return;
              el.__ftbHooked = true;
              found++;
              el.style.background = '#1da1f2';
              el.style.borderRadius = '999px';
              el.style.cursor = 'pointer';
              el.title = 'Decode & play THIS video (FreeTheBird)';
              el.addEventListener('click', function(e){
                e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation();
                // enable capture for a short window so the retry fetch is recorded
                window._ftbEnableCapture();
                setTimeout(function(){ window._ftbDisableCapture(); }, 4000);
                // let X retry (it will fetch the m3u8), then grab the URL for this tweet
                setTimeout(function(){
                  var u = _findUrlForButton(el);
                  console.log('[FreeTheBird] reload-video ' + (u||''));
                }, 600);
                el.textContent = 'Opening…';
                setTimeout(function(){ try{ el.textContent='Reload'; }catch(e){} }, 2500);
                return false;
              }, true);
            });
            if(found) console.log('[FreeTheBird] hooked ' + found + ' Reload button(s)');
          }
          var obs = new MutationObserver(hookReload);
          obs.observe(document.documentElement, {childList:true, subtree:true});
          hookReload();
          setInterval(hookReload, 1500);
          console.log('[FreeTheBird] reload hook installed (per-tweet mode)');
        })();
        """
        rp = QWebEngineScript()
        rp.setName("reload_patch")
        rp.setSourceCode(RELOAD_JS)
        rp.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        rp.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        rp.setRunsOnSubFrames(True)
        self.profile.scripts().insert(rp)

        # JS → Python bridge for the hijacked Reload buttons
        def _js_console(level, msg, line, src_id):
            try:
                if "[FreeTheBird] reload-video" in msg:
                    raw = msg.split("reload-video", 1)[1].strip()
                    url = ""
                    if raw:
                        # raw may be empty or just whitespace
                        parts = raw.split()
                        if parts:
                            url = parts[0]
                    if not url or not url.startswith("http"):
                        url = getattr(self, "_last_video_url", "") or getattr(self.ad_interceptor, "last_video_url", "")
                    if not url or url == "":
                        # last attempt: pull from JS state
                        def _got(v):
                            if v and v.startswith("http"):
                                self.status_label.setText(f"Got video URL, opening…")
                                self._play_video(v)
                            else:
                                all_urls = ""
                                try:
                                    all_urls = getattr(self.ad_interceptor, "last_video_url", "") or getattr(self, "_last_video_url", "")
                                except Exception:
                                    pass
                                msg2 = "No video URL found for this tweet.\n\nCaptured: %s\nTry scrolling the tweet into view, wait for 📹 next to Translate, then click Reload again." % (all_urls[:120] if all_urls else "none")
                                QMessageBox.information(self, "Video", msg2)
                                self.status_label.setText("No video URL — open tweet & wait for 📹")
                        try:
                            self.page.runJavaScript("(window._ftbLastVideoUrl||window._ftbAllVideoUrls[window._ftbAllVideoUrls.length-1]||'')", _got)
                        except Exception:
                            pass
                        return
                    self.status_label.setText(f"Opening: {url[:70]}")
                    self._play_video(url)
                    return
                if "[FreeTheBird] captured" in msg or "[FreeTheBird] hooked" in msg or "reload hook" in msg:
                    # silent — diagnostic, don't spam status bar
                    return
                elif "[FreeTheBird]" in msg:
                    if "lastVideoUrl" not in msg:
                        self.status_label.setText(msg[:160])
            except Exception as e:
                try:
                    self.status_label.setText(f"Bridge error: {e}")
                except Exception:
                    pass
        self.page._console_handler = _js_console

        self.browser = QWebEngineView()
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)
        self.browser.titleChanged.connect(self._on_title_changed)
        self.browser.loadStarted.connect(self._on_load_started)
        self.browser.loadFinished.connect(self._on_load_finished)

        # -- Restore saved zoom level --
        saved_zoom = self.cfg.get("zoom", 1.0)
        if saved_zoom != 1.0:
            self.browser.setZoomFactor(saved_zoom)

        # -- Fetch public IP (sync, before building menus) --
        # -- Build UI components (IP shows "..." until async fetch completes) --
        self._create_menubar()
        self._create_toolbar()
        self._create_tray()
        self._setup_shortcuts()

        # -- Auto-refresh timer --
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._do_refresh)
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)

        # -- Apply theme and show initial status --
        self._apply_theme()
        self._update_status()

        # -- Fetch IP and connection info in background --
        threading.Thread(target=self._fetch_ip_and_conn_info, daemon=True).start()

    # -------------------------------------------------------------------------
    # INTERNATIONALISATION
    # -------------------------------------------------------------------------

    def t(self, key):
        """Get translated string for the current language."""
        return STRINGS.get(self.lang, STRINGS["es"]).get(key, key)

    # -------------------------------------------------------------------------
    # NETWORK — IP & connection info
    # -------------------------------------------------------------------------

    def _fetch_ip_and_conn_info(self):
        """Fetch public IP and connection info in background thread.

        Tries multiple services for IP, then fetches geolocation.
        Updates the IP menu from the main thread via QTimer.singleShot.
        """
        services = [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ]
        for url in services:
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "curl/7.0")
                ip = urllib.request.urlopen(req, timeout=3).read().decode("utf-8").strip()
                if ip and len(ip) < 46:  # Valid IPv4 or IPv6
                    self.current_ip = ip
                    QTimer.singleShot(0, self._update_ip_menu)
                    break
            except (ssl.SSLError, ssl.CertificateError):
                continue
            except Exception:
                continue
        else:
            self.current_ip = "--"
            QTimer.singleShot(0, self._update_ip_menu)

        if self.current_ip != "--":
            self._fetch_conn_info()

    def _fetch_conn_info(self):
        """Fetch detailed connection info (ISP, location) in background thread.

        Tries ipwho.is first (HTTPS, no API key), then ipapi.co,
        then ip-api.com (HTTP only) as last resort.
        Normalizes all responses to a common format so _show_connection_info()
        works regardless of which service responded.

        Uses QTimer.singleShot(0) to safely update self.conn_info from
        the main thread, avoiding race conditions with _show_connection_info().
        """
        safe_ip = urllib.parse.quote(self.current_ip, safe="")
        services = [
            (f"https://ipwho.is/{safe_ip}", self._normalize_ipwho_is),
            (f"https://ipapi.co/{safe_ip}/json/", self._normalize_ipapi_co),
            (f"http://ip-api.com/json/{safe_ip}", self._normalize_ip_api_com),
        ]
        for url, normalize in services:
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "curl/7.0")
                response = urllib.request.urlopen(req, timeout=8)
                raw = json.loads(response.read().decode("utf-8"))
                data = normalize(raw)
                if data:
                    self.conn_info = data
                    return
            except (ssl.SSLError, ssl.CertificateError):
                continue
            except Exception:
                continue
        self.conn_info = None

    @staticmethod
    def _normalize_ipwho_is(raw):
        """Normalize ipwho.is response to common format (ipapi.co keys)."""
        if not raw.get("success"):
            return None
        conn = raw.get("connection", {})
        return {
            "org": conn.get("isp") or conn.get("org") or "--",
            "asn": f"AS{conn.get('asn', '--')}",
            "country_name": raw.get("country", "--"),
            "region": raw.get("region", "--"),
            "city": raw.get("city", "--"),
            "postal": raw.get("postal", "--"),
            "timezone": raw.get("timezone", {}).get("id", "--"),
            "latitude": raw.get("latitude", "--"),
            "longitude": raw.get("longitude", "--"),
        }

    @staticmethod
    def _normalize_ipapi_co(raw):
        """Normalize ipapi.co response to common format."""
        if raw.get("error"):
            return None
        return raw

    @staticmethod
    def _normalize_ip_api_com(raw):
        """Normalize ip-api.com response to common format (ipapi.co keys)."""
        if raw.get("status") != "success":
            return None
        return {
            "org": raw.get("isp", "--"),
            "asn": raw.get("as", "--"),
            "country_name": raw.get("country", "--"),
            "region": raw.get("regionName", "--"),
            "city": raw.get("city", "--"),
            "postal": raw.get("zip", "--"),
            "timezone": raw.get("timezone", "--"),
            "latitude": raw.get("lat", "--"),
            "longitude": raw.get("lon", "--"),
        }

    def _update_ip_menu(self):
        """Update the IP menu title from the main thread."""
        self.ip_menu.setTitle(f"🌐 IP: {self.current_ip}")

    def _show_connection_info(self):
        """Display connection details dialog (IP, ISP, geolocation)."""
        data = self.conn_info
        if data and not data.get("error"):
            info = "\n".join([
                f"{self.t('conn_ip')}: {self.current_ip}\n",
                f"{self.t('conn_isp')}: {data.get('org', '--')}",
                f"AS: {data.get('asn', '--')}\n",
                f"{self.t('conn_country')}: {data.get('country_name', '--')}",
                f"{self.t('conn_region')}: {data.get('region', '--')}",
                f"{self.t('conn_city')}: {data.get('city', '--')}",
                f"{self.t('conn_zip')}: {data.get('postal', '--')}",
                f"{self.t('conn_tz')}: {data.get('timezone', '--')}\n",
                f"{self.t('conn_lat')}: {data.get('latitude', '--')}",
                f"{self.t('conn_lon')}: {data.get('longitude', '--')}",
            ])
        else:
            info = f"{self.t('conn_ip')}: {self.current_ip}\n\n{self.t('conn_error')}"

        msg = QMessageBox(self)
        msg.setWindowTitle(self.t("conn_title"))
        msg.setText(info)
        if self.dark_mode:
            msg.setStyleSheet(DARK_DIALOG)
        msg.exec()

    # -------------------------------------------------------------------------
    # NOTIFICATIONS — Detect new notifications from page title
    # -------------------------------------------------------------------------

    def _on_title_changed(self, title):
        """Parse the page title for notification counts.

        X shows notifications as "(3) Home / X" in the title.
        When detected and the window is not active, a system
        notification is sent via the tray icon.
        """
        self.setWindowTitle(f"{APP_NAME} \u2014 {title}" if title else APP_NAME)

        if title and title != self.last_title:
            if title.startswith("(") and ")" in title:
                count_str = title[1:title.index(")")]
                if count_str.isdigit() and not self.isActiveWindow() and self.tray:
                    self.tray.showMessage(
                        APP_NAME, self.t("new_notif"),
                        QSystemTrayIcon.MessageIcon.Information, 5000,
                    )
        self.last_title = title

    # -------------------------------------------------------------------------
    # LOADING INDICATOR — Visual feedback during page load
    # -------------------------------------------------------------------------

    def _on_load_started(self):
        """Show loading indicator in the status bar."""
        self.status_label.setText(self.t("loading"))

    def _on_load_finished(self, ok):
        """Clear loading indicator when page finishes loading."""
        self._update_status()
        # sync sponsor block toggle (JS defaults to enabled)
        try:
            if not self.cfg.get("sponsor_block", True):
                self.page.runJavaScript("window._ftbSponsorSet && window._ftbSponsorSet(false);")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # THEME — Dark/light mode switching
    # -------------------------------------------------------------------------

    def _apply_theme(self):
        """Apply the current theme stylesheet to the entire window."""
        self.setStyleSheet(DARK_STYLE if self.dark_mode else LIGHT_STYLE)

    def _toggle_theme(self):
        """Switch between dark and light mode.

        Updates the theme action text in-place (no widget destruction).
        """
        self.dark_mode = not self.dark_mode
        self._apply_theme()
        self._save_state()
        label = self.t("light_mode") if self.dark_mode else self.t("dark_mode")
        self.theme_action.setText(label)

    def _toggle_tray(self, checked):
        """Enable/disable minimize-to-tray. Persists to config and updates app quit behavior."""
        self.tray_enabled = checked
        self.cfg["tray_enabled"] = checked
        save_config(self.cfg)
        QApplication.setQuitOnLastWindowClosed(not checked)
        if checked:
            if not self.tray:
                self._create_tray()
                # re-apply language to new tray menu if needed
                if hasattr(self, 'tray') and self.tray:
                    self.tray.show()
        else:
            if self.tray:
                try:
                    self.tray.hide()
                except Exception:
                    pass
                self.tray = None

    def _toggle_sponsor_block(self, checked):
        """Toggle sponsor block (Promoted by hide). Persists and updates live page."""
        self.cfg["sponsor_block"] = checked
        save_config(self.cfg)
        try:
            # window._ftbSponsorSet is defined by SPONSOR_BLOCK_JS
            js = f"window._ftbSponsorSet && window._ftbSponsorSet({str(checked).lower()});"
            self.page.runJavaScript(js)
        except Exception:
            pass
        self.status_label.setText("Sponsors hidden" if checked else "Sponsors shown")
        QTimer.singleShot(2000, self._update_status)

    # -------------------------------------------------------------------------
    # LANGUAGE — Hot-swap between Spanish and English
    #
    # CRITICAL: All UI updates use setText()/setTitle() on existing widgets.
    # Destroying and recreating widgets causes segfaults when QtWebEngine
    # is running alongside Chrome/Chromium (shared Chromium IPC resources).
    # -------------------------------------------------------------------------

    def _toggle_language(self):
        """Switch interface language without restarting the application.

        Updates all visible text in the menubar, toolbar, and system tray
        by calling setText()/setTitle() on stored widget references.
        No widgets are destroyed or recreated — this is critical to avoid
        segfaults with QtWebEngine.
        """
        self.lang = "en" if self.lang == "es" else "es"
        self.cfg["lang"] = self.lang
        save_config(self.cfg)

        # -- Toolbar texts --
        self.home_action.setText(self.t("home"))
        self.refresh_action.setText(self.t("refresh"))
        self.interval_label.setText(self.t("interval"))
        self.privacy_label.setText(self.t("privacy_on"))
        self.translate_action.setText(self.t("translate"))
        self._update_status()

        # -- Menubar texts --
        self.view_menu.setTitle(self.t("view"))
        theme_label = self.t("light_mode") if self.dark_mode else self.t("dark_mode")
        self.theme_action.setText(theme_label)
        self.ip_menu.setTitle(f"\U0001f310 IP: {self.current_ip}")
        self.conn_action.setText(self.t("conn_details"))
        lang_indicator = "\u2705ES | EN" if self.lang == "es" else "ES | \u2705EN"
        self.lang_menu.setTitle(lang_indicator)
        self.switch_action.setText(self.t("switch_to"))

        # -- System tray texts --
        if getattr(self, "tray_show", None):
            self.tray_show.setText(self.t("show_hide"))
        if getattr(self, "tray_refresh", None):
            self.tray_refresh.setText(self.t("refresh_now"))
        if getattr(self, "tray_quit", None):
            self.tray_quit.setText(self.t("quit"))

        # -- Session menu --
        self.session_menu.setTitle(self.t("session_menu"))

        # -- Tray toggle --
        self.tray_toggle_action.setText(self.t("tray_toggle"))
        if hasattr(self, "sponsor_toggle_action"):
            self.sponsor_toggle_action.setText(self.t("sponsor_block"))

        # -- Credit menu --
        credit_label = "Por @daboblog" if self.lang == "es" else "By @daboblog"
        self.credit_menu.setTitle(f"\U0001f512 {credit_label}")

    # -------------------------------------------------------------------------
    # TRANSLATOR — Translate selected text without leaving the app
    # -------------------------------------------------------------------------

    def _translate_selection(self):
        """Grab selected text from the page and translate it."""
        self.browser.page().runJavaScript(
            "window.getSelection().toString()", self._do_translate
        )

    def _do_translate(self, text):
        """Perform translation via Google Translate API in a background thread."""
        if not text or not text.strip():
            return

        self.status_label.setText("...")
        original = text.strip()[:200]
        target_lang = "es" if self.lang == "es" else "en"

        def fetch():
            try:
                encoded = urllib.parse.quote(original)
                url = (
                    "https://translate.googleapis.com/translate_a/single"
                    f"?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded}"
                )
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "Mozilla/5.0")
                data = json.loads(
                    urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
                )
                translated = "".join(part[0] for part in data[0] if part[0])
                QTimer.singleShot(0, lambda: self._show_translation(translated, original))
            except (ssl.SSLError, ssl.CertificateError):
                QTimer.singleShot(0, self._on_translate_error)
            except Exception:
                QTimer.singleShot(0, self._on_translate_error)

        threading.Thread(target=fetch, daemon=True).start()

    def _show_translation(self, translated, original):
        """Display translation result dialog (called from main thread)."""
        self._update_status()
        msg = QMessageBox(self)
        msg.setWindowTitle(self.t("translate_title"))
        msg.setText(translated)
        msg.setInformativeText(f"{self.t('translate_original')}: {original}")
        if self.dark_mode:
            msg.setStyleSheet(DARK_DIALOG)
        msg.exec()

    def _on_translate_error(self):
        """Handle translation error (called from main thread)."""
        self.status_label.setText(self.t("translate_error"))
        QTimer.singleShot(3000, self._update_status)

    # -------------------------------------------------------------------------
    # PRIVACY INFO — Show blocking stats to the user
    # -------------------------------------------------------------------------

    def _show_privacy_info(self):
        """Display privacy information dialog with blocking statistics."""
        info = self.t("privacy_body").format(
            app=APP_NAME,
            count=len(AD_DOMAINS),
            blocked=self.ad_interceptor.blocked_count,
        )
        msg = QMessageBox(self)
        msg.setWindowTitle(self.t("privacy_title"))
        msg.setText(info)
        if self.dark_mode:
            msg.setStyleSheet(DARK_DIALOG)
        msg.exec()

    # -------------------------------------------------------------------------
    # PURGE — Emergency cache reset (development tool)
    # -------------------------------------------------------------------------

    def _on_video_captured(self, url):
        """Called from interceptor when a video URL is seen — store for Reload handling (no UI spam)."""
        try:
            self._last_video_url = url
        except Exception:
            pass

    def _decoder_script(self):
        """Path to video_decoder.py in the same folder as freethebird.py."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_decoder.py")

    def _play_video(self, url):
        """Launch the separate video_decoder.py pop-out player (has full controls)."""
        url = (url or "").strip()
        if not url or not url.startswith("http"):
            url = getattr(self, "_last_video_url", "") or getattr(self.ad_interceptor, "last_video_url", "")
        if not url or not url.startswith("http"):
            QMessageBox.information(self, "Video",
                "No video URL captured for this tweet.\n\n"
                "1) Scroll the video tweet fully into view\n"
                "2) Wait for 📹 to appear next to Translate\n"
                "3) Click Reload again\n\n"
                "If it still fails, the video may have expired.")
            self.status_label.setText("No video URL — wait for 📹")
            QTimer.singleShot(4000, self._update_status)
            return
        script = self._decoder_script()
        if not os.path.isfile(script):
            QMessageBox.critical(self, "Video", "video_decoder.py not found next to freethebird.py:\n" + script)
            return
        # sanity: does it look like an X video URL?
        if "video.twimg.com" not in url and ".m3u8" not in url and ".mp4" not in url:
            # still try — X sometimes serves via other CDNs
            pass
        self.status_label.setText(f"Launching decoder: {url[:65]}…")
        try:
            # use Popen so main window stays responsive; decoder shows its own status
            subprocess.Popen([sys.executable, script, url],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.status_label.setText("Decoder launched — player window should appear")
        except Exception as e:
            QMessageBox.critical(self, "Video", f"Could not launch decoder:\n{e}\n\n{script} {url}")
            self.status_label.setText("Launch failed")
        QTimer.singleShot(3500, self._update_status)

    def _on_download_requested(self, download):
        """Handle downloads (images, etc.) — ask user where to save, default Downloads.
        X serves pbs.twimg.com/media/...?format=jpg without extension, so we infer it."""
        try:
            suggested = ""
            try:
                suggested = download.downloadFileName() or ""
            except Exception:
                pass
            url_str = ""
            try:
                url_str = download.url().toString()
            except Exception:
                try:
                    url_str = download.url().path()
                except Exception:
                    pass
            # fallback to url basename if suggested empty
            if not suggested:
                try:
                    suggested = os.path.basename(urllib.parse.urlparse(url_str).path) or "image"
                except Exception:
                    suggested = "image"
            # strip query artefacts like "?format=jpg"
            suggested = suggested.split("?")[0].split("&")[0]
            # infer extension if missing
            ext = os.path.splitext(suggested)[1].lower()
            if not ext:
                # 1) mimeType hint from Qt
                try:
                    mime = download.mimeType() if hasattr(download, "mimeType") else ""
                    mime_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "video/mp4": ".mp4"}
                    if mime in mime_map:
                        ext = mime_map[mime]
                except Exception:
                    pass
                # 2) url query format=jpg / format=png
                if not ext:
                    try:
                        q = urllib.parse.parse_qs(urllib.parse.urlparse(url_str).query)
                        fmt = (q.get("format") or [""])[0].lower()
                        if fmt in ("jpg", "jpeg"):
                            ext = ".jpg"
                        elif fmt in ("png", "webp", "gif", "mp4"):
                            ext = "." + fmt
                    except Exception:
                        pass
                # 3) path suffix fallback
                if not ext:
                    try:
                        path_ext = os.path.splitext(urllib.parse.urlparse(url_str).path)[1]
                        if path_ext:
                            ext = path_ext
                    except Exception:
                        pass
                if not ext:
                    ext = ".jpg"
                suggested = suggested + ext
            dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(dl_dir):
                dl_dir = os.path.expanduser("~")
            default_path = os.path.join(dl_dir, suggested)
            filt = "Images (*.jpg *.jpeg *.png *.webp *.gif);;Videos (*.mp4 *.m3u8);;All files (*)"
            path, selected = QFileDialog.getSaveFileName(self, "Save as", default_path, filt)
            if not path:
                download.cancel()
                return
            # if user removed extension, re-add from default
            if not os.path.splitext(path)[1]:
                path = path + ext
            try:
                download.setDownloadDirectory(os.path.dirname(path) or dl_dir)
                download.setDownloadFileName(os.path.basename(path))
            except Exception:
                try:
                    download.setPath(path)
                except Exception:
                    pass
            download.accept()
            self.status_label.setText(f"Downloading {os.path.basename(path)}...")
            # finished signal is isFinishedChanged in Qt6, fallback to stateChanged
            try:
                download.isFinishedChanged.connect(lambda: self.status_label.setText(f"Saved {os.path.basename(path)}") if download.isFinished() else None)
            except Exception:
                try:
                    download.stateChanged.connect(lambda s: self.status_label.setText(f"Saved {os.path.basename(path)}"))
                except Exception:
                    pass
            QTimer.singleShot(6000, self._update_status)
        except Exception as e:
            try:
                download.cancel()
            except Exception:
                pass
            self.status_label.setText(f"Download failed: {e}")
            QTimer.singleShot(3000, self._update_status)

    def _purge_and_restart(self):
        """Purge local app/QtWebEngine state and restart the application."""
        if self.tray:
            self.tray.hide()
        do_purge()

        python = sys.executable
        args = [python] + sys.argv
        subprocess.Popen(args)
        QApplication.quit()


    # -------------------------------------------------------------------------
    # SESSION IMPORT — Bypass embedded-login block by importing cookies from real browser
    # X often blocks QtWebEngine logins ("not allowed to log in at this time").
    # Logging in on real Chrome then pasting cookies here is 100% reliable.
    # -------------------------------------------------------------------------

    def _import_session_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.t("import_title"))
        dlg.resize(620, 420)
        lay = QVBoxLayout(dlg)
        lab = QLabel(self.t("import_instructions"))
        lab.setWordWrap(True)
        lay.addWidget(lab)
        edit = QTextEdit()
        edit.setPlaceholderText("auth_token=...; ct0=...  or  auth_token: ...  or  JSON  or  cookies.txt")
        lay.addWidget(edit)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        # Add "Open in browser" helper button
        open_btn = QPushButton(self.t("open_browser_login"))
        def _open_login():
            QDesktopServices.openUrl(QUrl("https://x.com/login"))
        open_btn.clicked.connect(_open_login)
        btns.addButton(open_btn, QDialogButtonBox.ButtonRole.ActionRole)
        lay.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        text = edit.toPlainText().strip()
        if not text:
            return
        ok = self._apply_cookies_from_text(text)
        msg = QMessageBox(self)
        msg.setWindowTitle(self.t("import_title"))
        if ok:
            msg.setText(self.t("import_ok"))
            if self.dark_mode:
                msg.setStyleSheet(DARK_DIALOG)
            msg.exec()
            self.browser.setUrl(QUrl("https://x.com/home"))
            self.browser.reload()
        else:
            msg.setText(self.t("import_fail"))
            if self.dark_mode:
                msg.setStyleSheet(DARK_DIALOG)
            msg.exec()

    def _apply_cookies_from_text(self, text):
        cookies = []
        t = text.strip()
        if not t:
            return False
        # 1) JSON array/object
        if t.startswith("[") or t.startswith("{"):
            try:
                data = json.loads(t)
                if isinstance(data, dict):
                    data = [data]
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("name")
                    value = entry.get("value")
                    if not name or value is None:
                        continue
                    c = QNetworkCookie(str(name).encode(), str(value).encode())
                    domain = str(entry.get("domain", ".x.com"))
                    if not domain.startswith("."):
                        domain = "." + domain
                    c.setDomain(domain)
                    c.setPath(str(entry.get("path", "/")))
                    if entry.get("secure"):
                        c.setSecure(True)
                    if entry.get("httpOnly"):
                        c.setHttpOnly(True)
                    cookies.append(c)
                    # mirror for twitter.com if x.com cookie
                    if "x.com" in domain:
                        c2 = QNetworkCookie(str(name).encode(), str(value).encode())
                        c2.setDomain(domain.replace("x.com", "twitter.com"))
                        c2.setPath(str(entry.get("path", "/")))
                        cookies.append(c2)
            except Exception:
                pass
        # 2) Netscape cookies.txt (tab-separated)
        if not cookies and "\t" in t:
            for line in t.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    domain, flag, path, secure, expiry, name, value = parts[:7]
                    c = QNetworkCookie(name.encode(), value.encode())
                    c.setDomain(domain)
                    c.setPath(path)
                    if secure.upper() == "TRUE":
                        c.setSecure(True)
                    cookies.append(c)
                elif len(parts) == 6:
                    # some exports omit flag
                    try:
                        domain, path, secure, expiry, name, value = parts[:6]
                        c = QNetworkCookie(name.encode(), value.encode())
                        c.setDomain(domain)
                        c.setPath(path)
                        cookies.append(c)
                    except Exception:
                        continue
        # 3) Raw Cookie header: "a=1; b=2" or "auth_token: xxx, ct0: yyy" or bare hex value
        if not cookies:
            # avoid treating JSON as header
            if not t.startswith("["):
                # split on ; , or newline
                parts = re.split(r'[;\n]+', t)
                # also handle comma-separated if no semicolon present
                if len(parts) == 1 and "," in t and "=" not in t and ":" in t:
                    parts = re.split(r'[,\n]+', t)
                for part in parts:
                    part = part.strip().strip(",")
                    if not part:
                        continue
                    # support both "=" and ":" separators
                    if "=" in part:
                        name, value = part.split("=", 1)
                    elif ":" in part:
                        name, value = part.split(":", 1)
                    elif re.fullmatch(r'[a-fA-F0-9]{32,64}', part):
                        # bare hex token — assume auth_token
                        name, value = "auth_token", part
                    else:
                        continue
                    name = name.strip().strip('"').strip("'")
                    value = value.strip().strip('"').strip("'").strip(",")
                    if not name or not value:
                        continue
                    # normalize common names
                    name = name.strip()
                    for dom in (".x.com", ".twitter.com"):
                        c = QNetworkCookie(name.encode(), value.encode())
                        c.setDomain(dom)
                        c.setPath("/")
                        c.setSecure(True)
                        cookies.append(c)
                # fallback: regex extract auth_token/ct0 even from messy paste
                if not cookies:
                    for m in re.finditer(r'(auth_token|ct0)\s*[:=]\s*([a-fA-F0-9%]{20,})', t):
                        name, value = m.group(1), m.group(2)
                        for dom in (".x.com", ".twitter.com"):
                            c = QNetworkCookie(name.encode(), value.encode())
                            c.setDomain(dom)
                            c.setPath("/")
                            c.setSecure(True)
                            cookies.append(c)
        if not cookies:
            return False
        # Make cookies persistent (otherwise session cookies vanish on close)
        far_future = QDateTime.currentDateTime().addDays(400)
        for c in cookies:
            if c.expirationDate().isNull() or c.expirationDate() < QDateTime.currentDateTime():
                c.setExpirationDate(far_future)
            c.setSecure(True)
            c.setHttpOnly(False)
        store = self.profile.cookieStore()
        for c in cookies:
            dom = c.domain() or ".x.com"
            url = QUrl(f"https://{dom.lstrip('.')}/")
            try:
                store.setCookie(c, url)
            except Exception:
                # fallback: try with QUrl https://x.com/
                try:
                    store.setCookie(c, QUrl("https://x.com/"))
                except Exception:
                    pass
        return True

    # -------------------------------------------------------------------------
    # MENUBAR — Top menu with all app features
    # -------------------------------------------------------------------------

    def _create_menubar(self):
        """Build the menu bar.

        All menu and action references are stored as instance attributes
        so _toggle_language() can update their text in-place without
        destroying/recreating widgets (which crashes QtWebEngine).

        Menu order: Vista | IP | ES/EN | EFF | @daboblog | GNU/Linux
        """
        mb = self.menuBar()

        # -- View menu (theme toggle + tray toggle + video diag) --
        self.view_menu = mb.addMenu(self.t("view"))
        theme_label = self.t("light_mode") if self.dark_mode else self.t("dark_mode")
        self.theme_action = self.view_menu.addAction(theme_label)
        self.theme_action.triggered.connect(self._toggle_theme)
        self.view_menu.addSeparator()
        self.tray_toggle_action = QAction(self.t("tray_toggle"), self)
        self.tray_toggle_action.setCheckable(True)
        self.tray_toggle_action.setChecked(self.tray_enabled)
        self.tray_toggle_action.toggled.connect(self._toggle_tray)
        self.view_menu.addAction(self.tray_toggle_action)
        self.sponsor_toggle_action = QAction(self.t("sponsor_block"), self)
        self.sponsor_toggle_action.setCheckable(True)
        self.sponsor_toggle_action.setChecked(self.cfg.get("sponsor_block", True))
        self.sponsor_toggle_action.toggled.connect(self._toggle_sponsor_block)
        self.view_menu.addAction(self.sponsor_toggle_action)
        self.view_menu.addSeparator()
        # -- IP menu (connection info) --
        self.ip_menu = mb.addMenu(f"\U0001f310 IP: {self.current_ip}")
        self.conn_action = self.ip_menu.addAction(self.t("conn_details"))
        self.conn_action.triggered.connect(self._show_connection_info)

        # -- Language selector --
        lang_indicator = "\u2705ES | EN" if self.lang == "es" else "ES | \u2705EN"
        self.lang_menu = mb.addMenu(lang_indicator)
        self.switch_action = self.lang_menu.addAction(self.t("switch_to"))
        self.switch_action.triggered.connect(self._toggle_language)

        # -- EFF (Electronic Frontier Foundation) --
        eff_menu = mb.addMenu("\u270a EFF")
        eff_action = eff_menu.addAction("EFF - Privacy")
        eff_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.eff.org/issues/privacy")
            )
        )

        # -- Author credit --
        credit_label = "Por @daboblog" if self.lang == "es" else "By @daboblog"
        self.credit_menu = mb.addMenu(f"\U0001f512 {credit_label}")
        x_action = self.credit_menu.addAction("@daboblog en X")
        x_action.triggered.connect(
            lambda: self.browser.setUrl(QUrl("https://x.com/daboblog"))
        )
        bsky_action = self.credit_menu.addAction("@daboblog en Bluesky")
        bsky_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://bsky.app/profile/daboblog.bsky.social")
            )
        )

        # -- Session menu (import from real browser) --
        self.session_menu = mb.addMenu(self.t("session_menu"))
        import_action = self.session_menu.addAction(self.t("import_session"))
        import_action.triggered.connect(self._import_session_dialog)
        open_login_action = self.session_menu.addAction(self.t("open_browser_login"))
        open_login_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://x.com/login")))

        # -- GNU/Linux love (rightmost) --
        gnu_menu = mb.addMenu("I \u2764\ufe0f GNU/Linux")
        gnu_es = gnu_menu.addAction("Wikipedia (ES)")
        gnu_es.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://es.wikipedia.org/wiki/GNU/Linux")
            )
        )
        gnu_en = gnu_menu.addAction("Wikipedia (EN)")
        gnu_en.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://en.wikipedia.org/wiki/GNU/Linux")
            )
        )

    # -------------------------------------------------------------------------
    # TOOLBAR — Bottom control bar
    # -------------------------------------------------------------------------

    def _create_toolbar(self):
        """Build the bottom toolbar with navigation and status controls.

        All action/label references are stored as instance attributes
        for in-place text updates during language switching.
        """
        tb = QToolBar("Controls")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, tb)

        # Navigation
        self.back_action = QAction("◀", self)
        self.back_action.setToolTip("Back (Alt+Left)")
        self.back_action.triggered.connect(self.browser.back)
        tb.addAction(self.back_action)

        self.forward_action = QAction("▶", self)
        self.forward_action.setToolTip("Forward (Alt+Right)")
        self.forward_action.triggered.connect(self.browser.forward)
        tb.addAction(self.forward_action)

        tb.addSeparator()

        self.home_action = QAction(self.t("home"), self)
        self.home_action.triggered.connect(
            lambda: self.browser.setUrl(QUrl("https://x.com/home"))
        )
        tb.addAction(self.home_action)

        self.refresh_action = QAction(self.t("refresh"), self)
        self.refresh_action.triggered.connect(self._do_refresh)
        tb.addAction(self.refresh_action)

        tb.addSeparator()

        # Auto-refresh toggle
        self.toggle_action = QAction(self.t("auto_on"), self)
        self.toggle_action.triggered.connect(self._toggle_auto_refresh)
        tb.addAction(self.toggle_action)

        # Interval spinner
        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(4, 0, 4, 0)
        self.interval_label = QLabel(self.t("interval"))
        interval_layout.addWidget(self.interval_label)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 3600)
        self.interval_spin.setSuffix("s")
        self.interval_spin.setValue(self.refresh_interval)
        self.interval_spin.valueChanged.connect(self._interval_changed)
        interval_layout.addWidget(self.interval_spin)
        interval_action = QWidgetAction(self)
        interval_action.setDefaultWidget(interval_widget)
        tb.addAction(interval_action)

        tb.addSeparator()

        # Zoom controls
        zoom_out = QAction(" \u2014 ", self)
        zoom_out.triggered.connect(self._zoom_out)
        tb.addAction(zoom_out)
        zoom_in = QAction(" + ", self)
        zoom_in.triggered.connect(self._zoom_in)
        tb.addAction(zoom_in)

        tb.addSeparator()

        # Privacy indicator (clickable)
        self.privacy_label = QLabel(
            self.t("privacy_on") if self.privacy_enabled else "Privacidad: OFF"
        )
        self.privacy_label.setStyleSheet(
            "padding: 0 4px; color: #2ecc71;" if self.privacy_enabled
            else "padding: 0 4px; color: #e74c3c;"
        )
        self.privacy_label.mousePressEvent = lambda e: self._show_privacy_info()
        tb.addWidget(self.privacy_label)

        tb.addSeparator()

        # Translate button
        self.translate_action = QAction(self.t("translate"), self)
        self.translate_action.triggered.connect(self._translate_selection)
        tb.addAction(self.translate_action)

        tb.addSeparator()

        # Status label (rightmost)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("padding: 0 8px; color: #888;")
        tb.addWidget(self.status_label)

        # Find bar (hidden by default, toggled with Ctrl+F)
        self.find_separator = tb.addSeparator()
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Ctrl+F")
        self.find_input.setMaximumWidth(200)
        self.find_input.textChanged.connect(self._find_in_page)
        self.find_input_action = tb.addWidget(self.find_input)
        self.find_separator.setVisible(False)
        self.find_input.setVisible(False)

    # -------------------------------------------------------------------------
    # FIND IN PAGE — Search text within the current page
    # -------------------------------------------------------------------------

    def _toggle_find_bar(self):
        """Show or hide the find bar and focus the input."""
        visible = not self.find_input.isVisible()
        self.find_separator.setVisible(visible)
        self.find_input.setVisible(visible)
        if visible:
            self.find_input.setFocus()
            self.find_input.selectAll()
        else:
            self.find_input.clear()
            self.browser.findText("")

    def _close_find_bar(self):
        """Hide the find bar and clear search highlights."""
        if self.find_input.isVisible():
            self.find_separator.setVisible(False)
            self.find_input.setVisible(False)
            self.find_input.clear()
            self.browser.findText("")

    def _find_in_page(self, text):
        """Search for text in the current page."""
        self.browser.findText(text)

    # -------------------------------------------------------------------------
    # SYSTEM TRAY — Minimize to tray, notifications
    # -------------------------------------------------------------------------

    def _create_tray(self):
        """Create the system tray icon and its context menu."""
        if not self.tray_enabled:
            self.tray = None
            self.tray_toggle = None
            self.tray_show = None
            self.tray_refresh = None
            self.tray_quit = None
            return
        self.tray = QSystemTrayIcon(self.app_icon, self)
        self._create_tray_menu()
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _create_tray_menu(self):
        """Build the tray context menu.

        References are stored for in-place text updates during
        language switching (no widget destruction).
        """
        menu = QMenu()
        self.tray_show = menu.addAction(self.t("show_hide"))
        self.tray_show.triggered.connect(self._toggle_visibility)
        self.tray_refresh = menu.addAction(self.t("refresh_now"))
        self.tray_refresh.triggered.connect(self._do_refresh)
        self.tray_toggle = menu.addAction(self.t("auto_on"))
        self.tray_toggle.triggered.connect(self._toggle_auto_refresh)
        menu.addSeparator()
        self.tray_quit = menu.addAction(self.t("quit"))
        self.tray_quit.triggered.connect(QApplication.quit)
        self.tray.setContextMenu(menu)

    # -------------------------------------------------------------------------
    # KEYBOARD SHORTCUTS
    # -------------------------------------------------------------------------

    def _setup_shortcuts(self):
        """Register global keyboard shortcuts.

        F5          — Refresh page
        Ctrl+R      — Toggle auto-refresh
        Ctrl+H      — Go to Home/Timeline
        Ctrl+M      — Go to Messages
        Ctrl+N      — Go to Notifications
        Ctrl+T      — Translate selected text
        Ctrl+F      — Find in page
        Ctrl+Q      — Quit application
        F11         — Toggle fullscreen
        Ctrl++/=    — Zoom in
        Ctrl+-      — Zoom out
        Ctrl+0      — Reset zoom to 100%
        Escape      — Close find bar
        """
        QShortcut(QKeySequence("F5"), self, self._do_refresh)
        QShortcut(QKeySequence("Ctrl+R"), self, self._toggle_auto_refresh)
        QShortcut(QKeySequence("Alt+Left"), self, self.browser.back)
        QShortcut(QKeySequence("Alt+Right"), self, self.browser.forward)
        QShortcut(QKeySequence("Back"), self, self.browser.back)
        QShortcut(QKeySequence("Forward"), self, self.browser.forward)
        QShortcut(QKeySequence("Ctrl+H"), self,
                  lambda: self.browser.setUrl(QUrl("https://x.com/home")))
        QShortcut(QKeySequence("Ctrl+Q"), self, QApplication.quit)
        QShortcut(QKeySequence("Ctrl+M"), self,
                  lambda: self.browser.setUrl(QUrl("https://x.com/messages")))
        QShortcut(QKeySequence("Ctrl+N"), self,
                  lambda: self.browser.setUrl(QUrl("https://x.com/notifications")))
        QShortcut(QKeySequence("Ctrl+T"), self, self._translate_selection)
        QShortcut(QKeySequence("Ctrl+F"), self, self._toggle_find_bar)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self._zoom_reset)
        QShortcut(QKeySequence("Escape"), self, self._close_find_bar)

    # -------------------------------------------------------------------------
    # ACTIONS — Refresh, zoom, auto-refresh, visibility
    # -------------------------------------------------------------------------

    def _do_refresh(self):
        """Reload the current page."""
        self.browser.reload()
        self.status_label.setText(self.t("refreshed"))
        QTimer.singleShot(3000, self._update_status)

    def _zoom_in(self):
        """Increase zoom level by 10%, max 300%."""
        z = min(self.browser.zoomFactor() + 0.1, 3.0)
        self.browser.setZoomFactor(z)
        self.status_label.setText(f"Zoom: {int(z * 100)}%")
        self._save_state()
        QTimer.singleShot(2000, self._update_status)

    def _zoom_out(self):
        """Decrease zoom level by 10%, min 30%."""
        z = max(self.browser.zoomFactor() - 0.1, 0.3)
        self.browser.setZoomFactor(z)
        self.status_label.setText(f"Zoom: {int(z * 100)}%")
        self._save_state()
        QTimer.singleShot(2000, self._update_status)

    def _zoom_reset(self):
        """Reset zoom to 100%."""
        self.browser.setZoomFactor(1.0)
        self.status_label.setText("Zoom: 100%")
        self._save_state()
        QTimer.singleShot(2000, self._update_status)

    def _toggle_auto_refresh(self):
        """Toggle automatic page refresh on/off."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)
        else:
            self.refresh_timer.stop()
        self._update_status()

    def _interval_changed(self, value):
        """Handle auto-refresh interval change from the spinner."""
        self.refresh_interval = value
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)
        self._update_status()

    def _update_status(self):
        """Update status bar and tray menu to reflect auto-refresh state."""
        if self.auto_refresh_enabled:
            self.toggle_action.setText(self.t("auto_on"))
            if getattr(self, "tray_toggle", None):
                self.tray_toggle.setText(self.t("auto_on"))
            self.status_label.setText(
                self.t("auto_each").format(self.refresh_interval)
            )
        else:
            self.toggle_action.setText(self.t("auto_off"))
            if getattr(self, "tray_toggle", None):
                self.tray_toggle.setText(self.t("auto_off"))
            self.status_label.setText(self.t("auto_disabled"))

    def _toggle_visibility(self):
        """Show or hide the main window."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and normal window mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _tray_activated(self, reason):
        """Handle tray icon click (toggle window visibility)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    # -------------------------------------------------------------------------
    # STATE PERSISTENCE
    # -------------------------------------------------------------------------

    def _save_state(self):
        """Save current window state (zoom, size, theme, language) to disk."""
        self.cfg["zoom"] = round(self.browser.zoomFactor(), 2)
        self.cfg["width"] = self.width()
        self.cfg["height"] = self.height()
        self.cfg["dark_mode"] = self.dark_mode
        self.cfg["lang"] = self.lang
        self.cfg["refresh_interval"] = self.refresh_interval
        self.cfg["tray_enabled"] = self.tray_enabled
        self.cfg["sponsor_block"] = getattr(self, "sponsor_toggle_action", None).isChecked() if hasattr(self, "sponsor_toggle_action") else self.cfg.get("sponsor_block", True)
        save_config(self.cfg)

    def closeEvent(self, event):
        """Override close: minimize to tray instead of quitting (unless --no-tray).

        If --no-tray is used or Shift is held while closing, the app quits
        instead of minimizing to the system tray.
        """
        # stop local decoder server if running
        try:
            if getattr(self, "_video_proc", None):
                self._video_proc.kill()
        except Exception:
            pass
        if not self.tray_enabled:
            self._save_state()
            event.accept()
            QApplication.quit()
            return
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self._save_state()
            if self.tray:
                self.tray.hide()
            event.accept()
            QApplication.quit()
            return
        event.ignore()
        self._save_state()
        self.hide()
        if self.tray:
            self.tray.showMessage(
                self.t("tray_title"), self.t("tray_msg"),
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )

    def resizeEvent(self, event):
        """Save window dimensions when resized (debounced, 500ms)."""
        super().resizeEvent(event)
        if not hasattr(self, "_resize_timer"):
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._save_state)
        self._resize_timer.start(500)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Application entry point.

    Usage:
        python3 freethebird.py                    # Default (X home, auto-refresh 120s)
        python3 freethebird.py --no-refresh       # Disable auto-refresh
        python3 freethebird.py --refresh 60       # Auto-refresh every 60s
        python3 freethebird.py --purge            # Purge cache and start fresh
        python3 freethebird.py --width 1400 --height 900
    """
    # Allow Ctrl+C to kill the app from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} — "
                    f"Privacy-first X client for GNU/Linux"
    )
    parser.add_argument("--version", action="version",
                        version=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument("--url", default="https://x.com/home",
                        help="Start URL (default: https://x.com/home)")
    parser.add_argument("--refresh", type=int, default=120,
                        help="Auto-refresh interval in seconds (default: 120)")
    parser.add_argument("--no-refresh", action="store_true",
                        help="Disable auto-refresh")
    parser.add_argument("--width", type=int, default=1200,
                        help="Initial window width (default: 1200)")
    parser.add_argument("--height", type=int, default=800,
                        help="Initial window height (default: 800)")
    parser.add_argument("--purge", action="store_true",
                        help="Purge QtWebEngine cache before starting")
    parser.add_argument("--no-privacy", action="store_true",
                        help="Disable ad-blocking and domain whitelisting "
                             "(use if the login flow is being blocked)")
    parser.add_argument("--no-tray", action="store_true",
                        help="Disable system tray; closing the window quits the app")
    args = parser.parse_args()

    if args.purge:
        do_purge()

    # Disable FedCM so Google Sign-In falls back to its classic flow,
    # which works reliably inside QtWebEngine (FedCM errors with
    # "Error retrieving a token" otherwise). Also allow video autoplay
    # and enable accelerated video decode (fixes "The media could not be played").
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    if "FedCm" not in flags:
        flags = (flags + " --disable-features=FedCm").strip()
    if "autoplay-policy" not in flags:
        flags = (flags + " --autoplay-policy=no-user-gesture-required").strip()
    # keep GPU acceleration on (some Qt builds disable it which breaks MSE)
    if "ignore-gpu-blocklist" not in flags:
        flags = (flags + " --ignore-gpu-blocklist").strip()
    if "enable-accelerated-video-decode" not in flags:
        flags = (flags + " --enable-accelerated-video-decode").strip()
    # Local ffmpeg stream server is http://127.0.0.1. X's Content-Security-Policy
    # (media-src https://...) would block it, so we disable web security — this lets
    # the decoded stream load into the page's <video> element. (No install needed.)
    if "disable-web-security" not in flags:
        flags = (flags + " --disable-web-security").strip()
    if "unsafely-treat-insecure-origin-as-secure" not in flags:
        flags = (flags + ' --unsafely-treat-insecure-origin-as-secure="http://127.0.0.1"').strip()
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = flags

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_DESKTOP_NAME)
    app.setQuitOnLastWindowClosed(args.no_tray)

    window = FreeTheBirdWindow(
        url=args.url,
        refresh_interval=args.refresh,
        auto_refresh=False,
        width=args.width,
        height=args.height,
        privacy_enabled=not args.no_privacy,
        tray_enabled=not args.no_tray,
    )
    # Sync quit behavior with persisted tray setting (View menu toggle)
    app.setQuitOnLastWindowClosed(not window.tray_enabled)
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
