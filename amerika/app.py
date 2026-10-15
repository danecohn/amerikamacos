import sys
from pathlib import Path
from urllib.parse import quote
from PySide6.QtCore import Qt,QTimer,QSettings
from PySide6.QtGui import QAction,QIcon,QKeySequence
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QStackedWidget,QPushButton,QSystemTrayIcon,QStyle,QDialog,QMessageBox
from .api import Api,BrowserLogin,ORIGIN,open_external
from .widgets import Page,Listing,text,button,row,field
from .social import Feed,Thread,Profile,Inbox,Alerts,Explore,Composer,person
from .hub import Settings,DeveloperHub,Plus
from .communities import Communities
from .dating import Dating
from .moderation import Moderation

STYLE='''
QWidget {background:#101012;color:#ffffff;font-size:14px;font-family:"Segoe UI","Helvetica Neue",sans-serif;}
QMainWindow {background:#101012;}
QLabel#heading {font-size:25px;font-weight:700;}
QPushButton {background:#202024;border:1px solid #4b4b50;border-radius:6px;padding:10px 14px;text-align:left;}
QPushButton:hover {background:#36363b;border-color:#ffffff;}
QPushButton:pressed {background:#4b4b50;}
QPushButton:disabled {color:#77777e;background:#19191c;}
QPushButton#primary {background:#c82433;border-color:#c82433;color:white;font-weight:700;}
QPushButton#primary:hover {background:#e02e40;}
QLineEdit,QPlainTextEdit,QComboBox {background:#1b1b1f;border:1px solid #55555c;border-radius:5px;padding:8px;selection-background-color:#c82433;}
QLineEdit:focus,QPlainTextEdit:focus,QComboBox:focus,QPushButton:focus {border:2px solid #ffffff;}
QScrollArea {border:0;}
QGroupBox {border:1px solid #414146;border-radius:6px;margin-top:18px;padding:14px;font-weight:600;}
QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 5px;}
QCheckBox {spacing:9px;padding:5px;}
QWidget#card {border-bottom:1px solid #414146;}
QMenu {border:1px solid #55555c;}
QMenu::item {padding:8px 18px;}
QMenu::item:selected {background:#c82433;}
'''

def asset_path(name):return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'assets'/name

class MainWindow(QMainWindow):
    def __init__(self,api=None):
        super().__init__();self.api=api or Api(parent=self);self.me=None;self.page=None;self.history=[];self.seen_alert=0;self.polling=False
        self.setWindowTitle('Amerika Social');self.resize(1260,850);self.setMinimumSize(900,600);self.setWindowIcon(QIcon(str(asset_path('logo.png'))));self.setStyleSheet(STYLE)
        central=QWidget();self.setCentralWidget(central);layout=QHBoxLayout(central);sidebar=QWidget();sidebar.setFixedWidth(225);nav=QVBoxLayout(sidebar);layout.addWidget(sidebar);nav.addWidget(text('A  Amerika',True));nav.addWidget(text('Why Can’t We Be Friends?'));self.identity=text('Browsing as a guest');nav.addWidget(self.identity)
        for title,call in [('Home',lambda:self.feed()),('My profile',lambda:self.profile(self.me['id']) if self.require_login() else None),('Friends',self.friends),('Discover & hashtags',self.explore),('Messages',self.inbox),('Notifications',self.alerts),('Amerika Communities',self.communities),('Amerika Dating',self.dating),('Developer hub',self.developers),('Account settings',self.settings),('Amerika Social Plus',self.plus)]:nav.addWidget(button(title,call))
        self.mod_button=button('Moderation',self.moderation);nav.addWidget(self.mod_button);self.mod_button.hide();nav.addWidget(button('+ Write a post',self.compose,True));nav.addStretch();self.auth_button=button('Sign in / register',self.signin);nav.addWidget(self.auth_button)
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
    def show_page(self,factory,remember=True):
        if self.page:
            self.page.active=False
            if hasattr(self.page,'upload_reply') and self.page.upload_reply:self.page.upload_reply.abort()
            self.pages.removeWidget(self.page);self.page.deleteLater()
        if remember:self.history.append(factory)
        self.page=factory();self.pages.addWidget(self.page);self.pages.setCurrentWidget(self.page)
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
    def local_signout(self):self.api.clear();self.login.cancel();self.restore({'actor':None});self.history=[];self.feed()
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
    def closeEvent(self,event):self.login.cancel();self.poller.stop();self.tray.hide();super().closeEvent(event)

def main():
    app=QApplication(sys.argv);app.setOrganizationName('Amerika Social');app.setApplicationName('Amerika Social');app.setApplicationVersion('1.0.0')
    smoke='--smoke-test' in sys.argv
    window=MainWindow(Api(restore=False) if smoke else None);window.show()
    if smoke:
        index=sys.argv.index('--smoke-test');output=sys.argv[index+1] if index+1<len(sys.argv) else 'native-smoke.png'
        def capture():
            ok=window.grab().save(output);window.close();app.exit(0 if ok else 1)
        QTimer.singleShot(5000,capture)
    sys.exit(app.exec())
