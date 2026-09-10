# Document Intelligence Architecture

## 1. Overview

Document Intelligence is an AI-powered financial document processing system that accepts invoices and financial statements in PDF, JPG, JPEG, and PNG formats.

The system validates uploaded files, extracts text using native PDF extraction or OCR, sends the extracted content to a Kimi LLM through an OpenAI-compatible API for structured extraction, performs deterministic financial validations, and persists the final result.

The application is designed as a modular REST-based system with separate components for API handling, validation, OCR, LLM extraction, financial validation, persistence, and frontend presentation.

---

## 2. Supported Documents

The system supports the following document types:

* Invoice
* Balance Sheet
* Profit & Loss Statement
* Cash Flow Statement

### Supported File Formats

* PDF
* JPG
* JPEG
* PNG

### File Constraints

* Maximum file size: 10 MB
* Maximum pages: 3

Documents that do not satisfy these requirements are rejected before OCR or LLM processing.

---

## 3. High-Level Architecture

```text
                        User
                          |
                          v
                 +-------------------+
                 | Frontend Dashboard|
                 | HTML / CSS / JS   |
                 +---------+---------+
                           |
                           | REST API
                           v
                 +-------------------+
                 |      FastAPI      |
                 |     API Layer     |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | Document Service  |
                 |   Orchestration   |
                 +---------+---------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
      +------------+ +-------------+ +-------------+
      | File       | | OCR / Text  | | Kimi LLM   |
      | Validation | | Extraction  | | Extraction  |
      +------------+ +-------------+ +-------------+
                           |
                           v
                 +-------------------+
                 | Financial         |
                 | Validation        |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | SQLite Database   |
                 |   Persistence     |
                 +-------------------+
```

---

## 4. Processing Pipeline

The document processing pipeline consists of the following stages:

```text
Upload
   |
   v
File Validation
   |
   v
Text Extraction / OCR
   |
   v
Kimi LLM Extraction
   |
   v
Pydantic Validation
   |
   v
Financial Validation
   |
   v
Persistence
   |
   v
API Response / Dashboard
```

---

### Step 1 — Upload

The frontend sends the document to:

```http
POST /api/v1/documents/process
```

The request contains:

* File
* Document type

The supported document types are:

* `invoice`
* `balance_sheet`
* `profit_and_loss`
* `cash_flow_statement`

---

### Step 2 — File Validation

File validation happens before OCR and LLM processing.

The system validates:

* File extension
* MIME type
* File size
* File readability
* PDF integrity
* PDF encryption status
* Page count
* Image integrity

### PDF Validation

For PDF files, the system checks:

1. Whether the file can be opened.
2. Whether the PDF is encrypted.
3. Whether the document contains more than three pages.
4. Whether the PDF structure is readable.

### Image Validation

For JPG, JPEG, and PNG files, the system checks:

1. Whether the image can be opened.
2. Whether the image is valid.
3. Whether the image can be decoded successfully.

Invalid documents are rejected before expensive OCR or LLM processing.

Example failure conditions:

```text
UNSUPPORTED_FILE_TYPE
CORRUPTED_FILE
PAGE_LIMIT_EXCEEDED
INVALID_IMAGE
```

---

### Step 3 — Text Extraction

The system uses two extraction paths depending on the input document.

#### PDF Processing

For PDFs:

1. Attempt native text extraction.
2. Extract text from all pages.
3. Determine whether sufficient text was extracted.
4. If sufficient text exists, use the extracted text.
5. If insufficient text exists, render the PDF pages.
6. Run OCR on the rendered pages.

This allows the system to support both:

* Digitally generated PDFs
* Scanned PDFs

#### Image Processing

For JPG, JPEG, and PNG:

1. Load and validate the image.
2. Correct image orientation when required.
3. Convert the image into a suitable format.
4. Apply preprocessing.
5. Run OCR.
6. Select the best OCR result.

### OCR Preprocessing

The image preprocessing pipeline can include:

* Grayscale conversion
* Contrast enhancement
* Image resizing
* Sharpening
* Noise reduction

OCR results include page-level information so that extracted fields can be associated with their source page.

---

### Step 4 — LLM Extraction

After text extraction, the extracted document text is sent to the Kimi LLM through its OpenAI-compatible API.

The LLM receives:

* Document type
* Extracted text
* Structured extraction schema
* Document-specific extraction rules

The extraction prompt instructs the model to:

* Extract visible information.
* Preserve the document's values.
* Extract all meaningful fields.
* Extract invoice line items separately.
* Preserve multi-period financial statement values.
* Return `null` when information is missing or unreadable.
* Avoid hallucinating values.
* Avoid modifying values simply to make a validation pass.
* Return structured JSON.

The response is then processed as follows:

```text
Kimi Response
      |
      v
JSON Parsing
      |
      v
Pydantic Validation
      |
      v
Structured Extraction Object
```

Pydantic schemas provide a consistent structure for the extracted data.

---

## 5. Document-Specific Extraction

### 5.1 Invoice

Invoice extraction includes fields such as:

* Invoice number
* Invoice date
* Vendor name
* Customer name
* Currency
* Subtotal
* Tax rate
* Tax amount
* Discount
* Total amount
* Cash received
* Change amount
* Total items
* Total quantity
* Line items

Each line item can contain:

* Item code
* Description
* Quantity
* Unit price
* Amount
* Evidence

Example:

```text
Item Code | Description | Qty | Unit Price | Amount
----------------------------------------------------
TS-001    | Notebook    | 2   | 50.00      | 100.00
TS-002    | Pen         | 5   | 10.00      | 50.00
```

---

### 5.2 Balance Sheet

Balance Sheet extraction preserves:

* Statement title
* Company name
* Currency
* Reporting periods
* Financial line items
* Evidence

Multiple reporting periods are represented separately.

For example:

```text
2024
2023
```

The system associates each extracted financial value with its corresponding period.

---

### 5.3 Profit & Loss Statement

Profit & Loss extraction preserves:

* Statement title
* Company name
* Currency
* Reporting periods
* Income items
* Expenditure items
* Profit values
* Appropriation-related values where present
* Evidence

---

### 5.4 Cash Flow Statement

Cash Flow extraction preserves:

* Statement title
* Company name
* Currency
* Reporting periods
* Operating cash flow
* Investing cash flow
* Financing cash flow
* Foreign exchange adjustment
* Net increase in cash
* Opening cash balance
* Closing cash balance
* Cash acquired on amalgamation where present
* Evidence

---

## 6. Evidence and Traceability

The system supports evidence for extracted fields.

Evidence can contain:

```text
source_text
page_number
```

Example:

```json
{
  "value": 177.0,
  "evidence": {
    "source_text": "Total: 177.00",
    "page_number": 1
  }
}
```

This allows users to trace extracted values back to the original document.

Evidence is particularly useful for:

* Debugging extraction errors
* Reviewing financial values
* Building user trust
* Auditing extracted information

---

## 7. Financial Validation

Financial validation is performed using deterministic application logic rather than relying on the LLM to perform the final calculations.

The purpose is to identify inconsistencies between extracted values.

Each validation contains:

* Check name
* Formula
* Input values
* Calculated value
* Reported value
* Variance
* Status

Possible statuses:

```text
PASS
FAIL
NOT_APPLICABLE
```

---

### 7.1 Invoice Validation

The invoice validator checks line-item calculations.

#### Quantity × Unit Price

```text
quantity × unit price ≈ line amount
```

Example:

```text
2 × 50 = 100
```

#### Line Items vs Subtotal

```text
sum(line items) ≈ subtotal
```

#### Total Reconciliation

```text
subtotal - discount + tax ≈ total
```

#### Cash and Change

When cash information is present:

```text
cash received - total ≈ change
```

A tolerance is used for approximate financial reconciliation.

---

### 7.2 Balance Sheet Validation

The Balance Sheet validator checks:

```text
total assets ≈ total capital and liabilities
```

The system can also validate component-level totals when sufficient values are available.

Validation is performed independently for each reporting period.

---

### 7.3 Profit & Loss Validation

The Profit & Loss validator checks relationships including:

```text
interest earned + other income ≈ total income
```

```text
interest expended
+ operating expenses
+ provisions
≈ total expenditure
```

```text
total income - total expenditure
≈ net profit before minority interest
```

```text
net profit before minority interest
- minority interest
≈ group net profit
```

Where appropriations are present, they can also be validated.

---

### 7.4 Cash Flow Validation

The Cash Flow validator checks:

```text
operating
+ investing
+ financing
+ FX adjustment
≈ net increase
```

It also checks:

```text
opening cash
+ net increase
+ cash acquired on amalgamation
≈ closing cash
```

If the cash acquired on amalgamation row is absent or explicitly represented as a dash, it is treated as zero for reconciliation.

---

## 8. Numeric Normalization

Financial documents can represent numbers in different formats.

The validation layer normalizes values before arithmetic.

Supported formats include:

```text
1,000.00
₹1,000.00
$1,000.00
(500.00)
-500.00
-
```

Parentheses are interpreted as negative values:

```text
(500.00) → -500.00
```

Explicit financial-statement dashes can be treated as zero when performing appropriate reconciliation calculations.

Missing values represented by `null` remain unavailable rather than being invented.

---

## 9. Tolerance Handling

Financial calculations use a default numerical tolerance.

```text
DEFAULT_TOLERANCE = 1.0
```

A validation passes when the absolute difference between the calculated value and reported value is within the configured tolerance.

Conceptually:

```text
abs(calculated - reported) <= tolerance
```

This prevents insignificant rounding differences from incorrectly causing validation failures.

---

## 10. Persistence Layer

Processed documents are persisted in SQLite using SQLAlchemy.

The database stores:

* Document ID
* Document name
* Document type
* Processing status
* File validation
* Extracted data
* Financial validation
* Processing metadata
* Error information
* Created timestamp
* Updated timestamp

The persistence layer allows previously processed documents to be retrieved without re-running OCR or LLM extraction.

---

## 11. Repository Layer

Database access is separated into repository functions.

The repository layer handles operations such as:

* Creating documents
* Retrieving all documents
* Retrieving the latest document by name

This keeps database logic separate from API and business logic.

---

## 12. Service Layer

The application separates major processing responsibilities into services.

### Document Validation Service

Responsible for:

* Extension validation
* MIME validation
* File size validation
* PDF validation
* Image validation
* Page-count validation

### OCR Service

Responsible for:

* Native PDF text extraction
* PDF rendering
* Image preprocessing
* OCR
* Page-level text extraction

### Extraction Service

Responsible for:

* Extraction prompt creation
* Kimi API communication
* JSON parsing
* Pydantic validation

### Financial Validation Service

Responsible for:

* Invoice reconciliation
* Balance Sheet validation
* Profit & Loss validation
* Cash Flow validation

### Document Service

Acts as the orchestration layer and coordinates:

```text
Validation
    ↓
OCR / Text Extraction
    ↓
LLM Extraction
    ↓
Financial Validation
    ↓
Persistence
```

---

## 13. API Layer

The backend is implemented using FastAPI.

### Process Document

```http
POST /api/v1/documents/process
```

Accepts:

* File
* Document type

Returns:

* Document name
* Processing status
* File validation
* Extracted data
* Financial validation
* Processing metadata
* Error information

---

### Get All Documents

```http
GET /api/v1/documents
```

Returns the list of persisted documents.

---

### Get Document

```http
GET /api/v1/documents/{document_name}
```

Returns the latest persisted result for the specified document.

---

### Health Check

```http
GET /api/v1/health
```

Returns the service health status.

---

### Swagger Documentation

FastAPI automatically provides interactive API documentation at:

```text
/docs
```

This allows API endpoints to be tested directly from the browser.

---

## 14. Frontend Architecture

The frontend is implemented using:

* HTML
* CSS
* JavaScript

The dashboard provides:

* Document upload
* Document type selection
* Processed document list
* Processing status
* Extracted field display
* Invoice line-item display
* Financial validation results
* Raw JSON result display

The frontend communicates with the FastAPI backend through REST APIs.

The frontend must never directly communicate with the Kimi API or expose the Kimi API key.

---

## 15. Error Handling

The application handles errors at multiple stages.

### Validation Errors

Examples:

```text
UNSUPPORTED_FILE_TYPE
CORRUPTED_FILE
PAGE_LIMIT_EXCEEDED
INVALID_IMAGE
```

### OCR Errors

OCR processing failures are captured and returned without silently producing incorrect extracted values.

### LLM Errors

LLM API failures and invalid extraction responses are handled through the extraction service.

### Unexpected Errors

Unexpected processing errors are caught by the API layer and persisted with appropriate error information.

Failed documents are returned with:

```json
{
  "processing_status": "FAILED",
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

---

## 16. Security and Configuration

Sensitive configuration is stored using environment variables.

The application uses the Kimi LLM through its OpenAI-compatible API.

The following environment variables are used:

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
DATABASE_URL
```

### Kimi API Configuration

The Kimi configuration follows the OpenAI-compatible API format:

```env
LLM_API_KEY=your_kimi_api_key
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
```

Where:

* `LLM_API_KEY` is the Kimi API credential.
* `LLM_BASE_URL` is the Kimi OpenAI-compatible API base URL.
* `LLM_MODEL` specifies the Kimi model used for document extraction.

### Local Development

For local development, create a `.env` file:

```env
LLM_API_KEY=your_kimi_api_key
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
DATABASE_URL=sqlite:///./document_intelligence.db
```

The actual API key must never be committed to source control.

### `.env.example`

The repository should contain a `.env.example` file without real credentials:

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
DATABASE_URL=sqlite:///./document_intelligence.db
```

### Production Deployment

For production deployment, Kimi credentials must be configured as environment variables or platform-managed secrets.

Example production configuration:

```text
LLM_API_KEY=<PRODUCTION_KIMI_API_KEY>
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
DATABASE_URL=<PRODUCTION_DATABASE_URL>
```

The production API key must:

1. Never be stored in source code.
2. Never be committed to Git.
3. Never be included in frontend JavaScript.
4. Never be exposed in API responses.
5. Never be written to application logs.
6. Be stored using the production platform's secret/environment-variable mechanism.
7. Be rotated if it is accidentally exposed.

### Kimi API Integration

The backend communicates with Kimi using an OpenAI-compatible client.

Conceptually, the integration follows:

```python
from openai import OpenAI

client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
)

response = client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=[
        {
            "role": "system",
            "content": "Extract structured financial information from the provided document."
        },
        {
            "role": "user",
            "content": extracted_document_text
        }
    ]
)
```

The Kimi API response is parsed by the extraction service and validated against the application's Pydantic schemas before financial validation is performed.

### Configuration Flow

```text
Production Secret / Environment Variable
                    |
                    v
             FastAPI Configuration
                    |
                    v
           Extraction Service
                    |
                    v
        OpenAI-Compatible Client
                    |
                    v
                Kimi API
                    |
                    v
        Structured LLM Response
                    |
                    v
          JSON / Pydantic Validation
                    |
                    v
          Financial Validation
```

### Security Requirements

The following rules apply to production:

* Kimi API keys are backend-only credentials.
* The frontend must never receive the Kimi API key.
* The frontend communicates only with the application's FastAPI API.
* API keys must not appear in logs, exceptions, screenshots, or API responses.
* Configuration values should be validated during application startup.
* Production secrets should be managed using environment variables or a dedicated secret-management service.
* `.env` files containing real credentials must remain outside source control.

### Configuration Validation

The application should fail fast during startup when required Kimi configuration is missing.

Required configuration:

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

This prevents the application from accepting document-processing requests when the LLM provider has not been configured correctly.

---

## 17. Logging

The backend uses structured application logging to record important processing events.

Logging can include:

* Document processing start
* File validation results
* OCR execution
* OCR confidence
* Selected OCR configuration
* LLM extraction stage
* Validation results
* Processing failures

Sensitive credentials and API keys must never be written to logs.

---

## 18. Testing Architecture

Automated tests are implemented using `pytest`.

Current automated coverage includes:

### API Tests

* Health endpoint
* Documents endpoint
* Swagger endpoint

### Schema Tests

* Invoice extraction schema
* Financial statement schema

### Financial Validation Tests

* Invoice validation success
* Invoice validation failure
* Cash Flow validation success

The current test suite can be executed using:

```bash
python -m pytest -v
```

---

## 19. Failure Scenario Testing

The system has been tested against several failure scenarios.

### Unsupported File

Example:

```text
unsupported_document.docx
```

Expected behavior:

```text
FAILED
UNSUPPORTED_FILE_TYPE
```

The document is rejected before OCR and LLM processing.

### Corrupted PDF

Example:

```text
corrupted.pdf
```

Expected behavior:

```text
FAILED
CORRUPTED_FILE
```

### Excessive Page Count

A PDF containing more than three pages is rejected before OCR and LLM processing.

### Invalid Image

An invalid image file is rejected during file validation.

---

## 20. Scanned Document Processing

The system supports scanned documents through OCR.

For example:

```text
scanned_invoice_test.png
```

The processing pipeline is:

```text
Scanned Image
     |
     v
Image Validation
     |
     v
Image Preprocessing
     |
     v
Tesseract OCR
     |
     v
Extracted Text
     |
     v
Kimi LLM
     |
     v
Structured Invoice
     |
     v
Financial Validation
```

The OCR pipeline preserves page information and extracted evidence.

---

## 21. Sample Output Structure

Representative outputs are stored in:

```text
sample_outputs/
```

The directory contains examples such as:

```text
invoice.json
balance_sheet.json
profit_and_loss.json
cash_flow_statement.json
scanned_invoice.json
failure_unsupported_file.json
```

These outputs are generated from persisted application results.

---

## 22. End-to-End Data Flow

The complete system flow is:

```text
                     +----------------+
                     |      User      |
                     +-------+--------+
                             |
                             v
                     +----------------+
                     |    Frontend    |
                     +-------+--------+
                             |
                             v
                     +----------------+
                     |    FastAPI     |
                     +-------+--------+
                             |
                             v
                  +-----------------------+
                  | File Validation       |
                  +-----------+-----------+
                              |
                           Valid
                              |
                              v
                  +-----------------------+
                  | Text Extraction       |
                  | Native PDF / OCR      |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | Kimi LLM Extraction   |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | Pydantic Validation   |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | Financial Validation  |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | SQLite Persistence    |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | API / Dashboard       |
                  +-----------------------+
```

---

## 23. Design Principles

The implementation follows these principles:

1. Validate before expensive processing.
2. Separate OCR from LLM extraction.
3. Use deterministic calculations for financial validation.
4. Preserve evidence where available.
5. Never modify extracted values merely to make a validation pass.
6. Treat missing information as `null` rather than inventing values.
7. Preserve multiple reporting periods independently.
8. Persist processing results.
9. Keep API, services, schemas, repositories, and models modular.
10. Keep secrets outside source control.
11. Make failure states explicit.
12. Keep the system testable without requiring an external LLM call for unit tests.
13. Keep LLM credentials isolated from the frontend.
14. Use environment-based configuration for deployment.

---

## 24. Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* SQLite

### Document Processing

* PyPDF
* PyMuPDF
* Pillow
* Tesseract OCR
* pytesseract

### AI

* Kimi LLM
* OpenAI-compatible API

### Frontend

* HTML
* CSS
* JavaScript

### Testing

* pytest
* FastAPI TestClient

---

## 25. Project Structure

```text
document-intelligence/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── documents.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging_config.py
│   │   │
│   │   ├── models/
│   │   │   └── document.py
│   │   │
│   │   ├── repositories/
│   │   │   └── document_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── document.py
│   │   │   └── extraction.py
│   │   │
│   │   ├── services/
│   │   │   ├── document_validation_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── financial_validation_service.py
│   │   │   └── document_service.py
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_extraction.py
│   │   └── test_financial_validation.py
│   │
│   └── scripts/
│       ├── __init__.py
│       └── export_sample_outputs.py
│
├── frontend/
│   ├── templates/
│   │   └── dashboard.html
│   │
│   └── static/
│       └── css/
│           └── style.css
│
├── docs/
│   └── ARCHITECTURE.md
│
├── sample_outputs/
│   ├── invoice.json
│   ├── balance_sheet.json
│   ├── profit_and_loss.json
│   ├── cash_flow_statement.json
│   ├── scanned_invoice.json
│   └── failure_unsupported_file.json
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```





