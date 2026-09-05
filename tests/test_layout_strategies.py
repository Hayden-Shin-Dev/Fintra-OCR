import unittest
from fintra.extraction.layout import Layout
from fintra.extraction.strategies import CommercialInvoiceExtractor, PackingListExtractor, BillOfLadingExtractor
from fintra.ocr.adapter import OCRRegion, OCRResult

def document(words,scale=1,kind='Commercial Invoice'):
    return OCRResult('random-id',kind,'not-used.png',[
        OCRRegion([[x*scale,y*scale],[(x+w)*scale,y*scale],[(x+w)*scale,(y+10)*scale],[x*scale,(y+10)*scale]],text,index=i)
        for i,(x,y,w,text) in enumerate(words)],metadata={'page_width':1000*scale,'page_height':1000*scale})

class LayoutTests(unittest.TestCase):
    def test_reading_order_groups_jittered_word_tops(self):
        result=document([(10,101,80,'ACME'),(100,99,50,'LIMITED'),(10,130,80,'SEOUL')])
        self.assertEqual(Layout(result).read(Layout(result).cells),'ACME LIMITED SEOUL')

    def test_scaling_translation_and_identifier_do_not_change_anchor_association(self):
        words=[(600,100,110,'INVOICE NO'),(730,100,100,'XQ-2026'),(600,140,110,'INVOICE DATE'),(730,140,140,'14-Nov-2020'),
               (600,550,70,'SUBTOTAL'),(760,550,70,'100.00'),(600,650,120,'GRAND TOTAL'),(760,650,70,'123.50')]
        for scale in (0.5,1,3):
            result=CommercialInvoiceExtractor(document(words,scale)).extract()
            self.assertEqual(result.invoice_number.value,'XQ-2026')
            self.assertEqual(result.invoice_date.value,'14-Nov-2020')
            self.assertEqual(result.total_amount.value,'123.50')

    def test_party_name_keeps_address_in_evidence_and_stops_at_next_heading(self):
        words=[(100,100,60,'SELLER'),(100,120,80,'ACME'),(200,120,70,'LIMITED'),(100,140,150,'123 SEOUL ROAD'),
               (100,180,70,'BUYER'),(100,200,100,'BETA INC')]
        result=CommercialInvoiceExtractor(document(words)).extract()
        self.assertEqual(result.seller.value,'ACME LIMITED')
        self.assertIn('123 SEOUL ROAD',result.seller.source_text)
        self.assertNotIn('BETA',result.seller.source_text)
        self.assertEqual(result.buyer.value,'BETA INC')

    def test_table_uses_headers_and_rows_at_arbitrary_scale(self):
        words=[(100,400,140,'DESCRIPTION'),(400,400,80,'QUANTITY'),(600,400,100,'UNIT PRICE'),(800,400,70,'AMOUNT'),
               (100,450,90,'Widget A'),(400,450,30,'3'),(600,450,60,'10.00'),(800,450,60,'30.00'),
               (100,520,90,'Widget B'),(400,520,30,'2'),(600,520,60,'5.00'),(800,520,60,'10.00'),(650,620,120,'GRAND TOTAL'),(820,620,60,'40.00')]
        for scale in (1,2):
            items=CommercialInvoiceExtractor(document(words,scale)).extract().items
            self.assertEqual(len(items),2)
            self.assertEqual(items[0].description.value,'Widget A')
            self.assertEqual(items[1].quantity.value,'2')
            self.assertEqual(items[1].amount.value,'10.00')

    def test_bl_date_not_selected_as_document_number(self):
        result=BillOfLadingExtractor(document([(600,100,150,'DATE SHIPPED'),(770,100,100,'2020-01-02'),
            (600,140,160,'BILL OF LADING NO'),(780,140,100,'AX-2020')],kind='B/L')).extract()
        self.assertEqual(result.bl_number.value,'AX-2020')
        self.assertEqual(result.shipment_date.value,'2020-01-02')

if __name__=='__main__':unittest.main()
