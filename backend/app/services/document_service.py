import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories.document_repository import create_document
from app.services.document_validation_service import (
    validate_document,
    DocumentValidationError,
)
from app.services.ocr_service import (
    extract_text,
    OCRProcessingError,
)
from app.services.extraction_service import (
    extract_document,
    ExtractionError,
)
from app.services.financial_validation_service import (
    validate_financial_document,
)


logger = logging.getLogger(__name__)


def process_document(
    db: Session,
    file_path: str,
    filename: str,
    content_type: str | None,
    file_bytes: bytes,
    document_type: str,
):

    logger.info(
        "Document processing started: filename=%s type=%s",
        filename,
        document_type,
    )

    # ========================================================
    # 1. FILE VALIDATION
    # ========================================================

    file_validation = validate_document(
        file_path=file_path,
        filename=filename,
        content_type=content_type,
        file_bytes=file_bytes,
    )

    logger.info(
        "File validation successful: filename=%s pages=%s",
        filename,
        file_validation["page_count"],
    )

    # ========================================================
    # 2. OCR / TEXT EXTRACTION
    # ========================================================

    extraction_result = extract_text(
        file_path
    )

    text = extraction_result["text"]

    ocr_used = extraction_result["ocr_used"]

    logger.info(
        "Text extraction completed: filename=%s ocr_used=%s",
        filename,
        ocr_used,
    )

    # ========================================================
    # 3. KIMI EXTRACTION
    # ========================================================

    extracted = extract_document(
        text=text,
        document_type=document_type,
    )

    logger.info(
        "AI extraction completed: filename=%s type=%s",
        filename,
        document_type,
    )

    # ========================================================
    # 4. FINANCIAL VALIDATION
    # ========================================================

    validation = validate_financial_document(
        data=extracted,
        document_type=document_type,
    )

    logger.info(
        "Financial validation completed: filename=%s status=%s",
        filename,
        validation["overall_status"],
    )

    # ========================================================
    # 5. CONVERT PYDANTIC → JSON
    # ========================================================

    extracted_data = extracted.model_dump()

    # ========================================================
    # 6. PERSIST
    # ========================================================

    document = create_document(
        db,
        document_name=filename,
        document_type=document_type,
        processing_status="EXTRACTED",
        file_validation=file_validation,
        extracted_data=extracted_data,
        validation=validation,
        processing_metadata={
            "ocr_used": ocr_used,
        },
    )

    logger.info(
        "Document saved successfully: id=%s filename=%s",
        document.id,
        filename,
    )

    return {
        "document_name": document.document_name,
        "document_type": document.document_type,
        "processing_status": document.processing_status,
        "file_validation": document.file_validation,
        "extracted_data": document.extracted_data,
        "validation": document.validation,
        "processing_metadata": document.processing_metadata,
        "error": None,
    }