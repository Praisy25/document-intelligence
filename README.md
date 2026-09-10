# Document Intelligence

AI-powered financial document processing system that extracts structured information from invoices and financial statements, validates financial calculations, preserves extraction evidence, and exposes the results through REST APIs and a web dashboard.

---

## 1. Project Overview

Document Intelligence is a modular document-processing application designed to process financial documents such as:

* Invoices
* Balance Sheets
* Profit & Loss Statements
* Cash Flow Statements

The system accepts PDF, JPG, JPEG, and PNG documents.

It automatically:

1. Validates the uploaded document
2. Extracts native PDF text when available
3. Uses OCR for scanned/image-based documents
4. Sends extracted text to an LLM for structured extraction
5. Validates the LLM response using Pydantic schemas
6. Performs deterministic financial calculations
7. Stores the processed result in a database
8. Exposes the result through REST APIs
9. Displays the result through a web dashboard

---

## 2. Key Features

### Document Processing

* PDF, JPG, JPEG, and PNG support
* Maximum document size configurable
* Maximum page count configurable
* PDF integrity validation
* Image readability validation
* Unsupported file detection
* Corrupted document detection

### Text Extraction

* Native PDF text extraction
* OCR fallback for scanned PDFs
* OCR support for images
* Image preprocessing
* Multi-page processing
* Page-level evidence

### AI Extraction

* Kimi LLM integration
* Document-type-specific extraction prompts
* Structured JSON output
* Pydantic schema validation
* Evidence/source text preservation
* No-value-hallucination instructions

### Financial Validation

Deterministic validation rules are implemented for all supported document types.

#### Invoice

* Quantity × unit price ≈ line amount
* Sum of line items ≈ subtotal
* Subtotal − discount + tax ≈ total
* Cash received − total ≈ change

#### Balance Sheet

* Total assets ≈ total capital and liabilities
* Component-level reconciliation where applicable
* Multi-period validation

#### Profit & Loss

* Interest earned + other income ≈ total income
* Interest expended + operating expenses + provisions ≈ total expenditure
* Total income − total expenditure ≈ net profit
* Net profit − minority interest ≈ group net profit
* Appropriations where applicable

#### Cash Flow Statement

* Operating + investing + financing + FX adjustment ≈ net increase
* Opening cash + net increase + applicable adjustments ≈ closing cash
* Negative values preserved
* Multi-period validation

---

## 3. Architecture

```text
                    ┌──────────────────────┐
                    │       Frontend       │
                    │    HTML/CSS/JS       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │      REST API        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Document Validation │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Text Extraction /    │
                    │ OCR                  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Kimi LLM         │
                    │ Structured Extraction│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Pydantic Validation  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Financial Validation │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       SQLite         │
                    │      Database        │
                    └──────────────────────┘
```

For detailed architecture documentation:

* `docs/ARCHITECTURE.md`

---

## 4. Processing Pipeline

```text
Upload Document
      │
      ▼
Validate File
      │
      ├── Invalid ──────► FAILED
      │
      ▼
Extract Native Text
      │
      ├── Sufficient ───► Continue
      │
      └── Insufficient
              │
              ▼
             OCR
              │
              ▼
        Extracted Text
              │
              ▼
           Kimi LLM
              │
              ▼
        Structured JSON
              │
              ▼
       Pydantic Validation
              │
              ▼
     Financial Validation
              │
              ▼
          Persistence
              │
              ▼
          API Response
```

---

## 5. Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* SQLite

### Document Processing

* PyMuPDF
* pypdf
* Pillow
* Tesseract OCR
* pytesseract

### AI / LLM

* Kimi API
* OpenAI-compatible Python client
* Structured prompting

### Frontend

* HTML
* CSS
* JavaScript

### Testing

* pytest
* FastAPI TestClient
* httpx

### Development

* Git
* VS Code
* Python virtual environment

---

## 6. Project Structure

```text
document-intelligence/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │       └── documents.py
│   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging_config.py
│   │
│   │   ├── models/
│   │   │   └── document.py
│   │
│   │   ├── repositories/
│   │   │   └── document_repository.py
│   │
│   │   ├── schemas/
│   │   │   ├── document.py
│   │   │   └── extraction.py
│   │
│   │   ├── services/
│   │   │   ├── document_validation_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── financial_validation_service.py
│   │   │   └── document_service.py
│   │
│   │   └── main.py
│
│   ├── scripts/
│   │   └── export_sample_outputs.py
│
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_schemas.py
│   │   └── test_financial_validation.py
│
│   └── requirements.txt
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
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── AI_USAGE.md
│   └── PRODUCTION_NOTES.md
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
└── README.md
```

---

## 7. Requirements

### Python

Recommended Python version:

```text
Python 3.11+
```

The application should be run inside a virtual environment.

### Tesseract OCR

Tesseract must be installed separately because `pytesseract` is a Python wrapper around the Tesseract executable.

On macOS:

```bash
brew install tesseract
```

Verify:

```bash
tesseract --version
```

---

## 8. Installation

Clone the repository:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd document-intelligence
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Install Tesseract:

```bash
brew install tesseract
```

---

## 9. Environment Configuration

Create a `.env` file in the project root:

```env
APP_NAME=Document Intelligence

DATABASE_URL=sqlite:///./document_intelligence.db

LLM_PROVIDER=kimi
LLM_API_KEY=YOUR_KIMI_API_KEY
LLM_MODEL=kimi-k3
LLM_BASE_URL=https://api.moonshot.ai/v1

OCR_PROVIDER=tesseract

MAX_FILE_SIZE_MB=10
MAX_PAGES=3

API_PREFIX=/api/v1
CORS_ORIGINS=*
ENVIRONMENT=development
```

Never commit the real `.env` file.

Only `.env.example` should be committed.

---

## 10. Run the Application

From the project root:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000
```

Open the dashboard:

```text
http://127.0.0.1:8000/
```

---

## 11. API Documentation

FastAPI automatically provides Swagger UI.

Open:

```text
http://127.0.0.1:8000/docs
```

Alternative OpenAPI documentation:

```text
http://127.0.0.1:8000/redoc
```

Detailed API documentation is available in:

```text
docs/API.md
```

---

## 12. API Endpoints

### Health Check

```http
GET /api/v1/health
```

Example response:

```json
{
  "status": "healthy",
  "service": "document-intelligence"
}
```

---

### Process Document

```http
POST /api/v1/documents/process
```

Form parameters:

```text
file
document_type
```

Supported document types:

```text
invoice
balance_sheet
profit_and_loss
cash_flow_statement
```

Example using curl:

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/documents/process" \
  -F "file=@sample_invoice.pdf" \
  -F "document_type=invoice"
```

---

### List Documents

```http
GET /api/v1/documents
```

Returns previously processed documents.

---

### Get Document

```http
GET /api/v1/documents/{document_name}
```

Returns the latest processing result for the specified document name.

---

## 13. Example Processing Result

A successful response contains:

```json
{
  "document_name": "invoice.pdf",
  "document_type": "invoice",
  "processing_status": "EXTRACTED",
  "file_validation": {
    "file_type": "application/pdf",
    "is_supported": true,
    "is_readable": true,
    "page_count": 1,
    "status": "PASS"
  },
  "extracted_data": {},
  "validation": {
    "overall_status": "PASS",
    "total_checks": 5,
    "passed_checks": 5,
    "failed_checks": 0,
    "not_applicable_checks": 0,
    "validations": []
  },
  "processing_metadata": {
    "ocr_used": false
  },
  "error": null
}
```

Complete examples are available in:

```text
sample_outputs/
```

---

## 14. Evidence

The extraction schema supports source evidence.

Example:

```json
{
  "value": 177,
  "evidence": {
    "source_text": "Total: 177.00",
    "page_number": 1
  }
}
```

Evidence helps establish a relationship between the extracted value and the source document.

---

## 15. Scanned Document Processing

The system supports scanned documents through OCR.

Example pipeline:

```text
Scanned Image
     ↓
Image Preprocessing
     ↓
Tesseract OCR
     ↓
Extracted Text
     ↓
Kimi LLM
     ↓
Structured Data
```

The OCR pipeline uses preprocessing techniques such as:

* Grayscale conversion
* Contrast enhancement
* Image resizing
* Sharpening
* Multiple Tesseract page segmentation configurations

The system selects the most suitable OCR result before sending text to the LLM.

---

## 16. Financial Validation

Financial validation is performed using deterministic Python logic.

The LLM is responsible for extraction, while the validation service performs mathematical reconciliation.

This separation reduces the risk of relying on an LLM for financial arithmetic.

Examples:

```text
Quantity × Unit Price ≈ Line Amount
```

```text
Subtotal − Discount + Tax ≈ Total
```

```text
Opening Cash + Net Increase ≈ Closing Cash
```

A tolerance is used to account for small rounding differences.

---

## 17. Error Handling

The application handles failures such as:

* Unsupported file type
* Corrupted PDF
* Invalid image
* Page count exceeding the configured limit
* OCR processing failure
* LLM extraction failure
* Invalid structured output

Example failure:

```json
{
  "processing_status": "FAILED",
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "Unsupported file type."
  }
}
```

Invalid documents are rejected before expensive OCR/LLM processing whenever possible.

---

## 18. Testing

Run the complete automated test suite from the `backend` directory:

```bash
python -m pytest -v
```

The test suite covers:

* Health endpoint
* Documents endpoint
* Swagger endpoint
* Invoice schema
* Financial statement schema
* Invoice validation success
* Invoice validation failure
* Cash flow validation

The project also includes manual failure-scenario testing for:

* Unsupported document
* Corrupted PDF
* Page-limit violation
* Invalid image

---

## 19. Sample Test Documents

Sample output files are available in:

```text
sample_outputs/
```

Examples include:

```text
invoice.json
balance_sheet.json
profit_and_loss.json
cash_flow_statement.json
scanned_invoice.json
failure_unsupported_file.json
```

These demonstrate both successful extraction and failure handling.

---

## 20. Logging

The application provides structured application logs.

Example:

```text
2026-09-10 12:00:00 | INFO | document_service | Processing document
2026-09-10 12:00:01 | INFO | ocr_service | OCR completed
2026-09-10 12:00:03 | INFO | extraction_service | LLM extraction completed
2026-09-10 12:00:03 | INFO | financial_validation_service | Validation completed
```

Sensitive information such as API keys should never be logged.

---

## 21. Persistence

Processed documents are stored using SQLAlchemy.

The stored information includes:

* Document name
* Document type
* Processing status
* File validation result
* Extracted data
* Financial validation result
* Processing metadata
* Error information
* Timestamps

The current implementation uses SQLite for development.

PostgreSQL is recommended for production.

---

## 22. Security

Security considerations include:

* Environment-based API keys
* File extension validation
* MIME-type validation
* File size limits
* Page count limits
* File integrity checks
* Safe error responses
* No secrets committed to Git

For production deployment, additional authentication, authorization, rate limiting, encryption, and secret management should be added.

See:

```text
docs/PRODUCTION_NOTES.md
```

---

## 23. AI Usage

AI is used primarily for semantic document extraction.

The LLM:

* Identifies document fields
* Extracts line items
* Maps values to reporting periods
* Produces structured JSON
* Provides source evidence where available

The system does not rely on the LLM for financial arithmetic validation.

AI-assisted development was also used for:

* Debugging
* Code assistance
* Prompt engineering
* Test generation
* Documentation

All implementation decisions and generated code were reviewed and tested.

Detailed declaration:

```text
docs/AI_USAGE.md
```

---

## 24. Design Principles

The project follows several core principles.

### Separation of Concerns

Different responsibilities are implemented in separate services.

```text
Validation
    ↓
OCR
    ↓
Extraction
    ↓
Financial Validation
    ↓
Persistence
    ↓
API
    ↓
Frontend
```

### AI + Deterministic Logic

AI handles semantic extraction.

Deterministic code handles:

* Financial calculations
* Validation
* Persistence
* API behavior

### Source Grounding

Extracted values should be supported by source text whenever possible.

### Fail Fast

Invalid files should be rejected before expensive processing.

### Configurability

Important limits and external services are configured using environment variables.

### Testability

Business logic is separated from API routes to make unit testing easier.

---

## 25. Production Improvements

The current implementation is an assessment-focused proof of concept.

For production, recommended improvements include:

* PostgreSQL
* Object storage
* Authentication
* Authorization
* Background processing
* Redis/message queue
* Horizontal scaling
* Centralized logging
* Metrics and monitoring
* Automated backups
* CI/CD
* Human-in-the-loop review
* Model and prompt versioning
* Better OCR/layout understanding
* More extensive evaluation datasets

Detailed discussion:

```text
docs/PRODUCTION_NOTES.md
```

---

## 26. Future Enhancements

Potential future features include:

* More document types
* Advanced table extraction
* Confidence scoring
* Human review workflow
* Document search
* Batch document processing
* Export to Excel/CSV
* Multi-language OCR
* Role-based access control
* Cloud object storage
* Asynchronous processing
* LLM model routing
* Document comparison
* Historical financial analysis

---

## 27. Project Status

### Completed

* File validation
* PDF processing
* JPG/PNG processing
* OCR processing
* Kimi LLM extraction
* Structured extraction schemas
* Evidence extraction
* Invoice validation
* Balance Sheet validation
* Profit & Loss validation
* Cash Flow validation
* Database persistence
* REST API
* Swagger documentation
* Frontend dashboard
* Automated tests
* Failure scenario testing
* Sample outputs
* Architecture documentation
* API documentation
* AI usage documentation
* Production notes

### Remaining

* Public deployment
* Final PPT
* Final repository cleanup
* Final README review

---

## 28. Author

Praisy Cathrin Mathi M

MSc Data Science

VIT Vellore

---

## 29. License

This project was developed as part of an AI Engineer technical assessment / academic project.

Add an appropriate open-source license if the repository is intended for public reuse.

