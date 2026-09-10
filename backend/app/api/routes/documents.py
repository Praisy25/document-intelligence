import logging
import os
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.repositories.document_repository import (
    create_document,
    get_all_documents,
    get_latest_by_name,
)

from app.schemas.document import DocumentResponse

from app.services.document_service import (
    process_document,
)

from app.services.document_validation_service import (
    DocumentValidationError,
)

from app.services.extraction_service import (
    ExtractionError,
)

from app.services.ocr_service import (
    OCRProcessingError,
)


logger = logging.getLogger(__name__)


router = APIRouter()


SUPPORTED_DOCUMENT_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement",
}


# ============================================================
# POST /process
# ============================================================

@router.post(
    "/process",
    response_model=DocumentResponse,
)
async def process_document_api(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Document type validation
    # --------------------------------------------------------

    if document_type not in SUPPORTED_DOCUMENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DOCUMENT_TYPE",
                "message": (
                    "document_type must be one of: "
                    "invoice, balance_sheet, "
                    "profit_and_loss, cash_flow_statement"
                ),
            },
        )

    # --------------------------------------------------------
    # Filename validation
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILENAME",
                "message": (
                    "The uploaded file must have "
                    "a filename."
                ),
            },
        )

    filename = file.filename

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "EMPTY_FILE",
                "message": (
                    "The uploaded file is empty."
                ),
            },
        )

    temporary_path = None

    try:

        # ----------------------------------------------------
        # Preserve extension
        # ----------------------------------------------------

        suffix = Path(
            filename
        ).suffix.lower()

        # ----------------------------------------------------
        # Create temporary file
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_file.write(file_bytes)

            temporary_path = temp_file.name

        # ----------------------------------------------------
        # Main processing
        # ----------------------------------------------------

        result = process_document(
            file_path=temporary_path,
            filename=filename,
            content_type=file.content_type,
            file_bytes=file_bytes,
            document_type=document_type,
            db=db,
        )

        return result

    # ========================================================
    # File validation failure
    # ========================================================

    except DocumentValidationError as exc:

        logger.warning(
            "Document validation failed: "
            "filename=%s code=%s message=%s",
            filename,
            exc.code,
            exc.message,
        )

        failure_metadata = {
            "error_code": exc.code,
            "error_message": exc.message,
        }

        # Persist failed document

        try:

            create_document(
                db=db,
                document_name=filename,
                document_type=document_type,
                processing_status="FAILED",
                file_validation=None,
                extracted_data=None,
                validation=None,
                processing_metadata=failure_metadata,
            )

        except Exception:

            logger.exception(
                "Failed to persist validation failure: "
                "filename=%s",
                filename,
            )

        return {
            "document_name": filename,
            "document_type": document_type,
            "processing_status": "FAILED",
            "file_validation": None,
            "extracted_data": None,
            "validation": None,
            "processing_metadata": failure_metadata,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        }

    # ========================================================
    # OCR failure
    # ========================================================

    except OCRProcessingError as exc:

        logger.error(
            "OCR failed: filename=%s message=%s",
            filename,
            exc.message,
        )

        failure_metadata = {
            "error_code": "OCR_FAILED",
            "error_message": exc.message,
        }

        try:

            create_document(
                db=db,
                document_name=filename,
                document_type=document_type,
                processing_status="FAILED",
                file_validation=None,
                extracted_data=None,
                validation=None,
                processing_metadata=failure_metadata,
            )

        except Exception:

            logger.exception(
                "Failed to persist OCR failure: "
                "filename=%s",
                filename,
            )

        return {
            "document_name": filename,
            "document_type": document_type,
            "processing_status": "FAILED",
            "file_validation": None,
            "extracted_data": None,
            "validation": None,
            "processing_metadata": failure_metadata,
            "error": {
                "code": "OCR_FAILED",
                "message": exc.message,
            },
        }

    # ========================================================
    # Gemini extraction failure
    # ========================================================

    except ExtractionError as exc:

        logger.error(
            "AI extraction failed: "
            "filename=%s message=%s",
            filename,
            exc.message,
        )

        failure_metadata = {
            "error_code": "EXTRACTION_FAILED",
            "error_message": exc.message,
        }

        try:

            create_document(
                db=db,
                document_name=filename,
                document_type=document_type,
                processing_status="FAILED",
                file_validation=None,
                extracted_data=None,
                validation=None,
                processing_metadata=failure_metadata,
            )

        except Exception:

            logger.exception(
                "Failed to persist extraction failure: "
                "filename=%s",
                filename,
            )

        return {
            "document_name": filename,
            "document_type": document_type,
            "processing_status": "FAILED",
            "file_validation": None,
            "extracted_data": None,
            "validation": None,
            "processing_metadata": failure_metadata,
            "error": {
                "code": "EXTRACTION_FAILED",
                "message": exc.message,
            },
        }

    # ========================================================
    # Unexpected error
    # ========================================================

    except Exception as exc:

        logger.exception(
            "Unexpected document processing error: "
            "filename=%s",
            filename,
        )

        failure_metadata = {
            "error_code": "DOCUMENT_PROCESSING_ERROR",
            "error_message": str(exc),
            "error_type": type(exc).__name__,
        }

        try:

            create_document(
                db=db,
                document_name=filename,
                document_type=document_type,
                processing_status="FAILED",
                file_validation=None,
                extracted_data=None,
                validation=None,
                processing_metadata=failure_metadata,
            )

        except Exception:

            logger.exception(
                "Failed to persist unexpected failure: "
                "filename=%s",
                filename,
            )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "DOCUMENT_PROCESSING_ERROR",
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
        )

    finally:

        # ----------------------------------------------------
        # Delete temporary file
        # ----------------------------------------------------

        if (
            temporary_path
            and os.path.exists(temporary_path)
        ):

            os.remove(
                temporary_path
            )


# ============================================================
# GET /documents
# ============================================================

@router.get("")
def list_documents(
    db: Session = Depends(get_db),
):

    documents = get_all_documents(db)

    return {
        "documents": [
            {
                "id": document.id,
                "document_name": document.document_name,
                "document_type": document.document_type,
                "processing_status": document.processing_status,
                "created_at": document.created_at,
            }
            for document in documents
        ]
    }


# ============================================================
# GET /documents/{document_name}
# ============================================================

@router.get(
    "/{document_name}",
    response_model=DocumentResponse,
)
def get_document(
    document_name: str,
    db: Session = Depends(get_db),
):

    document = get_latest_by_name(
        db=db,
        document_name=document_name,
    )

    if document is None:

        raise HTTPException(
            status_code=404,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": (
                    f"Document '{document_name}' "
                    "was not found."
                ),
            },
        )

    metadata = document.processing_metadata or {}

    error = None

    if document.processing_status == "FAILED":

        error_code = metadata.get(
            "error_code"
        )

        error_message = metadata.get(
            "error_message"
        )

        if error_code and error_message:

            error = {
                "code": error_code,
                "message": error_message,
            }

    return {
        "document_name": document.document_name,
        "document_type": document.document_type,
        "processing_status": document.processing_status,
        "file_validation": document.file_validation,
        "extracted_data": document.extracted_data,
        "validation": document.validation,
        "processing_metadata": document.processing_metadata,
        "error": error,
    }