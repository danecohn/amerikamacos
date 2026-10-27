from urllib.parse import quote,urlencode
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFileDialog,QLineEdit,QComboBox,QCheckBox,QPlainTextEdit
from .widgets import Page,Listing,Media,Form,text,button,row,clear,field,confirm
from .hub import Settings

class Dating(Page):
    def __init__(self,app,view='explore',subject=None,thread=None):
        super().__init__(app,'Vigil Dating');self.view=view;self.subject=subject;self.thread=thread;self.photos=[];self.media=[];self.upload_reply=None;self.built=False
        self.add(text('18+ · Find a date. Make a friend. Be yourself. Dating is optional and separate from your social profile.'))
        self.add(row(button('Explore',lambda:app.dating()),button('Requests & matches',lambda:app.dating('inbox')),button('My profile',lambda:app.dating('edit'))))
        self.loaders.append(self.load);self.load()
    def load(self):
        if self.view=='chat' and self.built:self.load_chat();return
        self.get('dating/me',self.ready)
    def ready(self,data):
        self.owner=data;self.own=data.get('profile');self.options=data.get('options',{})
        if data.get('restricted'):self.status.setText('Your Dating profile was removed. Contact an administrator to appeal.');return
        if self.built:return
        self.built=True
        if not self.own or self.view=='edit':self.editor();return
        if self.view=='inbox':self.inbox_area=QVBoxLayout();self.content.addLayout(self.inbox_area);self.loaders.append(self.load_inbox);self.load_inbox();return
        if self.view=='chat':self.chat();return
        if self.view=='profile':self.profile();return
        self.filters={}
        filters=self.section('Filter by age, preferences and approximate distance')
        self.min_age=QLineEdit('18');self.max_age=QLineEdit('120');filters.addWidget(row(text('Minimum age'),self.min_age,text('Maximum age'),self.max_age))
        for key,options in self.options.items():
            combo=QComboBox();combo.addItems(['Any',*options]);self.filters[key]=combo;filters.addWidget(row(text(key.title()),combo))
        self.nearby=QCheckBox('Sort by approximate distance');filters.addWidget(self.nearby);filters.addWidget(button('Apply filters',self.search))
        self.results=QVBoxLayout();self.content.addLayout(self.results);self.current=None;self.search()
    def search(self):
        query={'minAge':self.min_age.text(),'maxAge':self.max_age.text(),**{key:c.currentText() for key,c in self.filters.items() if c.currentIndex()>0}}
        if self.nearby.isChecked():query['nearby']='1'
        if self.current:self.loaders.remove(self.current.reload);self.current.hide();self.current.deleteLater()
        self.current=Listing(self,'dating/profiles?'+urlencode(query),'profiles',self.card,grid=True);self.results.addWidget(self.current)
    def card(self,p):
        w=QWidget();w.setObjectName('card');layout=QVBoxLayout(w);layout.setContentsMargins(16,16,16,16);layout.setSpacing(12)
        if p.get('photos'):layout.addWidget(Media(self.api,p['photos'][0]))
        layout.addWidget(text(p['name']+', '+str(p['age']),True));layout.addWidget(text(p.get('intent','')+' · '+(p.get('distance') or 'Distance private')));layout.addWidget(button('View Dating profile',lambda:self.app.dating('profile',p['id'])));return w
    def editor(self):
        p=self.own or {};self.photos=list(p.get('photos',[]));self.photo_area=QVBoxLayout();self.content.addLayout(self.photo_area);self.render_photos()
        self.upload_button=self.add(button('Add profile photo' if self.own else 'Save a private draft below before adding photos',self.upload_profile));self.upload_button.setEnabled(bool(self.own))
        fields=[field('age','Age (18+)','number',18),field('adultConfirmed','I am 18 or older and respect consent','bool',False)]
        fields += [field(key,{'intent':'Here for','gender':'Gender','sexuality':'Sexuality','role':'Dominant / submissive / switch'}.get(key,key),'select','Both' if key=='intent' else 'Prefer not to say',options) for key,options in self.options.items()]
        fields += [field('genderDetail','Gender in your words',required=False,max_length=80),field('sexualityDetail','Sexuality in your words',required=False,max_length=80),field('bio','About you','multiline',required=False,max_length=1500),field('favoriteSong','Favorite song',required=False,max_length=200),field('perfectDay','My perfect day','multiline',required=False,max_length=400),field('lookingFor','What I am looking for','multiline',required=False,max_length=400),field('enabled','Show my profile in the grid','bool',False)]
        self.profile_form=self.form('Your Dating profile','dating/profile',fields,initial=p,extra={'photos':[m['id'] for m in self.photos]},after=self.saved_profile,submit='Save Dating profile' if self.own else 'Save private draft')
        if self.own:
            self.add(button('Share location for approximate distance',lambda:Settings.locate(self,'dating/location')))
            self.add(self.action('Turn off distance','dating/location',{'enabled':False}));self.add(self.action('Pause profile','dating/pause',{},after=lambda d:self.app.dating('edit')))
            self.add(self.action('Delete Dating profile','dating/delete',{},after=lambda d:self.app.dating(),warning='Permanently delete your Dating profile, media and conversations? Your social account remains.'))
        for a in self.owner.get('blocked',[]):self.add(self.action('Unblock '+a['name'],'dating/block',{'subject':a['id'],'blocked':False}))
    def saved_profile(self,data):self.app.dating('edit')
    def render_photos(self):
        clear(self.photo_area)
        for i,m in enumerate(self.photos):
            self.photo_area.addWidget(Media(self.api,m));self.photo_area.addWidget(row(button('Remove photo',lambda item=m:self.remove_photo(item)),button('Move earlier',lambda index=i:self.move_photo(index))))
    def remove_photo(self,item):self.photos.remove(item);self.profile_form.extra['photos']=[m['id'] for m in self.photos];self.render_photos()
    def move_photo(self,index):
        if index>0:self.photos[index-1],self.photos[index]=self.photos[index],self.photos[index-1];self.profile_form.extra['photos']=[m['id'] for m in self.photos];self.render_photos()
    def upload_profile(self):
        if len(self.photos)>=6:self.status.setText('Up to six photos are supported.');return
        self.upload('dating/upload?purpose=profile',False,self.photo_ready)
    def photo_ready(self,data):self.photos.append(data);self.profile_form.extra['photos']=[m['id'] for m in self.photos];self.render_photos();self.status.setText('Photo added. Save your profile to keep the changes.')
    def upload(self,path,video,after):
        filename,_=QFileDialog.getOpenFileName(self,'Select video' if video else 'Select photo','','Videos (*.mp4 *.mov *.m4v *.webm)' if video else 'Images (*.jpg *.jpeg *.png *.webp *.heic *.heif)')
        if not filename:return
        if self.upload_reply:self.status.setText('Wait for the current upload or cancel it.');return
        self.cancel_button=self.add(button('Cancel upload',lambda:self.upload_reply.abort() if self.upload_reply else None))
        def finish():self.upload_reply=None;self.cancel_button.hide()
        def done(data):finish();after(data)
        def error(e):finish();self.status.setText(e)
        try:self.upload_reply=self.api.request(path,done=done,error=error,file=filename,progress=lambda sent,total:self.status.setText(f'Uploading {sent*100//max(total,1)}%'))
        except (ValueError,OSError) as e:error(str(e))
    def profile(self):
        def render(data):
            p=data['profile'];self.add(text(p['name']+', '+str(p['age']),True))
            for photo in p.get('photos',[]):self.add(Media(self.api,photo))
            for key in ('bio','intent','gender','genderDetail','sexuality','sexualityDetail','role','favoriteSong','perfectDay','lookingFor','distance'):
                if p.get(key):self.add(text(key+': '+str(p[key])))
            if data.get('conversation'):self.add(button('Open request or match',lambda:self.app.dating(thread=data['conversation']['id'])))
            else:self.form('Introduce yourself','dating/request',[field('text','Your introduction','multiline',max_length=2000)],extra={'recipient':p['id']},after=lambda d:self.app.dating(thread=d['id']),submit='Send message request')
            self.safety(p['id'])
        self.get('dating/profile?id='+quote(self.subject,safe=''),render)
    def load_inbox(self):
        def render(data):
            clear(self.inbox_area)
            for t in data.get('conversations',[]):
                if t['status'] not in ('pending','accepted'):continue
                self.inbox_area.addWidget(text(t['peer']['name']+' · '+('Matched' if t['status']=='accepted' else 'Sent — awaiting acceptance' if t['sender']==self.app.me['id'] else 'Received — accept to match')+' · '+str(t.get('unread',0))+' unread'))
                self.inbox_area.addWidget(text((t.get('last') or {}).get('text') or 'Attachment'));self.inbox_area.addWidget(button('Open conversation',lambda id=t['id']:self.app.dating(thread=id)))
        self.get('dating/inbox',render)
    def chat(self):
        self.chat_header=QVBoxLayout();self.content.addLayout(self.chat_header);self.chat_messages=QVBoxLayout();self.content.addLayout(self.chat_messages);self.more=self.add(button('Older messages',lambda:self.load_chat(True)));self.cursor=None;self.seen=set();self.chat_ready=False;self.load_chat()
    def load_chat(self,more=False):
        def render(data):
            t=data['conversation'];peer=data['peer'];self.cursor=data.get('cursor');self.more.setVisible(self.cursor is not None)
            if not more:clear(self.chat_messages);self.seen=set()
            for m in data.get('messages',[]):
                if m['id'] in self.seen:continue
                self.seen.add(m['id']);self.chat_messages.addWidget(text(('You' if m['sender']==self.app.me['id'] else peer['name'])+' · '+m.get('created','')));self.chat_messages.addWidget(text(m.get('text','')))
                for media in m.get('media',[]):self.chat_messages.addWidget(Media(self.api,media))
            self.api.request('dating/read',{'id':self.thread})
            if self.chat_ready:
                if t['status']!=self.chat_status:self.app.dating(thread=self.thread)
                return
            self.chat_ready=True;self.chat_status=t['status'];self.chat_header.addWidget(text(peer['name']+' · '+t['status'],True))
            if t['status']=='pending' and t['sender']!=self.app.me['id']:self.chat_header.addWidget(row(self.action('Accept — it’s a match','dating/respond',{'id':self.thread,'action':'accept'},after=lambda d:self.app.dating(thread=self.thread)),self.action('Decline','dating/respond',{'id':self.thread,'action':'decline'},after=lambda d:self.app.dating('inbox'))))
            elif t['status']=='accepted':
                self.message_input=QPlainTextEdit();self.message_input.setAccessibleName('Dating message');self.add(self.message_input);self.staged=QVBoxLayout();self.content.addLayout(self.staged)
                self.add(row(button('Add photo',lambda:self.upload_chat(False)),button('Add video',lambda:self.upload_chat(True)),button('Send',self.send_message,True)))
                self.add(self.action('Unmatch','dating/unmatch',{'id':self.thread},after=lambda d:self.app.dating('inbox'),warning='End this match and stop further Dating messages?'))
            else:self.add(text('You can message after the recipient accepts.'))
            self.safety(peer['id'],self.thread)
        self.get('dating/thread?id='+str(self.thread)+('&before='+str(self.cursor) if more else ''),render)
    def upload_chat(self,video):self.upload('dating/upload?purpose=chat&thread='+str(self.thread),video,self.chat_upload_done)
    def chat_upload_done(self,data):self.media.append(data);self.render_staged()
    def render_staged(self):
        clear(self.staged)
        for m in self.media:self.staged.addWidget(row(text(m.get('mime','Attachment')+' ready'),button('Remove',lambda item=m:self.remove_staged(item))))
    def remove_staged(self,item):self.media.remove(item);self.render_staged()
    def send_message(self):
        if self.upload_reply:self.status.setText('Wait for the upload to finish.');return
        body={'id':self.thread,'text':self.message_input.toPlainText(),'media':[m['id'] for m in self.media]}
        def done(d):self.message_input.clear();self.media=[];self.render_staged();self.load_chat()
        self.api.request('dating/message',body,done,lambda e:self.status.setText(e))
    def safety(self,subject,thread=None):
        area=self.section('Safety — block and private report');area.addWidget(self.action('Block Dating account','dating/block',{'subject':subject,'blocked':True},after=lambda d:self.app.dating('inbox'),warning='Block this person in Dating?'))
        self.form('Private report','dating/report',[field('reason','Reason','select','Harassment',['Harassment','Spam or scam','Non-consensual content','Underage account','Illegal content','Other']),field('detail','Details','multiline',max_length=2000)],extra={'subject':subject,**({'thread':thread} if thread else {})},layout=area,submit='Submit report')
