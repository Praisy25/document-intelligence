import io
import logging
import re
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, ImageFilter, ImageOps
from pytesseract import Output


logger = logging.getLogger(__name__)


class OCRProcessingError(Exception):
    """
    Raised when OCR or text extraction fails.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


MIN_TEXT_LENGTH = 30
PDF_RENDER_SCALE = 4

OCR_CONFIGS = [
    "--psm 6",
    "--psm 4",
    "--psm 11",
]


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def _preprocess_image(image: Image.Image) -> Image.Image:
    """
    Prepare an image for OCR.

    Keeps preprocessing intentionally moderate so that
    table structure and small characters are not destroyed.
    """

    image = ImageOps.grayscale(image)

    image = ImageOps.autocontrast(
        image,
        cutoff=1,
    )

    image = image.resize(
        (
            image.width * 2,
            image.height * 2,
        ),
        Image.Resampling.LANCZOS,
    )

    image = image.filter(
        ImageFilter.SHARPEN
    )

    image = image.filter(
        ImageFilter.UnsharpMask(
            radius=1,
            percent=120,
            threshold=3,
        )
    )

    return image


# ============================================================
# OCR CONFIDENCE
# ============================================================

def _calculate_confidence(
    image: Image.Image,
    config: str,
) -> float:
    """
    Calculate average Tesseract OCR confidence.
    """

    try:
        data = pytesseract.image_to_data(
            image,
            config=config,
            output_type=Output.DICT,
        )

        confidences = []

        for confidence in data.get("conf", []):
            try:
                value = float(confidence)

                if value >= 0:
                    confidences.append(value)

            except (TypeError, ValueError):
                continue

        if not confidences:
            return 0.0

        return round(
            sum(confidences) / len(confidences),
            2,
        )

    except Exception as exc:
        logger.warning(
            "[OCR] Confidence calculation failed: %s",
            exc,
        )

        return 0.0


# ============================================================
# OCR STRUCTURE SCORING
# ============================================================

def _normalize_text(text: str) -> str:
    """
    Normalize whitespace while preserving lines.
    """

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def _candidate_score(
    text: str,
    confidence: float,
) -> float:
    """
    Score OCR output based on information preservation.

    Confidence alone is not sufficient because a high-confidence
    OCR result can still lose table rows.

    This score rewards:
    - item codes
    - numeric values
    - table-like lines
    - invoice/financial keywords
    - overall OCR confidence
    """

    if not text:
        return -1000.0

    text = _normalize_text(text)

    lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ]

    lower_text = text.lower()

    # --------------------------------------------------------
    # Numeric tokens
    # --------------------------------------------------------

    numeric_tokens = re.findall(
        r"(?<!\w)-?\d+(?:[.,]\d+)*",
        text,
    )

    # --------------------------------------------------------
    # Item codes
    # Example: TS-001, ITEM-123
    # --------------------------------------------------------

    item_codes = re.findall(
        r"\b[A-Z]{1,10}[-_]\d{2,}\b",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Financial/document keywords
    # --------------------------------------------------------

    keywords = [
        "invoice",
        "invoice no",
        "date",
        "vendor",
        "customer",
        "item",
        "description",
        "qty",
        "quantity",
        "price",
        "amount",
        "subtotal",
        "tax",
        "total",
        "cash",
        "change",
        "balance",
        "assets",
        "liabilities",
        "capital",
        "income",
        "expense",
        "profit",
        "loss",
        "cash flow",
        "operating",
        "investing",
        "financing",
    ]

    keyword_hits = sum(
        1
        for keyword in keywords
        if keyword in lower_text
    )

    # --------------------------------------------------------
    # Numeric/table lines
    # --------------------------------------------------------

    numeric_lines = 0

    for line in lines:

        numbers = re.findall(
            r"(?<!\w)-?\d+(?:[.,]\d+)*",
            line,
        )

        if len(numbers) >= 2:
            numeric_lines += 1

    # --------------------------------------------------------
    # Item-code lines
    # --------------------------------------------------------

    item_code_lines = 0

    for line in lines:

        if re.search(
            r"\b[A-Z]{1,10}[-_]\d{2,}\b",
            line,
            flags=re.IGNORECASE,
        ):
            item_code_lines += 1

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

    score = (
        confidence * 0.35
        + min(len(lines), 30) * 1.5
        + min(len(numeric_tokens), 40) * 2.0
        + min(len(item_codes), 10) * 8.0
        + min(keyword_hits, 15) * 2.0
        + min(numeric_lines, 15) * 5.0
        + min(item_code_lines, 10) * 12.0
    )

    return round(
        score,
        2,
    )


# ============================================================
# RUN ONE OCR CANDIDATE
# ============================================================

def _run_candidate(
    image: Image.Image,
    config: str,
    source: str,
) -> dict:
    """
    Run Tesseract using one page segmentation mode.
    """

    text = pytesseract.image_to_string(
        image,
        config=config,
    ).strip()

    text = _normalize_text(text)

    confidence = _calculate_confidence(
        image,
        config,
    )

    score = _candidate_score(
        text,
        confidence,
    )

    logger.info(
        "[OCR %s] %s | %d chars | %.2f confidence",
        source.upper(),
        config,
        len(text),
        confidence,
    )

    logger.info(
        "[OCR %s PREVIEW]\n%s",
        source.upper(),
        text[:2000],
    )

    logger.info(
        "[OCR %s] %s score: %.2f",
        source.upper(),
        config,
        score,
    )

    return {
        "text": text,
        "confidence": confidence,
        "config": config,
        "source": source,
        "score": score,
    }


# ============================================================
# RUN MULTIPLE OCR MODES
# ============================================================

def run_ocr(
    image: Image.Image,
    source: str,
) -> dict:
    """
    Run several Tesseract configurations and select
    the candidate with the best information-preservation score.
    """

    candidates = []

    for config in OCR_CONFIGS:

        try:

            candidate = _run_candidate(
                image=image,
                config=config,
                source=source,
            )

            candidates.append(candidate)

        except Exception as exc:

            logger.warning(
                "[OCR %s] %s failed: %s",
                source.upper(),
                config,
                exc,
            )

    if not candidates:

        raise OCRProcessingError(
            f"OCR failed for source: {source}"
        )

    selected = max(
        candidates,
        key=lambda candidate: candidate["score"],
    )

    logger.info(
        "[OCR %s] Selected config: %s",
        source.upper(),
        selected["config"],
    )

    logger.info(
        "[OCR %s] Selected confidence: %.2f",
        source.upper(),
        selected["confidence"],
    )

    logger.info(
        "[OCR %s] Selected score: %.2f",
        source.upper(),
        selected["score"],
    )

    return selected


# ============================================================
# PDF NATIVE TEXT
# ============================================================

def extract_text_from_pdf(
    file_bytes: bytes,
) -> tuple[str, bool]:
    """
    Try native PDF text extraction first.

    If the PDF contains insufficient native text,
    fall back to OCR.
    """

    try:

        pdf = fitz.open(
            stream=file_bytes,
            filetype="pdf",
        )

        native_pages = []

        for page in pdf:

            page_text = page.get_text(
                "text"
            ).strip()

            native_pages.append(
                page_text
            )

        native_text = "\n\n".join(
            native_pages
        ).strip()

        logger.info(
            "[PDF] Native text length: %d",
            len(native_text),
        )

        # Native PDF text is good enough.
        if len(native_text) >= MIN_TEXT_LENGTH:

            return (
                native_text,
                False,
            )

        logger.info(
            "[PDF] Native text insufficient. "
            "Falling back to OCR."
        )

        result = ocr_pdf(
            file_bytes
        )

        return (
            result["text"],
            True,
        )

    except Exception as exc:

        logger.exception(
            "[PDF] Extraction failed: %s",
            exc,
        )

        raise OCRProcessingError(
            f"PDF extraction failed: {exc}"
        )


# ============================================================
# PDF OCR
# ============================================================

def ocr_pdf(
    file_bytes: bytes,
) -> dict:
    """
    Render each PDF page and perform OCR.

    Page numbers are preserved.
    """

    try:

        pdf = fitz.open(
            stream=file_bytes,
            filetype="pdf",
        )

        page_results = []

        for page_index, page in enumerate(pdf):

            page_number = page_index + 1

            logger.info(
                "[OCR PDF] Processing page %d",
                page_number,
            )

            matrix = fitz.Matrix(
                PDF_RENDER_SCALE,
                PDF_RENDER_SCALE,
            )

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            image_bytes = pixmap.tobytes(
                "png"
            )

            image = Image.open(
                io.BytesIO(image_bytes)
            ).convert("RGB")

            processed_image = (
                _preprocess_image(image)
            )

            original_result = run_ocr(
                image,
                source=(
                    f"pdf-page-{page_number}-original"
                ),
            )

            processed_result = run_ocr(
                processed_image,
                source=(
                    f"pdf-page-{page_number}-processed"
                ),
            )

            selected = max(
                [
                    original_result,
                    processed_result,
                ],
                key=lambda candidate: candidate["score"],
            )

            page_results.append(
                {
                    "page_number": page_number,
                    "text": selected["text"],
                    "confidence": selected["confidence"],
                    "config": selected["config"],
                    "source": selected["source"],
                    "score": selected["score"],
                }
            )

            logger.info(
                "[OCR PDF] Page %d selected: %s",
                page_number,
                selected["config"],
            )

        combined_text = "\n\n".join(
            page["text"]
            for page in page_results
            if page["text"]
        ).strip()

        return {
            "text": combined_text,
            "pages": page_results,
        }

    except OCRProcessingError:
        raise

    except Exception as exc:

        logger.exception(
            "[OCR PDF] OCR failed: %s",
            exc,
        )

        raise OCRProcessingError(
            f"PDF OCR failed: {exc}"
        )


# ============================================================
# IMAGE OCR
# ============================================================

def ocr_image(
    file_bytes: bytes,
) -> dict:
    """
    OCR PNG/JPG/JPEG documents.

    Both original and preprocessed images are tested.
    """

    try:

        image = Image.open(
            io.BytesIO(file_bytes)
        )

        image = ImageOps.exif_transpose(
            image
        )

        if image.mode not in {
            "RGB",
            "L",
        }:
            image = image.convert(
                "RGB"
            )

        logger.info(
            "[OCR IMAGE] Original size: %s",
            image.size,
        )

        # ----------------------------------------------------
        # Original image
        # ----------------------------------------------------

        logger.info(
            "[OCR IMAGE] Running OCR on original image."
        )

        original_result = run_ocr(
            image,
            source="original",
        )

        # ----------------------------------------------------
        # Preprocessed image
        # ----------------------------------------------------

        processed_image = (
            _preprocess_image(image)
        )

        logger.info(
            "[OCR IMAGE] Processed size: %s",
            processed_image.size,
        )

        logger.info(
            "[OCR IMAGE] Running OCR on preprocessed image."
        )

        processed_result = run_ocr(
            processed_image,
            source="processed",
        )

        # ----------------------------------------------------
        # Select best candidate
        # ----------------------------------------------------

        selected = max(
            [
                original_result,
                processed_result,
            ],
            key=lambda candidate: candidate["score"],
        )

        logger.info(
            "[OCR IMAGE] Selected source: %s",
            selected["source"],
        )

        logger.info(
            "[OCR IMAGE] Selected config: %s",
            selected["config"],
        )

        logger.info(
            "[OCR IMAGE] Selected confidence: %.2f",
            selected["confidence"],
        )

        logger.info(
            "[OCR IMAGE] Selected score: %.2f",
            selected["score"],
        )

        logger.info(
            "[OCR IMAGE] Final text length: %d",
            len(selected["text"]),
        )

        logger.info(
            "[OCR IMAGE FINAL PREVIEW]\n%s",
            selected["text"][:3000],
        )

        return {
            "text": selected["text"],
            "pages": [
                {
                    "page_number": 1,
                    "text": selected["text"],
                    "confidence": selected["confidence"],
                    "config": selected["config"],
                    "source": selected["source"],
                    "score": selected["score"],
                }
            ],
        }

    except OCRProcessingError:
        raise

    except Exception as exc:

        logger.exception(
            "[OCR IMAGE] OCR failed: %s",
            exc,
        )

        raise OCRProcessingError(
            f"Image OCR failed: {exc}"
        )


# ============================================================
# MAIN FUNCTION
# ============================================================

def extract_text(
    file_path: str,
) -> dict:
    """
    Main OCR/text extraction function.

    IMPORTANT:
    This function follows the contract expected by
    document_service.py:

        result = extract_text(file_path)

        result["text"]
        result["ocr_used"]

    Returns:
        {
            "text": str,
            "ocr_used": bool
        }
    """

    path = Path(
        file_path
    )

    extension = path.suffix.lower()

    logger.info(
        "[EXTRACT TEXT] Processing: %s",
        path,
    )

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------

    try:

        file_bytes = path.read_bytes()

    except Exception as exc:

        logger.exception(
            "[EXTRACT TEXT] Could not read file: %s",
            exc,
        )

        raise OCRProcessingError(
            f"Could not read document: {exc}"
        )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if extension == ".pdf":

        text, ocr_used = (
            extract_text_from_pdf(
                file_bytes
            )
        )

        return {
            "text": text,
            "ocr_used": ocr_used,
        }

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    if extension in {
        ".jpg",
        ".jpeg",
        ".png",
    }:

        result = ocr_image(
            file_bytes
        )

        return {
            "text": result["text"],
            "ocr_used": True,
        }

    # --------------------------------------------------------
    # Unsupported
    # --------------------------------------------------------

    raise OCRProcessingError(
        f"Unsupported file extension: {extension}"
    )