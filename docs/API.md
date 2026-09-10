# Document Intelligence API

## 1. Overview

Document Intelligence exposes a REST API built with FastAPI.

### Base URL

For local development:

```text
http://127.0.0.1:8000
```

### API Prefix

```text
/api/v1
```

The API supports:

* Document processing
* Document retrieval
* Document listing
* Service health checks

---

# 2. API Endpoints

| Method | Endpoint                            | Purpose                  |
| ------ | ----------------------------------- | ------------------------ |
| POST   | `/api/v1/documents/process`         | Process a document       |
| GET    | `/api/v1/documents`                 | List processed documents |
| GET    | `/api/v1/documents/{document_name}` | Retrieve a document      |
| GET    | `/api/v1/health`                    | Health check             |
| GET    | `/docs`                             | Swagger UI               |

---

# 3. Process Document

## Endpoint

```http
POST /api/v1/documents/process
```

Processes an uploaded financial document.

The processing pipeline performs:

```text
Upload
   ↓
File Validation
   ↓
Text Extraction / OCR
   ↓
Kimi LLM Extraction
   ↓
Pydantic Validation
   ↓
Financial Validation
   ↓
SQLite Persistence
   ↓
Response
```

---

## Request

The endpoint uses `multipart/form-data`.

### Parameters

| Parameter       | Type   | Required | Description                     |
| --------------- | ------ | -------- | ------------------------------- |
| `file`          | File   | Yes      | PDF, JPG, JPEG, or PNG document |
| `document_type` | String | Yes      | Type of financial document      |

### Supported Document Types

```text
invoice
balance_sheet
profit_and_loss
cash_flow_statement
```

### File Constraints

* Maximum file size: 10 MB
* Maximum pages for PDF: 3
* Supported formats: PDF, JPG, JPEG, PNG

### Example Using cURL

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/documents/process" \
  -F "file=@invoice.pdf" \
  -F "document_type=invoice"
```

---

# 4. Successful Response

A successful processing request returns the structured document result.

Example:

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

---

# 5. Invoice Response

Invoice extraction can contain:

```text
invoice_number
invoice_date
vendor_name
customer_name
currency
subtotal
tax_rate
tax_amount
discount
total_amount
cash_received
change_amount
total_items
total_quantity
line_items
```

Each extracted field can contain evidence.

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

---

## Invoice Line Items

Example:

```json
{
  "line_items": [
    {
      "item_code": "TS-001",
      "description": "Notebook",
      "quantity": 2,
      "unit_price": 50.0,
      "amount": 100.0,
      "evidence": {
        "source_text": "TS-001 Notebook 2 50.00 100.00",
        "page_number": 1
      }
    }
  ]
}
```

---

# 6. Financial Statement Response

Balance Sheet, Profit & Loss, and Cash Flow documents use a common structure.

Example:

```json
{
  "statement_title": "Balance Sheet",
  "company_name": "Example Company",
  "currency": "INR",
  "periods": [
    "2024",
    "2023"
  ],
  "line_items": [
    {
      "name": "Total Assets",
      "value": 100000.0,
      "period": "2024",
      "evidence": {
        "source_text": "Total Assets 100,000",
        "page_number": 1
      }
    }
  ]
}
```

Multiple reporting periods are preserved independently.

---

# 7. Validation Response

Financial validations contain:

```text
check_name
formula
input_values
calculated_value
reported_value
variance
status
```

Example:

```json
{
  "check_name": "Invoice total reconciliation",
  "formula": "subtotal - discount + tax ≈ total",
  "input_values": {
    "subtotal": 150.0,
    "discount": 0.0,
    "tax_amount": 27.0,
    "reported_total": 177.0
  },
  "calculated_value": 177.0,
  "reported_value": 177.0,
  "variance": 0.0,
  "status": "PASS"
}
```

Possible validation statuses:

```text
PASS
FAIL
NOT_APPLICABLE
```

---

# 8. Validation Summary

The validation response contains:

```json
{
  "overall_status": "PASS",
  "total_checks": 5,
  "passed_checks": 5,
  "failed_checks": 0,
  "not_applicable_checks": 0,
  "validations": []
}
```

### Overall Status

#### `PASS`

All applicable validations passed.

#### `FAIL`

At least one applicable validation failed.

#### `NOT_APPLICABLE`

There was insufficient information to perform the relevant validations.

---

# 9. Get All Documents

## Endpoint

```http
GET /api/v1/documents
```

Returns persisted documents.

### Example

```bash
curl http://127.0.0.1:8000/api/v1/documents
```

### Response

```json
[
  {
    "id": 1,
    "document_name": "invoice.pdf",
    "document_type": "invoice",
    "processing_status": "EXTRACTED",
    "created_at": "2026-09-11T00:00:00"
  }
]
```

The endpoint returns documents ordered by creation time, with the newest documents appearing first.

---

# 10. Get Document

## Endpoint

```http
GET /api/v1/documents/{document_name}
```

Retrieves the latest persisted result for a document name.

### Example

```bash
curl \
  "http://127.0.0.1:8000/api/v1/documents/invoice.pdf"
```

The response contains the complete stored processing result, including:

* File validation
* Extracted data
* Financial validation
* Processing metadata
* Error information

---

# 11. Health Check

## Endpoint

```http
GET /api/v1/health
```

Used to verify that the backend service is running.

### Request

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Response

```json
{
  "status": "healthy",
  "service": "document-intelligence"
}
```

---

# 12. Error Handling

The API returns structured failure information.

Example:

```json
{
  "document_name": "unsupported_document.docx",
  "document_type": "invoice",
  "processing_status": "FAILED",
  "file_validation": null,
  "extracted_data": null,
  "validation": null,
  "processing_metadata": {
    "error_code": "UNSUPPORTED_FILE_TYPE",
    "error_message": "Only PDF / JPG / PNG documents are supported."
  },
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "Only PDF / JPG / PNG documents are supported."
  }
}
```

---

# 13. Error Codes

The system can return errors such as:

| Error Code              | Description                         |
| ----------------------- | ----------------------------------- |
| `UNSUPPORTED_FILE_TYPE` | File format is not supported        |
| `CORRUPTED_FILE`        | File cannot be read                 |
| `PAGE_LIMIT_EXCEEDED`   | Document contains more than 3 pages |
| `INVALID_IMAGE`         | Image cannot be decoded/read        |
| `OCR_ERROR`             | OCR processing failed               |
| `EXTRACTION_ERROR`      | LLM extraction failed               |
| `PROCESSING_ERROR`      | Unexpected processing error         |

---

# 14. Processing Order

Validation errors occur before OCR and LLM processing.

```text
Request
   |
   v
File Validation
   |
   +---- Invalid ----> FAILED Response
   |
   v
Text Extraction / OCR
   |
   v
Kimi Extraction
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
Successful Response
```

This prevents invalid documents from unnecessarily consuming OCR or LLM resources.

---

# 15. OCR Processing

For native PDFs:

```text
PDF
 ↓
Native text extraction
 ↓
Sufficient text?
 ├── Yes → Continue to LLM
 └── No  → OCR
```

For scanned documents:

```text
Image / Scanned PDF
        ↓
Image preprocessing
        ↓
Tesseract OCR
        ↓
Extracted text
        ↓
Kimi LLM
```

The response indicates whether OCR was used through:

```json
{
  "processing_metadata": {
    "ocr_used": true
  }
}
```

---

# 16. Evidence

Where available, extracted fields contain evidence.

Example:

```json
{
  "value": "OCR-TEST-001",
  "evidence": {
    "source_text": "Invoice No: OCR-TEST-001",
    "page_number": 1
  }
}
```

Evidence helps users verify where an extracted value originated.

---

# 17. API Documentation

FastAPI automatically generates OpenAPI documentation.

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### OpenAPI JSON

```text
http://127.0.0.1:8000/openapi.json
```

Swagger can be used to:

* Inspect API endpoints
* View request parameters
* Upload documents
* Execute API requests
* Inspect responses
* Test error scenarios

---

# 18. Example End-to-End API Flow

### 1. Upload Invoice

```http
POST /api/v1/documents/process
```

### 2. System Validates the File

```text
PDF
 ↓
Readable
 ↓
1 page
 ↓
PASS
```

### 3. Text Extraction

For a digitally generated PDF:

```text
Native PDF extraction
```

For a scanned document:

```text
Tesseract OCR
```

### 4. Kimi Extraction

```text
Extracted text
      ↓
    Kimi
      ↓
Structured JSON
```

### 5. Pydantic Validation

```text
Structured JSON
      ↓
Pydantic schema validation
      ↓
Valid extraction object
```

### 6. Financial Validation

```text
Extracted values
      ↓
Deterministic calculations
      ↓
PASS / FAIL / NOT_APPLICABLE
```

### 7. Persistence

```text
SQLite
```

### 8. Retrieval

```http
GET /api/v1/documents/{document_name}
```

---

# 19. Running the API Locally

From the project root:

```bash
cd backend
```

Activate the virtual environment:

```bash
source ../venv/bin/activate
```

Start the server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Dashboard:

```text
http://127.0.0.1:8000/
```

---

# 20. API Testing

Automated API tests are located under:

```text
backend/tests/test_api.py
```

Run the tests:

```bash
python -m pytest -v
```

The test suite verifies:

* Health endpoint
* Documents endpoint
* Swagger endpoint

---

# 21. Production Configuration

The application uses environment variables for configuration.

Kimi API credentials must never be hard-coded in the source code.

Required environment variables:

```env
LLM_API_KEY=your_kimi_api_key
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
DATABASE_URL=sqlite:///./document_intelligence.db
```

### Environment Variables

| Variable       | Description                         |
| -------------- | ----------------------------------- |
| `LLM_API_KEY`  | Kimi API key                        |
| `LLM_BASE_URL` | Kimi OpenAI-compatible API base URL |
| `LLM_MODEL`    | Kimi model used for extraction      |
| `DATABASE_URL` | Database connection URL             |

### Production Security

For production:

* Store `LLM_API_KEY` as a platform-managed secret.
* Never commit the real API key to Git.
* Never expose the API key to the frontend.
* Never return the API key in API responses.
* Never write the API key to logs.
* Keep `.env` excluded from source control.
* Use `.env.example` only for documenting required variables.
* Rotate the API key if it is accidentally exposed.

### `.env.example`

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
DATABASE_URL=sqlite:///./document_intelligence.db
```

The production frontend communicates only with the FastAPI backend. The frontend does not communicate directly with Kimi.

---

# 22. API Security Model

The architecture follows a backend-only LLM credential model:

```text
                    User
                      |
                      v
                Frontend
                      |
                      | REST API
                      v
                 FastAPI
                      |
                      v
             Extraction Service
                      |
                      | API Key
                      v
                 Kimi API
```

The Kimi API key remains inside the backend environment.

The browser receives only the application's document-processing response.

---

# 23. API Request Lifecycle

A complete request follows this lifecycle:

```text
HTTP Request
     |
     v
FastAPI Router
     |
     v
Request Validation
     |
     v
File Validation
     |
     v
Document Service
     |
     +--------------------+
     |                    |
     v                    v
Native PDF           OCR Service
Extraction              |
     |                   |
     +---------+---------+
               |
               v
        Extracted Text
               |
               v
        Kimi Extraction
               |
               v
       JSON Parsing
               |
               v
     Pydantic Validation
               |
               v
    Financial Validation
               |
               v
       SQLite Persistence
               |
               v
        API Response
```

---

# 24. Response Statuses

The application uses processing statuses to communicate the state of document processing.

Typical statuses include:

```text
EXTRACTED
FAILED
```

A successfully processed document contains extracted data and financial validation results.

A failed document contains structured error information describing the failure.

---

# 25. API Design Principles

The API follows these principles:

1. Validate files before expensive processing.
2. Reject unsupported files early.
3. Keep OCR and LLM processing separate.
4. Use deterministic application logic for financial validation.
5. Preserve evidence for extracted values where available.
6. Return structured JSON responses.
7. Validate LLM output using Pydantic.
8. Persist processing results.
9. Keep LLM credentials backend-only.
10. Never expose secrets through API responses.
11. Return explicit error codes.
12. Keep API versioning under `/api/v1`.
13. Provide OpenAPI/Swagger documentation.
14. Keep the API testable through automated tests.

---

# 26. Complete Endpoint Summary

| Method | Endpoint                            | Description                               |
| ------ | ----------------------------------- | ----------------------------------------- |
| `POST` | `/api/v1/documents/process`         | Upload and process a financial document   |
| `GET`  | `/api/v1/documents`                 | Retrieve all persisted documents          |
| `GET`  | `/api/v1/documents/{document_name}` | Retrieve the latest result for a document |
| `GET`  | `/api/v1/health`                    | Check backend health                      |
| `GET`  | `/docs`                             | Open Swagger UI                           |
| `GET`  | `/openapi.json`                     | Retrieve OpenAPI specification            |

---

# 27. Example Client Integration

A Python client can interact with the API using the `requests` library.

Example:

```python
import requests

url = "http://127.0.0.1:8000/api/v1/documents/process"

with open("invoice.pdf", "rb") as file:
    response = requests.post(
        url,
        files={
            "file": file
        },
        data={
            "document_type": "invoice"
        }
    )

print(response.status_code)
print(response.json())
```

The client does not require access to the Kimi API key because the Kimi integration is handled internally by the backend.

---

# 28. Production Request Flow

In production, the external request flow is:

```text
Client
  |
  v
Production Frontend
  |
  | HTTPS
  v
Production FastAPI
  |
  +--------------------+
  |                    |
  v                    v
Document Processing   Database
  |
  v
Kimi API
```

The production deployment should ensure that:

* API traffic uses HTTPS.
* LLM credentials remain server-side.
* Database credentials remain server-side.
* Uploaded documents are validated before processing.
* Processing failures are returned as structured API responses.
* Logs do not contain secrets.

---

# 29. API Documentation Maintenance

Whenever an API endpoint, request parameter, response schema, error code, or processing behavior changes, this document should be updated.

The API documentation should remain consistent with the actual FastAPI implementation.

Swagger/OpenAPI documentation generated by FastAPI should be used as the runtime reference for the deployed API.

---

# 30. Final API Architecture

```text
                         CLIENT
                           |
                           v
                 +-------------------+
                 | Production        |
                 | Frontend          |
                 +---------+---------+
                           |
                         HTTPS
                           |
                           v
                 +-------------------+
                 | FastAPI           |
                 | REST API          |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | Document Service  |
                 | Orchestration      |
                 +---------+---------+
                           |
              +------------+------------+
              |            |            |
              v            v            v
        +---------+   +---------+   +---------+
        | File    |   | OCR /   |   | Kimi    |
        | Valid.  |   | Text    |   | LLM     |
        +---------+   +---------+   +---------+
                           |
                           v
                 +-------------------+
                 | Pydantic          |
                 | Validation        |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | Financial         |
                 | Validation        |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | Database          |
                 | Persistence       |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | JSON API Response |
                 +-------------------+
```

This document defines the REST API contract, processing lifecycle, response structures, validation behavior, error handling, Kimi integration, security requirements, and production request flow for the Document Intelligence application.

