import copy
from types import SimpleNamespace
import cv2
import numpy as np
from fintraocr.ocr import PaddleEngine

def test_orientation_retry_matches_polygon_and_preserves_both_readings(tmp_path):
 path=tmp_path/'input.png';cv2.imwrite(str(path),np.full((80,200,3),255,dtype=np.uint8))
 polys=[[[0,0],[80,0],[80,20],[0,20]],[[0,30],[80,30],[80,50],[0,50]]]
 primary={'rec_texts':['garbled','upright after rotation'],'rec_scores':[.5,.99],'rec_polys':polys,'textline_orientation_angles':[1,1]}
 alternate={'rec_texts':['wrong orientation','Readable name'],'rec_scores':[.4,.99],'rec_polys':list(reversed(polys))}
 class Model:
  def predict(self,image,**kwargs):return [SimpleNamespace(json=copy.deepcopy(alternate if kwargs else primary))]
 engine=object.__new__(PaddleEngine);engine.model=Model()
 result=engine.extract([path])
 assert [t.text for t in result.tokens]==['Readable name','upright after rotation']
 audit=result.pages[0].preprocessing['orientation_audit']
 assert [v['selected_rotation_degrees'] for v in audit['comparisons']]==[0,180]
 assert audit['comparisons'][0]['original_text']=='garbled'
