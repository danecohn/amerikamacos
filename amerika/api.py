import base64
import hashlib
import json
import mimetypes
import secrets
from pathlib import Path
from urllib.parse import urlsplit

import keyring
from PySide6.QtCore import QObject, Signal, QUrl, QFile, QIODevice, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import QDesktopServices

ORIGIN = 'https://www.amerika.social'
MAX_UPLOAD = 250_000_000

def media_mime(path):
    return {'.mov':'video/quicktime','.heic':'image/heic','.heif':'image/heif','.m4v':'video/mp4'}.get(Path(path).suffix.lower(), mimetypes.guess_type(path)[0] or 'application/octet-stream')

def safe_url(value):
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password

def open_external(value):
    if safe_url(value):
        QDesktopServices.openUrl(QUrl(value))

class Vault:
    service = 'social.amerika.desktop'
    def load(self):
        try:
            if keyring.get_keyring().priority < 1: return None
            return keyring.get_password(self.service, 'session')
        except Exception: return None
    def save(self, token):
        try:
            if keyring.get_keyring().priority < 1: return False
            keyring.set_password(self.service, 'session', token)
            return True
        except Exception: return False
    def clear(self):
        try: keyring.delete_password(self.service, 'session')
        except keyring.errors.PasswordDeleteError: pass
        except Exception: pass

class Api(QObject):
    expired = Signal()
    def __init__(self, origin=ORIGIN, parent=None, restore=True):
        super().__init__(parent)
        if origin != ORIGIN and not (origin.startswith('http://127.0.0.1:') and origin.count('/') == 2):
            raise ValueError('Use the production HTTPS server or an explicit local test server.')
        self.origin = origin
        self.network = QNetworkAccessManager(self)
        self.vault = Vault()
        self.token = self.vault.load() if restore else None
        self.epoch = 0

    def set_token(self, token):
        self.epoch += 1
        self.token = token
        return self.vault.save(token)

    def clear(self):
        self.epoch += 1
        self.token = None
        self.vault.clear()

    def request(self, path, body=None, done=None, error=None, file=None, progress=None):
        if path.startswith('/') or '://' in path: raise ValueError('Use a relative API path.')
        req = QNetworkRequest(QUrl(self.origin + '/api/' + path))
        req.setTransferTimeout(180000 if file else 30000)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        req.setRawHeader(b'Accept', b'application/json')
        identity = self.epoch
        if self.token: req.setRawHeader(b'Authorization', ('Bearer '+self.token).encode())
        device = None
        if file:
            if Path(file).stat().st_size > MAX_UPLOAD: raise ValueError('Each file must be at most 250 MB.')
            device = QFile(file, self)
            if not device.open(QIODevice.OpenModeFlag.ReadOnly): raise ValueError('Could not open the selected file.')
            req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, media_mime(file))
            reply = self.network.post(req, device)
            device.setParent(reply)
            if progress: reply.uploadProgress.connect(progress)
        elif body is not None:
            req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
            reply = self.network.post(req, json.dumps(body).encode())
        else: reply = self.network.get(req)
        def finish():
            try:
                if identity != self.epoch: return
                status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
                raw = bytes(reply.readAll())
                try: data = json.loads(raw)
                except (ValueError, UnicodeDecodeError): data = {}
                if not 200 <= status < 300:
                    if status == 401 and self.token and path.split('?')[0] not in ('account/delete','recovery/codes','agents/link'):
                        self.clear(); self.expired.emit()
                    message = data.get('error') or ('Network unavailable. Check your connection and retry.' if not status else f'Server returned HTTP {status}.')
                    if data.get('retryAfter'): message += f" Retry in {data['retryAfter']} seconds."
                    if error: error(message)
                elif done: done(data)
            finally: reply.deleteLater()
        reply.finished.connect(finish)
        return reply

    def asset(self, url, done, error=None):
        url = self.origin+url if url.startswith('/') else url
        if not safe_url(url) and not url.startswith(self.origin+'/'): return
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(60000)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        # Asset URLs are public or short-lived signed links. Never send the account token to an asset host.
        reply = self.network.get(request)
        epoch = self.epoch
        def finish():
            try:
                if epoch != self.epoch: return
                if reply.error() != QNetworkReply.NetworkError.NoError:
                    if error: error('Media could not be loaded.')
                else: done(bytes(reply.readAll()))
            finally: reply.deleteLater()
        reply.finished.connect(finish)
        return reply

class BrowserLogin(QObject):
    connected = Signal(dict, bool)
    failed = Signal(str)
    opened = Signal()
    def __init__(self, api, parent=None):
        super().__init__(parent); self.api = api; self.timer = QTimer(self); self.timer.setInterval(2500)
        self.timer.timeout.connect(self.poll); self.active = False; self.inflight = False; self.attempt = 0
    def start(self):
        self.cancel(); self.active = True; self.attempt += 1; generation = self.attempt
        self.verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip('=')
        def ready(data):
            if not self.active or generation != self.attempt: return
            self.id = data['id']; self.polls = 0
            open_external(self.api.origin + '/desktop-connect#' + self.id)
            self.opened.emit(); self.timer.start()
        self.api.request('desktop/start', {'challenge':challenge}, ready, lambda message:self.fail(message) if self.active and generation==self.attempt else None)
    def fail(self, message):
        self.cancel(); self.failed.emit(message)
    def cancel(self):
        self.active = False; self.timer.stop(); self.attempt += 1; self.inflight = False
    def poll(self):
        if not self.active or self.inflight: return
        self.polls += 1
        if self.polls > 120: self.fail('Sign-in expired. Start again.'); return
        self.inflight = True; generation = self.attempt
        def result(data):
            if not self.active or generation != self.attempt: return
            self.inflight = False
            if data.get('pending'): return
            self.cancel(); saved = self.api.set_token(data['token']); self.connected.emit(data['actor'], saved)
        self.api.request('desktop/exchange', {'id':self.id,'verifier':self.verifier}, result, lambda message:self.fail(message) if self.active and generation==self.attempt else None)
