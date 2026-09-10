# AI Usage Declaration

## 1. Overview

This project uses AI/LLM technology as part of the document extraction pipeline.

The purpose of the AI component is to convert OCR/native extracted document text into a structured JSON representation while preserving the information present in the source document.

The LLM is not responsible for determining whether a financial document is mathematically correct. Financial validations are performed deterministically by the application's validation service.

---

# 2. Where AI Is Used

The LLM is used in the following stage:

```text
Document
   ↓
File Validation
   ↓
Native Text Extraction / OCR
   ↓
Extracted Text
   ↓
Kimi LLM
   ↓
Structured JSON
   ↓
Pydantic Schema Validation
   ↓
Financial Validation
   ↓
Persistence
   ↓
API Response
```

The LLM receives the extracted document text and the expected document type.

Supported document types are:

* Invoice
* Balance Sheet
* Profit & Loss Statement
* Cash Flow Statement

---

# 3. LLM Provider

The project uses an OpenAI-compatible client to communicate with the Kimi API.

Configuration is controlled through environment variables.

Example:

```env
LLM_PROVIDER=kimi
LLM_API_KEY=YOUR_KIMI_API_KEY
LLM_MODEL=kimi-k3
LLM_BASE_URL=https://api.moonshot.ai/v1
```

The API key is never stored in source code or committed to the repository.

For production, the actual API key must be provided through the deployment platform's secret or environment-variable configuration.

---

# 4. Role of the LLM

The LLM is responsible for:

* Identifying relevant fields from extracted text
* Extracting invoice metadata
* Extracting invoice line items
* Extracting financial statement line items
* Associating financial values with reporting periods
* Returning structured JSON
* Providing evidence/source text where available

For example, invoice text such as:

```text
Item Code Description Qty Unit Price Amount
TS-001 Note book 2 50.00 100.00
TS-002 Pen 5 10.00 50.00
```

should produce structured line items similar to:

```json
[
  {
    "item_code": "TS-001",
    "description": "Note book",
    "quantity": 2,
    "unit_price": 50,
    "amount": 100
  },
  {
    "item_code": "TS-002",
    "description": "Pen",
    "quantity": 5,
    "unit_price": 10,
    "amount": 50
  }
]
```

---

# 5. Prompt Engineering

The extraction service uses document-type-specific prompts.

The prompt contains:

1. The document type
2. The expected JSON schema
3. Extraction rules
4. Numeric extraction rules
5. Evidence requirements
6. Multi-period handling rules for financial statements
7. Instructions to avoid hallucination
8. Instructions for handling missing values

The LLM is explicitly instructed to return structured JSON only.

The prompt also instructs the model to preserve values from the source document rather than altering them to satisfy downstream validations.

---

# 6. Anti-Hallucination Strategy

The system follows a source-grounded extraction approach.

The LLM is instructed:

* Do not invent missing values.
* Do not infer values that are not visible in the source text.
* Use `null` when a value is missing or unreadable.
* Do not modify numbers merely to make a financial validation pass.
* Preserve negative values.
* Preserve values belonging to their correct reporting period.
* Extract visible quantities and amounts rather than ignoring them.
* Use evidence/source text whenever possible.

For example, if the document does not contain a currency, the system should return:

```json
{
  "value": null,
  "evidence": null
}
```

rather than guessing a currency.

---

# 7. Structured Output Validation

The LLM response is parsed as JSON.

The resulting JSON is then validated using Pydantic schemas.

For example:

```python
schema.model_validate(raw_result)
```

This provides an additional validation layer between the LLM output and the rest of the application.

The application therefore does not directly trust arbitrary LLM output.

The processing flow is:

```text
Kimi LLM Response
        ↓
JSON Parsing
        ↓
Pydantic Schema Validation
        ↓
Structured Extraction Object
        ↓
Financial Validation
```

---

# 8. Evidence and Traceability

Extracted fields can contain evidence:

```json
{
  "value": 177,
  "evidence": {
    "source_text": "Total: 177.00",
    "page_number": 1
  }
}
```

This provides traceability between the structured output and the original document content.

Evidence is particularly useful for:

* Debugging extraction errors
* Reviewing AI results
* Demonstrating where a value came from
* Improving user trust
* Supporting future human-in-the-loop workflows

---

# 9. OCR + AI Pipeline

AI is not used as a replacement for OCR.

The processing pipeline first attempts native PDF text extraction.

If sufficient text cannot be extracted, OCR is used.

For digitally generated PDFs:

```text
PDF
 ↓
Native PDF Text Extraction
 ↓
Extracted Text
 ↓
Kimi LLM
 ↓
Structured Extraction
```

For scanned documents:

```text
Scanned PDF / Image
       ↓
Image Validation
       ↓
Image Preprocessing
       ↓
Tesseract OCR
       ↓
OCR Text
       ↓
Kimi LLM
       ↓
Structured Extraction
```

This separation allows the OCR layer and LLM extraction layer to be independently tested.

---

# 10. Financial Validation Is Deterministic

The LLM extracts values, but it does not decide whether the financial calculations are correct.

Financial validation is performed using deterministic Python logic.

For example, an invoice line item is validated using:

```text
quantity × unit price ≈ line amount
```

An invoice total is validated using:

```text
subtotal - discount + tax ≈ total
```

A balance sheet is validated using:

```text
total assets ≈ total capital and liabilities
```

A cash flow statement is validated using:

```text
operating
+ investing
+ financing
+ FX adjustment
≈ net increase in cash
```

This design reduces dependence on the LLM for arithmetic correctness.

---

# 11. Why AI Is Used

Traditional rule-based extraction becomes difficult when documents have:

* Different layouts
* Different field names
* Different table structures
* Different financial statement formats
* Different ordering of fields
* OCR-related formatting variations

The LLM provides semantic understanding of the extracted text while the application maintains deterministic validation and persistence logic.

The resulting architecture separates semantic extraction from business-rule validation.

---

# 12. Limitations

The AI extraction layer can still be affected by:

* Poor OCR quality
* Very low-resolution scans
* Complex table layouts
* Ambiguous document formatting
* Unusual abbreviations
* Missing source text
* Incorrect OCR character recognition
* LLM extraction mistakes

Therefore, AI output should not automatically be treated as authoritative financial data in a production financial system without appropriate controls.

---

# 13. Production Recommendations

For production use, the following improvements are recommended.

### Human Review

Flag documents when:

* Required fields are missing
* OCR confidence is low
* Financial validations fail
* Multiple interpretations are possible
* Extraction confidence is low

### Model Evaluation

Maintain a labeled evaluation dataset and measure:

* Field-level precision
* Field-level recall
* Table extraction accuracy
* Numeric accuracy
* Period assignment accuracy
* Validation accuracy

### Model Monitoring

Track:

* Extraction failure rate
* OCR failure rate
* Validation failure rate
* Average processing time
* Token usage
* API cost
* Model response errors

### Security

Sensitive documents should be handled using:

* Secure API communication
* Secret management
* Access control
* Encryption
* Data retention policies
* Audit logging

---

# 14. AI-Assisted Development

AI tools were also used during development to assist with:

* Code generation
* Debugging
* Architecture discussions
* Prompt design
* Test generation
* Documentation drafting
* Error analysis

All generated code and recommendations were reviewed, tested, and integrated manually.

The final application behavior is determined by the implemented source code and automated tests.

---

# 15. Transparency

The project intentionally separates AI-assisted extraction from deterministic application logic.

```text
AI / LLM
   │
   │ Semantic Extraction
   ▼
Structured Data
   │
   │ Pydantic Validation
   ▼
Validated Extraction
   │
   │ Deterministic Financial Validation
   ▼
Validated Result
   │
   ▼
Database + API + Frontend
```

This separation makes the system easier to test, debug, monitor, and improve.

---

# 16. AI Data Flow

The complete AI-related data flow is:

```text
                    Financial Document
                           |
                           v
                   File Validation
                           |
                           v
              Native PDF / OCR Extraction
                           |
                           v
                     Extracted Text
                           |
                           v
                   Document-Type Prompt
                           |
                           v
                       Kimi LLM
                           |
                           v
                    Structured JSON
                           |
                           v
                 JSON Parsing / Pydantic
                           |
                           v
                  Structured Data Object
                           |
                           v
               Deterministic Validation
                           |
                           v
                     Persistence
```

The LLM is therefore one component of the overall processing pipeline rather than the sole decision-making component.

---

# 17. AI Security

The Kimi API key is a backend-only secret.

The following rules apply:

1. The Kimi API key must never be included in frontend code.
2. The Kimi API key must never be committed to Git.
3. The Kimi API key must never be returned in API responses.
4. The Kimi API key must never be written to logs.
5. The Kimi API key must be stored using environment variables or a secret manager.
6. Production secrets should be rotated if they are accidentally exposed.

Example:

```env
LLM_API_KEY=YOUR_KIMI_API_KEY
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
```

The placeholder above must be replaced only in the deployment environment, not in the source-controlled documentation.

---

# 18. AI Failure Handling

The application does not assume that every LLM request will succeed.

Potential AI-related failures include:

* Kimi API unavailable
* API timeout
* Authentication failure
* Invalid LLM response
* Invalid JSON
* Missing required fields
* Pydantic schema validation failure
* Unexpected model output

The extraction service should convert these failures into structured application errors.

Example:

```json
{
  "processing_status": "FAILED",
  "error": {
    "code": "EXTRACTION_ERROR",
    "message": "LLM extraction failed."
  }
}
```

A failed LLM extraction must not be silently treated as a successful document extraction.

---

# 19. AI and Financial Accuracy

The system follows a two-layer approach for financial document processing.

### Layer 1 — AI Extraction

Kimi is used to identify and structure information from the document.

### Layer 2 — Deterministic Validation

Python application logic independently checks financial relationships.

```text
Document
   ↓
AI Extraction
   ↓
Structured Financial Data
   ↓
Deterministic Calculations
   ↓
PASS / FAIL / NOT_APPLICABLE
```

This architecture ensures that the LLM is used for semantic understanding while deterministic application logic is used for financial reconciliation.

---

# 20. Responsible AI Considerations

The system is designed to minimize unnecessary model assumptions.

Key principles include:

* Source-grounded extraction
* Explicit handling of missing information
* Evidence preservation
* Deterministic financial calculations
* Explicit failure states
* Human review for exceptional cases
* Secure handling of sensitive documents
* Monitoring of extraction quality

AI-generated results should be reviewed appropriately before being used for high-impact financial decisions.

---

# 21. Summary

The Document Intelligence system uses Kimi as an AI extraction component within a controlled document-processing pipeline.

The overall architecture is:

```text
File
 ↓
Validation
 ↓
Native PDF Extraction / OCR
 ↓
Kimi LLM
 ↓
Structured JSON
 ↓
Pydantic Validation
 ↓
Deterministic Financial Validation
 ↓
SQLite Persistence
 ↓
REST API
 ↓
Frontend
```

The key design principle is:

> Use AI for semantic document understanding and deterministic application logic for financial correctness.

This approach provides a clear separation between AI-generated extraction and application-controlled validation, making the system easier to test, debug, monitor, and deploy.
