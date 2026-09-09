from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

DocType = Literal["commercial_invoice", "packing_list", "bill_of_lading", "unknown"]
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
class Token(Strict):
    id: str
    page: int = Field(ge=1)
    text: str
    bbox: list[tuple[float, float]] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0, le=1)
class Page(Strict):
    page: int = Field(ge=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    source: str
    preprocessing: dict = Field(default_factory=dict)
class OCRDocument(Strict):
    pages: list[Page]
    tokens: list[Token]
    engine: str = "paddleocr"
    @model_validator(mode="after")
    def integrity(self):
        ids = [t.id for t in self.tokens]
        pages = [p.page for p in self.pages]
        if len(set(ids)) != len(ids) or len(set(pages)) != len(pages):
            raise ValueError("Duplicate token/page IDs")
        if any(t.page not in pages for t in self.tokens):
            raise ValueError("Token references unknown page")
        return self
class Span(Strict):
    token_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
class Selection(Strict):
    spans: list[Span] = Field(default_factory=list)
    label_spans: list[Span] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)
    ambiguous: bool = False
    method: str = "legacy"
    reasons: list[str] = Field(default_factory=list)
    reference_spans: list[Span] = Field(default_factory=list)
    reference_field: str | None = None
class Proposal(Strict):
    document_type: DocType
    type_score: float = Field(ge=0, le=1)
    type_evidence: list[Span] = Field(default_factory=list)
    fields: dict[str, Selection | None] = Field(default_factory=dict)
    items: list[dict[str, Selection | None]] = Field(default_factory=list)
class Evidence(Strict):
    token_id: str
    page: int
    text: str
    selected_text: str
    start: int
    end: int
    bbox: list[tuple[float, float]]
    confidence: float
class FieldValue(Strict):
    value: str | None = None
    raw_text: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    label_evidence: list[Evidence] = Field(default_factory=list)
    ocr_confidence: float | None = None
    mapping_score: float | None = None
    status: Literal["accepted", "missing", "review"] = "missing"
    issues: list[str] = Field(default_factory=list)
    null_reason: str | None = None
    presence_status: Literal['not_observed','label_only','value_observed','unresolved_evidence'] = 'not_observed'
    reference_evidence: list[Evidence] = Field(default_factory=list)
    provenance: str = "legacy"
    reference_field: str | None = None
class Result(Strict):
    document_type: DocType
    fields: dict[str, FieldValue]
    items: list[dict[str, FieldValue]]
    ocr: OCRDocument
    proposal: Proposal | None = None
    issues: list[str] = Field(default_factory=list)
    mapping_metadata: dict = Field(default_factory=dict)
    schema_version: str = "2.0"
