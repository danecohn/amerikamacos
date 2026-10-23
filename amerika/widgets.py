import base64
import io
from pathlib import Path
from urllib.parse import quote
from html import escape
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QLineEdit,QPlainTextEdit,QCheckBox,QComboBox,QFormLayout,QGroupBox,QDialog,QDialogButtonBox,QScrollArea,QFileDialog,QMessageBox,QApplication,QSlider,QSizePolicy)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from .api import open_external, ORIGIN
from shiboken6 import isValid
from .design import icon

def text(value, title=False):
    label=QLabel(str(value or '')); label.setTextFormat(Qt.TextFormat.PlainText); label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if title: label.setObjectName('heading')
    return label

class StatusLabel(QLabel):
    def __init__(self):
        super().__init__('');self.setWordWrap(True);self.setTextFormat(Qt.TextFormat.PlainText);self.hide()
    def setText(self,value):
        super().setText(str(value));self.setVisible(bool(value))

def button(label, call, primary=False):
    b=QPushButton(label); b.setCursor(Qt.CursorShape.PointingHandCursor); b.clicked.connect(lambda checked=False:call())
    if primary: b.setObjectName('primary')
    return b

def row(*widgets):
    w=QWidget(); layout=QHBoxLayout(w); layout.setContentsMargins(0,0,0,0)
    for widget in widgets: layout.addWidget(widget)
    layout.addStretch(); return w

def clear(layout):
    while layout.count():
        item=layout.takeAt(0)
        if item.widget(): item.widget().deleteLater()

def confirm(parent,title,message):
    return QMessageBox.question(parent,title,message) == QMessageBox.StandardButton.Yes

def secret(parent, data):
    d=QDialog(parent); d.setWindowTitle('Connection details — save privately'); d.resize(640,420); layout=QVBoxLayout(d)
    layout.addWidget(text('Private credentials and recovery codes are shown only here. Save them securely.'))
    import json
    output=QPlainTextEdit(json.dumps(data,indent=2,ensure_ascii=False)); output.setReadOnly(True); layout.addWidget(output)
    layout.addWidget(button('Copy details',lambda:QApplication.clipboard().setText(output.toPlainText())))
    layout.addWidget(button('Close',d.accept)); d.exec()

def field(key,label=None,kind='text',default='',options=None,required=True,max_length=2000):
    return dict(key=key,label=label or key.replace('_',' ').title(),kind=kind,default=default,options=options,required=required,max=max_length)

class Form(QGroupBox):
    def __init__(self,title,api,path,fields,extra=None,after=None,initial=None,submit='Save',parent=None):
        super().__init__(title,parent); self.api=api; self.path=path; self.fields=fields; self.extra=extra or {}; self.after=after; self.controls={}
        layout=QVBoxLayout(self); form=QFormLayout(); form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        for f in fields:
            value=(initial or {}).get(f['key'],f.get('default','')); kind=f.get('kind','text')
            if kind=='bool': widget=QCheckBox(); widget.setChecked(bool(value))
            elif kind=='select':
                widget=QComboBox(); widget.addItems([str(v) for v in f['options']]); widget.setCurrentText(str(value))
            elif kind=='scopes':
                widget=QWidget(); inner=QVBoxLayout(widget); widget.boxes=[]
                for scope in f['options']:
                    box=QCheckBox(scope); box.setChecked(scope in value); inner.addWidget(box); widget.boxes.append(box)
            elif kind=='multiline': widget=QPlainTextEdit(str(value or '')); widget.setMaximumHeight(130)
            else:
                widget=QLineEdit(str(value or '')); widget.setMaxLength(f.get('max',2000))
                if kind=='password': widget.setEchoMode(QLineEdit.EchoMode.Password)
            widget.setAccessibleName(f['label']); self.controls[f['key']]=widget; form.addRow(f['label'],widget)
        layout.addLayout(form); self.status=StatusLabel(); layout.addWidget(self.status); self.send_button=button(submit,self.send,True);self.send_button.setMinimumWidth(110); layout.addWidget(self.send_button,0,Qt.AlignmentFlag.AlignRight)

    def values(self):
        body=dict(self.extra)
        for f in self.fields:
            w=self.controls[f['key']]; kind=f.get('kind','text')
            if kind=='bool': v=w.isChecked()
            elif kind=='scopes': v=[box.text() for box in w.boxes if box.isChecked()]
            elif kind=='select': v=w.currentText()
            elif kind=='multiline': v=w.toPlainText()
            else: v=w.text()
            if kind=='number':
                try: v=int(v)
                except ValueError: raise ValueError(f"Enter a number for {f['label']}.")
            if f.get('required',True) and kind not in ('bool','scopes') and not str(v).strip(): raise ValueError('Complete '+f['label']+'.')
            if isinstance(v,str) and len(v)>f.get('max',2000): raise ValueError(f"{f['label']} is too long.")
            body[f['key']]=v
        return body

    def send(self):
        try: body=self.values()
        except ValueError as e: self.status.setText(str(e)); return
        self.send_button.setEnabled(False); self.status.setText('Saving…')
        def done(data):
            from shiboken6 import isValid
            if not isValid(self): return
            self.send_button.setEnabled(True); self.status.setText('Saved.')
            for f in self.fields:
                if f.get('kind')=='password': self.controls[f['key']].clear()
            if any(data.get(k) for k in ('token','mcpUrl','recoveryCodes','signingSecret','secret','instructions')): secret(self,data)
            if self.after: self.after(data)
        def error(message):
            from shiboken6 import isValid
            if isValid(self): self.send_button.setEnabled(True); self.status.setText(message)
        self.api.request(self.path,body,done,error)

class Page(QWidget):
    def __init__(self,app,title):
        super().__init__(); self.app=app; self.api=app.api; self.generation=0; self.loaders=[]; self.active=True
        root=QVBoxLayout(self);root.setContentsMargins(28,26,28,16);root.setSpacing(18)
        header=QWidget();header_layout=QHBoxLayout(header);header_layout.setContentsMargins(0,0,0,0);heading=QWidget();heading_layout=QVBoxLayout(heading);heading_layout.setContentsMargins(0,0,0,0);heading_layout.setSpacing(5);eyebrow=text('ALTSTACK SOCIAL');eyebrow.setObjectName('eyebrow');heading_layout.addWidget(eyebrow);heading_layout.addWidget(text(title,True));header_layout.addWidget(heading);header_layout.addStretch();refresh=button('Refresh',app.refresh);refresh.setIcon(icon('refresh',size=18));refresh.setAccessibleName('Refresh page');refresh.setToolTip('Refresh this view · F5 or Ctrl+R / Command+R');header_layout.addWidget(refresh);root.addWidget(header)
        self.status=StatusLabel();self.status.setObjectName('muted'); root.addWidget(self.status); self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter); root.addWidget(self.scroll)
        self.body=QWidget();self.body.setMaximumWidth(920); self.content=QVBoxLayout(self.body);self.content.setContentsMargins(0,0,8,12);self.content.setSpacing(18); self.content.setAlignment(Qt.AlignmentFlag.AlignTop); self.scroll.setWidget(self.body)
    def refresh(self):
        self.generation+=1
        for task in list(self.loaders): task()
    def get(self,path,done,error=None):
        generation=self.generation; self.status.setText('Loading…')
        def ok(data):
            if not isValid(self) or not self.active or generation!=self.generation:return
            self.status.setText(''); done(data)
        def err(message):
            if isValid(self) and self.active and generation==self.generation:
                self.status.setText(message)
                if error:error(message)
        return self.api.request(path,done=ok,error=err)
    def add(self,widget): self.content.addWidget(widget); return widget
    def section(self,title,initial=False):
        group=QWidget();group.setObjectName('sectionCard');outer=QVBoxLayout(group);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);header=QPushButton(title);header.setObjectName('disclosureHeader');header.setCheckable(True);header.setChecked(initial);header.setAccessibleName(title);header.setCursor(Qt.CursorShape.PointingHandCursor);outer.addWidget(header);body=QWidget();inner=QVBoxLayout(body);inner.setContentsMargins(18,4,18,18);inner.setSpacing(16);outer.addWidget(body);body.setVisible(initial)
        def toggle(value):body.setVisible(value);header.setIcon(icon('chevron-down' if value else 'chevron-right','#c6c6d1',18))
        header.toggled.connect(toggle);toggle(initial);self.add(group);return inner
    def action(self,label,path,body,after=None,warning=None):
        def run():
            if warning and not confirm(self,label,warning):return
            self.api.request(path,body,lambda d:after(d) if after else self.refresh(),lambda e:self.status.setText(e))
        return button(label,run)
    def form(self,title,path,fields,extra=None,after=None,initial=None,layout=None,submit='Save'):
        form=Form(title,self.api,path,fields,extra,after,initial,submit,self)
        (layout or self.content).addWidget(form); return form

class Listing(QWidget):
    def __init__(self,page,path,key,render,query_key='cursor',grid=False):
        super().__init__();self.page=page;self.path=path;self.key=key;self.render=render;self.query_key=query_key;self.cursor=None;self.inflight=False;self.epoch=0
        self.grid=grid;self.count=0
        self.layout=QVBoxLayout(self);self.layout.setContentsMargins(0,0,0,0);self.layout.setSpacing(18);self.items=QGridLayout() if grid else QVBoxLayout();self.items.setSpacing(18);self.layout.addLayout(self.items);self.more=button('Load more',lambda:self.load(True));self.layout.addWidget(self.more);self.more.hide();page.loaders.append(self.reload);self.reload()
    def reload(self): self.epoch+=1;self.inflight=False;self.load()
    def load(self,more=False):
        if self.inflight:return
        self.inflight=True;epoch=self.epoch;self.more.setEnabled(False)
        path=self.path+(('&' if '?' in self.path else '?')+self.query_key+'='+quote(str(self.cursor),safe='') if more else '')
        def done(data):
            if not isValid(self) or epoch!=self.epoch:return
            self.inflight=False;self.more.setEnabled(True)
            if not more:clear(self.items);self.count=0
            rows=data.get(self.key,[])
            for item in rows:
                widget=self.render(item)
                if self.grid:self.items.addWidget(widget,self.count//2,self.count%2)
                else:self.items.addWidget(widget)
                self.count+=1
            if not rows and not more:self.items.addWidget(text('Nothing here yet.'))
            self.cursor=data.get('cursor');self.more.setVisible(self.cursor is not None)
        def failed(message):
            if isValid(self):self.inflight=False;self.more.setEnabled(True)
        self.page.get(path,done,failed)

class Media(QWidget):
    def __init__(self,api,item,parent=None):
        super().__init__(parent);self.api=api;self.item=item;self.retried=False;self.url=item.get('url','');layout=QVBoxLayout(self)
        if item.get('mime','').startswith('video/'):
            self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.video=QVideoWidget();self.video.setMinimumHeight(260);self.player.setVideoOutput(self.video);layout.addWidget(self.video)
            self.player.setSource(QUrl(api.origin+self.url if self.url.startswith('/') else self.url));self.player.errorOccurred.connect(lambda *args:self.renew())
            self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.sliderMoved.connect(self.player.setPosition);self.player.positionChanged.connect(self.slider.setValue);self.player.durationChanged.connect(lambda value:self.slider.setRange(0,value));layout.addWidget(self.slider)
            layout.addWidget(row(button('Play / pause',lambda:self.player.pause() if self.player.isPlaying() else self.player.play()),button('Mute / unmute',lambda:self.audio.setMuted(not self.audio.isMuted()))))
        else:
            self.image=QLabel('Loading photo…');self.image.setAlignment(Qt.AlignmentFlag.AlignCenter);self.image.setMinimumHeight(100);self.image.setMaximumHeight(320);self.image.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);layout.addWidget(self.image);layout.addWidget(button('Open photo',self.zoom));self.pixmap=None;self.load_image()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if getattr(self,'pixmap',None):self.image.setPixmap(self.pixmap.scaled(max(100,self.image.width()),320,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def renew(self):
        if not isValid(self):return
        if self.retried or not self.item.get('id') or 'dating/' not in self.url:return
        self.retried=True
        def done(data):
            self.url=data['url']
            if hasattr(self,'player'):self.player.setSource(QUrl(self.api.origin+self.url if self.url.startswith('/') else self.url));self.player.play()
            else:self.load_image()
        self.api.request('dating/media-link?id='+quote(self.item['id'],safe=''),done=done)
    def load_image(self):
        def done(raw):
            from shiboken6 import isValid
            if not isValid(self):return
            pix=QPixmap();pix.loadFromData(raw)
            if pix.isNull():self.image.setText('Photo unavailable');return
            self.pixmap=pix;self.image.setPixmap(pix.scaled(560,320,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));self.image.setAccessibleName(self.item.get('alt') or 'Photo')
        if self.url.startswith('data:image/'):
            try:done(base64.b64decode(self.url.split(',',1)[1]))
            except Exception:self.image.setText('Photo unavailable')
        else:self.api.asset(self.url,done,lambda e:self.renew())
    def zoom(self):
        if not self.pixmap:return
        dialog=QDialog(self);dialog.setWindowTitle(self.item.get('alt') or 'Makk photo');dialog.resize(900,700);layout=QVBoxLayout(dialog);scroll=QScrollArea();image=QLabel();image.setPixmap(self.pixmap);scroll.setWidget(image);layout.addWidget(scroll);layout.addWidget(button('Close',dialog.accept));dialog.exec()

def profile_photo(path):
    from PIL import Image, ImageOps
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError: pass
    with Image.open(path) as source:
        image=ImageOps.exif_transpose(source).convert('RGB');image.thumbnail((400,400))
        for quality in (85,65,40,20):
            out=io.BytesIO();image.save(out,format='JPEG',quality=quality)
            if len(out.getvalue())<=150000:return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()
    raise ValueError('Choose a smaller profile picture.')
