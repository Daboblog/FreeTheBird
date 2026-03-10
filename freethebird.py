#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  FreeTheBird — A privacy-first, lightweight X (Twitter) client for GNU/Linux ║
║                                                                               ║
║  Version:    5.0                                                              ║
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

from PyQt6.QtCore import Qt, QTimer, QUrl, QSize, QByteArray
from PyQt6.QtGui import (
    QIcon, QAction, QPixmap, QPainter, QColor,
    QShortcut, QKeySequence, QDesktopServices,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QMenu,
    QMessageBox, QToolBar, QLabel, QSpinBox,
    QWidgetAction, QHBoxLayout, QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtSvg import QSvgRenderer

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

APP_NAME = "FreeTheBird"
APP_VERSION = "1.2.0"
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
    "abs.twimg.com", "pbs.twimg.com", "video.twimg.com", "t.co",
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


# =============================================================================
# CONFIGURATION — Load & save user preferences
# =============================================================================

def load_config():
    """Load configuration from disk, falling back to defaults."""
    cfg = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg):
    """Persist configuration to disk."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


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
    blocked_count = 0

    def interceptRequest(self, info):
        host = info.requestUrl().host().lower()
        # O(1) average: split hostname and check each level against the set
        parts = host.split(".")
        for i in range(len(parts)):
            if ".".join(parts[i:]) in AD_DOMAINS:
                info.block(True)
                AdBlockInterceptor.blocked_count += 1
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

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        host = url.host().lower()

        # Allow whitelisted X/Twitter domains
        if host in ALLOWED_HOSTS:
            return True

        # Allow authentication providers for login flows
        for auth_host in AUTH_HOSTS:
            if auth_host in host:
                return True

        # External links → open in system browser
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False

        return True

    def createWindow(self, window_type):
        """Handle pop-up windows by redirecting them to the system browser."""
        page = FreeTheBirdPage(self.profile(), self.parent())
        page.urlChanged.connect(
            lambda url: (QDesktopServices.openUrl(url), page.deleteLater())
        )
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

    def __init__(self, url, refresh_interval, auto_refresh, width, height):
        super().__init__()

        # -- Load persisted configuration --
        self.cfg = load_config()
        self.lang = self.cfg.get("lang", "es")
        self.dark_mode = self.cfg.get("dark_mode", True)
        self.refresh_interval = refresh_interval
        self.auto_refresh_enabled = auto_refresh
        self.app_icon = create_app_icon()
        self.last_title = ""
        self.current_ip = "..."
        self.conn_info = None

        # -- Window setup --
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.app_icon)
        self.resize(self.cfg.get("width", width), self.cfg.get("height", height))

        # -- WebEngine with isolated profile --
        self.profile = QWebEngineProfile(APP_DESKTOP_NAME, self)
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

        # -- Privacy: attach ad/tracker interceptor --
        self.ad_interceptor = AdBlockInterceptor(self)
        self.profile.setUrlRequestInterceptor(self.ad_interceptor)

        # -- Browser view --
        self.page = FreeTheBirdPage(self.profile, self)
        self.browser = QWebEngineView()
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)
        self.browser.titleChanged.connect(self._on_title_changed)

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

        # Fetch geolocation if we got a valid IP
        if self.current_ip != "--":
            try:
                url = f"https://ipapi.co/{self.current_ip}/json/"
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "curl/7.0")
                response = urllib.request.urlopen(req, timeout=8)
                self.conn_info = json.loads(response.read().decode("utf-8"))
            except (ssl.SSLError, ssl.CertificateError):
                self.conn_info = None
            except Exception:
                self.conn_info = None

    def _update_ip_menu(self):
        """Update the IP menu title from the main thread."""
        self.ip_menu.setTitle(f"\U0001f310 IP: {self.current_ip}")

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
                if count_str.isdigit() and not self.isActiveWindow():
                    self.tray.showMessage(
                        APP_NAME, self.t("new_notif"),
                        QSystemTrayIcon.MessageIcon.Information, 5000,
                    )
        self.last_title = title

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
        self.tray_show.setText(self.t("show_hide"))
        self.tray_refresh.setText(self.t("refresh_now"))
        self.tray_quit.setText(self.t("quit"))

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
        """Perform translation via Google Translate API and show result."""
        if not text or not text.strip():
            return

        target_lang = "es" if self.lang == "es" else "en"
        try:
            encoded = urllib.parse.quote(text.strip())
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

            msg = QMessageBox(self)
            msg.setWindowTitle(self.t("translate_title"))
            msg.setText(translated)
            msg.setInformativeText(
                f"{self.t('translate_original')}: {text.strip()[:200]}"
            )
            if self.dark_mode:
                msg.setStyleSheet(DARK_DIALOG)
            msg.exec()
        except (ssl.SSLError, ssl.CertificateError):
            self.status_label.setText(self.t("translate_error"))
            QTimer.singleShot(3000, self._update_status)
        except Exception:
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
            blocked=AdBlockInterceptor.blocked_count,
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

    def _purge_and_restart(self):
        """Purge local app/QtWebEngine state and restart the application."""
        self.tray.hide()
        do_purge()

        python = sys.executable
        args = [python] + sys.argv
        subprocess.Popen(args)
        QApplication.quit()


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

        # -- View menu (theme toggle) --
        self.view_menu = mb.addMenu(self.t("view"))
        theme_label = self.t("light_mode") if self.dark_mode else self.t("dark_mode")
        self.theme_action = self.view_menu.addAction(theme_label)
        self.theme_action.triggered.connect(self._toggle_theme)

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
        self.privacy_label = QLabel(self.t("privacy_on"))
        self.privacy_label.setStyleSheet("padding: 0 4px; color: #2ecc71;")
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

    # -------------------------------------------------------------------------
    # SYSTEM TRAY — Minimize to tray, notifications
    # -------------------------------------------------------------------------

    def _create_tray(self):
        """Create the system tray icon and its context menu."""
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
        Ctrl+Q      — Quit application
        F11         — Toggle fullscreen
        Ctrl++/=    — Zoom in
        Ctrl+-      — Zoom out
        Ctrl+0      — Reset zoom to 100%
        """
        QShortcut(QKeySequence("F5"), self, self._do_refresh)
        QShortcut(QKeySequence("Ctrl+R"), self, self._toggle_auto_refresh)
        QShortcut(QKeySequence("Ctrl+H"), self,
                  lambda: self.browser.setUrl(QUrl("https://x.com/home")))
        QShortcut(QKeySequence("Ctrl+Q"), self, QApplication.quit)
        QShortcut(QKeySequence("Ctrl+M"), self,
                  lambda: self.browser.setUrl(QUrl("https://x.com/messages")))
        QShortcut(QKeySequence("Ctrl+N"), self,
                  lambda: self.browser.setUrl(QUrl("https://x.com/notifications")))
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self._zoom_reset)

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
            self.tray_toggle.setText(self.t("auto_on"))
            self.status_label.setText(
                self.t("auto_each").format(self.refresh_interval)
            )
        else:
            self.toggle_action.setText(self.t("auto_off"))
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
        save_config(self.cfg)

    def closeEvent(self, event):
        """Override close: minimize to tray instead of quitting."""
        event.ignore()
        self._save_state()
        self.hide()
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
    args = parser.parse_args()

    if args.purge:
        do_purge()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_DESKTOP_NAME)
    app.setQuitOnLastWindowClosed(False)

    window = FreeTheBirdWindow(
        url=args.url,
        refresh_interval=args.refresh,
        auto_refresh=not args.no_refresh,
        width=args.width,
        height=args.height,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
