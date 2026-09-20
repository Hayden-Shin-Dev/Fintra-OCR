# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import base64,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import publish_endpoint as publisher
class PublicLinkTests(unittest.TestCase):
    def test_allow_only_https_quick_tunnels(self):
        for bad in ['http://good.trycloudflare.com','https://evil.com','https://good.trycloudflare.com.evil.org','https://user@good.trycloudflare.com','https://good.trycloudflare.com/path']:
            with self.assertRaises(ValueError):publisher.endpoint_record(bad)
    def test_public_record_has_no_private_data(self):
        record=publisher.endpoint_record('https://good.trycloudflare.com')
        self.assertEqual(set(record),{'origin','online','updated_at'})
    def test_publishes_new_origin(self):
        old={'origin':'https://old.trycloudflare.com','online':True}
        response={'sha':'test','content':base64.b64encode(json.dumps(old).encode()).decode()}
        with patch.object(publisher,'github_token',return_value='test-secret'),patch.object(publisher,'github',side_effect=[response,{}]) as api:
            publisher.publish('https://new.trycloudflare.com')
            body=api.call_args_list[1].args[1]
            decoded=json.loads(base64.b64decode(body['content']))
            self.assertEqual(decoded['origin'],'https://new.trycloudflare.com')
            self.assertNotIn('test-secret',json.dumps(decoded))
            self.assertEqual(body['sha'],'test')
    def test_unchanged_endpoint_does_not_commit(self):
        old={'origin':'https://same.trycloudflare.com','online':True}
        response={'sha':'test','content':base64.b64encode(json.dumps(old).encode()).decode()}
        with patch.object(publisher,'github_token',return_value='secret'),patch.object(publisher,'github',return_value=response) as api:
            publisher.publish(old['origin']);self.assertEqual(api.call_count,1)
    def test_offline_state_published(self):
        old={'origin':'https://same.trycloudflare.com','online':True}
        response={'sha':'test','content':base64.b64encode(json.dumps(old).encode()).decode()}
        with patch.object(publisher,'github_token',return_value='secret'),patch.object(publisher,'github',side_effect=[response,{}]) as api:
            publisher.publish(old['origin'],False)
            self.assertFalse(json.loads(base64.b64decode(api.call_args_list[1].args[1]['content']))['online'])
