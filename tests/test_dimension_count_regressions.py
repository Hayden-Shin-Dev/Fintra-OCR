from fintraocr.table_captions import package_count_caption
from tests.test_structural import doc,run
from fintraocr.layout import value_spans
import pytest

@pytest.mark.parametrize('scale',[.6,1,2.2])
def test_count_heading_requires_package_cell_and_independent_table_headers(scale):
    d=doc([('BILL OF LADING',20,20,400),('Marks and numbers',20,160,200),('No. of cont or other packs',320,160,260),('Measurement',740,160,180),('MARK-X',20,220,130),('9 PACKAGE',320,220,150),('2.5 CBM',740,220,150)],scale)
    assert package_count_caption(d.tokens[2],d,20*scale)
    r=run(d,dtype='bill_of_lading')
    assert len(r.items)==1
    assert r.items[0]['package_count'].value=='9'
    assert r.items[0]['volume'].value=='2.5'
    assert r.items[0]['volume_unit'].value=='m3'
    assert r.items[0]['package_type'].value=='PKG'

def test_known_mass_is_not_volume_and_generic_quantity_is_preserved():
    d=doc([('25 KGS',20,20,150)])
    assert not value_spans(d.tokens[0],'number','volume')
    assert not value_spans(d.tokens[0],'unit','volume_unit')
    assert value_spans(d.tokens[0],'number','gross_weight')
    assert value_spans(d.tokens[0],'number','quantity')

def test_prose_count_or_mass_cell_without_packaging_evidence_abstains():
    d=doc([('BILL OF LADING',20,20,400),('Marks and numbers',20,160,200),('No. of cont or other packs',320,160,260),('Measurement',740,160,180),('9 KG',320,220,150)])
    assert package_count_caption(d.tokens[2],d,20) is None
