# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,json,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import answer_budget,review_actions,grounded_chat

class AnswerLatencyTests(unittest.TestCase):
 def test_deadline_applies_across_calls(self):
  with answer_budget.scope(seconds=-1):
   with self.assertRaises(TimeoutError):answer_budget.remaining()
  self.assertEqual(answer_budget.remaining(),150)
 def test_stream_cancel_closes_response(self):
  event=threading.Event()
  class Response:
   closed=False
   def __enter__(self):return self
   def __exit__(self,*args):self.closed=True
   def __iter__(self):
    yield b'{"message":{"thinking":"working"},"done":false}'
    event.set()
    yield b'{"message":{"content":"late"},"done":true}'
  response=Response()
  with answer_budget.scope(event):
   with self.assertRaises(InterruptedError):answer_budget.receive('http://127.0.0.1:18434/api/chat',{}, {},lambda *a,**k:response,lambda *a:None)
  self.assertTrue(response.closed)
 def test_stream_keeps_complete_content(self):
  import io
  with answer_budget.scope():
   out=answer_budget.receive('http://127.0.0.1:18434/api/chat',{}, {},lambda *a,**k:io.BytesIO(b'{"message":{"content":"{\\"ok\\":"},"done":false}\n{"message":{"content":"true}"},"done":true}\n'),lambda *a:None)
  self.assertEqual(json.loads(out['message']['content']),{'ok':True})
 def test_real_reported_case_actions_no_inference_or_mutation(self):
  p=Path(__file__).resolve().parents[1]/'team-preview/analyses/f55765671657411993e6e5e92b2c723e/result.json'
  if not p.exists():self.skipTest('Local reported case not present')
  audit=json.loads(p.read_text('utf-8'))['audit'];before=json.dumps(audit)
  for q in ['어떤 순서로 검토하면 좋을까?','이 결과로 검토 메모 초안을 써줘']:
   with patch.object(grounded_chat,'model',side_effect=AssertionError('Unneeded inference')):
    r=grounded_chat.answer(audit,q)
   self.assertIn('3525',r['answer']);self.assertIn('3400',r['answer'])
   self.assertTrue(r['citations']);self.assertIn('아직 수행하지 않은',r['answer'])
  self.assertEqual(before,json.dumps(audit))
 def test_specific_followup_not_intercepted(self):
  self.assertIsNone(review_actions.respond('환율 차이가 있으면 어떤 순서로 검토하면 좋을까?',[]))
