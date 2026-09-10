from typing import Any

from pydantic import BaseModel


class FileValidation(BaseModel):
    """
    Result of validating the uploaded file.
    """

    file_type: str

    is_supported: bool

    is_readable: bool

    page_count: int | None = None

    status: str


class ProcessingError(BaseModel):
    """
    Structured processing error.
    """

    code: str

    message: str


class DocumentResponse(BaseModel):
    """
    Response returned by document APIs.
    """

    document_name: str

    document_type: str

    processing_status: str

    file_validation: FileValidation | None = None

    extracted_data: dict[str, Any] | None = None

    validation: dict[str, Any] | None = None

    processing_metadata: dict[str, Any] | None = None

    error: ProcessingError | None = None