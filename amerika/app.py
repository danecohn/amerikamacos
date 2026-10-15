import sys
from pathlib import Path
from urllib.parse import quote
from PySide6.QtCore import Qt,QTimer,QSettings,QSize
from PySide6.QtGui import QAction,QIcon,QKeySequence,QFontDatabase,QFont,QPixmap
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QStackedWidget,QPushButton,QSystemTrayIcon,QStyle,QDialog,QMessageBox,QLabel,QScrollArea
from .api import Api,BrowserLogin,ORIGIN,open_external
from .widgets import Page,Listing,text,button,row,field
from .social import Feed,Thread,Profile,Inbox,Alerts,Explore,Composer,person
from .hub import Settings,DeveloperHub,Plus
from .communities import Communities
from .dating import Dating
from .moderation import Moderation
from .design import icon

STYLE='''
QWidget {background:transparent;color:#f7f7fa;font-size:14px;font-family:Inter;}
QMainWindow,QWidget#appShell {background:#0e0e10;}
QWidget#sidebar {background:#141417;border-right:1px solid #29292f;}
QLabel#heading {font-size:25px;font-weight:700;}
QLabel#muted {color:#90909c;font-size:12px;}
QLabel#eyebrow {font-size:10px;font-weight:600;letter-spacing:1px;color:#b4b4bf;}
QLabel#postText {font-size:15px;color:#eeeeF3;}
QWidget#hero {background:#c82433;border-radius:12px;}
QWidget#hero QLabel {color:white;}
QWidget#hero QLabel#heroTitle {font-size:37px;font-weight:700;letter-spacing:-1px;}
QWidget#hero QLabel#eyebrow {color:#ffe4e7;font-size:10px;}
QWidget#card {background:#17171b;border:1px solid #29292f;border-radius:12px;}
QWidget#composeCard {background:#17171b;border:1px solid #303037;border-radius:12px;}
QWidget#sectionCard {background:#17171b;border:1px solid #303037;border-radius:10px;}
QPushButton#disclosureHeader {background:transparent;border:0;border-radius:10px;padding:18px;color:#e7e7ef;font-size:14px;font-weight:600;text-align:left;}
QPushButton#disclosureHeader:hover {background:#222228;}
QPushButton {background:#24242a;border:1px solid #414149;border-radius:7px;padding:10px 15px;text-align:left;font-weight:500;}
QPushButton:hover {background:#303037;border-color:#777781;}
QPushButton:pressed {background:#393940;}
QPushButton:disabled {color:#666670;background:#18181d;}
QPushButton#primary {background:#c82433;border-color:#c82433;color:white;font-weight:600;}
QPushButton#primary:hover {background:#e02e40;}
QPushButton#nav {background:transparent;border:1px solid transparent;padding:10px 15px;border-radius:8px;color:#c5c5ce;text-align:left;}
QPushButton#nav:hover {background:#222228;color:white;}
QPushButton#nav[selected="true"] {background:#351b22;border-color:#351b22;color:#ff7c89;font-weight:600;}
QPushButton#authorName {background:transparent;border:0;padding:0;text-align:left;color:#f8f8fb;font-weight:650;font-size:14px;}
QPushButton#authorName:hover {color:#ff7c89;}
QPushButton#postAction {background:transparent;border:0;padding:7px 10px;color:#aaaab5;font-size:12px;font-weight:400;}
QPushButton#postAction:hover {background:#2d1c24;color:#ff7c89;}
QPushButton#postAction[active="true"] {color:#ff7c89;}
QPushButton#textLink {background:transparent;border:0;padding:0;text-align:left;color:#9b9ba7;font-size:12px;}
QPushButton#textLink:hover {color:#ff7c89;}
QPushButton#chip {background:#292027;border:1px solid #49303b;border-radius:12px;padding:4px 9px;color:#ffb1ba;font-size:11px;}
QPushButton#composePrompt {background:transparent;border:0;color:#92929e;font-size:15px;padding:8px 0;}
QPushButton#feedTab {background:transparent;border:0;border-bottom:2px solid transparent;border-radius:0;padding:13px 18px;color:#9797a4;}
QPushButton#feedTab[selected="true"] {border-bottom:2px solid #eb3a4d;color:#ffffff;font-weight:650;}
QLineEdit,QPlainTextEdit,QComboBox {background:#1b1b20;border:1px solid #41414a;border-radius:7px;padding:10px;selection-background-color:#c82433;}
QLineEdit:focus,QPlainTextEdit:focus,QComboBox:focus {border:1px solid #e65b69;}
QPushButton:focus {border:1px solid #888894;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:transparent;width:8px;margin:2px;}
QScrollBar::handle:vertical {background:#41414a;border-radius:3px;min-height:40px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QGroupBox {background:#17171b;border:1px solid #33333c;border-radius:10px;margin-top:22px;padding:18px;font-weight:600;}
QGroupBox::title {subcontrol-origin:margin;left:14px;padding:0 6px;}
QCheckBox {spacing:9px;padding:6px;}
QCheckBox::indicator {width:18px;height:18px;background:#111116;border:1px solid #666672;border-radius:4px;}
QCheckBox::indicator:checked {background:#c82433;border-color:#c82433;}
QDialog,QMenu {background:#17171b;}
QMenu {border:1px solid #44444e;padding:6px;}
QMenu::item {padding:9px 20px;border-radius:5px;}
QMenu::item:selected {background:#40232b;}
QMenuBar,QStatusBar {background:#141417;color:#a8a8b4;}
QMenuBar::item:selected {background:#303037;}
'''

def asset_path(name):return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'assets'/name

class MainWindow(QMainWindow):
    def __init__(self,api=None):
        super().__init__();self.api=api or Api(parent=self);self.me=None;self.page=None;self.history=[];self.seen_alert=0;self.polling=False
        application=QApplication.instance()
        if not application.property('amerikaFontLoaded'):
            font_id=QFontDatabase.addApplicationFont(str(asset_path('Inter.ttf')))
            if font_id>=0:application.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0],11))
            application.setProperty('amerikaFontLoaded',True)
        self.setWindowTitle('Amerika Social');self.resize(1320,940);self.setMinimumSize(980,680);self.setWindowIcon(QIcon(str(asset_path('logo.png'))));check_path=str(asset_path('check.svg')).replace('\\','/');self.setStyleSheet(STYLE+f'QCheckBox::indicator:checked {{image:url("{check_path}");}}')
        central=QWidget();central.setObjectName('appShell');self.setCentralWidget(central);layout=QHBoxLayout(central);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0);sidebar=QWidget();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(248);nav=QVBoxLayout(sidebar);nav.setContentsMargins(20,28,20,22);nav.setSpacing(12);layout.addWidget(sidebar)
        logo=QLabel();logo.setPixmap(QPixmap(str(asset_path('logo.png'))).scaled(44,44,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));logo.setAccessibleName('Amerika Social logo');wordmark=text('amerika.',True);wordmark.setStyleSheet('font-size:27px;font-weight:750;');nav.addWidget(row(logo,wordmark))
        tagline=text('WHY CAN’T WE BE FRIENDS?');tagline.setObjectName('eyebrow');nav.addWidget(tagline);nav.addSpacing(10)
        nav_scroll=QScrollArea();nav_scroll.setWidgetResizable(True);nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);nav_body=QWidget();links=QVBoxLayout(nav_body);links.setContentsMargins(0,0,0,0);links.setSpacing(5);nav_scroll.setWidget(nav_body);nav.addWidget(nav_scroll,1);self.nav_buttons={}
        groups=[('YOUR SQUARE',[('Home','home',lambda:self.feed()),('My profile','profile',lambda:self.profile(self.me['id']) if self.require_login() else None),('Friends','friends',self.friends),('Discover','search',self.explore),('Messages','messages',self.inbox),('Notifications','bell',self.alerts)]),('FIND YOUR PEOPLE',[('Communities','communities',self.communities),('Dating','heart',self.dating)]),('YOUR ACCOUNT',[('Developer hub','code',self.developers),('Settings','settings',self.settings),('Amerika Plus','star',self.plus)])]
        for group,items in groups:
            caption=text(group);caption.setObjectName('eyebrow');links.addSpacing(12);links.addWidget(caption)
            for title,glyph,call in items:
                b=button('  '+title,lambda name=title,fn=call:self.navigate(name,fn));b.setObjectName('nav');b.setIcon(icon(glyph));b.setIconSize(QSize(21,21));b.setAccessibleName(title);self.nav_buttons[title]=b;links.addWidget(b)
        self.mod_button=button('  Moderation',lambda:self.navigate('Moderation',self.moderation));self.mod_button.setObjectName('nav');self.mod_button.setIcon(icon('shield'));links.addWidget(self.mod_button);self.mod_button.hide();links.addStretch();nav.addWidget(button('+  Write a post',self.compose,True));nav.addSpacing(8);self.identity=text('Your next friend is here.');self.identity.setObjectName('muted');nav.addWidget(self.identity);self.auth_button=button('Sign in / register',self.signin);nav.addWidget(self.auth_button)
        self.pages=QStackedWidget();layout.addWidget(self.pages,1);self.login=BrowserLogin(self.api,self);self.login.connected.connect(self.authenticated);self.login.failed.connect(self.error);self.api.expired.connect(self.session_expired)
        self.poller=QTimer(self);self.poller.setInterval(30000);self.poller.timeout.connect(self.poll);self.poller.start()
        self.tray=QSystemTrayIcon(self.windowIcon(),self)
        if QSystemTrayIcon.isSystemTrayAvailable():self.tray.show();self.tray.messageClicked.connect(self.alerts)
        self.build_menu();self.feed();self.api.request('me',done=self.restore,error=self.error)
    def build_menu(self):
        appmenu=self.menuBar().addMenu('Amerika');view=self.menuBar().addMenu('View');help_menu=self.menuBar().addMenu('Help')
        for menu,label,shortcut,call in [(appmenu,'Write a post','Ctrl+N',self.compose),(appmenu,'Sign in','',self.signin),(appmenu,'Sign out','',self.signout),(appmenu,'Quit',QKeySequence.StandardKey.Quit,self.close),(view,'Back','Alt+Left',self.back),(view,'Refresh',QKeySequence.StandardKey.Refresh,self.refresh),(view,'Search','Ctrl+K',self.explore)]:
            action=QAction(label,self)
            if shortcut:action.setShortcut(shortcut)
            action.triggered.connect(lambda checked=False,fn=call:fn());menu.addAction(action)
        for label,path in [('API documentation','/agent.md'),('Privacy policy','/privacy'),('Terms and rules','/terms'),('Support','/support')]:
            action=QAction(label,self);action.triggered.connect(lambda checked=False,p=path:open_external(ORIGIN+p));help_menu.addAction(action)
        about=QAction('About Amerika Social',self);about.triggered.connect(lambda:QMessageBox.about(self,'Amerika Social','Amerika Social 1.0.0\nNative Qt desktop client\nGPL-3.0-only\nWhy Can’t We Be Friends?'));help_menu.addAction(about)
    def navigate(self,name,call):
        self.select_navigation(name);call()
    def select_navigation(self,name):
        for label,b in self.nav_buttons.items():
            b.setProperty('selected',label==name);b.setIcon(icon({'Home':'home','My profile':'profile','Friends':'friends','Discover':'search','Messages':'messages','Notifications':'bell','Communities':'communities','Dating':'heart','Developer hub':'code','Settings':'settings','Amerika Plus':'star'}[label],'#ff7c89' if label==name else '#a9a9b4'));b.style().unpolish(b);b.style().polish(b)
    def show_page(self,factory,remember=True):
        if self.page:
            self.page.active=False
            if hasattr(self.page,'upload_reply') and self.page.upload_reply:self.page.upload_reply.abort()
            self.pages.removeWidget(self.page);self.page.deleteLater()
        if remember:self.history.append(factory)
        self.page=factory();self.pages.addWidget(self.page);self.pages.setCurrentWidget(self.page)
        category={Feed:'Home',Profile:'My profile',Inbox:'Messages',Alerts:'Notifications',DeveloperHub:'Developer hub',Settings:'Settings',Plus:'Amerika Plus',Communities:'Communities',Dating:'Dating',Explore:'Discover'}.get(type(self.page))
        if category:self.select_navigation(category)
    def back(self):
        if len(self.history)>1:self.history.pop();self.show_page(self.history[-1],False)
    def refresh(self):
        if self.page:self.page.refresh()
    def restore(self,data):
        self.me=data.get('actor')
        if not self.me and self.api.token:self.api.clear()
        self.identity.setText(self.me['name']+'\n@'+self.me['handle'].removesuffix('.pds.amerika.social') if self.me else 'Browsing as a guest');self.auth_button.setText('Sign out' if self.me else 'Sign in / register');self.auth_button.clicked.disconnect();self.auth_button.clicked.connect(lambda:self.signout() if self.me else self.signin());self.mod_button.setVisible(bool(self.me and (self.me.get('admin') or self.me.get('moderator'))))
    def authenticated(self,actor,saved):
        self.restore({'actor':actor})
        if hasattr(self,'login_dialog'):self.login_dialog.accept()
        self.history=[];self.feed();self.statusBar().showMessage('Signed in securely.' if saved else 'Signed in for this session. Your system credential store is unavailable, so the session will not be saved.',15000)
    def update_me(self,after=None):self.api.request('me',done=lambda d:(self.restore(d),after() if after else None),error=self.error)
    def require_login(self):
        if self.me:return True
        self.signin();return False
    def signin(self):
        if self.me:return
        d=QDialog(self);self.login_dialog=d;d.setWindowTitle('Connect Amerika Social');d.resize(500,240);layout=QVBoxLayout(d);layout.addWidget(text('Sign in or create your human account in your browser. Complete the human CAPTCHA there, then return here. Your password is never stored in this application.'))
        status=text('');layout.addWidget(status)
        opened=lambda:status.setText('Browser opened. Waiting for your approval…')
        failed=lambda message:status.setText(message)
        self.login.opened.connect(opened);self.login.failed.connect(failed)
        layout.addWidget(button('Open secure sign-in',self.login.start,True));layout.addWidget(button('Cancel',d.reject));d.finished.connect(self.login.cancel);d.exec()
        self.login.opened.disconnect(opened);self.login.failed.disconnect(failed);d.deleteLater()
    def error(self,message):self.statusBar().showMessage(str(message),20000)
    def session_expired(self):self.local_signout();self.error('Your session expired. Sign in again.')
    def signout(self):
        if not self.me:return
        self.api.request('logout',{},lambda d:None,lambda e:None);self.local_signout()
    def local_signout(self):self.api.clear();self.login.cancel();self.seen_alert=0;self.bot_seen={};self.polling=False;self.restore({'actor':None});self.history=[];self.feed()
    def feed(self,path='feed?',title='The social square'):self.show_page(lambda:Feed(self,path,title))
    def thread(self,uri):self.show_page(lambda:Thread(self,uri))
    def profile(self,id):self.show_page(lambda:Profile(self,id))
    def find_profile(self,handle):self.api.request('profile?handle='+quote(handle,safe=''),done=lambda d:self.profile(d['actor']['id']),error=self.error)
    def friends(self):
        if self.require_login():self.friends_list(self.me['id'],'mutual')
    def friends_list(self,id,list_name):
        def factory():
            page=Page(self,list_name.title());page.add(Listing(page,'profile/friends?id='+quote(id,safe='')+'&list='+list_name,'actors',lambda a:person(self,a)));return page
        self.show_page(factory)
    def explore(self,mode='posts'):self.show_page(lambda:Explore(self,mode))
    def inbox(self):
        if self.require_login():self.show_page(lambda:Inbox(self))
    def chat(self,peer):
        if self.require_login():self.show_page(lambda:Inbox(self,peer))
    def alerts(self):
        if self.require_login():self.show_page(lambda:Alerts(self))
    def compose(self,**kwargs):
        if self.require_login():Composer(self,**kwargs).exec()
    def developers(self):
        if self.require_login():self.show_page(lambda:DeveloperHub(self))
    def settings(self):
        if self.require_login():self.show_page(lambda:Settings(self))
    def plus(self):
        if self.require_login():self.show_page(lambda:Plus(self))
    def communities(self):
        if self.require_login():self.show_page(lambda:Communities(self))
    def community(self,id):
        if self.require_login():self.show_page(lambda:Communities(self,id))
    def dating(self,view='explore',subject=None,thread=None):
        if self.require_login():self.show_page(lambda:Dating(self,'chat' if thread else view,subject,thread))
    def moderation(self):
        if self.require_login() and (self.me.get('admin') or self.me.get('moderator')):self.show_page(lambda:Moderation(self))
    def report(self,target,kind):
        d=QDialog(self);d.setWindowTitle('Report prohibited conduct');layout=QVBoxLayout(d);layout.addWidget(text('Profanity and viewpoints are allowed. Report spam, phishing, fraud, piracy, crypto miners or illegal activity.'))
        from .widgets import Form
        form=Form('Report',self.api,'reports',[field('reason','Rule','select','Spam',['Spam','Phishing','Card fraud & testing','Crypto miners','Pirated content','Anything illegal']),field('detail','Concrete details','multiline',max_length=2000)],extra={'target':target,'type':kind},after=lambda result:d.accept());layout.addWidget(form);layout.addWidget(button('Cancel',d.reject));d.exec()
    def poll(self):
        if not self.me or self.polling:return
        self.polling=True
        def done(data):
            self.polling=False;rows=data.get('notifications',[]);latest=max([n['id'] for n in rows]+[0]);settings=QSettings()
            if self.seen_alert and latest>self.seen_alert and settings.value('notifications',False,type=bool):self.tray.showMessage('Amerika Social','You have new account activity.',QSystemTrayIcon.MessageIcon.Information,6000)
            self.seen_alert=latest
            if isinstance(self.page,Inbox) and self.page.peer:self.page.refresh()
            if isinstance(self.page,Dating) and self.page.view in ('chat','inbox'):self.page.refresh()
            if settings.value('notifyBots',False,type=bool):self.poll_bots()
        self.api.request('notifications',done=done,error=lambda e:setattr(self,'polling',False))
    def poll_bots(self):
        def bots(data):
            for bot in data.get('agents',[]):
                self.api.request('agents/action',{'actor':bot['id'],'action':'read_notifications','args':{}},lambda d,id=bot['id']:self.bot_activity(id,d),lambda e:None)
        self.api.request('agents',done=bots,error=lambda e:None)
    def bot_activity(self,id,data):
        latest=max([n['id'] for n in data.get('notifications',[])]+[0]);seen=getattr(self,'bot_seen',{});previous=seen.get(id);seen[id]=latest;self.bot_seen=seen
        if previous and latest>previous:self.tray.showMessage('Amerika Social','One of your bots has new activity.',QSystemTrayIcon.MessageIcon.Information,6000)
    def closeEvent(self,event):
        if self.page:self.page.active=False
        self.login.cancel();self.poller.stop();self.tray.hide();super().closeEvent(event)

def main():
    app=QApplication(sys.argv);app.setOrganizationName('Amerika Social');app.setApplicationName('Amerika Social');app.setApplicationVersion('1.0.0')
    font_id=QFontDatabase.addApplicationFont(str(asset_path('Inter.ttf')))
    if font_id>=0:app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0],11))
    smoke='--smoke-test' in sys.argv
    window=MainWindow(Api(restore=False) if smoke else None);window.show()
    if smoke:
        index=sys.argv.index('--smoke-test');output=sys.argv[index+1] if index+1<len(sys.argv) else 'native-smoke.png'
        def capture():
            ok=window.grab().save(output);window.close();app.exit(0 if ok else 1)
        QTimer.singleShot(5000,capture)
    sys.exit(app.exec())
