from fintraocr.table_captions import complete_column_parts,merged_table_caption
from tests.test_structural import doc,run
import pytest

@pytest.mark.parametrize('scale',[.55,1,2.1])
def test_merged_caption_columns_and_footer_preserve_one_goods_row(scale):
    d=doc([('COMMERCIAL INVOICE',20,20,400),('PKGS DESCRIPTION',20,160,320),('QTY VALUE',600,160,200),('3',20,220,20),('Valve assembly',150,220,190),('8',610,220,20),('480.00',700,220,90),('REASON FOR RETURN: Inspection',20,290,420),('I declare the information in this invoice is correct.',20,340,700),('7',850,500,20)],scale)
    r=run(d)
    assert len(r.items)==1
    row=r.items[0]
    assert row['package_count'].value=='3'
    assert row['description'].value=='Valve assembly'
    assert row['quantity'].value=='8'
    assert row['amount'].value=='480.00'
    assert row['description'].label_evidence[0].selected_text=='DESCRIPTION'
    assert row['quantity'].label_evidence[0].token_id==row['amount'].label_evidence[0].token_id
    assert row['quantity'].label_evidence[0].end<=row['amount'].label_evidence[0].start

def test_prose_partial_caption_and_isolated_words_do_not_create_columns():
    for text in ['Please check quantity value','QTY 42 VALUE','VALUE: 100','description of packages shipped','QTY VALUE additional']:
        assert complete_column_parts(text)==[]
    d=doc([('COMMERCIAL INVOICE',20,20,400),('QTY VALUE',20,200,200)])
    assert merged_table_caption(d.tokens[1],d,20)==[]
