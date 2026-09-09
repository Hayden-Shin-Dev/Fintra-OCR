import re
from .models import Evidence, FieldValue, Result
from .schemas import SCHEMAS, ITEM_SCHEMAS, ALIASES
from .normalize import normalize,UNITS
import unicodedata

class MappingEngine:
    def __init__(self, selector=None, min_score=0.85, min_ocr=0.70, date_order=None, decimal_separator=None):
        if not 0 <= min_score <= 1 or not 0 <= min_ocr <= 1: raise ValueError("Invalid confidence threshold")
        if date_order not in (None,"DMY","MDY"): raise ValueError("Invalid date order")
        if decimal_separator not in (None,".",","): raise ValueError("Invalid decimal separator")
        self.selector, self.min_score, self.min_ocr = selector, min_score, min_ocr
        self.date_order, self.decimal_separator = date_order, decimal_separator
    @staticmethod
    def evidence(spans, tokens):
        evidence, seen = [], set()
        for s in spans:
            t = tokens.get(s.token_id)
            if t is None or not 0 <= s.start < s.end <= len(t.text):
                raise ValueError("invalid_evidence_span")
            key = (s.token_id,s.start,s.end)
            if key in seen: raise ValueError("duplicate_evidence_span")
            seen.add(key)
            evidence.append(Evidence(token_id=t.id,page=t.page,text=t.text,selected_text=t.text[s.start:s.end],
                start=s.start,end=s.end,bbox=t.bbox,confidence=t.confidence))
        return evidence
    def field(self, selection, spec, tokens, field_key=None):
        if selection is None: return FieldValue(null_reason="not_proposed")
        try:
            ev = self.evidence(selection.spans,tokens)
            labels = self.evidence(selection.label_spans,tokens)
        except ValueError as e:
            return FieldValue(status="review",mapping_score=selection.score,issues=[str(e)],null_reason="evidence_resolution_failed",provenance=selection.method,presence_status='unresolved_evidence')
        if not ev: return FieldValue(status="review",mapping_score=selection.score,issues=["missing_evidence",*selection.reasons],null_reason="value_span_not_resolved",label_evidence=labels,provenance=selection.method,presence_status='label_only' if labels else 'not_observed')
        raw = " ".join(e.selected_text for e in ev)
        score = min(e.confidence for e in ev + labels)
        normal_input=raw
        if selection.method=='wrapped_decimal' and spec.kind=='number' and len(ev)==2:
            if re.fullmatch(r'[+-]?\d+[.,]',ev[0].selected_text) and re.fullmatch(r'\d+',ev[1].selected_text):normal_input=''.join(e.selected_text for e in ev)
        if selection.method=='wrapped_identifier' and spec.kind=='text' and all(re.fullmatch(r'[\d.]+',e.selected_text) for e in ev) and 6<=sum(len(re.sub(r'\D','',e.selected_text)) for e in ev)<=10:normal_input=''.join(e.selected_text for e in ev)
        if spec.kind=='unit' and selection.method=='shared_header':
            compact=''.join(unicodedata.normalize('NFKC',e.selected_text) for e in ev).replace(' ','').casefold()
            if compact in UNITS:normal_input=compact
        value, issues = normalize(normal_input,spec.kind,self.date_order,self.decimal_separator)
        normalization_failed=bool(issues)
        # HS headings/subheadings are numeric identifiers. Preserve national
        # extensions, punctuation and leading zeros, but never accept prose
        # accidentally linked from a footer as a tariff identifier.
        if field_key=='hs_code' and value is not None and not re.fullmatch(r'\d[\d.\- ]*',value):
            issues.append('invalid_hs_code_characters')
        if selection.method != "legacy":
            if not labels:issues.append("missing_label_evidence")
            if selection.method not in {"shared_header","compatibility_alias"} and any(e.token_id==l.token_id and max(e.start,l.start)<min(e.end,l.end) for e in ev for l in labels):
                issues.append("label_used_as_value")
        issues.extend(selection.reasons)
        if selection.ambiguous: issues.append("ambiguous_mapping")
        if selection.score < self.min_score: issues.append("low_mapping_score")
        if score < self.min_ocr: issues.append("low_ocr_confidence")
        return FieldValue(value=None if issues else value,raw_text=raw,evidence=ev,label_evidence=labels,
            presence_status='value_observed',
            reference_evidence=self.evidence(selection.reference_spans,tokens),reference_field=selection.reference_field,provenance=selection.method,
            ocr_confidence=score,mapping_score=selection.score,status="review" if issues else "accepted",issues=issues,
            null_reason=("normalization_failed" if normalization_failed else "mapping_validation_failed") if issues else None)
    def map(self, document, document_type=None, proposal=None):
        if document_type is not None and document_type not in SCHEMAS: raise ValueError("Unsupported document type")
        if proposal is None:
            if self.selector is None: raise ValueError("A semantic selector or saved proposal is required")
            proposal = self.selector.select(document,document_type)
        tokens = {t.id:t for t in document.tokens}
        issues = []
        dtype = proposal.document_type
        try:
            type_ev = self.evidence(proposal.type_evidence,tokens)
            type_ok = bool(type_ev) and min(e.confidence for e in type_ev) >= self.min_ocr
        except ValueError: type_ok = False
        if dtype == "unknown" or proposal.type_score < self.min_score or not type_ok:
            issues.append("uncertain_document_type")
            dtype = "unknown"
        if document_type and dtype != document_type:
            issues.append("requested_type_mismatch")
            dtype = "unknown"
        if dtype == "unknown":
            return Result(document_type=dtype,fields={},items=[],ocr=document,proposal=proposal,issues=issues,mapping_metadata=getattr(self.selector,"metadata",{}))
        def materialize(selected, schema, location):
            extra = set(selected) - set(schema)
            if extra: issues.append(f"unknown_fields:{location}:" + ",".join(sorted(extra)))
            return {k:self.field(selected.get(k),s,tokens,k) for k,s in schema.items()}
        fields = materialize(proposal.fields,SCHEMAS[dtype],"header")
        for key,field in fields.items():
            if field.status=="missing":field.null_reason=getattr(self.selector,"metadata",{}).get("null_stage",{}).get(key,"not_proposed")
            if field.null_reason=='label_without_resolvable_value':field.presence_status='label_only'
            if field.null_reason=='label_rejected':field.presence_status='unresolved_evidence'
        items = [materialize(row,ITEM_SCHEMAS[dtype],str(i)) for i,row in enumerate(proposal.items)]
        for field in fields.values():
            if field.provenance=='explicit_reference':
                target=fields.get(field.reference_field)
                phrase=' '.join(e.selected_text for e in field.reference_evidence)
                valid=target and target.status=='accepted' and target.evidence==field.evidence and re.fullmatch(r'(?i)same\s+(?:as|to)\s+(above|consignee|shipper|buyer|seller)\s*\.?',phrase)
                if not valid:
                    field.value=None;field.status='review';field.null_reason='invalid_reference';field.issues.append('invalid_reference')
        # A value span cannot silently populate two distinct fields or table rows.
        uses = {}
        for name, field in list(fields.items()) + [pair for row in items for pair in row.items()]:
            if field.provenance in {"compatibility_alias","explicit_reference"}:continue
            for e in field.evidence:
                for old_start,old_end,old_name,other in uses.get(e.token_id,[]):
                    if name == old_name and name in {"unit","weight_unit","volume_unit","currency"} and 'shared_header' in {field.provenance,other.provenance}: continue
                    if name.endswith('weight_unit') and old_name.endswith('weight_unit') and 'shared_header' in {field.provenance,other.provenance}:continue
                    from .domain import compound_labels
                    explicit_roles=any(a.token_id==b.token_id and {name,old_name} <= {v[0] for v in compound_labels(a.selected_text)} for a in field.label_evidence for b in other.label_evidence)
                    party_roles={k for k,s in SCHEMAS[dtype].items() if s.kind=='party'}
                    if name!=old_name and {name,old_name}<=party_roles and explicit_roles and field.evidence==other.evidence:continue
                    if {name,old_name}=={'currency','payment_terms'}:
                        currency_field=field if name=='currency' else other
                        payment_field=other if name=='currency' else field
                        # Only a currency component selected by code, linked to an
                        # accepted parent and contained in the exact parent spans.
                        contained=all(any(c.token_id==p.token_id and p.start<=c.start<c.end<=p.end for p in payment_field.evidence) for c in currency_field.evidence)
                        if currency_field.provenance=='payment_currency_component' and currency_field.reference_field=='payment_terms' and normalize(currency_field.raw_text or '', 'currency')[0] is not None and payment_field.status=='accepted' and contained and currency_field.reference_evidence==payment_field.evidence:continue
                    if other is not field and max(e.start,old_start) < min(e.end,old_end):
                        for target in (field,other):
                            target.value = None; target.status = "review"
                            target.null_reason = "conflicting_span_reuse"
                            if "conflicting_span_reuse" not in target.issues: target.issues.append("conflicting_span_reuse")
                uses.setdefault(e.token_id,[]).append((e.start,e.end,name,field))
        for alias,canonical in ALIASES[dtype].items():
            if fields[alias].provenance=='compatibility_alias':
                fields[alias]=fields[canonical].model_copy(deep=True);fields[alias].provenance='compatibility_alias'
        for field in fields.values():
            if field.provenance=='explicit_reference' and (field.reference_field not in fields or fields[field.reference_field].status!='accepted'):
                field.value=None;field.status='review';field.null_reason='referenced_field_unresolved';field.issues.append('referenced_field_unresolved')
        auxiliary=getattr(self.selector,"metadata",{}).get('auxiliary_tables',[])
        if auxiliary:issues.append('auxiliary_container_table_requires_review')
        table_review=getattr(self.selector,"metadata",{}).get('table_diagnostics',[])
        if table_review:issues.append('unassigned_table_row_requires_review')
        if auxiliary or table_review or any(f.status == "review" for f in list(fields.values()) + [f for row in items for f in row.values()]):
            issues.append("human_review_required")
        return Result(document_type=dtype,fields=fields,items=items,ocr=document,proposal=proposal,issues=issues,mapping_metadata=getattr(self.selector,"metadata",{}))
