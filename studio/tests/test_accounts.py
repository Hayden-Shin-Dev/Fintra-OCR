# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Run in an isolated process: python -m unittest discover -s tests -p test_accounts.py."""
import concurrent.futures
import importlib.util
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from accounts import Accounts


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Accounts(Path(self.tmp.name) / 'users.sqlite3')

    def test_password_persistence_and_case_insensitive_identity(self):
        user = self.db.register('Reviewer', 'strong-password')
        self.assertEqual(Accounts(self.db.path).authenticate('reviewer', 'strong-password'), user)
        self.assertIsNone(self.db.authenticate('reviewer', 'wrong'))
        self.assertIsNone(self.db.authenticate('unknown', 'strong-password'))
        self.assertNotIn(b'strong-password', self.db.path.read_bytes())

    def test_validation(self):
        for name, password in [('../test', 'strong-password'), ('ab', 'strong-password'), ('valid', 'short'), ('valid', 'a'*129), (None, 'strong-password')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.db.register(name, password)

    def test_concurrent_duplicate_registration(self):
        def register(_):
            try:return self.db.register('SameUser', 'strong-password')
            except ValueError:return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            result = list(pool.map(register, range(4)))
        self.assertEqual(sum(r is not None for r in result), 1)
        with self.assertRaises(ValueError):self.db.register('sameuser', 'another-password')

    def test_legacy_migration_is_idempotent(self):
        legacy = Path(self.tmp.name) / 'account.json'
        salt = 'a'*32
        legacy.write_text(json.dumps({'name':'test','salt':salt,'hash':Accounts.digest('test',salt)}))
        owner = self.db.migrate(legacy)
        self.assertEqual(self.db.migrate(legacy), owner)
        self.assertEqual(self.db.authenticate('test','test')['user_id'],owner)


class AuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.environment = patch.dict(os.environ, {'FINTRA_WORKSPACE_DATA':str(root),'FINTRA_WEB_DATA':str(root/'analyses'),'FINTRA_ACCOUNT_FILE':str(root/'account.json'),'FINTRA_PUBLIC_ORIGIN':'','FINTRA_WEB_PORT':'0'})
        cls.environment.start()
        salt = 'b'*32
        (root/'account.json').write_text(json.dumps({'name':'test','salt':salt,'hash':Accounts.digest('test',salt)}))
        cls.legacy_id = 'a'*32
        folder = root/'analyses'/cls.legacy_id
        folder.mkdir(parents=True)
        (folder/'status.json').write_text(json.dumps({'id':cls.legacy_id,'status':'complete','created':1,'files':[],'documents':[],'document_records':[]}))
        import engine
        legacy_job=json.loads((folder/'status.json').read_text())
        cls.engine_state=patch.multiple(engine,DATA=root/'analyses',JOBS={cls.legacy_id:legacy_job},PORT=0)
        cls.engine_state.start()
        spec=importlib.util.spec_from_file_location('fintra_auth_test_server',Path(__file__).resolve().parents[1]/'backend/server.py')
        server=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)
        cls.server = server
        cls.http = server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        server.engine.PORT = cls.http.server_port
        cls.thread = threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
        cls.engine_state.stop();cls.environment.stop();cls.tmp.cleanup()

    def call(self, path, body=None, cookie=None, raw=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=5)
        request_headers = {'X-Fintra-Request':'1'}
        if cookie:request_headers['Cookie']=cookie
        if headers:request_headers.update(headers)
        conn.request('POST' if body is not None or raw is not None else 'GET',path,body=raw if raw is not None else json.dumps(body) if body is not None else None,headers=request_headers)
        response=conn.getresponse();data=response.read();status=response.status
        cookie=response.getheader('Set-Cookie');conn.close()
        return status,json.loads(data),cookie

    def setUp(self):
        self.server.ATTEMPTS.clear()

    def register(self, name):
        status,_,cookie=self.call('/api/register',{'name':name,'password':'strong-password','confirm_password':'strong-password'})
        self.assertEqual(status,200)
        return cookie

    def test_complete_isolation_flow(self):
        alice=self.register('alice');bob=self.register('bob')
        self.assertIn('HttpOnly',alice)
        self.assertIn('SameSite=Strict',alice)
        status,history,_=self.call('/api/analyses',cookie=alice)
        self.assertEqual((status,history),(200,[]))
        self.assertEqual(self.call('/api/login',{'name':'test','password':'test'})[0],200)
        legacy=self.call('/api/login',{'name':'test','password':'test'})[2]
        self.assertIn(self.legacy_id,[r['id'] for r in self.call('/api/analyses',cookie=legacy)[1]])
        multipart=b'--boundary\r\nContent-Disposition: form-data; name="documents"; filename="invoice.png"\r\nContent-Type: image/png\r\n\r\nimage\r\n--boundary--\r\n'
        with patch.object(self.server.engine.POOL,'submit'):
            status,created,_=self.call('/api/analyses',raw=multipart,cookie=alice,headers={'Content-Type':'multipart/form-data; boundary=boundary'})
        self.assertEqual(status,202);jid=created['id']
        self.assertEqual(self.call('/api/analyses/'+jid,cookie=alice)[0],200)
        self.assertEqual(self.call('/api/analyses',cookie=bob)[1],[])
        for prefix in ('/api/analyses/','/api/jobs/'):
            for suffix in ('','/result','/download','/report','/edited-report','/draft','/workpaper','/documents/document-0/image/1','/evidence/e-'+'c'*24,'/chat','/chat/'+'d'*32+'/events'):
                with self.subTest(prefix=prefix,suffix=suffix):
                    self.assertEqual(self.call(prefix+jid+suffix,cookie=bob)[0],404)
            for suffix in ('/cancel','/corrections','/compare','/draft','/workpaper','/chat','/chat/'+'d'*32+'/cancel'):
                with self.subTest(prefix=prefix,suffix=suffix):
                    self.assertEqual(self.call(prefix+jid+suffix,{},cookie=bob)[0],404)
        for route in ('/api/support','/api/support/bind'):
            self.assertEqual(self.call(route,{'analysis_id':jid,'question':'자료 설명'},cookie=bob)[0],404)
        with patch.object(self.server.SUPPORT_POOL,'submit'),patch.object(self.server.threading,'Timer'):
            status,task,_=self.call('/api/support',{'question':'안녕하세요'},cookie=alice)
        self.assertEqual(status,202)
        self.assertEqual(self.call('/api/support/history',cookie=bob)[1]['messages'],[])
        for suffix in ('','/events'):
            self.assertEqual(self.call('/api/support/'+task['id']+suffix,cookie=bob)[0],404)
        self.assertEqual(self.call('/api/logout',{},cookie=alice)[0],200)
        self.assertEqual(self.call('/api/analyses/'+jid,cookie=alice)[0],401)
        owner=self.server.engine.JOBS[jid]['owner_id']
        saved=json.loads((self.server.engine.DATA/jid/'status.json').read_text('utf-8'))
        self.assertEqual(saved['owner_id'],owner)
        alice=self.call('/api/login',{'name':'alice','password':'strong-password'})[2]
        self.assertEqual(self.call('/api/analyses/'+jid,cookie=alice)[0],200)

    def test_registration_errors_origin_and_rate_limit(self):
        self.assertEqual(self.call('/api/register',{'name':'new','password':'strong-password','confirm_password':'different'})[0],400)
        self.assertEqual(self.call('/api/register',{'name':'new','password':'strong-password','confirm_password':'strong-password'},headers={'Origin':'https://evil.example'})[0],403)
        for _ in range(20):self.call('/api/login',{'name':'absent','password':'bad'})
        self.assertEqual(self.call('/api/login',{'name':'test','password':'test'})[0],429)


if __name__=='__main__':unittest.main()
