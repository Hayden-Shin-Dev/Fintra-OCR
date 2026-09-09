# FintraOCR JSON 계약 v2.0

금액·수량은 이진 부동소수점 오차를 피하기 위한 Decimal 문자열, 날짜는 YYYY-MM-DD, 식별자는 선행 0을 보존하는 문자열입니다. 단위는 명시된 표기의 정규화이며 서로 다른 단위 사이의 환산이나 합계 계산은 하지 않습니다.

presence_status는 not_observed / label_only / value_observed / unresolved_evidence로 관측 상태를 구분합니다. 국가명은 원문을 보존하면서 ISO alpha-2 코드로 표준화합니다.

각 문서의 fields 및 각 items 행에는 아래 적용 필드가 항상 존재합니다. value=null일 때 status와 null_reason, issues로 사유를 확인합니다. missing은 선택되지 않았다는 뜻이며 문서에 확실히 없다는 증명이 아닙니다. 실제 존재 여부를 아는 정답 데이터 평가에서는 부재와 추출 실패를 별도로 셉니다.

## 공통 의미와 호환

issue_date는 현재 문서 발행일입니다. 상업송장의 invoice_date 및 포장명세서의 packing_date는 호환 별칭으로 유지합니다. 다른 문서의 invoice_date는 참조된 송장의 날짜입니다. invoice_number와 bill_of_lading_number 등 명시적 참조 식별자는 어느 문서에서도 유지합니다. buyer, seller, exporter, shipper, consignee, notify_party는 별도 역할입니다. Exporter를 Seller로 자동 합치지 않습니다. total_packages는 문서 합계, items.package_count는 행별 포장 개수, items.quantity는 상품 수량입니다.

모든 필드에 원본 OCR 토큰과 문자 범위, 원문과 선택 문자열, page/bbox/confidence, 라벨 근거가 들어갑니다. 명시적 동일 당사자 참조는 reference_evidence와 reference_field를 함께 저장합니다. bbox는 문자별 좌표가 아니라 원본 OCR 토큰 전체 영역입니다.

기존 fields/items 경로와 status(accepted/missing/review)를 유지하고 null_reason, provenance, reference_evidence를 추가했습니다. 새 필드는 추가 방식이며 기존 스키마 사용자에게는 필요한 키만 읽는 방법을 권장합니다. accepted는 구조/근거 검증을 통과한 후보이지 사람이 승인한 정답이 아닙니다.

gross_weight_unit과 net_weight_unit을 별도로 보존합니다. 기존 weight_unit은 명시된 중량 단위가 서로 일치할 때만 공통 단위로 채우며 서로 다르면 review/null입니다.

견적송장 참조 `proforma_invoice_number`는 상업송장 번호와 분리했습니다. 신용장 개설은행 `letter_of_credit_issuing_bank`를 명시적 참조 필드로 추가했습니다. 송장 품목에도 `marks`를 보존합니다. 기존 경로를 삭제하거나 의미가 다른 당사자를 합치지 않았습니다.

제품 사이즈 `product_size`는 수량 단위와 분리합니다. 송장 품목의 `package_count`도 상품 수량과 별개입니다. 화인 영역에 명시된 포장 개수·단위는 문자 구간을 나눠 보존합니다.

운송 주선인 이름과 등록 번호, 청구 대상자와 인도 대상자, 신용장 발행일과 현재 문서 발행일, 배송일과 본선 적재일을 분리했습니다. 품목별 주문 번호는 items[].purchase_order_number에 보존합니다. incoterms는 명시적 인도 조건 코드가 있을 때만 표준화하며 결제 문구를 대신 넣지 않습니다.

소재(material)·색상(color)을 품목별로 보존합니다. shipping_origin은 배송 출발지이며 선적항이나 제조 원산지로 바꾸지 않습니다.

## commercial_invoice

### fields

| 필드 | 자료형 | 의미 |
|---|---|---|
| invoice_number | text | Commercial invoice identifier, not purchase order or shipment identifier |
| invoice_date | date | Date of issue of the invoice |
| seller | party | Seller legal name; do not include address |
| buyer | party | Buyer legal name; may differ from consignee |
| purchase_order_number | text | Buyer's purchase order identifier |
| currency | currency | Explicit currency code or unambiguous currency name |
| subtotal | number | Explicit subtotal before tax and charges |
| tax | number | Explicit tax amount |
| total_amount | number | Final invoice payable amount, not an individual line amount |
| incoterms | incoterms | Explicit trade delivery rule and named place; not payment text |
| payment_terms | text | Explicit payment terms |
| total_packages | number | Explicit total count of packages, not item quantity |
| gross_weight | number | Explicit total gross weight numeric value |
| net_weight | number | Explicit total net weight numeric value |
| weight_unit | unit | Unit explicitly attached to the total weight |
| volume | number | Explicit total cargo volume numeric value |
| volume_unit | unit | Unit explicitly attached to volume |
| proforma_invoice_number | text | Explicit proforma invoice reference; not a commercial invoice identifier |
| bill_of_lading_number | text | Bill of lading identifier, including an explicit reference |
| packing_list_number | text | Packing list identifier, including an explicit reference |
| booking_number | text | Carrier booking identifier; not the bill of lading identifier |
| buyer_reference | text | Buyer's reference as printed, without assuming it is a purchase order |
| document_reference | text | Other explicitly labelled document reference |
| letter_of_credit_number | text | Explicit letter of credit identifier |
| insurance_policy_number | text | Explicit insurance or marine cover policy identifier |
| letter_of_credit_issuing_bank | party | Explicit bank issuing the letter of credit; not carrier or beneficiary |
| shipping_origin | text | Explicit ship-from location; not necessarily port of loading or country where goods were manufactured |
| carrier | party | Explicitly named carrier; do not infer it from vessel or shipper |
| mode_of_transport | text | Explicit initial carriage or transport mode, not vessel name |
| routing_instructions | text | Explicit domestic routing/export instructions, not voyage |
| movement_type | text | Explicit type of movement, not voyage |
| freight_payable_at | text | Place at which freight is payable, not prepaid/collect terms |
| vessel | text | Explicit vessel or vessel/aircraft name |
| voyage | text | Voyage identifier |
| port_of_loading | text | Port of loading |
| port_of_discharge | text | Port of discharge |
| place_of_delivery | text | Final delivery destination |
| departure_date | date | Explicit departure date, not issue or on-board date |
| country_of_origin | country | Explicit country of origin of goods, ISO alpha-2 normalization |
| country_of_destination | country | Explicit country of destination, not a port or city, ISO alpha-2 normalization |
| exporter | party | Explicit exporter legal name; preserve distinct party roles |
| shipper | party | Explicit shipper legal name; preserve distinct party roles |
| consignee | party | Explicit consignee legal name; preserve distinct party roles |
| notify_party | party | Explicit notify party legal name; preserve distinct party roles |
| issue_date | date | Issue date of THIS document; not a referenced invoice date or departure date |
| forwarding_agent | party | Explicit forwarding agent legal name, not shipper or carrier |
| forwarding_agent_number | text | Explicit forwarding agent registration/FMC identifier; not the agent legal name |
| delivery_party | party | Explicit party labelled for delivery to; distinct from consignee |
| bill_to_party | party | Explicit billing or third-party billing legal name; not automatically buyer |
| quotation_number | text | Explicit quotation reference; not invoice or purchase order number |
| letter_of_credit_date | date | Explicit issue date of referenced letter of credit, not this document date |
| issue_place | text | Explicit place where this document was issued, distinct from cargo ports |
| shipment_date | date | Explicit shipment date; not automatically departure, on-board or issue date |
| declared_value | number | Explicit declared cargo value, not invoice amount or reference |
| gross_weight_unit | unit | Explicit gross weight unit; may differ from the other weight |
| net_weight_unit | unit | Explicit net weight unit; may differ from the other weight |

### items

| 필드 | 자료형 | 의미 |
|---|---|---|
| material | material | Material or composition explicitly printed for this goods row; not product code |
| color | text | Color explicitly printed for this goods row |
| description | text | Goods description for this row only |
| quantity | number | Goods quantity for this row, not package count |
| unit | unit | Explicit quantity unit for this row |
| product_code | text | Product code |
| unit_price | number | Price per unit for this row |
| amount | number | Extended amount for this row |
| package_count | number | Package count for this cargo row only |
| gross_weight | number | Gross weight numeric value for this row only |
| net_weight | number | Net weight numeric value for this row only |
| weight_unit | unit | Explicit weight unit applying to this row |
| volume | number | Volume numeric value for this row only |
| volume_unit | unit | Explicit volume unit applying to this row |
| purchase_order_number | text | Explicit purchase order reference for this item row; not a document-wide order or product code |
| product_size | text | Explicit product size or size designation, not a quantity unit |
| marks | text | Shipping marks for this row; not product description |
| hs_code | text | Explicit customs HS code; keep punctuation and leading zeros |
| package_type | unit | Explicit package type for this row |
| gross_weight_unit | unit | Explicit gross weight unit applying to this row |
| net_weight_unit | unit | Explicit net weight unit applying to this row |

## packing_list

### fields

| 필드 | 자료형 | 의미 |
|---|---|---|
| packing_list_number | text | Packing list's own identifier |
| packing_date | date | Packing list issue date |
| invoice_number | text | Referenced commercial invoice identifier |
| shipper | party | Name of the party shipping/exporting goods; preserve legal name |
| consignee | party | Name of the party receiving the shipment, not notify party |
| total_packages | number | Explicit total count of packages, not item quantity |
| gross_weight | number | Explicit total gross weight numeric value |
| net_weight | number | Explicit total net weight numeric value |
| weight_unit | unit | Unit explicitly attached to the total weight |
| volume | number | Explicit total cargo volume numeric value |
| volume_unit | unit | Unit explicitly attached to volume |
| proforma_invoice_number | text | Explicit proforma invoice reference; not a commercial invoice identifier |
| bill_of_lading_number | text | Bill of lading identifier, including an explicit reference |
| purchase_order_number | text | Explicit purchase order identifier; buyer reference alone is not a purchase order |
| booking_number | text | Carrier booking identifier; not the bill of lading identifier |
| buyer_reference | text | Buyer's reference as printed, without assuming it is a purchase order |
| document_reference | text | Other explicitly labelled document reference |
| letter_of_credit_number | text | Explicit letter of credit identifier |
| insurance_policy_number | text | Explicit insurance or marine cover policy identifier |
| letter_of_credit_issuing_bank | party | Explicit bank issuing the letter of credit; not carrier or beneficiary |
| shipping_origin | text | Explicit ship-from location; not necessarily port of loading or country where goods were manufactured |
| carrier | party | Explicitly named carrier; do not infer it from vessel or shipper |
| mode_of_transport | text | Explicit initial carriage or transport mode, not vessel name |
| routing_instructions | text | Explicit domestic routing/export instructions, not voyage |
| movement_type | text | Explicit type of movement, not voyage |
| freight_payable_at | text | Place at which freight is payable, not prepaid/collect terms |
| vessel | text | Explicit vessel or vessel/aircraft name |
| voyage | text | Voyage identifier |
| port_of_loading | text | Port of loading |
| port_of_discharge | text | Port of discharge |
| place_of_delivery | text | Final delivery destination |
| departure_date | date | Explicit departure date, not issue or on-board date |
| country_of_origin | country | Explicit country of origin of goods, ISO alpha-2 normalization |
| country_of_destination | country | Explicit country of destination, not a port or city, ISO alpha-2 normalization |
| seller | party | Explicit seller legal name; preserve distinct party roles |
| buyer | party | Explicit buyer legal name; preserve distinct party roles |
| exporter | party | Explicit exporter legal name; preserve distinct party roles |
| notify_party | party | Explicit notify party legal name; preserve distinct party roles |
| issue_date | date | Issue date of THIS document; not a referenced invoice date or departure date |
| forwarding_agent | party | Explicit forwarding agent legal name, not shipper or carrier |
| forwarding_agent_number | text | Explicit forwarding agent registration/FMC identifier; not the agent legal name |
| delivery_party | party | Explicit party labelled for delivery to; distinct from consignee |
| bill_to_party | party | Explicit billing or third-party billing legal name; not automatically buyer |
| quotation_number | text | Explicit quotation reference; not invoice or purchase order number |
| letter_of_credit_date | date | Explicit issue date of referenced letter of credit, not this document date |
| issue_place | text | Explicit place where this document was issued, distinct from cargo ports |
| shipment_date | date | Explicit shipment date; not automatically departure, on-board or issue date |
| declared_value | number | Explicit declared cargo value, not invoice amount or reference |
| invoice_date | date | Issue date of the referenced invoice, not this document |
| gross_weight_unit | unit | Explicit gross weight unit; may differ from the other weight |
| net_weight_unit | unit | Explicit net weight unit; may differ from the other weight |

### items

| 필드 | 자료형 | 의미 |
|---|---|---|
| material | material | Material or composition explicitly printed for this goods row; not product code |
| color | text | Color explicitly printed for this goods row |
| description | text | Goods description for this row only |
| quantity | number | Goods quantity for this row, not package count |
| unit | unit | Explicit quantity unit for this row |
| marks | text | Shipping marks |
| package_count | number | Package count for this cargo row only |
| gross_weight | number | Gross weight numeric value for this row only |
| net_weight | number | Net weight numeric value for this row only |
| weight_unit | unit | Explicit weight unit applying to this row |
| volume | number | Volume numeric value for this row only |
| volume_unit | unit | Explicit volume unit applying to this row |
| purchase_order_number | text | Explicit purchase order reference for this item row; not a document-wide order or product code |
| product_size | text | Explicit product size or size designation, not a quantity unit |
| product_code | text | Explicit product identifier for this row |
| hs_code | text | Explicit customs HS code; keep punctuation and leading zeros |
| package_type | unit | Explicit package type for this row |
| gross_weight_unit | unit | Explicit gross weight unit applying to this row |
| net_weight_unit | unit | Explicit net weight unit applying to this row |

## bill_of_lading

### fields

| 필드 | 자료형 | 의미 |
|---|---|---|
| bill_of_lading_number | text | Bill of lading identifier, not booking number |
| issue_date | date | Bill of lading issue date |
| on_board_date | date | Shipped on board date, distinguish from issue date |
| shipper | party | Name of the party shipping/exporting goods; preserve legal name |
| consignee | party | Name of the party receiving the shipment, not notify party |
| notify_party | party | Notify party legal name |
| carrier | party | Carrier legal name |
| vessel | text | Vessel name |
| voyage | text | Voyage identifier |
| port_of_loading | text | Port where cargo is loaded |
| port_of_discharge | text | Port where cargo is discharged |
| place_of_receipt | text | Place of receipt |
| place_of_delivery | text | Final place of delivery |
| freight_terms | freight_terms | Freight prepaid or collect terms |
| total_packages | number | Explicit total count of packages, not item quantity |
| gross_weight | number | Explicit total gross weight numeric value |
| net_weight | number | Explicit total net weight numeric value |
| weight_unit | unit | Unit explicitly attached to the total weight |
| volume | number | Explicit total cargo volume numeric value |
| volume_unit | unit | Unit explicitly attached to volume |
| proforma_invoice_number | text | Explicit proforma invoice reference; not a commercial invoice identifier |
| invoice_number | text | Commercial invoice identifier, including a reference on another document |
| packing_list_number | text | Packing list identifier, including an explicit reference |
| purchase_order_number | text | Explicit purchase order identifier; buyer reference alone is not a purchase order |
| booking_number | text | Carrier booking identifier; not the bill of lading identifier |
| buyer_reference | text | Buyer's reference as printed, without assuming it is a purchase order |
| document_reference | text | Other explicitly labelled document reference |
| letter_of_credit_number | text | Explicit letter of credit identifier |
| insurance_policy_number | text | Explicit insurance or marine cover policy identifier |
| letter_of_credit_issuing_bank | party | Explicit bank issuing the letter of credit; not carrier or beneficiary |
| shipping_origin | text | Explicit ship-from location; not necessarily port of loading or country where goods were manufactured |
| mode_of_transport | text | Explicit initial carriage or transport mode, not vessel name |
| routing_instructions | text | Explicit domestic routing/export instructions, not voyage |
| movement_type | text | Explicit type of movement, not voyage |
| freight_payable_at | text | Place at which freight is payable, not prepaid/collect terms |
| departure_date | date | Explicit departure date, not issue or on-board date |
| country_of_origin | country | Explicit country of origin of goods, ISO alpha-2 normalization |
| country_of_destination | country | Explicit country of destination, not a port or city, ISO alpha-2 normalization |
| seller | party | Explicit seller legal name; preserve distinct party roles |
| buyer | party | Explicit buyer legal name; preserve distinct party roles |
| exporter | party | Explicit exporter legal name; preserve distinct party roles |
| forwarding_agent | party | Explicit forwarding agent legal name, not shipper or carrier |
| forwarding_agent_number | text | Explicit forwarding agent registration/FMC identifier; not the agent legal name |
| delivery_party | party | Explicit party labelled for delivery to; distinct from consignee |
| bill_to_party | party | Explicit billing or third-party billing legal name; not automatically buyer |
| quotation_number | text | Explicit quotation reference; not invoice or purchase order number |
| letter_of_credit_date | date | Explicit issue date of referenced letter of credit, not this document date |
| issue_place | text | Explicit place where this document was issued, distinct from cargo ports |
| shipment_date | date | Explicit shipment date; not automatically departure, on-board or issue date |
| declared_value | number | Explicit declared cargo value, not invoice amount or reference |
| invoice_date | date | Issue date of the referenced invoice, not this document |
| gross_weight_unit | unit | Explicit gross weight unit; may differ from the other weight |
| net_weight_unit | unit | Explicit net weight unit; may differ from the other weight |

### items

| 필드 | 자료형 | 의미 |
|---|---|---|
| material | material | Material or composition explicitly printed for this goods row; not product code |
| color | text | Color explicitly printed for this goods row |
| description | text | Goods description for this row only |
| quantity | number | Goods quantity for this row, not package count |
| unit | unit | Explicit quantity unit for this row |
| marks | text | Shipping marks |
| container_number | text | Container identifier |
| seal_number | text | Seal identifier |
| package_count | number | Package count for this cargo row only |
| gross_weight | number | Gross weight numeric value for this row only |
| net_weight | number | Net weight numeric value for this row only |
| weight_unit | unit | Explicit weight unit applying to this row |
| volume | number | Volume numeric value for this row only |
| volume_unit | unit | Explicit volume unit applying to this row |
| purchase_order_number | text | Explicit purchase order reference for this item row; not a document-wide order or product code |
| product_size | text | Explicit product size or size designation, not a quantity unit |
| product_code | text | Explicit product identifier for this row |
| hs_code | text | Explicit customs HS code; keep punctuation and leading zeros |
| package_type | unit | Explicit package type for this row |
| gross_weight_unit | unit | Explicit gross weight unit applying to this row |
| net_weight_unit | unit | Explicit net weight unit applying to this row |
