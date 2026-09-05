import unittest
from fintra.domain.schema import BillOfLading,CommercialInvoice,DocumentMetadata,evidence
from fintra.ocr.adapter import OCRRegion,OCRResult
from fintra.extraction.refinement import typed_refinement, ordered_refinement

class RefinementTests(unittest.TestCase):
    def test_identifier_is_not_guessed_with_two_candidates(self):
        result=OCRResult('unused','B/L','unused',[])
        doc=BillOfLading(DocumentMetadata('x','B/L'),bl_number=evidence('BILL OF LADING NO XQ99271'))
        self.assertEqual(typed_refinement(result,doc).bl_number.value,'XQ99271')
        other=BillOfLading(DocumentMetadata('x','B/L'),bl_number=evidence('XQ99271 AX99272'))
        self.assertEqual(typed_refinement(result,other).bl_number.value,'XQ99271 AX99272')

    def test_explicit_suffix_recovers_missing_unit(self):
        poly=[[0,0],[100,0],[100,10],[0,10]]
        result=OCRResult('x','B/L','x',[OCRRegion(poly,'250KGS')])
        doc=BillOfLading(DocumentMetadata('x','B/L'))
        self.assertEqual(typed_refinement(result,doc).weight_unit.value,'KG')

    def test_reordering_never_reinserts_inline_label(self):
        poly=[[0,0],[100,0],[100,10],[0,10]]
        result=OCRResult('x','Commercial Invoice','x',[OCRRegion(poly,'Seller: ACME')])
        doc=CommercialInvoice(DocumentMetadata('x','Commercial Invoice'),seller=evidence('ACME',source_text='Seller: ACME',bbox=poly))
        self.assertEqual(ordered_refinement(result,doc).seller.value,'ACME')
