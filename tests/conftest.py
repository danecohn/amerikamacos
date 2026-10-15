import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QObject,Signal,QTimer
from amerika.app import MainWindow

ME={'id':'human','name':'Reviewer','handle':'reviewer.pds.amerika.social','kind':'human','bio':'Native app test','plus':True,'admin':True}
PEER={'id':'neighbor','name':'Neighbor','handle':'neighbor.pds.amerika.social','kind':'human','bio':'Hello','following':True}
BOT={'id':'bot','name':'Community Host','handle':'host.pds.amerika.social','kind':'agent','bio':'Friendly agent','personality':'Be kind','plus':True}
POST={'uri':'preview:post','text':'Hello #friends @neighbor','created':'2026-10-14T00:00:00Z','author':PEER,'likes':1,'replies':1,'reposts':0,'media':[]}
OPTIONS={'intent':['Both','Dating','Friendship'],'gender':['Prefer not to say','Woman','Man','Nonbinary'],'sexuality':['Prefer not to say','Straight','Gay','Bisexual'],'role':['Prefer not to say','Dominant','Submissive','Switch']}
PROFILE={'id':'human','name':'Reviewer','age':25,'adultConfirmed':True,'enabled':False,'photos':[],'intent':'Both','gender':'Prefer not to say','sexuality':'Prefer not to say','role':'Prefer not to say','bio':'Native Dating test'}
COMMUNITY={'id':'community','name':'Music friends','slug':'music-friends','members':2,'posts':1,'role':'owner','joined':True,'description':'Music','guidelines':'Be friendly'}

class FakeApi(QObject):
    expired=Signal()
    def __init__(self):super().__init__();self.origin='https://www.amerika.social';self.token='synthetic-test-session';self.calls=[];self.responses={};self.epoch=0
    def clear(self):self.token=None;self.epoch+=1
    def set_token(self,token):self.token=token;return False
    def asset(self,url,done,error=None):return None
    def request(self,path,body=None,done=None,error=None,**kwargs):
        self.calls.append((path,body));base=path.split('?')[0]
        result=self.responses.get(path,self.responses.get(base))
        if result is None:
            result={'me':{'actor':ME},'feed':{'posts':[POST],'cursor':None},'thread':{'post':POST,'root':POST,'conversation':[],'conversationCursor':None},'profile':{'actor':PEER},'actors':{'actors':[PEER,BOT],'cursor':None},'profile/friends':{'actors':[PEER],'cursor':None},'friends':{'friends':[PEER]},'notifications':{'notifications':[],'cursor':None,'unread':0},'messages':{'messages':[],'conversations':[],'cursor':None},'agents':{'agents':[BOT],'keys':[]},'account-mcp':{'keys':[]},'oauth/grants':{'grants':[]},'mcp-events':{'subscriptions':[]},'webhooks':{'webhooks':[]},'account/blocks':{'accounts':[]},'welcome':{'invites':[]},'billing':{'plus':True,'enabled':True},'dating/me':{'profile':PROFILE,'options':OPTIONS,'blocked':[]},'dating/profile':{'profile':{**PROFILE,'id':'neighbor','name':'Neighbor'},'conversation':None},'dating/profiles':{'profiles':[],'cursor':None},'dating/inbox':{'conversations':[]},'dating/thread':{'conversation':{'id':1,'status':'accepted','sender':'neighbor'},'peer':PEER,'messages':[],'cursor':None},'communities/list':{'communities':[COMMUNITY],'cursor':None},'communities/detail':{'community':COMMUNITY},'communities/members':{'members':[],'cursor':None},'communities/moderation':{'posts':[],'cursor':None},'hashtags':{'tags':['friends']},'moderation/overview':{'role':'admin','rules':['Spam','Phishing'],'counts':{},'operations':{}},'moderation/reports':{'reports':[],'cursor':None},'moderation/posts':{'posts':[],'cursor':None},'moderation/accounts':{'accounts':[],'cursor':None},'moderation/audit':{'audit':[],'cursor':None},'moderation/staff':{'staff':[]},'moderation/connections':{'connections':[]},'dating/admin/reports':{'reports':[]},'admin/deletions':{'jobs':[]}}.get(base,{'ok':True})
        if done:QTimer.singleShot(0,lambda:done(result))
        return None

@pytest.fixture
def window(qtbot):
    api=FakeApi();window=MainWindow(api);qtbot.addWidget(window);window.show();qtbot.waitUntil(lambda:window.me is not None);return window,api
