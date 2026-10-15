from urllib.parse import quote
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLineEdit,QComboBox
from .widgets import Page,Listing,Media,text,button,row,clear,field,secret
from .hub import EXPIRY,webhooks
from .social import PostCard

class Moderation(Page):
    def __init__(self,app):
        super().__init__(app,'Moderation & administration');self.built=False;self.tab='reports';self.listing=None
        self.add(text('Enforce prohibited conduct with concrete evidence. Swearing, criticism and unpopular viewpoints are allowed.'))
        self.summary=self.add(text(''));self.loaders.append(self.overview);self.overview()
    def overview(self):
        def render(data):
            self.data=data;counts=data.get('counts',{});self.summary.setText(f"{counts.get('openReports',0)} open reports · {counts.get('removedPosts',0)} removed posts · {counts.get('suspendedAccounts',0)} suspended accounts")
            if self.built:return
            self.built=True;self.add(row(*[button(t.title(),lambda tab=t:self.select(tab)) for t in ('reports','posts','accounts','audit')]))
            self.query=QLineEdit();self.query.setPlaceholderText('Search reports, posts or accounts');self.add(self.query);self.status_filter=QComboBox();self.status_filter.addItems(['open','closed','all','removed','suspended']);self.add(self.status_filter);self.add(button('Apply filters',lambda:self.select(self.tab)));self.results=QVBoxLayout();self.content.addLayout(self.results);self.select('reports')
            if data.get('role')=='admin':self.admin_sections()
        self.get('moderation/overview',render)
    def select(self,tab):
        self.tab=tab
        if self.listing:self.loaders.remove(self.listing.reload);self.listing.hide();self.listing.deleteLater()
        status=self.status_filter.currentText()
        if tab!='reports' and status in ('open','closed'):status='all'
        self.listing=Listing(self,'moderation/'+tab+'?status='+status+'&q='+quote(self.query.text(),safe=''),tab,self.item);self.results.addWidget(self.listing)
    def decision(self,layout,target,actions,report=None):
        self.form('Record moderation decision','moderation/action',[field('rule','Banned-content rule','select',self.data['rules'][0],self.data['rules']),field('evidence','Concrete evidence (10–1,800 characters)','multiline',max_length=1800),field('action','Decision','select',actions[0],actions)],extra={'target':target,**({'report':report} if report else {})},after=lambda d:self.refresh(),layout=layout,submit='Record decision')
    def item(self,item):
        w=QWidget();layout=QVBoxLayout(w)
        if self.tab=='audit':
            for key in ('action','reason','target','admin','created'):layout.addWidget(text(key+': '+str(item.get(key,''))))
        elif self.tab=='reports':
            layout.addWidget(text(item.get('reason','')+' · '+item.get('target_type','')+' · '+item.get('status','')));layout.addWidget(text(item.get('detail','')));content=item.get('content') or {};layout.addWidget(text(content.get('text') or content.get('bio') or item.get('target','')))
            actions=['dismiss','remove-post','restore-post'] if item.get('target_type')=='post' else ['dismiss','suspend','unsuspend'] if item.get('target_type')=='account' else ['dismiss']
            self.decision(layout,item['target'],actions,item['id'])
            if item.get('target_type')=='message' and content.get('sender'):self.decision(layout,content['sender'],['suspend','unsuspend'],item['id'])
        elif self.tab=='posts':layout.addWidget(PostCard(self,item));layout.addWidget(text(item.get('reviewText','')));self.decision(layout,item['uri'],['remove-post','restore-post'])
        else:layout.addWidget(text(item.get('name','')+' @'+item.get('handle','')));layout.addWidget(text(item.get('suspension_reason','')));self.decision(layout,item['id'],['suspend','unsuspend'])
        return w
    def admin_sections(self):
        staff=self.section('Staff roles');self.staff_rows=QVBoxLayout();staff.addLayout(self.staff_rows)
        self.form('Change staff access','moderation/role',[field('actor','Human handle or account ID'),field('role','Role','select','moderator',['moderator','admin','none']),field('reason','Reason for access change (10+ characters)','multiline')],after=lambda d:self.load_staff(),layout=staff)
        connections=self.section('Moderation OAuth MCP');self.connection_rows=QVBoxLayout();connections.addLayout(self.connection_rows)
        connections.addWidget(text('Read-only by default. Optional actions are reversible and rate limited. Private messages, Dating evidence, staff changes and billing are excluded.'))
        self.form('Create moderation connection','moderation/connection',[field('name','Connection name',max_length=80),*EXPIRY,field('actions','Allow reversible moderation actions','bool',False)],after=lambda d:self.load_connections(),layout=connections)
        self.private_reports=self.section('Private Dating reports');self.operations=self.section('Operations and backups');self.operation_summary=text('');self.operations.addWidget(self.operation_summary)
        self.operations.addWidget(self.action('Run and verify backup','admin/backup',{},after=lambda d:self.load_operations()))
        self.deletions=QVBoxLayout();self.operations.addLayout(self.deletions);self.loaders.extend([self.load_staff,self.load_connections,self.load_private,self.load_operations]);self.load_staff();self.load_connections();self.load_private();self.load_operations()
    def load_staff(self):
        def render(data):
            clear(self.staff_rows)
            for a in data.get('staff',[]):self.staff_rows.addWidget(text(a['name']+' @'+a['handle']+' · '+a['role']))
        self.get('moderation/staff',render)
    def load_connections(self):
        def render(data):
            # Preserve secret-entry form drafts across refresh.
            if getattr(self,'connection_ids',None)==[c['id'] for c in data.get('connections',[])]:return
            self.connection_ids=[c['id'] for c in data.get('connections',[])];clear(self.connection_rows)
            for c in data.get('connections',[]):
                self.connection_rows.addWidget(text(c['name']+' · '+('Revoked' if c.get('revoked') else str(c.get('expires') or 'Never expires'))))
                if c.get('revoked'):continue
                self.connection_rows.addWidget(button('View moderation MCP link',lambda value=c:secret(self,{'mcpUrl':value['mcpUrl']})))
                self.connection_rows.addWidget(self.action('Revoke moderation connection','moderation/revoke',{'id':c['id']},after=lambda d:self.invalidate_connections(),warning='Disconnect this moderation bot?'))
                webhooks(self,self.connection_rows,[self.app.me],c['id'])
        self.get('moderation/connections',render)
    def invalidate_connections(self):self.connection_ids=None;self.load_connections()
    def load_private(self):
        def render(data):
            clear(self.private_reports)
            for r in data.get('reports',[]):
                self.private_reports.addWidget(text(r.get('name','')+' · '+r.get('reason','')));self.private_reports.addWidget(text(r.get('detail','')));snapshot=r.get('snapshot') or {};self.private_reports.addWidget(text((snapshot.get('profile') or {}).get('bio','')))
                for m in snapshot.get('messages',[]):self.private_reports.addWidget(text(str(m.get('sender',''))+': '+m.get('text','')))
                for media in r.get('media',[]):self.private_reports.addWidget(Media(self.api,media))
                self.form('Dating report decision','dating/admin/action',[field('reason','Action reason','multiline'),field('action','Action','select','dismiss',['dismiss','remove','restore'])],extra={'id':r['id']},after=lambda d:self.load_private(),layout=self.private_reports)
        self.get('dating/admin/reports',render)
    def load_operations(self):
        ops=self.data.get('operations',{});self.operation_summary.setText('Billing: '+str(self.data.get('billingConfigured',False))+'\nLast backup: '+str(ops.get('lastBackup') or 'None')+'\nVerified restore: '+str(ops.get('remoteVerifiedAt') or 'Not yet verified')+'\nBackup overdue: '+str(ops.get('overdue',True)))
        def render(data):
            clear(self.deletions)
            for job in data.get('jobs',[]):self.deletions.addWidget(text('Deletion '+job.get('actor','')+': '+job.get('status','')+' · '+str(job.get('attempts',0))+' retries · '+str(job.get('last_error') or '')))
        self.get('admin/deletions',render)
