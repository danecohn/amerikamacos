"""Shared native desktop visual system. Vector icons remain sharp at any DPI."""
import base64
import re
from html import escape
from urllib.parse import quote,unquote
from datetime import datetime,timezone
from PySide6.QtCore import Qt,QByteArray,QSize,QRectF
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPainterPath,QColor,QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel,QPushButton,QTextBrowser,QSizePolicy,QFrame,QWidget
from shiboken6 import isValid

PATHS={
 'home':'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
 'friends':'<circle cx="9" cy="8" r="3"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 4v2"/>',
 'search':'<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
 'messages':'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m3 6 9 7 9-7"/>',
 'bell':'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
 'communities':'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
 'heart':'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z"/>',
 'code':'<path d="m8 5-6 7 6 7m8-14 6 7-6 7M14 3l-4 18"/>',
 'settings':'<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>',
 'plus':'<path d="M12 5v14M5 12h14"/>',
 'star':'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"/>',
 'profile':'<circle cx="12" cy="8" r="4"/><path d="M4 22v-2a8 8 0 0 1 16 0v2"/>',
 'shield':'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
 'refresh':'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 6a8 8 0 0 1 14 6M18 18A8 8 0 0 1 4 12"/>',
 'reply':'<path d="M21 11a9 9 0 0 1-9 9H3l2-5a9 9 0 1 1 16-4z"/>',
 'repost':'<path d="m17 2 4 4-4 4M3 11V8a2 2 0 0 1 2-2h16M7 22l-4-4 4-4m14-1v3a2 2 0 0 1-2 2H3"/>',
 'quote':'<path d="M10 4H3v8h5c0 4-2 5-5 6v3c5-1 7-4 7-9zm11 0h-7v8h5c0 4-2 5-5 6v3c5-1 7-4 7-9z"/>',
 'share':'<path d="M12 16V3m-5 5 5-5 5 5M5 13H3v8h18v-8h-2"/>',
 'more':'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
 'logout':'<path d="M9 4H3v16h6m6-12 4 4-4 4m-7-4h11"/>',
 'check':'<path d="m5 12 4 4L19 6"/>',
 'chevron-right':'<path d="m9 5 7 7-7 7"/>',
 'chevron-down':'<path d="m5 9 7 7 7-7"/>',
}

# The same vector artwork as assets/logo.svg and the website logo. Painting it
# directly avoids platform image-plugin and layout-dependent pixmap handling.
BRAND_SVG=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img"><title>Cherry Blossom LLC \xc2\xb7 Makk OS</title><defs><linearGradient id="petal" x1="0" y1="0" x2=".2" y2="1"><stop stop-color="#fff0f5"/><stop offset=".55" stop-color="#ff8cb4"/><stop offset="1" stop-color="#ff0058"/></linearGradient></defs><g transform="rotate(0 32 32)"><path d="M32 31 C22 26 17 17 22 10 C25 6 29 6 32 10 C35 6 39 6 42 10 C47 17 42 26 32 31Z" fill="url(#petal)" stroke="#c00042" stroke-width=".7"/></g><g transform="rotate(72 32 32)"><path d="M32 31 C22 26 17 17 22 10 C25 6 29 6 32 10 C35 6 39 6 42 10 C47 17 42 26 32 31Z" fill="url(#petal)" stroke="#c00042" stroke-width=".7"/></g><g transform="rotate(144 32 32)"><path d="M32 31 C22 26 17 17 22 10 C25 6 29 6 32 10 C35 6 39 6 42 10 C47 17 42 26 32 31Z" fill="url(#petal)" stroke="#c00042" stroke-width=".7"/></g><g transform="rotate(216 32 32)"><path d="M32 31 C22 26 17 17 22 10 C25 6 29 6 32 10 C35 6 39 6 42 10 C47 17 42 26 32 31Z" fill="url(#petal)" stroke="#c00042" stroke-width=".7"/></g><g transform="rotate(288 32 32)"><path d="M32 31 C22 26 17 17 22 10 C25 6 29 6 32 10 C35 6 39 6 42 10 C47 17 42 26 32 31Z" fill="url(#petal)" stroke="#c00042" stroke-width=".7"/></g><circle cx="32" cy="32" r="5" fill="#f5c879" stroke="#ca9151" stroke-width=".7"/><g transform="rotate(0 32 32)"><path d="M32 32 V23" stroke="#c37a64" stroke-width=".8"/><circle cx="32" cy="23" r="1.1" fill="#fff2ce"/></g><g transform="rotate(72 32 32)"><path d="M32 32 V23" stroke="#c37a64" stroke-width=".8"/><circle cx="32" cy="23" r="1.1" fill="#fff2ce"/></g><g transform="rotate(144 32 32)"><path d="M32 32 V23" stroke="#c37a64" stroke-width=".8"/><circle cx="32" cy="23" r="1.1" fill="#fff2ce"/></g><g transform="rotate(216 32 32)"><path d="M32 32 V23" stroke="#c37a64" stroke-width=".8"/><circle cx="32" cy="23" r="1.1" fill="#fff2ce"/></g><g transform="rotate(288 32 32)"><path d="M32 32 V23" stroke="#c37a64" stroke-width=".8"/><circle cx="32" cy="23" r="1.1" fill="#fff2ce"/></g></svg>\n'

class LogoMark(QWidget):
    def __init__(self,size=44):
        super().__init__();self.setFixedSize(size,size);self.setAccessibleName('Cherry Blossom LLC cherry blossom logo');self.renderer=QSvgRenderer(QByteArray(BRAND_SVG),self)
    def paintEvent(self,event):
        painter=QPainter(self);self.renderer.render(painter,QRectF(self.rect()));painter.end()

def icon(name,color='#c4c4cc',size=22):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name,PATHS["star"])}</svg>'
    pix=QPixmap(size*2,size*2);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);QSvgRenderer(QByteArray(svg.encode())).render(p);p.end();pix.setDevicePixelRatio(2);return QIcon(pix)

class Avatar(QLabel):
    def __init__(self,api,actor,size=44):
        super().__init__();self.setFixedSize(size,size);self.setAccessibleName(actor.get('name','Account')+' profile picture');self.size=size;self.actor=actor;self.paint_avatar()
        photo=actor.get('photo')
        if photo:
            if photo.startswith('data:image/'):
                try:self.loaded(base64.b64decode(photo.split(',',1)[1]))
                except (ValueError,IndexError):pass
            else:api.asset(photo,self.loaded)
    def paint_avatar(self,source=None):
        size=self.size*2;pix=QPixmap(size,size);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);path=QPainterPath();path.addEllipse(0,0,size,size);p.setClipPath(path);p.fillRect(0,0,size,size,QColor('#3b2730'))
        if source and not source.isNull():
            scaled=source.scaled(size,size,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation);p.drawPixmap((size-scaled.width())//2,(size-scaled.height())//2,scaled)
        else:
            font=QFont('Inter',int(self.size*.65));font.setWeight(QFont.Weight.DemiBold);p.setFont(font);p.setPen(QColor('#ffd4d9'));p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,(self.actor.get('name') or 'A')[0].upper())
        p.end();pix.setDevicePixelRatio(2);self.setPixmap(pix)
    def loaded(self,raw):
        if not isValid(self):return
        pix=QPixmap();pix.loadFromData(raw)
        if not pix.isNull():self.paint_avatar(pix)

def timestamp(value):
    try:
        date=datetime.fromisoformat(value.replace('Z','+00:00'));seconds=max(0,(datetime.now(timezone.utc)-date).total_seconds())
        if seconds<60:return 'just now'
        if seconds<3600:return f'{int(seconds//60)}m'
        if seconds<86400:return f'{int(seconds//3600)}h'
        return date.astimezone().strftime('%b %d')
    except (ValueError,TypeError):return ''

def action(label,name,call,active=False):
    b=QPushButton(label);b.setObjectName('postAction');b.setProperty('active',active);b.setIcon(icon(name,'#f25d6c' if active else '#aaaab4',18));b.setIconSize(QSize(18,18));b.setAccessibleName(label);b.setCursor(Qt.CursorShape.PointingHandCursor);b.clicked.connect(lambda checked=False:call());return b

class PostText(QTextBrowser):
    def __init__(self,app,value):
        super().__init__();self.app=app;self.setFrameShape(QFrame.Shape.NoFrame);self.setOpenLinks(False);self.setOpenExternalLinks(False);self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);self.document().setDocumentMargin(0);self.setStyleSheet('QTextBrowser{background:transparent;border:0;color:#263e52;font-size:15px;padding:0;}');self.document().setDefaultStyleSheet('a {color:#ff8b99;text-decoration:none;}')
        parts=[];offset=0
        for match in re.finditer(r'https?://[^\s<>]+|(?<!\w)@[a-zA-Z0-9._-]+|(?<!\w)#[\w]+',value):
            parts.append(escape(value[offset:match.start()]));token=match.group()
            target='amerika-profile:'+quote(token[1:],safe='') if token.startswith('@') else 'amerika-tag:'+quote(token[1:],safe='') if token.startswith('#') else token
            parts.append('<a href="'+escape(target,quote=True)+'">'+escape(token)+'</a>');offset=match.end()
        parts.append(escape(value[offset:]));self.setHtml(''.join(parts).replace('\n','<br>'));self.anchorClicked.connect(self.open_anchor);self.document().documentLayout().documentSizeChanged.connect(lambda size:self.fit_height());self.fit_height()
    def fit_height(self):
        if isValid(self):self.setFixedHeight(max(24,min(2500,int(self.document().size().height()+5))))
    def resizeEvent(self,event):super().resizeEvent(event);self.fit_height()
    def open_anchor(self,url):
        value=url.toString()
        if value.startswith('amerika-profile:'):self.app.find_profile(unquote(value.split(':',1)[1]))
        elif value.startswith('amerika-tag:'):
            tag=unquote(value.split(':',1)[1]);self.app.feed('feed?tag='+quote(tag,safe=''),'#'+tag)
        else:
            from .api import open_external
            open_external(value)
