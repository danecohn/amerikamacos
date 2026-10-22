from urllib.parse import quote
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLineEdit
from .widgets import Page,Listing,text,button,row,clear,field
from .social import PostCard,person

class Communities(Page):
    def __init__(self,app,community=None):
        super().__init__(app,'Makk Communities');self.community_id=community;self.detail_area=QVBoxLayout();self.content.addLayout(self.detail_area);self.group=None
        if community:
            self.loaders.append(self.load_detail);self.load_detail();return
        self.add(text('Community posts appear in the main timeline and in their own spaces.'))
        self.add(row(button('All communities',lambda:self.search(False)),button('My communities',lambda:self.search(True)),button('My communities timeline',lambda:app.feed('feed?communities=joined','My communities'))))
        self.query=QLineEdit();self.query.setPlaceholderText('Find communities');self.add(self.query);self.add(button('Search',lambda:self.search(False)));self.results=QVBoxLayout();self.content.addLayout(self.results);self.current=None;self.search(False)
        self.form('Create a community','communities/create',[field('name','Name',max_length=80),field('slug','Address (lowercase letters, numbers and hyphens)',max_length=40),field('description','Description','multiline',max_length=1500),field('guidelines','Community guidelines','multiline',required=False,max_length=2000)],after=lambda d:app.community(d['community']['id']),layout=self.section('Create a community'))
    def search(self,joined):
        if self.current:
            self.loaders.remove(self.current.reload);self.current.hide();self.current.deleteLater()
        self.current=Listing(self,'communities/list?q='+quote(self.query.text(),safe='')+('&joined=1' if joined else ''),'communities',self.card);self.results.addWidget(self.current)
    def card(self,c):
        w=QWidget();w.setObjectName('card');layout=QVBoxLayout(w);layout.setContentsMargins(22,20,22,20);layout.setSpacing(12);layout.addWidget(text(c['name'],True));layout.addWidget(text(c.get('description','')));meta=text(f"c/{c['slug']} · {c.get('members',0)} members · {c.get('posts',0)} posts");meta.setObjectName('muted');layout.addWidget(meta);layout.addWidget(button('Open community',lambda:self.app.community(c['id'])));return w
    def load_detail(self):
        def done(data):
            c=data['community'];self.group=c
            if hasattr(self,'details_built'):
                self.summary.setText(c['name']+' · '+str(c.get('members',0))+' members · '+str(c.get('role') or 'Visitor'));return
            self.details_built=True;self.summary=text(c['name']+' · '+str(c.get('members',0))+' members · '+str(c.get('role') or 'Visitor'),True);self.detail_area.addWidget(self.summary);self.detail_area.addWidget(text(c.get('description','')));self.detail_area.addWidget(text(c.get('guidelines','')))
            if c.get('joined'):
                self.detail_area.addWidget(button('Post to community',lambda:self.app.compose(community=c['id']),True))
                if c.get('role')!='owner':self.detail_area.addWidget(self.action('Leave community','communities/leave',{'id':c['id']},after=lambda d:self.app.community(c['id'])))
            else:self.detail_area.addWidget(self.action('Join community','communities/join',{'id':c['id']},after=lambda d:self.app.community(c['id'])))
            members=self.section('Members');members.addWidget(Listing(self,'communities/members?id='+c['id'],'members',self.member))
            if c.get('role')=='owner':
                settings=self.section('Community settings');self.form('Edit community','communities/edit',[field('name','Name',max_length=80),field('description','Description','multiline',max_length=1500),field('guidelines','Guidelines','multiline',required=False,max_length=2000)],extra={'id':c['id']},initial=c,layout=settings)
                settings.addWidget(self.action('Restore community' if c.get('archived') else 'Archive community','communities/archive',{'id':c['id'],'archived':not c.get('archived')},warning='Change whether this community accepts new posts?',after=lambda d:self.app.community(c['id'])))
            if c.get('role') in ('owner','moderator'):
                moderation=self.section('Community moderation');moderation.addWidget(Listing(self,'communities/members?id='+c['id']+'&restricted=1','members',lambda m:row(text(m['name']),self.action('Restore membership','communities/member',{'id':c['id'],'subject':m['actor'],'banned':False}))))
                moderation.addWidget(Listing(self,'communities/moderation?id='+c['id'],'posts',self.removed_post))
            self.add(Listing(self,'feed?community='+quote(c['id'],safe=''),'posts',self.post))
        self.get('communities/detail?id='+quote(self.community_id,safe=''),done)
    def post(self,p):
        w=QWidget();layout=QVBoxLayout(w);layout.addWidget(PostCard(self,p))
        if self.group.get('role') in ('owner','moderator'):self.form('Remove from community','communities/post',[field('reason','Reason',max_length=1000)],extra={'id':self.community_id,'uri':p['uri']},after=lambda d:self.refresh(),layout=layout,submit='Remove from community')
        return w
    def removed_post(self,p):
        w=QWidget();layout=QVBoxLayout(w);layout.addWidget(text(p['text']));self.form('Restore post','communities/post',[field('reason','Restoration reason',max_length=1000)],extra={'id':self.community_id,'uri':p['uri'],'restore':True},after=lambda d:self.refresh(),layout=layout);return w
    def member(self,m):
        c=self.group;w=QWidget();layout=QVBoxLayout(w);layout.addWidget(text(m['name']+' · '+m['role']));layout.addWidget(button('View profile',lambda:self.app.profile(m['actor'])))
        if c.get('role') in ('owner','moderator') and m['actor']!=self.app.me['id'] and m['role']!='owner':
            self.form('Restrict member','communities/member',[field('reason','Restriction reason',max_length=1000)],extra={'id':c['id'],'subject':m['actor'],'banned':True},after=lambda d:self.refresh(),layout=layout)
            if c['role']=='owner' and m.get('kind')=='human':
                layout.addWidget(self.action('Make member' if m['role']=='moderator' else 'Make moderator','communities/member',{'id':c['id'],'subject':m['actor'],'role':'member' if m['role']=='moderator' else 'moderator'},after=lambda d:self.refresh()))
                layout.addWidget(self.action('Transfer ownership','communities/transfer',{'id':c['id'],'subject':m['actor']},warning='Transfer ownership to this person? You will become a moderator.',after=lambda d:self.app.community(c['id'])))
        return w
