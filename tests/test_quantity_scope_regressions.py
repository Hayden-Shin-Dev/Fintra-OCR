import fintraocr.table_captions as experiment_quantity104
from tests.test_structural import doc,run
import pytest

@pytest.mark.parametrize('scale',[.5,1,2.4])
def test_ordered_quantity_does_not_merge_into_shipped_quantity(scale):
    d=doc([('PACKING LIST',20,20,400),('Description',20,140,200),('Quantity',350,140,100),('Quantity',580,140,100),('UOM',820,140,70),('Ordered',350,165,100),('Shipped',580,165,100),('Valve',20,230,180),('18',350,230,50),('11',580,230,50),('EA',820,230,50),('Pump',20,290,180),('6',350,290,50),('4',580,290,50),('PCS',820,290,50)],scale)
    r=run(d,dtype='packing_list')
    assert len(r.items)==2
    assert [x['quantity'].value for x in r.items]==['11','4']
    assert [x['unit'].value for x in r.items]==['ea','pcs']
    assert r.mapping_metadata['quantity_column_scope']

def test_distant_words_are_not_quantity_column_qualifiers():
    d=doc([('PACKING LIST',20,20,400),('Quantity',20,140,100),('Ordered',600,165,100),('Shipped',20,600,100)])
    assert experiment_quantity104.quantity_column_qualifiers(d,20)==[]
