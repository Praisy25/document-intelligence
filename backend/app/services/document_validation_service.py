from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from app.core.config import settings


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


class DocumentValidationError(Exception):
    """Raised when an uploaded document fails validation."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_extension(filename: str) -> bool:
    """
    Check whether the file has a supported extension.
    """

    extension = Path(filename).suffix.lower()

    return extension in SUPPORTED_EXTENSIONS


def validate_mime_type(
    content_type: str | None,
) -> bool:
    """
    Check whether the uploaded MIME type is supported.
    """

    return content_type in SUPPORTED_MIME_TYPES


def validate_file_not_empty(
    file_bytes: bytes,
) -> None:
    """
    Reject empty files.
    """

    if not file_bytes:

        raise DocumentValidationError(
            code="EMPTY_FILE",
            message="The uploaded file is empty.",
        )


def validate_file_size(
    file_bytes: bytes,
) -> None:
    """
    Reject files larger than the configured
    maximum upload size.
    """

    max_size_bytes = (
        settings.max_file_size_mb
        * 1024
        * 1024
    )

    actual_size_bytes = len(file_bytes)

    if actual_size_bytes > max_size_bytes:

        actual_size_mb = (
            actual_size_bytes
            / (1024 * 1024)
        )

        raise DocumentValidationError(
            code="FILE_SIZE_LIMIT_EXCEEDED",
            message=(
                f"File size is "
                f"{actual_size_mb:.2f} MB. "
                f"Maximum allowed size is "
                f"{settings.max_file_size_mb} MB."
            ),
        )


def validate_pdf(
    file_path: str,
) -> int:
    """
    Validate PDF readability/integrity
    and return page count.
    """

    try:

        reader = PdfReader(file_path)

        if reader.is_encrypted:

            try:

                reader.decrypt("")

            except Exception:

                raise DocumentValidationError(
                    code="CORRUPTED_FILE",
                    message=(
                        "The PDF is encrypted "
                        "or cannot be read."
                    ),
                )

        page_count = len(reader.pages)

        if page_count == 0:

            raise DocumentValidationError(
                code="CORRUPTED_FILE",
                message=(
                    "The PDF contains no "
                    "readable pages."
                ),
            )

        if page_count > settings.max_pages:

            raise DocumentValidationError(
                code="PAGE_LIMIT_EXCEEDED",
                message=(
                    "Documents must contain "
                    f"no more than "
                    f"{settings.max_pages} pages."
                ),
            )

        return page_count

    except DocumentValidationError:
        raise

    except Exception:

        raise DocumentValidationError(
            code="CORRUPTED_FILE",
            message=(
                "The PDF is corrupted "
                "or cannot be read."
            ),
        )


def validate_image(
    file_path: str,
) -> int:
    """
    Validate JPG/PNG readability.

    Images represent one page.
    """

    try:

        with Image.open(file_path) as image:

            image.verify()

        return 1

    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
    ):

        raise DocumentValidationError(
            code="CORRUPTED_FILE",
            message=(
                "The image is corrupted "
                "or cannot be read."
            ),
        )


def validate_document(
    file_path: str,
    filename: str,
    content_type: str | None,
    file_bytes: bytes,
) -> dict:
    """
    Main document validation function.

    Validation order:

    1. Extension
    2. MIME type
    3. Empty file
    4. File size
    5. File integrity
    6. Page count
    """

    # ---------------------------------------------------------
    # 1. Extension validation
    # ---------------------------------------------------------

    if not validate_extension(filename):

        raise DocumentValidationError(
            code="UNSUPPORTED_FILE_TYPE",
            message=(
                "Only PDF / JPG / PNG "
                "documents are supported."
            ),
        )

    # ---------------------------------------------------------
    # 2. MIME type validation
    # ---------------------------------------------------------

    if not validate_mime_type(content_type):

        raise DocumentValidationError(
            code="UNSUPPORTED_FILE_TYPE",
            message=(
                "Only PDF / JPG / PNG "
                "documents are supported."
            ),
        )

    # ---------------------------------------------------------
    # 3. Empty file validation
    # ---------------------------------------------------------

    validate_file_not_empty(file_bytes)

    # ---------------------------------------------------------
    # 4. File size validation
    # ---------------------------------------------------------

    validate_file_size(file_bytes)

    # ---------------------------------------------------------
    # 5. Determine file extension
    # ---------------------------------------------------------

    extension = Path(
        filename
    ).suffix.lower()

    # ---------------------------------------------------------
    # 6. Actual file validation
    # ---------------------------------------------------------

    if extension == ".pdf":

        page_count = validate_pdf(
            file_path
        )

    else:

        page_count = validate_image(
            file_path
        )

    # ---------------------------------------------------------
    # 7. Successful validation
    # ---------------------------------------------------------

    return {
        "file_type": content_type,

        "is_supported": True,

        "is_readable": True,

        "page_count": page_count,

        "status": "PASS",
    }