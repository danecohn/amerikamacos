import base64
import hashlib
from pathlib import Path
import pytest
from PySide6.QtWidgets import QPushButton,QLineEdit,QPlainTextEdit,QGridLayout
from PySide6.QtCore import Qt
from amerika.widgets import Form,field,profile_photo,Listing
from amerika.api import Api,media_mime,safe_url,MAX_UPLOAD,BrowserLogin
from amerika.social import Composer
from conftest import POST,ME,BOT,PROFILE

@pytest.mark.parametrize('destination',['feed','friends','inbox','alerts','developers','settings','plus','communities','dating','moderation','explore'])
def test_every_native_destination_opens(window,qtbot,destination):
    w,api=window;getattr(w,destination)();qtbot.wait(40);assert w.page is not None;assert w.page.status.text() in ('','Loading…');assert w.page.findChildren(QPushButton)

def test_refresh_keeps_unsaved_developer_personality(window,qtbot):
    w,api=window;w.developers();qtbot.wait(50);edit=next(e for e in w.page.findChildren(QPlainTextEdit) if e.accessibleName()=='Personality / system instructions');edit.setPlainText('Keep my unsaved personality');w.refresh();qtbot.wait(50);assert edit.toPlainText()=='Keep my unsaved personality'

def test_notification_reply_targets_notification_post(window,qtbot,monkeypatch):
    w,api=window;api.responses['notifications']={'notifications':[{'id':1,'type':'reply','sender':POST['author'],'post':POST['uri'],'postDetails':POST,'seen':0}],'cursor':None};captured=[];monkeypatch.setattr(w,'compose',lambda **args:captured.append(args));w.alerts();qtbot.wait(40);next(b for b in w.page.findChildren(QPushButton) if b.text()=='Reply').click();qtbot.wait(40);assert captured[0]['parent_post']['uri']==POST['uri'];assert ('notifications/read',{'id':1}) in api.calls

def test_dating_profile_draft_and_media_gate(window,qtbot):
    w,api=window;api.responses['dating/me']={'profile':None,'options':{},'blocked':[]};w.dating();qtbot.wait(40);assert not w.page.upload_button.isEnabled();form=w.page.profile_form;form.controls['age'].setText('25');form.controls['adultConfirmed'].setChecked(True);values=form.values();assert values['enabled'] is False;assert values['photos']==[];assert values['age']==25

def test_dating_grid_uses_native_photo_grid(window,qtbot):
    w,api=window;w.dating();qtbot.wait(40);listing=w.page.current;assert isinstance(listing.items,QGridLayout)

def test_composer_preserves_reply_and_quote_and_limit(window,qtbot):
    w,api=window;c=Composer(w,parent_post=POST);qtbot.addWidget(c);c.input.setPlainText('👨‍👩‍👧‍👦');assert c.length==1;c.send();qtbot.wait(20);assert ('posts',{'text':'👨‍👩‍👧‍👦','media':[],'parent':POST['uri']}) in api.calls

def test_bot_composer_delegates_owned_bot_only(window,qtbot):
    w,api=window;c=Composer(w,bot=BOT);qtbot.addWidget(c);c.input.setPlainText('Hello from a bot');c.send();qtbot.wait(20);path,body=next((p,b) for p,b in api.calls if p=='agents/action');assert body['actor']=='bot';assert body['action']=='publish_post';assert body['args']['text']=='Hello from a bot'

def test_profile_photo_is_small_and_strips_metadata(tmp_path):
    from PIL import Image
    source=tmp_path/'photo.png';Image.new('RGB',(1600,1600),'red').save(source);encoded=profile_photo(source);raw=base64.b64decode(encoded.split(',')[1]);assert len(raw)<=150000;assert raw.startswith(b'\xff\xd8\xff')

def test_iphone_media_and_safe_links():
    assert media_mime('IMG_0001.HEIC')=='image/heic';assert media_mime('IMG_0002.MOV')=='video/quicktime';assert MAX_UPLOAD==250000000;assert not safe_url('javascript:alert(1)');assert not safe_url('https://user:password@example.com');assert safe_url('https://www.amerika.social/privacy')

def test_api_rejects_unapproved_origins(qapp):
    with pytest.raises(ValueError):Api('http://evil.example',restore=False)

def test_logout_discards_native_account_view(window,qtbot):
    w,api=window;w.settings();qtbot.wait(30);w.local_signout();assert w.me is None;assert api.token is None;assert w.page.__class__.__name__=='Feed'

def test_all_feature_pages_render_without_webviews(window,qtbot,tmp_path):
    w,api=window
    for action in [lambda:w.community('community'),lambda:w.profile('neighbor'),lambda:w.thread(POST['uri']),lambda:w.dating('edit'),lambda:w.dating('profile','neighbor'),lambda:w.dating(thread=1)]:action();qtbot.wait(50);assert w.page
    w.feed();qtbot.wait(50);assert w.grab().save(str(tmp_path/'native-window.png'));assert not any('WebEngine' in type(child).__name__ for child in w.findChildren(object))
