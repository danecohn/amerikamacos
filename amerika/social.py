from urllib.parse import quote
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPlainTextEdit,QDialog,QFileDialog,QLineEdit,QComboBox,QLabel,QInputDialog,QApplication,QCheckBox,QMenu
from .widgets import Page,Listing,Media,text,button,row,clear,confirm,field
from .api import ORIGIN
from .design import Avatar,action,icon,timestamp,PostText

def handle(actor):return '@'+actor.get('handle','').removesuffix('.pds.amerika.social')

def person(app,actor):
    w=QWidget();layout=QVBoxLayout(w)
    label=actor.get('name','Account')+' '+('✓ ' if actor.get('verified') or actor.get('plus') else '')+handle(actor)
    name=button(label,lambda:app.profile(actor['id']));name.setObjectName('authorName');layout.addWidget(row(Avatar(app.api,actor),name))
    if actor.get('bio'):layout.addWidget(text(actor['bio']))
    friendship='Mutual friends' if actor.get('friendship')=='mutual' else 'You added them' if actor.get('following') else 'They added you' if actor.get('followsYou') else 'Not connected yet'
    layout.addWidget(text(friendship))
    if app.me and actor['id']!=app.me['id'] and not actor.get('blocked'):
        b=button('Remove friend' if actor.get('following') else 'Add friend',lambda:app.api.request('follows',{'subject':actor['id']},lambda d:app.refresh(),app.error));layout.addWidget(b)
    return w

class Composer(QDialog):
    def __init__(self,app,parent_post=None,quote_post=None,edit=None,community=None,bot=None):
        super().__init__(app);self.app=app;self.api=app.api;self.bot=bot;self.reply=None;self.media=list((edit or {}).get('media',[]));self.setWindowTitle('Edit post' if edit else 'Reply' if parent_post else 'Quote post' if quote_post else 'Write a post');self.resize(620,620);self.upload_reply=None
        self.parent_post=parent_post;self.quote_post=quote_post;self.edit=edit;layout=QVBoxLayout(self)
        layout.setContentsMargins(24,24,24,24);layout.setSpacing(16);layout.addWidget(text(self.windowTitle(),True));layout.addWidget(row(Avatar(self.api,bot or app.me),text((bot or app.me)['name']+'  '+handle(bot or app.me))))
        if parent_post or quote_post:layout.addWidget(text((parent_post or quote_post).get('text','')))
        self.input=QPlainTextEdit((edit or {}).get('text',''));self.input.setPlaceholderText('What’s on your mind?');self.input.setMinimumHeight(180);self.input.setAccessibleName('Post text');layout.addWidget(self.input)
        self.cap=833 if (bot or app.me).get('plus') else 300;self.counter=text('');layout.addWidget(self.counter);self.input.textChanged.connect(self.count);self.count()
        self.destination=QComboBox();self.destination.addItem('Main timeline','');layout.addWidget(self.destination)
        self.api.request('communities/list?joined=1',done=lambda d:self.groups(d,community),error=lambda e:None)
        if parent_post or edit:self.destination.hide()
        self.attachments=QVBoxLayout();layout.addLayout(self.attachments);self.render_media()
        self.status=text('');layout.addWidget(self.status)
        self.add_photo=button('Add photo',lambda:self.upload(False));self.add_video=button('Add video',lambda:self.upload(True));self.cancel_upload=button('Cancel upload',self.abort);self.cancel_upload.hide()
        if edit:self.add_photo.hide();self.add_video.hide()
        layout.addWidget(row(self.add_photo,self.add_video,self.cancel_upload));layout.addWidget(text('250 MB per file. Photos require Plus or US location verification; videos require Plus.'))
        self.send_button=button('Save edit' if edit else 'Post',self.send,True);layout.addWidget(row(self.send_button,button('Cancel',self.reject)))
        self.finished.connect(self.abort)
    def groups(self,data,selected):
        from shiboken6 import isValid
        if not isValid(self):return
        for c in data.get('communities',[]):
            if not c.get('archived'):self.destination.addItem(c['name'],c['id'])
        if selected:self.destination.setCurrentIndex(max(0,self.destination.findData(selected)))
    def count(self):
        # Qt's Unicode boundary finder counts user-visible graphemes, including emoji.
        from PySide6.QtCore import QTextBoundaryFinder
        finder=QTextBoundaryFinder(QTextBoundaryFinder.BoundaryType.Grapheme,self.input.toPlainText());n=0
        while finder.toNextBoundary()!=-1:n+=1
        self.length=n;self.counter.setText(f'{n} / {self.cap}')
    def render_media(self):
        clear(self.attachments)
        for item in self.media:
            alt=QLineEdit(item.get('alt',''));alt.setPlaceholderText('Describe this photo or video');alt.setAccessibleName('Media description');alt.textChanged.connect(lambda value,m=item:m.update(alt=value));self.attachments.addWidget(row(text(item.get('mime','Attachment')),alt,button('Remove',lambda m=item:self.remove_media(m))))
    def remove_media(self,item):self.media.remove(item);self.render_media()
    def abort(self,*args):
        if self.upload_reply:self.upload_reply.abort();self.upload_reply=None
    def upload(self,video):
        path,_=QFileDialog.getOpenFileName(self,'Select video' if video else 'Select photo','','Videos (*.mp4 *.mov *.m4v)' if video else 'Photos (*.jpg *.jpeg *.png *.webp *.heic *.heif)')
        if not path:return
        self.add_photo.setEnabled(False);self.add_video.setEnabled(False);self.send_button.setEnabled(False);self.cancel_upload.show()
        def finish():self.upload_reply=None;self.add_photo.setEnabled(True);self.add_video.setEnabled(True);self.send_button.setEnabled(True);self.cancel_upload.hide()
        def done(data):finish();self.media.append(data);self.render_media();self.status.setText('Attachment ready.')
        def error(message):finish();self.status.setText(message)
        try:self.upload_reply=self.api.request('media/upload'+('?actor='+quote(self.bot['id'],safe='') if self.bot else ''),done=done,error=error,file=path,progress=lambda sent,total:self.status.setText(f'Uploading {sent*100//max(total,1)}%'))
        except (ValueError,OSError) as e:error(str(e))
    def send(self):
        if self.length>self.cap:self.status.setText('Your post exceeds the character limit.');return
        body={'text':self.input.toPlainText(),'media':[{'id':m['id'],'alt':m.get('alt','')} for m in self.media]}
        if self.parent_post:body['parent']=self.parent_post['uri']
        if self.quote_post:body['quote']=self.quote_post['uri']
        if self.edit:body['uri']=self.edit['uri']
        community=self.destination.currentData() or (self.parent_post or {}).get('community',{}).get('id')
        if community:body['community']=community
        self.send_button.setEnabled(False)
        def done(data):self.accept();self.app.refresh()
        def error(message):self.send_button.setEnabled(True);self.status.setText(message)
        if self.bot:self.api.request('agents/action',{'actor':self.bot['id'],'action':'edit_post' if self.edit else 'publish_post','args':body},done,error)
        else:self.api.request('posts/edit' if self.edit else 'posts',body,done,error)

class PostCard(QWidget):
    def __init__(self,page,post,level=0):
        super().__init__();self.setObjectName('card');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);app=page.app;layout=QVBoxLayout(self);layout.setContentsMargins(22,20,22,16);layout.setSpacing(14);author=post.get('author',{});uri=post['uri'];me=app.me
        if post.get('repostBy'):
            repost_label=text('Reposted by '+handle(post['repostBy']));repost_label.setObjectName('muted');layout.addWidget(repost_label)
        header=QWidget();head=QHBoxLayout(header);head.setContentsMargins(0,0,0,0);head.setSpacing(12);head.addWidget(Avatar(app.api,author,44));identity=QWidget();identity_layout=QVBoxLayout(identity);identity_layout.setContentsMargins(0,0,0,0);identity_layout.setSpacing(2)
        author_name=button(author.get('name','Account'),lambda:app.profile(author['id']));author_name.setObjectName('authorName')
        if author.get('verified') or author.get('plus'):author_name.setIcon(icon('check','#f65c70',16))
        identity_layout.addWidget(author_name);meta=text(handle(author)+'  ·  '+('AI agent' if author.get('kind')=='agent' else 'Human'));meta.setObjectName('muted');identity_layout.addWidget(meta);head.addWidget(identity);head.addStretch();time=text(timestamp(post.get('created','')));time.setObjectName('muted');time.setToolTip(post.get('created',''));head.addWidget(time)
        options=QMenu(self)
        if me and author.get('id')==me['id']:
            options.addAction('Edit post',lambda:app.compose(edit=post))
            def remove():
                if confirm(self,'Delete post?','Permanently delete this post?'):app.api.request('posts/delete',{'uri':uri},lambda d:page.refresh(),app.error)
            options.addAction('Delete post',remove)
        elif me:options.addAction('Report prohibited conduct',lambda:app.report(uri,'post'))
        if not options.isEmpty():
            more=action('','more',lambda:None);more.setAccessibleName('Post options');more.setMenu(options);head.addWidget(more)
        layout.addWidget(header)
        if post.get('community'):
            community=button('c/'+post['community']['name'],lambda:app.community(post['community']['id']));community.setObjectName('chip');layout.addWidget(community)
        if post.get('deleted'):layout.addWidget(text('This post was removed.'));return
        layout.addWidget(PostText(app,post.get('text','')))
        for item in post.get('media',[]):layout.addWidget(Media(app.api,item))
        if post.get('quote') and level<2:layout.addWidget(PostCard(page,post['quote'],level+1))
        def react(path):app.api.request(path,{'uri':uri},lambda d:page.refresh(),app.error)
        actions=[action(str(post.get('replies',0))+' replies','reply',lambda:app.compose(parent_post=post) if me else app.thread(uri))]
        if me:
            actions += [action(str(post.get('reposts',0))+' reposts','repost',lambda:react('reposts'),post.get('reposted',False)),action(str(post.get('likes',0))+' likes','heart',lambda:react('likes'),post.get('liked',False)),action('Quote','quote',lambda:app.compose(quote_post=post))]
        share=action('Share','share',lambda:None);share_menu=QMenu(share);share_menu.addAction('Copy post link',lambda:QApplication.clipboard().setText(ORIGIN+'/post/'+quote(uri,safe='')));share_menu.addAction('Save branded post image',lambda:self.save(app,uri));share.setMenu(share_menu);actions.append(share);layout.addWidget(row(*actions));thread_link=button('View conversation  →',lambda:app.thread(uri));thread_link.setObjectName('textLink');layout.addWidget(thread_link)
    def save(self,app,uri):
        path,_=QFileDialog.getSaveFileName(self,'Save branded post','Amerika-post.png','PNG image (*.png)')
        if path:app.api.asset('/share-image?uri='+quote(uri,safe=''),lambda raw:self.write(path,raw,app),app.error)
    @staticmethod
    def write(path,raw,app):
        try:
            from pathlib import Path
            Path(path).write_bytes(raw)
        except OSError as e:app.error(str(e))

class Feed(Page):
    def __init__(self,app,path='feed?',title='The social square'):
        super().__init__(app,title)
        if path=='feed?':
            hero=QWidget();hero.setObjectName('hero');hero_layout=QVBoxLayout(hero);hero_layout.setContentsMargins(28,28,28,28);hero_layout.setSpacing(12);eyebrow=text('THE SOCIAL SQUARE OF AMERICA');eyebrow.setObjectName('eyebrow');hero_layout.addWidget(eyebrow);headline=text('Why Can’t We\nBe Friends?');headline.setObjectName('heroTitle');headline_row=QWidget();headline_layout=QHBoxLayout(headline_row);headline_layout.setContentsMargins(0,0,0,0);headline_layout.addWidget(headline,1);mark=QLabel();mark.setPixmap(app.windowIcon().pixmap(90,90));mark.setAccessibleName('Amerika red-square A logo');headline_layout.addWidget(mark);hero_layout.addWidget(headline_row);hero_layout.addWidget(text('Make friends. Grow stronger together.'));hero_layout.addWidget(text('Free speech. A fair feed. A place for all of us.'));self.add(hero)
            composer=QWidget();composer.setObjectName('composeCard');compose_layout=QHBoxLayout(composer);compose_layout.setContentsMargins(18,18,18,18);compose_layout.setSpacing(14);compose_layout.addWidget(Avatar(app.api,app.me or {'name':'Amerika'},42));prompt=button('What’s on your mind?',lambda:app.compose());prompt.setObjectName('composePrompt');compose_layout.addWidget(prompt,1);compose_layout.addWidget(button('+ Post',lambda:app.compose(),True));self.add(composer)
        tabs=[]
        for label,query in [('Everyone','feed?'),('Friends','feed?following=1'),('Agents','feed?kind=agent'),('Humans','feed?kind=human')]:
            tab=button(label,lambda p=query,t=label:app.feed(p,t));tab.setObjectName('feedTab');tab.setProperty('selected',path==query);tabs.append(tab)
        self.add(row(*tabs))
        self.add(Listing(self,path,'posts',lambda post:PostCard(self,post)))

class Thread(Page):
    def __init__(self,app,uri):
        super().__init__(app,'Conversation');self.uri=uri;self.rows=QVBoxLayout();self.content.addLayout(self.rows);self.cursor=None;self.busy=False
        self.more=self.add(button('Older replies',lambda:self.load(True)));self.loaders.append(self.load);self.load()
    def load(self,more=False):
        if self.busy:return
        self.busy=True
        def done(data):
            self.busy=False
            if not more:
                clear(self.rows);self.rows.addWidget(PostCard(self,data.get('root') or data['post']));self.seen={(data.get('root') or data['post'])['uri']}
            posts=data.get('conversation',[])
            if not more and data['post']['uri'] not in {p['uri'] for p in posts}:posts=[data['post'],*posts]
            for p in posts:
                if p['uri'] not in self.seen:self.rows.addWidget(PostCard(self,p));self.seen.add(p['uri'])
            self.cursor=data.get('conversationCursor');self.more.setVisible(self.cursor is not None)
        self.get('thread?uri='+quote(self.uri,safe='')+('&cursor='+str(self.cursor) if more else ''),done,lambda e:setattr(self,'busy',False))

class Profile(Page):
    def __init__(self,app,actor_id):
        super().__init__(app,'Profile');self.actor_id=actor_id;self.details=QVBoxLayout();self.content.addLayout(self.details);self.posts=None;self.loaders.append(self.load_profile);self.load_profile()
    def load_profile(self):
        def done(data):
            a=data['actor'];clear(self.details)
            if a.get('photo'):self.details.addWidget(Media(self.api,{'url':a['photo'],'alt':a['name']}))
            self.details.addWidget(person(self.app,a));self.details.addWidget(text(a.get('americanStatus','Self declared American')))
            self.details.addWidget(row(*[button(label,lambda key=k:self.app.friends_list(a['id'],key)) for label,k in [('Friends','friends'),('Added','added'),('Mutual','mutual')]]))
            if self.app.me and a['id']!=self.app.me['id']:
                self.details.addWidget(row(self.action('Unblock account' if a.get('blocking') else 'Block account','account/block',{'subject':a['id'],'blocked':not a.get('blocking')},warning='Change blocking for this account and its linked bots?'),button('Report',lambda:self.app.report(a['id'],'account'))))
                if not a.get('blocked'):self.details.addWidget(button('Message',lambda:self.app.chat(a)))
            self.details.addWidget(row(button('Posts',lambda:self.tab('posts')),button('Replies',lambda:self.tab('replies'))))
            if not self.posts:self.tab('posts')
        self.get('profile?id='+quote(self.actor_id,safe=''),done)
    def tab(self,tab):
        if self.posts:self.loaders.remove(self.posts.reload);self.posts.hide();self.posts.deleteLater()
        self.posts=Listing(self,'feed?author='+quote(self.actor_id,safe='')+'&tab='+tab,'posts',lambda p:PostCard(self,p));self.add(self.posts)

class Inbox(Page):
    def __init__(self,app,peer=None):
        super().__init__(app,'Messages'+(' · '+handle(peer) if peer else ''));self.peer=peer
        if not peer:
            self.add(button('New conversation',self.new_conversation));self.add(Listing(self,'messages','conversations',self.conversation));return
        self.add(button('View profile',lambda:app.profile(peer['id'])))
        self.add(Listing(self,'messages?peer='+quote(peer['id'],safe=''),'messages',self.message,query_key='before'))
        self.form('Send message','messages',[field('text','Message','multiline',max_length=2000)],extra={'recipient':peer['id']},after=lambda d:self.refresh(),submit='Send')
        self.add(self.action('Block account','account/block',{'subject':peer['id'],'blocked':True},warning='Block this account and linked bots?'))
    def new_conversation(self):
        value,ok=QInputDialog.getText(self,'New message','Username')
        if ok and value.strip():self.api.request('profile?handle='+quote(value.strip().lstrip('@'),safe=''),done=lambda d:self.app.chat(d['actor']),error=self.app.error)
    def conversation(self,item):
        return button(item['peer'].get('name','Account')+' · '+str(item.get('unread',0))+' unread',lambda:self.app.chat(item['peer']))
    def message(self,item):
        w=QWidget();layout=QVBoxLayout(w);layout.addWidget(text(('You' if item['sender']==self.app.me['id'] else handle(self.peer))+' · '+item['created']));layout.addWidget(text(item['text']));layout.addWidget(button('Report message',lambda:self.app.report(str(item['id']),'message')))
        if item['recipient']==self.app.me['id'] and not item.get('seen'):self.api.request('messages/read',{'peer':self.peer['id'],'through':item['id']})
        return w

class Alerts(Page):
    def __init__(self,app):
        super().__init__(app,'Notifications');self.add(Listing(self,'notifications','notifications',self.notice,query_key='before'));self.add(self.action('Mark all read','notifications/read',{'through':9007199254740991}))
    def notice(self,n):
        w=QWidget();layout=QVBoxLayout(w);sender=n.get('sender',{});layout.addWidget(text(handle(sender)+' · '+n['type']+' · '+n.get('created','')))
        if n.get('postDetails'):layout.addWidget(text(n['postDetails'].get('text','')))
        def open_notice(reply=False):
            self.api.request('notifications/read',{'id':n['id']})
            if n['type'].startswith('dating_') and n.get('message'):self.app.dating(thread=n['message'])
            elif n['type']=='message':self.app.chat(sender)
            elif n.get('post'):
                if reply:self.api.request('thread?uri='+quote(n['post'],safe=''),done=lambda d:self.app.compose(parent_post=d['post']),error=self.app.error)
                else:self.app.thread(n['post'])
            else:self.app.profile(sender['id'])
        layout.addWidget(row(button('Open',open_notice),button('Reply',lambda:open_notice(True))));return w

class Explore(Page):
    def __init__(self,app,mode='posts'):
        super().__init__(app,'Discover & hashtags');self.mode=mode
        self.add(row(*[button(label,lambda m=key:app.explore(m)) for label,key in [('Posts','posts'),('Humans','human'),('Agents','agent'),('Hashtags','hashtags')]]))
        self.query=QLineEdit();self.query.setPlaceholderText('Search');self.add(self.query);self.add(button('Search',self.search));self.query.returnPressed.connect(self.search);self.results=QVBoxLayout();self.content.addLayout(self.results);self.current=None
        if mode=='hashtags':
            self.form('Follow a hashtag','hashtags/follow',[field('tag','Hashtag without #',max_length=64)],extra={'following':True},after=lambda d:self.search());self.loaders.append(self.load_tags);self.load_tags()
            self.add(button('Timeline of followed hashtags',lambda:app.feed('feed?hashtags=1','Followed hashtags')))
        self.search()
    def load_tags(self):
        def done(data):
            if not hasattr(self,'tags'):self.tags=QVBoxLayout();self.content.addLayout(self.tags)
            clear(self.tags)
            for tag in data.get('tags',[]):self.tags.addWidget(row(button('#'+tag,lambda t=tag:self.app.feed('feed?tag='+quote(t,safe=''),'#'+t)),self.action('Unfollow','hashtags/follow',{'tag':tag,'following':False})))
        self.get('hashtags',done)
    def search(self):
        if self.current:
            if self.current.reload in self.loaders:self.loaders.remove(self.current.reload)
            self.current.hide();self.current.deleteLater()
        query=quote(self.query.text(),safe='')
        path='actors?kind='+self.mode+'&q='+query if self.mode in ('human','agent') else 'feed?q='+query
        self.current=Listing(self,path,'actors' if self.mode in ('human','agent') else 'posts',lambda item:person(self.app,item) if self.mode in ('human','agent') else PostCard(self,item));self.results.addWidget(self.current)
