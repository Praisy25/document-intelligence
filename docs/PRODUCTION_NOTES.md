# Production Notes

## 1. Overview

The current implementation is designed as a modular proof-of-concept for AI-powered financial document intelligence.

The application separates:

* File validation
* OCR and text extraction
* LLM-based structured extraction
* Schema validation
* Financial validation
* Persistence
* REST APIs
* Frontend presentation

For production deployment, additional controls would be required around security, scalability, observability, reliability, and data governance.

---

# 2. Current Architecture

The current system follows this processing flow:

```text
                  ┌─────────────────────┐
                  │       Frontend      │
                  │ HTML / CSS / JS     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │      FastAPI        │
                  │      REST API       │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  File Validation    │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Text Extraction /   │
                  │ OCR                 │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Kimi LLM Extraction │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Pydantic Validation │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Financial Validation│
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │      Database       │
                  └─────────────────────┘
```

---

# 3. Deployment

The current application consists of:

* FastAPI backend
* Static frontend
* SQLite database during development
* Tesseract OCR
* Kimi API for LLM extraction

A production deployment should separate the application environment from local development.

A typical production architecture could be:

```text
                     Internet
                         │
                         ▼
                 ┌───────────────┐
                 │ Reverse Proxy │
                 │ HTTPS / TLS   │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ FastAPI App   │
                 │ Uvicorn       │
                 └───────┬───────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         PostgreSQL     OCR      Kimi API
```

HTTPS should always be enabled in production.

---

# 4. Database

## Current Implementation

The project currently uses SQLite for simplicity:

```env
DATABASE_URL=sqlite:///./document_intelligence.db
```

SQLite is appropriate for:

* Local development
* Testing
* Demonstrations
* Small proof-of-concept deployments

## Production Recommendation

Use PostgreSQL for production.

Advantages include:

* Better concurrent access
* Transaction support
* Better scalability
* Stronger operational tooling
* Better support for larger datasets
* Easier horizontal application scaling

The repository layer helps isolate database operations from the rest of the application, making a future database migration easier.

---

# 5. File Storage

The current application processes uploaded files temporarily.

For production, uploaded files should not be stored permanently on the application server unless required.

A scalable architecture could use object storage:

```text
User Upload
     │
     ▼
Object Storage
     │
     ▼
Processing Worker
     │
     ├── OCR
     └── LLM
```

Possible object-storage solutions include:

* Amazon S3
* Google Cloud Storage
* Azure Blob Storage

Document metadata can remain in PostgreSQL while the actual files are stored in object storage.

---

# 6. Security

Financial documents may contain sensitive information.

Production deployment should therefore implement strong security controls.

## API Security

Recommended controls:

* HTTPS
* Authentication
* Authorization
* Rate limiting
* Request validation
* File type validation
* File size limits
* Request timeouts
* Secure HTTP headers

## Authentication

The current proof-of-concept does not require user authentication.

A production system should use an authentication mechanism such as:

```text
User
  ↓
Authentication
  ↓
Access Token
  ↓
API
```

Authorization should ensure that users can only access documents they are permitted to view.

---

# 7. Secret Management

API keys must never be hard-coded in source code.

The project uses environment variables:

```env
LLM_API_KEY=YOUR_KIMI_API_KEY
LLM_BASE_URL=https://api.moonshot.ai/v1
LLM_MODEL=kimi-k3
```

The `.env` file should never be committed to Git.

Production environments should use a dedicated secret-management system.

Examples include:

* Cloud secret managers
* Environment-level secrets
* Vault-based secret management

API keys should never be written to application logs.

---

# 8. File Upload Security

Uploaded documents should be treated as untrusted input.

Production validation should include:

* Extension validation
* MIME-type validation
* File size validation
* Page count validation
* File integrity validation
* Image integrity validation
* Malicious file detection
* Filename sanitization

The application already performs basic validation before OCR or LLM processing.

The current page limit is:

```text
Maximum pages = 3
```

The current maximum file size is:

```text
Maximum file size = 10 MB
```

These values can be configured through environment variables.

---

# 9. OCR Reliability

The system uses native PDF extraction whenever possible.

If sufficient text cannot be extracted, OCR is used.

```text
PDF
 │
 ├── Native text available
 │          │
 │          ▼
 │      Extract text
 │
 └── Insufficient text
            │
            ▼
           OCR
```

For scanned documents, image preprocessing is applied before OCR.

Production improvements could include:

* Better image preprocessing
* Automatic image rotation
* Language detection
* Multiple OCR engines
* OCR confidence thresholds
* Layout-aware OCR
* Table-aware OCR
* Human review for low-confidence documents

---

# 10. LLM Reliability

The LLM is an important part of the extraction pipeline, but it should not be treated as a guaranteed source of truth.

Possible LLM failures include:

* API timeout
* API rate limit
* Invalid response
* Malformed JSON
* Missing fields
* Incorrect field mapping
* Incorrect period assignment
* Hallucinated values

The application reduces these risks using:

```text
LLM Response
     ↓
JSON Parsing
     ↓
Pydantic Validation
     ↓
Financial Validation
```

Production systems should also implement retry policies and timeout controls.

Transient API failures should be retried carefully with bounded retries and backoff.

---

# 11. LLM Cost Control

LLM APIs may charge based on input and output usage.

Financial documents can contain large amounts of text.

Production optimizations could include:

* Extract only meaningful document text
* Remove unnecessary whitespace
* Avoid sending duplicate text
* Use document-type-specific prompts
* Limit output size
* Cache repeated processing where appropriate
* Use smaller models for simple extraction
* Route difficult documents to more capable models

A production system should monitor:

```text
Requests
Tokens
Processing Time
Failures
Cost per Document
```

---

# 12. Financial Validation

Financial validation is intentionally implemented as deterministic application logic rather than relying on the LLM.

Examples include:

## Invoice

```text
quantity × unit price ≈ line amount
```

```text
sum(line items) ≈ subtotal
```

```text
subtotal - discount + tax ≈ total
```

```text
cash received - total ≈ change
```

## Balance Sheet

```text
total assets ≈ total capital and liabilities
```

## Profit & Loss

```text
total income - total expenditure ≈ net profit
```

## Cash Flow

```text
operating
+ investing
+ financing
+ FX adjustment
≈ net increase in cash
```

This separation provides an important production safety layer.

---

# 13. Numeric Tolerance

Financial documents can contain rounding differences.

Therefore, validations use a tolerance rather than requiring exact floating-point equality.

Current default:

```text
Tolerance = 1.0
```

For example:

```text
Calculated value = 100.00
Reported value   = 100.50
Variance         = 0.50
```

The check can still PASS when the variance is within the configured tolerance.

For production, tolerance rules should be configurable by:

* Currency
* Document type
* Validation rule
* Business requirements

---

# 14. Error Handling

The system distinguishes different classes of processing failures.

Examples include:

```text
UNSUPPORTED_FILE_TYPE
CORRUPTED_FILE
PAGE_LIMIT_EXCEEDED
OCR_ERROR
EXTRACTION_ERROR
PROCESSING_ERROR
```

The API returns structured error responses rather than exposing internal stack traces.

Production systems should additionally:

* Log detailed internal errors
* Return safe client-facing messages
* Generate unique request IDs
* Track failed processing jobs
* Retry transient external failures
* Alert operators when failure rates increase

---

# 15. Asynchronous Processing

The current implementation processes a document during the API request.

For a production system with large document volumes, synchronous processing may cause long API response times.

A scalable design would use background workers:

```text
POST /documents/process
          │
          ▼
      Create Job
          │
          ▼
         Queue
          │
          ▼
    Background Worker
          │
       ┌──┴──┐
       ▼     ▼
      OCR   LLM
       │     │
       └──┬──┘
          ▼
       Validate
          │
          ▼
       Database
```

Possible technologies include:

* Celery
* Redis
* RabbitMQ
* Cloud task queues

The API could immediately return a job ID:

```json
{
  "job_id": "abc123",
  "status": "PROCESSING"
}
```

The frontend could then retrieve the processing status.

---

# 16. Scalability

The current application is suitable for a small workload.

For larger workloads, the following architecture could be used:

```text
                     Load Balancer
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
        API Server    API Server    API Server
            │             │             │
            └─────────────┼─────────────┘
                          ▼
                        Queue
                          │
                 ┌────────┼────────┐
                 ▼        ▼        ▼
              Worker   Worker   Worker
                 │        │        │
                 └────────┼────────┘
                          ▼
                      PostgreSQL
                          │
                          ▼
                     Object Storage
```

This allows API servers and processing workers to scale independently.

---

# 17. Observability

Production deployments should provide three major observability layers.

## Logs

Record:

* Request ID
* Document name
* Document type
* Processing stage
* Processing duration
* OCR usage
* LLM errors
* Validation results
* Failure reason

Sensitive document contents and API keys should not be logged.

## Metrics

Useful metrics include:

```text
documents_processed_total
documents_failed_total
ocr_usage_total
llm_requests_total
validation_failures_total
average_processing_time
average_ocr_time
average_llm_time
```

## Health Checks

The application exposes:

```text
GET /api/v1/health
```

A production health endpoint should also verify critical dependencies where appropriate.

---

# 18. Monitoring and Alerts

Production monitoring should alert when:

* Error rates increase
* OCR failures increase
* LLM API failures increase
* Processing latency increases
* Database connectivity fails
* Queue backlog increases
* API rate limits are reached
* Storage usage becomes high

Monitoring allows operators to identify failures before they significantly affect users.

---

# 19. Data Retention

Financial documents may contain sensitive business information.

A production deployment should define:

* How long uploaded files are stored
* How long extracted data is stored
* When temporary files are deleted
* Who can access documents
* When records are permanently deleted

A retention policy should be defined according to the organization's legal and business requirements.

---

# 20. Privacy

The system should minimize unnecessary exposure of document contents.

Recommended practices:

* Encrypt data in transit
* Encrypt stored documents
* Restrict database access
* Restrict object-storage access
* Avoid logging sensitive document text
* Avoid exposing raw files through public URLs
* Apply access control to extracted results

LLM provider data-handling policies should also be reviewed before using the system with real financial documents.

---

# 21. Backup and Recovery

Production databases should be backed up regularly.

Recommended strategy:

```text
Application
     │
     ▼
PostgreSQL
     │
     ├── Automated Backups
     │
     └── Recovery Testing
```

Object storage should also use appropriate backup/versioning policies when documents need long-term retention.

Recovery procedures should be tested rather than relying only on backup creation.

---

# 22. Testing Before Production

Before production deployment, testing should include:

## Functional Testing

* All four supported document types
* Native PDFs
* Scanned PDFs
* JPG/PNG documents
* Multi-page documents
* Missing fields

## Validation Testing

* Passing financial statements
* Intentionally incorrect totals
* Negative values
* Multiple reporting periods
* Rounding differences

## Failure Testing

* Unsupported files
* Corrupted files
* Oversized files
* Page-limit violations
* Invalid images
* OCR failures
* LLM failures
* Database failures

## Load Testing

Test:

* Concurrent uploads
* Large document volume
* Queue behavior
* API latency
* Database performance

---

# 23. CI/CD

A production repository should run automated checks before deployment.

Example pipeline:

```text
Git Push
   ↓
Run Tests
   ↓
Lint / Static Analysis
   ↓
Build Application
   ↓
Security Checks
   ↓
Deploy
```

Deployment should only proceed when required checks pass.

---

# 24. Containerization

Docker can be used to make the application environment reproducible.

A production container would package:

* Python runtime
* FastAPI application
* Required Python packages
* Tesseract OCR
* Application configuration

A multi-container deployment could separate:

```text
Frontend / API
     │
     ├── PostgreSQL
     ├── Redis
     └── Worker
```

Containerization also simplifies deployment across development, testing, and production environments.

---

# 25. Performance Improvements

Potential optimizations include:

* Reuse OCR configuration
* Avoid unnecessary OCR when native text is available
* Compress large images before processing
* Cache repeated document processing
* Use asynchronous workers
* Batch database operations where appropriate
* Use connection pooling
* Optimize LLM prompts
* Limit unnecessary output tokens

Performance should be measured before optimization.

---

# 26. Human-in-the-Loop

For high-value financial workflows, fully automated extraction should not always be the final step.

A production workflow could be:

```text
Document
    ↓
AI Extraction
    ↓
Validation
    ↓
Confidence / Risk Check
    │
    ├── Low Risk ──→ Automatic Approval
    │
    └── High Risk ─→ Human Review
                         │
                         ▼
                    Final Approval
```

Human review can be triggered when:

* Required fields are missing
* Financial checks fail
* OCR confidence is low
* The document is ambiguous
* Important values cannot be verified

---

# 27. Auditability

Production financial systems should maintain an audit trail.

An audit record could include:

```text
Document ID
Processing timestamp
User ID
Model used
Model version
Prompt version
OCR engine/version
Extraction status
Validation status
Reviewer
Review timestamp
```

This makes it possible to understand how a result was generated and modified.

---

# 28. Model Versioning

LLM behavior can change between model versions.

Production systems should record the model used for every document.

Example:

```json
{
  "llm_provider": "kimi",
  "llm_model": "kimi-k3"
}
```

Prompt versions should also be tracked.

This makes historical results reproducible and helps diagnose changes in extraction quality.

---

# 29. Configuration Management

Application configuration should be externalized through environment variables.

Important configuration values include:

```env
LLM_PROVIDER=kimi
LLM_API_KEY=YOUR_KIMI_API_KEY
LLM_MODEL=kimi-k3
LLM_BASE_URL=https://api.moonshot.ai/v1

OCR_PROVIDER=tesseract

MAX_FILE_SIZE_MB=10
MAX_PAGES=3

DATABASE_URL=sqlite:///./document_intelligence.db

API_PREFIX=/api/v1
ENVIRONMENT=development
```

Different environments should use different configurations:

```text
Development
Testing
Production
```

Secrets should never be included in the Git repository.

---

# 30. Current Limitations

The current proof-of-concept has several limitations:

1. SQLite is used instead of PostgreSQL.
2. Processing is synchronous.
3. Authentication is not implemented.
4. Role-based authorization is not implemented.
5. Object storage is not implemented.
6. A production queue/worker system is not implemented.
7. Advanced OCR/layout understanding is limited.
8. LLM confidence scoring is not fully implemented.
9. Production-grade monitoring is not implemented.
10. Automated deployment infrastructure is not included.
11. The system is designed for documents up to three pages.
12. Financial validation rules currently cover predefined document types.

These limitations are acceptable for the scope of the assessment but should be addressed before handling production financial workloads.

---

# 31. Recommended Production Roadmap

## Phase 1 — Security

* Add authentication
* Add authorization
* Add HTTPS
* Add rate limiting
* Add secure secret management
* Harden file upload handling

## Phase 2 — Scalability

* Move SQLite to PostgreSQL
* Add object storage
* Introduce Redis/message queue
* Add background workers
* Add horizontal API scaling

## Phase 3 — Reliability

* Add retries
* Add timeouts
* Add circuit breakers
* Add health checks
* Add monitoring and alerting

## Phase 4 — AI Quality

* Build a labeled evaluation dataset
* Measure extraction accuracy
* Add confidence scoring
* Improve table extraction
* Add human review workflows
* Track prompt/model versions

## Phase 5 — Operations

* Add CI/CD
* Containerize the application
* Add centralized logging
* Add metrics dashboards
* Implement backup and recovery
* Establish data-retention policies

---

# 32. Production Target Architecture

A mature version of the system could look like:

```text
                         Users
                           │
                           ▼
                     HTTPS / Gateway
                           │
                           ▼
                      Load Balancer
                           │
               ┌───────────┼───────────┐
               ▼           ▼           ▼
            FastAPI     FastAPI     FastAPI
               │           │           │
               └───────────┼───────────┘
                           ▼
                         Queue
                           │
                  ┌────────┼────────┐
                  ▼        ▼        ▼
               Worker   Worker   Worker
                  │        │        │
                  ▼        ▼        ▼
                 OCR      LLM   Validation
                  │        │        │
                  └────────┼────────┘
                           ▼
                       PostgreSQL
                           │
                           ▼
                     Object Storage
                           │
                           ▼
                    Monitoring / Audit
```

This architecture allows the document processing pipeline to scale independently while maintaining security, observability, and traceability.

---

# 33. Final Production Principle

The most important design principle is:

> Use AI for semantic extraction, but use deterministic software for validation, security, persistence, and business-critical decisions.

This keeps the system flexible enough to process different document layouts while reducing the risk of allowing an LLM to make unchecked financial decisions.
