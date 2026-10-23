import json
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from amerika.api import Api,BrowserLogin
from conftest import FakeApi

@pytest.fixture
def server():
    records=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            records.append((self.path,self.headers.get('Authorization')))
            code=401 if self.path=='/api/expired' else 200
            body=b'native-image-bytes' if self.path=='/asset' else json.dumps({'ok':True,'error':'Sign in again.'}).encode()
            self.send_response(code);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            data=self.rfile.read(int(self.headers.get('Content-Length','0')));records.append((self.path,self.headers.get('Authorization'),data))
            code=401 if self.path=='/api/account/delete' else 200
            body=json.dumps({'ok':True,'error':'Incorrect password.'}).encode();self.send_response(code);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}',records
    server.shutdown();server.server_close()

def test_assets_load_without_disclosing_session(server,qtbot):
    origin,records=server;api=Api(origin,restore=False);api.token='synthetic';values=[];errors=[];api.asset('/asset',values.append,errors.append);qtbot.waitUntil(lambda:bool(values or errors));assert not errors;assert values==[b'native-image-bytes'];assert records[0][1] is None

def test_json_requests_send_session_only_to_api(server,qtbot):
    origin,records=server;api=Api(origin,restore=False);api.token='synthetic';values=[];api.request('posts',{'text':'Native API test'},values.append);qtbot.waitUntil(lambda:bool(values));assert records[0][1]=='Bearer synthetic';assert json.loads(records[0][2])['text']=='Native API test'

def test_account_switch_discards_inflight_response(server,qtbot):
    origin,records=server;api=Api(origin,restore=False);api.token='synthetic';values=[];api.request('me',done=values.append);api.epoch+=1;qtbot.wait(200);assert not values

def test_wrong_delete_password_preserves_session_but_expired_auth_clears_it(server,qtbot,monkeypatch):
    origin,records=server;api=Api(origin,restore=False);api.token='synthetic';monkeypatch.setattr(api.vault,'clear',lambda:None);errors=[];api.request('account/delete',{'password':'wrong'},error=errors.append);qtbot.waitUntil(lambda:bool(errors));assert api.token=='synthetic';errors.clear();api.request('expired',error=errors.append);qtbot.waitUntil(lambda:bool(errors));assert api.token is None

def test_browser_pairing_uses_pkce_and_cancel_ignores_late_result(qapp,monkeypatch,qtbot):
    import base64,hashlib
    api=FakeApi();api.responses['desktop/start']={'id':'a'*43};opened=[];monkeypatch.setattr('amerika.api.open_external',opened.append);flow=BrowserLogin(api);flow.start();qtbot.wait(20);challenge=api.calls[-1][1]['challenge'];expected=base64.urlsafe_b64encode(hashlib.sha256(flow.verifier.encode()).digest()).decode().rstrip('=');assert challenge==expected;assert opened==['https://altstack.io/desktop-connect#'+'a'*43];flow.cancel();assert not flow.timer.isActive()
