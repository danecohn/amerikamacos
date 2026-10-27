from urllib.parse import quote
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFileDialog,QCheckBox,QInputDialog
from PySide6.QtCore import QSettings
from .widgets import Page,Listing,Form,Media,text,button,row,clear,field,profile_photo,secret,confirm
from .social import person,handle,PostCard
from .api import ORIGIN,open_external
from .design import Avatar

CONSENT=[field('americanConfirmed','I am the American operator','bool',False),field('rulesAccepted','I agree to the Community Rules','bool',False)]
EXPIRY=[field('days','Expires after days (1–90)','number',30),field('neverExpires','Never expires','bool',False)]
PERMISSIONS=['read','post','like','follow','profile','messages']
CONNECTION=[field('name','Connection name',max_length=64),*EXPIRY,field('scopes','Permissions','scopes',['read','post'],PERMISSIONS)]

def change_photo(page,actor):
    path,_=QFileDialog.getOpenFileName(page,'Choose profile photo','','Images (*.jpg *.jpeg *.png *.webp *.heic *.heif)')
    if not path:return
    try:data=profile_photo(path)
    except Exception as e:page.status.setText(str(e));return
    body={'actor':actor['id'],'photo':data} if actor['id']!=page.app.me['id'] else {'name':actor['name'],'bio':actor.get('bio',''),'photo':data}
    page.api.request('agents/photo' if actor['id']!=page.app.me['id'] else 'profile',body,lambda d:page.app.update_me(page.refresh),lambda e:page.status.setText(e))

def webhooks(page,layout,actors,connection=None):
    actors_by_label={handle(a):a['id'] for a in actors}
    prefix='moderation/webhook' if connection else 'webhooks';context={'connection':connection} if connection else {}
    fields=[field('url','Receiver URL (HTTPS)'),field('signingSecret','Receiver signing secret (optional)','password',required=False)]
    if not connection:fields=[field('actor','Account','select',next(iter(actors_by_label),''),list(actors_by_label)),*fields,field('events','Events','scopes',['reply','mention','quote'],['reply','mention','quote','repost','like','follow','message']),field('includeMessages','Explicitly send private message text to receiver','bool',False)]
    form=page.form('Create webhook',prefix,fields,extra=context,layout=layout)
    old_values=form.values
    def values():
        result=old_values()
        if not connection:result['actor']=actors_by_label[result['actor']]
        return result
    form.values=values
    listing=QVBoxLayout();layout.addLayout(listing)
    def render(data):
        clear(listing)
        for hook in data.get('webhooks',[]):
            listing.addWidget(text(hook['url']+' · '+('Enabled' if hook.get('enabled') else 'Disabled')))
            for d in hook.get('deliveries',[]):listing.addWidget(text(f"{d.get('status')} · {d.get('attempts',0)} attempts · HTTP {d.get('last_status') or '—'} · {d.get('last_error') or ''}"))
            if not hook.get('enabled'):continue
            extra={**context,'id':hook['id']}
            listing.addWidget(page.action('Send test event',prefix+('-test' if connection else '/test'),extra,after=lambda d:load()))
            page.form('Change signing secret',prefix+('-secret' if connection else '/secret'),[field('signingSecret','New receiver secret','password')],extra=extra,after=lambda d:load(),layout=listing)
            listing.addWidget(page.action('Disable webhook',prefix+('-disable' if connection else '/disable'),extra,after=lambda d:load()))
    def load():page.get('moderation/webhooks?connection='+quote(connection,safe='') if connection else 'webhooks',render)
    form.after=lambda d:load();page.loaders.append(load);load()

class DeveloperHub(Page):
    def __init__(self,app):
        super().__init__(app,'Developer hub');self.add(text('Your human account controls your bots. API and MCP original posting is restricted to bots. Like and repost permissions can be granted for the human account.'))
        self.bot_area=self.section('Your bots',initial=True);self.bots_loaded=False;self.bot_ids=[]
        self.form('Create a bot','agents',[field('name','Bot name',max_length=64),field('handle','Bot username',max_length=253),field('password','Bot password (10+ characters)','password',max_length=256),*CONSENT],after=lambda d:self.load_bots(),layout=self.section('Create a bot'))
        self.form('Link an existing bot','agents/link',[field('handle','Bot handle'),field('password','Bot password','password',max_length=256),*CONSENT],after=lambda d:self.load_bots(),layout=self.section('Link or reconnect a bot'))
        self.keys_area=self.section('Issued bot credentials');self.account_area=self.section('Full-account OAuth MCP');self.account_area.addWidget(text(ORIGIN+'/mcp/service'))
        self.form('New account connection','account-mcp',[field('name','Connection name',max_length=64),*EXPIRY],after=lambda d:self.load_account(),layout=self.account_area)
        self.account_keys=QVBoxLayout();self.account_area.addLayout(self.account_keys)
        self.grants_area=self.section('Approved OAuth apps');self.events_area=self.section('MCP event subscriptions')
        self.hooks_area=self.section('Account and bot webhooks');self.hooks_ready=False
        guide=self.section('API guide and MCP setup');guide.addWidget(text('API base: '+ORIGIN+'/api\nAuthorization: Bearer YOUR_BOT_API_KEY\nPOST /posts {"text":"Hello"}\nGET /feed · GET /notifications · GET /messages\nOAuth MCP: '+ORIGIN+'/mcp/service\nCreate bot connections above, save personality instructions, and revoke access when no longer needed.'))
        guide.addWidget(button('Open full API guide',lambda:open_external(ORIGIN+'/agent.md')))
        self.loaders.extend([self.load_bots,self.load_account,self.load_grants,self.load_events]);self.refresh()
    def load_bots(self):
        def render(data):
            bots=data.get('agents',[]);ids=[b['id'] for b in bots]
            # Keep editable bot drafts mounted on refresh. Rebuild only when account ownership changes.
            if ids!=self.bot_ids or not self.bots_loaded:
                self.bot_ids=ids;self.bots_loaded=True;clear(self.bot_area)
                if not bots:self.bot_area.addWidget(text('Create or link your first bot.'))
                for bot in bots:self.bot_area.addWidget(self.bot(bot))
            clear(self.keys_area)
            for k in data.get('keys',[]):
                self.keys_area.addWidget(text(k['name']+' · '+', '.join(k.get('scopes',[]))+' · '+str(k.get('expires') or 'Never expires')))
                if not k.get('revoked'):
                    self.keys_area.addWidget(button('View MCP link',lambda value=k:secret(self,{'mcpUrl':value['mcpUrl']})))
                    self.keys_area.addWidget(self.action('Revoke credential','agent-keys/revoke',{'id':k['id']},after=lambda d:self.load_bots(),warning='Revoke this credential? Connected AI tools will lose access.'))
            if not self.hooks_ready:self.hooks_ready=True;webhooks(self,self.hooks_area,[self.app.me,*bots])
        self.get('agents',render)
    def bot(self,bot):
        w=QWidget();w.setObjectName('card');outer=QVBoxLayout(w);outer.setContentsMargins(18,18,18,18);outer.setSpacing(14);name=text(bot['name']+'  '+handle(bot));name.setStyleSheet('font-weight:650;font-size:16px;');outer.addWidget(row(Avatar(self.api,bot),name));outer.addWidget(text('Your AI agent · '+('Plus active' if bot.get('plus') else 'Standard account')))
        details=QWidget();details.hide();layout=QVBoxLayout(details);layout.setContentsMargins(0,12,0,0);layout.setSpacing(16);outer.addWidget(row(button('Manage bot',lambda:details.setVisible(not details.isVisible())),button('View profile',lambda:self.app.profile(bot['id'])),button('Write as bot',lambda:self.app.compose(bot=bot),True)));outer.addWidget(details);layout.addWidget(button('Change profile picture',lambda:change_photo(self,bot)))
        for list_name in ('friends','added','mutual'):layout.addWidget(button('View '+list_name,lambda key=list_name:self.app.friends_list(bot['id'],key)))
        self.form('Bot profile','agents/profile',[field('name','Name',max_length=64),field('bio','Bio','multiline',required=False,max_length=300)],extra={'actor':bot['id']},initial=bot,layout=layout)
        self.form('Bot personality','agents/personality',[field('personality','Personality / system instructions','multiline',required=False,max_length=12000)],extra={'actor':bot['id']},initial=bot,layout=layout)
        self.form('Bot friends privacy','profile/privacy',[field('friendsPrivate','Keep friends lists private','bool',False)],extra={'actor':bot['id']},initial=bot,layout=layout)
        self.form('Bot OAuth MCP connection','bot-mcp',CONNECTION,extra={'actor':bot['id']},after=lambda d:self.load_bots(),layout=layout)
        self.form('Bot API key','agent-keys',CONNECTION,extra={'actor':bot['id']},after=lambda d:self.load_bots(),layout=layout)
        self.form('Bot recovery codes','recovery/codes',[field('password','Current bot password','password',max_length=256)],extra={'actor':bot['id']},layout=layout)
        for action,title in [('read_posts','Read bot posts'),('read_feed','Read bot feed'),('read_notifications','Read bot notifications'),('read_messages','Read bot messages')]:layout.addWidget(button(title,lambda a=action:self.api.request('agents/action',{'actor':bot['id'],'action':a,'args':{}},lambda d:self.bot_results(bot,a,d),self.app.error)))
        for inviter in bot.get('welcome',{}).get('invites',[]):layout.addWidget(self.action('Accept invitation from '+handle(inviter),'welcome/accept',{'actor':bot['id'],'subject':inviter['id']}))
        return w
    def bot_results(self,bot,action,data):
        # Human-driven inspection of owned bot activity, with native post and message actions.
        from PySide6.QtWidgets import QDialog,QScrollArea
        dialog=QDialog(self);dialog.setWindowTitle(bot['name']+' · '+action);dialog.resize(780,700);layout=QVBoxLayout(dialog);scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();items=QVBoxLayout(body);scroll.setWidget(body);layout.addWidget(scroll)
        rows=data.get('posts') or data.get('notifications') or data.get('messages') or data.get('conversations') or []
        if isinstance(rows,dict):rows=list(rows.values())
        for item in rows:
            if 'uri' in item:
                items.addWidget(PostCard(self,item));items.addWidget(row(button('Reply as bot',lambda p=item:self.app.compose(bot=bot,parent_post=p)),button('Quote as bot',lambda p=item:self.app.compose(bot=bot,quote_post=p)),button('Like as bot',lambda p=item:self.bot_action(bot,'like_post',{'uri':p['uri']})),button('Repost as bot',lambda p=item:self.bot_action(bot,'repost',{'uri':p['uri']}))))
                if item.get('author',{}).get('id')==bot['id']:items.addWidget(row(button('Edit bot post',lambda p=item:self.app.compose(bot=bot,edit=p)),button('Delete bot post',lambda p=item:self.bot_action(bot,'delete_post',{'uri':p['uri']},True))))
            else:
                items.addWidget(text(str(item.get('text') or item.get('type') or item.get('name') or item.get('id',''))))
                if action=='read_notifications' and item.get('post'):
                    items.addWidget(row(button('Open notification thread',lambda n=item:self.app.thread(n['post'])),button('Reply as bot',lambda n=item:self.api.request('thread?uri='+quote(n['post'],safe=''),done=lambda d:self.app.compose(bot=bot,parent_post=d['post']),error=self.app.error))))
        self.form('Send message as bot','agents/action',[field('recipient','Recipient account ID'),field('text','Message','multiline')],extra={'actor':bot['id'],'action':'send_message'},layout=items,submit='Send')
        f=items.itemAt(items.count()-1).widget();old=f.values;f.values=lambda:{'actor':bot['id'],'action':'send_message','args':{k:v for k,v in old().items() if k in ('recipient','text')}}
        layout.addWidget(button('Close',dialog.accept));dialog.exec()
    def bot_action(self,bot,action,args,warning=False):
        if warning and not confirm(self,'Delete bot post?','This permanently deletes the selected bot post.'):return
        self.api.request('agents/action',{'actor':bot['id'],'action':action,'args':args},lambda d:self.status.setText('Bot action completed.'),self.app.error)
    def load_account(self):
        def render(data):
            clear(self.account_keys)
            for k in data.get('keys',[]):
                self.account_keys.addWidget(text(k['name']+' · '+str(k.get('expires') or 'Never expires')))
                if not k.get('revoked'):self.account_keys.addWidget(row(button('View OAuth MCP link',lambda value=k:secret(self,{'mcpUrl':value['mcpUrl']})),self.action('Revoke connection','account-mcp/revoke',{'id':k['id']},after=lambda d:self.load_account(),warning='Disconnect this account MCP connection?')))
        self.get('account-mcp',render)
    def load_grants(self):
        def render(data):
            clear(self.grants_area)
            for g in data.get('grants',[]):self.grants_area.addWidget(text(g.get('name') or g.get('clientName') or g.get('client_id') or 'Authorized app'));self.grants_area.addWidget(self.action('Revoke OAuth access','oauth/revoke',{'id':g['id']},after=lambda d:self.load_grants(),warning='Disconnect this application?'))
        self.get('oauth/grants',render)
    def load_events(self):
        def render(data):
            clear(self.events_area)
            for e in data.get('subscriptions',[]):
                self.events_area.addWidget(text(e.get('name','')+' · '+e.get('url','')+' · '+str(e.get('expires',''))))
                if e.get('enabled'):self.events_area.addWidget(self.action('Stop event subscription','mcp-events/disable',{'id':e['id']},after=lambda d:self.load_events()))
        self.get('mcp-events',render)

class Settings(Page):
    def __init__(self,app):
        super().__init__(app,'Account settings');me=app.me
        photo_card=QWidget();photo_card.setObjectName('card');photo_layout=QVBoxLayout(photo_card);photo_layout.setContentsMargins(20,20,20,20);photo_layout.setSpacing(14);photo_layout.addWidget(row(Avatar(self.api,me,56),text(me['name']+'  '+handle(me),True)));photo_layout.addWidget(row(button('Change profile picture',lambda:change_photo(self,app.me)),self.action('Remove picture','profile',{'name':me['name'],'bio':me.get('bio',''),'photo':None},after=lambda d:app.update_me(),warning='Remove your current profile picture?')));self.add(photo_card)
        self.form('Your profile','profile',[field('name','Display name',max_length=64),field('bio','Bio','multiline',required=False,max_length=300)],initial=me,after=lambda d:app.update_me())
        self.form('Friends privacy','profile/privacy',[field('friendsPrivate','Keep my friends lists private','bool',False)],extra={'actor':me['id']},initial=me)
        location=self.section('Optional US location verification');location.addWidget(text('A location check shows presence in the US, not citizenship. Your exact location is not displayed. Sharing is optional.'))
        location.addWidget(button('Check my current location',lambda:self.locate('location/verify')));location.addWidget(self.action('Remove location verification','location/remove',{},after=lambda d:app.update_me(self.refresh)))
        codes=self.section('Recovery codes');self.form('Generate new recovery codes','recovery/codes',[field('password','Your current password','password',max_length=256)],extra={'actor':me['id']},layout=codes)
        self.blocks=self.section('Blocked accounts');self.welcome=self.section('Welcome invitations');self.loaders.extend([self.load_blocks,self.load_welcome]);self.refresh()
        preferences=self.section('Desktop preferences');settings=QSettings();notifications=QCheckBox('Notify me about new activity while the app is running');notifications.setChecked(settings.value('notifications',False,type=bool));notifications.toggled.connect(lambda value:settings.setValue('notifications',value));preferences.addWidget(notifications)
        bots=QCheckBox('Include activity from my linked bots');bots.setChecked(settings.value('notifyBots',False,type=bool));bots.toggled.connect(lambda value:settings.setValue('notifyBots',value));preferences.addWidget(bots)
        preferences.addWidget(text('Notifications contain a generic activity alert. Message text and Dating details are not shown on the desktop. The application must be running.'))
        self.add(row(button('Developer hub',app.developers),button('Vigil Social Plus',app.plus),button('Sign out',app.signout)))
        deletion=self.section('Permanently delete account');deletion.addWidget(text('Deletes your account, linked bots, social data, Dating profile and media. Minimal billing and moderation records may be retained. Backups rotate out separately. Stripe subscriptions are canceled; Apple subscriptions must be canceled separately.'))
        deletion.addWidget(button('Manage Apple subscriptions',lambda:open_external('https://apps.apple.com/account/subscriptions')))
        form=self.form('Delete account','account/delete',[field('password','Current password','password',max_length=256),field('confirmation','Type DELETE',max_length=6)],after=lambda d:app.local_signout(),layout=deletion,submit='Permanently delete my account')
        original=form.send
        form.send=lambda:original() if confirm(self,'Permanently delete account?','This cannot be undone and includes all your bots.') else None
    def load_blocks(self):
        def render(data):
            clear(self.blocks)
            for a in data.get('accounts',[]):self.blocks.addWidget(row(text(a['name']+' '+handle(a)),self.action('Unblock','account/block',{'subject':a['id'],'blocked':False},after=lambda d:self.load_blocks())))
        self.get('account/blocks',render)
    def load_welcome(self):
        def render(data):
            clear(self.welcome)
            for a in data.get('invites',[]):self.welcome.addWidget(row(text('Add '+handle(a)+'?'),self.action('Accept','welcome/accept',{'actor':self.app.me['id'],'subject':a['id']},after=lambda d:self.load_welcome()),self.action('Dismiss','welcome/dismiss',{'actor':self.app.me['id'],'subject':a['id']},after=lambda d:self.load_welcome())))
        self.get('welcome',render)
    def locate(self,path):
        if not confirm(self,'Share current location?','Use a one-time device location check for this optional feature?'):return
        from PySide6.QtPositioning import QGeoPositionInfoSource
        source=QGeoPositionInfoSource.createDefaultSource(self)
        if not source:self.status.setText('Location services are unavailable. Enable them in system settings, or leave this optional feature off.');return
        self.position_source=source
        def received(position):
            from PySide6.QtPositioning import QGeoPositionInfo
            coords=position.coordinate();accuracy=position.attribute(QGeoPositionInfo.Attribute.HorizontalAccuracy)
            body={'latitude':coords.latitude(),'longitude':coords.longitude(),'accuracy':accuracy,'timestamp':position.timestamp().toMSecsSinceEpoch(),'consent':True,'enabled':True}
            self.api.request(path,body,lambda d:self.app.update_me(self.refresh),self.app.error);source.deleteLater()
        source.positionUpdated.connect(received);source.errorOccurred.connect(lambda error:self.status.setText('Location is unavailable or permission was denied.'));source.requestUpdate(25000)

class Plus(Page):
    def __init__(self,app):
        super().__init__(app,'Vigil Social Plus');self.add(text('Unlimited original posts, an 833-character cap, photo and video uploads, and a verified badge. Linked bots inherit Plus.'))
        self.summary=self.add(text('Checking subscription…'));self.loaders.append(self.load);self.load()
        self.add(button('Upgrade securely with Stripe',lambda:self.checkout('billing/checkout'),True));self.add(button('Manage Stripe subscription',lambda:self.checkout('billing/portal')))
        self.add(button('Manage Apple subscription',lambda:open_external('https://apps.apple.com/account/subscriptions')))
        self.add(self.action('Refresh purchase status','billing/refresh',{},after=lambda d:app.update_me(self.load)))
    def load(self):self.get('billing',lambda d:self.summary.setText('Plus is active.' if d.get('plus') or d.get('active') else 'US$8/month. The secure checkout shows the final price and terms before payment.'))
    def checkout(self,path):self.api.request(path,{},lambda d:open_external(d['url']),self.app.error)
