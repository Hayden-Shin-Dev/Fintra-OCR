"""Explicit low-latency structural pass; no LLM calls or hidden accuracy claim."""
from .grounded import GroundedSelector

class StructuralSelector(GroundedSelector):
    def __init__(self):
        super().__init__('not-used')
        self.metadata.update(model=None,engine='structural-fast-v1',limitations=['Unrecognized labels require semantic analysis or human review.'])

    def label_request(self,document):
        self.metadata['trace'].append({'stage':'label_selection','method':'domain_candidates_and_relative_structure','model_called':False})
        return {'document_type':'unknown','title_ids':[],'labels':[]}
