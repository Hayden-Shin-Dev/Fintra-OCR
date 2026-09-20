# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import review_writer

class ReviewRepairTests(unittest.TestCase):
    def test_rejected_draft_is_repaired_with_reason(self):
        calls=[]
        def once(question,checks,refs,ask):
            calls.append(1)
            if len(calls)==1:return '',[],{'reason':'인식 시점 오류를 단정함'}
            answer=ask('작성',{}, {'properties':{'implication':{}}})
            return answer['text'],['source'],{'approved':True}
        def ask(prompt,data,schema):
            self.assertEqual(data['corrections'],['인식 시점 오류를 단정함'])
            return {'text':'수정된 조건부 설명'}
        with patch.object(review_writer,'_interpret_once',once):
            text,refs,verdict=review_writer.interpret('위험',[],[],ask)
        self.assertEqual(text,'수정된 조건부 설명');self.assertEqual(verdict['attempts'],2)
    def test_exhaustion_never_approves_rejected_draft(self):
        with patch.object(review_writer,'_interpret_once',return_value=('',[],{'reason':'근거 없음'})) as once:
            text,refs,verdict=review_writer.interpret('위험',[],[],lambda *a:None)
        self.assertFalse(text);self.assertEqual(once.call_count,3)
        self.assertEqual(len(verdict['repair_history']),3)

if __name__=='__main__':unittest.main()
