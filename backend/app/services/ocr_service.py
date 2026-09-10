from pathlib import Path
import logging

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps, ImageFilter


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

MIN_TEXT_LENGTH = 30

# Higher resolution improves OCR accuracy for scanned documents.
PDF_RENDER_SCALE = 4

# OCR configurations.
#
# PSM 6:
# Treat the image as a uniform block of text.
# Usually best for invoices/tables.
#
# PSM 4:
# Assume a single column of text.
#
# PSM 11:
# Sparse text detection.
OCR_CONFIGS = [
    "--psm 6",
    "--psm 4",
    "--psm 11",
]


# ============================================================
# EXCEPTIONS
# ============================================================

class OCRProcessingError(Exception):
    """Raised when text extraction or OCR fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess an image to improve OCR accuracy.

    Steps:
    1. Convert to grayscale.
    2. Improve contrast.
    3. Upscale 2x.
    4. Sharpen.
    5. Apply mild unsharp masking.

    Important:
    We do NOT modify the actual financial text.
    """

    # Convert to grayscale.
    processed = ImageOps.grayscale(image)

    # Improve contrast.
    processed = ImageOps.autocontrast(
        processed,
        cutoff=1,
    )

    # Upscale 2x.
    processed = processed.resize(
        (
            processed.width * 2,
            processed.height * 2,
        ),
        Image.Resampling.LANCZOS,
    )

    # Sharpen.
    processed = processed.filter(
        ImageFilter.SHARPEN
    )

    # Mild additional sharpening.
    processed = processed.filter(
        ImageFilter.UnsharpMask(
            radius=1,
            percent=150,
            threshold=3,
        )
    )

    return processed


# ============================================================
# OCR CONFIDENCE
# ============================================================

def calculate_ocr_confidence(
    image: Image.Image,
    config: str,
) -> float:
    """
    Calculate average OCR confidence using Tesseract.

    Tesseract returns confidence values per detected word.
    We average valid confidence values.
    """

    try:
        data = pytesseract.image_to_data(
            image,
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        confidences = []

        for confidence in data["conf"]:
            try:
                value = float(confidence)

                if value >= 0:
                    confidences.append(value)

            except (TypeError, ValueError):
                continue

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)

    except Exception:
        return 0.0


# ============================================================
# RUN OCR
# ============================================================

def run_ocr(
    image: Image.Image,
    label: str,
) -> dict:
    """
    Run OCR using multiple Tesseract configurations.

    Returns the best OCR candidate.

    For structured financial documents, PSM 6 is preferred because
    it usually preserves table rows and columns better.
    """

    candidates = []

    for config in OCR_CONFIGS:

        try:
            text = pytesseract.image_to_string(
                image,
                config=config,
            ).strip()

            confidence = calculate_ocr_confidence(
                image,
                config,
            )

            logger.info(
                "[OCR %s] %s | %s chars | %.2f confidence",
                label,
                config,
                len(text),
                confidence,
            )

            logger.info(
                "[OCR %s PREVIEW]\n%s",
                label,
                text[:1000],
            )

            candidates.append(
                {
                    "text": text,
                    "confidence": confidence,
                    "config": config,
                }
            )

        except Exception as exc:

            logger.warning(
                "[OCR %s] %s failed: %s",
                label,
                config,
                str(exc),
            )

    if not candidates:
        raise OCRProcessingError(
            f"OCR failed for {label}: no OCR candidates were produced."
        )

    # --------------------------------------------------------
    # IMPORTANT SELECTION LOGIC
    # --------------------------------------------------------
    #
    # For invoices and financial documents, confidence alone
    # is NOT enough.
    #
    # In the user's test:
    #
    # PSM 6  -> 91.72 confidence -> preserves Qty 2 and 5
    # PSM 4  -> 91.33 confidence -> preserves Qty 2 and 5
    # PSM 11 -> 92.05 confidence -> loses Qty 2 and 5
    #
    # Therefore we prioritize PSM 6, then PSM 4, then PSM 11.
    # Within the same preferred configuration, confidence is used.
    # --------------------------------------------------------

    preferred_psm_order = {
        "--psm 6": 3,
        "--psm 4": 2,
        "--psm 11": 1,
    }

    # First remove completely empty results.
    non_empty_candidates = [
        candidate
        for candidate in candidates
        if candidate["text"].strip()
    ]

    if not non_empty_candidates:
        raise OCRProcessingError(
            f"OCR failed for {label}: OCR returned no readable text."
        )

    best_result = max(
        non_empty_candidates,
        key=lambda item: (
            preferred_psm_order.get(
                item["config"],
                0,
            ),
            item["confidence"],
            len(item["text"]),
        ),
    )

    logger.info(
        "[OCR %s] Selected config: %s",
        label,
        best_result["config"],
    )

    logger.info(
        "[OCR %s] Selected confidence: %.2f",
        label,
        best_result["confidence"],
    )

    return best_result


# ============================================================
# PDF NATIVE TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(
    file_path: str,
) -> dict:
    """
    Extract native text from a PDF.

    Every page is processed.

    If the combined native text is too short,
    OCR is performed on the PDF pages.
    """

    pdf = None

    try:

        pdf = fitz.open(file_path)

        pages = []
        combined_text_parts = []

        for page_number, page in enumerate(
            pdf,
            start=1,
        ):

            text = page.get_text(
                "text"
            ).strip()

            logger.info(
                "[PDF TEXT] Page %s: %s characters extracted directly",
                page_number,
                len(text),
            )

            logger.info(
                "[PDF TEXT PREVIEW] Page %s:\n%s",
                page_number,
                text[:1000],
            )

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "ocr_used": False,
                }
            )

            if text:
                combined_text_parts.append(text)

        combined_text = "\n".join(
            combined_text_parts
        ).strip()

        logger.info(
            "[PDF TEXT] Total native text length: %s",
            len(combined_text),
        )

        # If enough native text exists, use it.
        if len(combined_text) >= MIN_TEXT_LENGTH:

            return {
                "text": combined_text,
                "pages": pages,
                "ocr_used": False,
            }

        logger.info(
            "[PDF TEXT] Insufficient native text. Falling back to OCR."
        )

        return ocr_pdf(file_path)

    except OCRProcessingError:
        raise

    except Exception as exc:

        logger.exception(
            "Failed to extract text from PDF."
        )

        raise OCRProcessingError(
            f"Failed to extract text from PDF: {str(exc)}"
        )

    finally:

        if pdf is not None:
            pdf.close()


# ============================================================
# OCR PDF
# ============================================================

def ocr_pdf(
    file_path: str,
) -> dict:
    """
    Render each PDF page as an image and perform OCR.

    Each page is processed independently.
    """

    pdf = None

    try:

        pdf = fitz.open(file_path)

        pages = []
        combined_text_parts = []

        for page_number, page in enumerate(
            pdf,
            start=1,
        ):

            logger.info(
                "[OCR PDF] Processing page %s",
                page_number,
            )

            # Render PDF page at high resolution.
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(
                    PDF_RENDER_SCALE,
                    PDF_RENDER_SCALE,
                ),
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                [
                    pixmap.width,
                    pixmap.height,
                ],
                pixmap.samples,
            )

            logger.info(
                "[OCR PDF] Page %s original size: %s",
                page_number,
                image.size,
            )

            # Preprocess.
            processed_image = preprocess_image(
                image
            )

            logger.info(
                "[OCR PDF] Page %s processed size: %s",
                page_number,
                processed_image.size,
            )

            result = run_ocr(
                processed_image,
                f"PDF PAGE {page_number}",
            )

            text = result["text"].strip()

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "ocr_used": True,
                }
            )

            if text:
                combined_text_parts.append(text)

        combined_text = "\n\n".join(
            combined_text_parts
        ).strip()

        logger.info(
            "[OCR PDF] Final text length: %s",
            len(combined_text),
        )

        logger.info(
            "[OCR PDF FINAL PREVIEW]\n%s",
            combined_text[:2000],
        )

        if len(combined_text) < MIN_TEXT_LENGTH:

            raise OCRProcessingError(
                "OCR completed but insufficient readable text "
                "was detected in the PDF."
            )

        return {
            "text": combined_text,
            "pages": pages,
            "ocr_used": True,
        }

    except OCRProcessingError:
        raise

    except Exception as exc:

        logger.exception(
            "OCR failed for PDF."
        )

        raise OCRProcessingError(
            f"OCR failed for PDF: {str(exc)}"
        )

    finally:

        if pdf is not None:
            pdf.close()


# ============================================================
# OCR IMAGE
# ============================================================

def ocr_image(
    file_path: str,
) -> dict:
    """
    Perform OCR on JPG/JPEG/PNG images.

    Runs OCR on:
    1. Original image
    2. Preprocessed/upscaled image

    The preprocessed result is preferred because it generally
    provides better table and financial-number recognition.

    Page number is explicitly set to 1 because a standalone image
    represents one document page.
    """

    try:

        logger.info(
            "[OCR IMAGE] Processing: %s",
            file_path,
        )

        image = Image.open(
            file_path
        )

        # Ensure the image is fully loaded.
        image.load()

        # Correct camera/image orientation using EXIF data.
        image = ImageOps.exif_transpose(
            image
        )

        # Convert to RGB for consistent processing.
        image = image.convert(
            "RGB"
        )

        logger.info(
            "[OCR IMAGE] Original size: %s",
            image.size,
        )

        # ----------------------------------------------------
        # ORIGINAL IMAGE OCR
        # ----------------------------------------------------

        logger.info(
            "[OCR IMAGE] Running OCR on original image."
        )

        original_result = run_ocr(
            image,
            "ORIGINAL",
        )

        # ----------------------------------------------------
        # PREPROCESSED IMAGE OCR
        # ----------------------------------------------------

        processed_image = preprocess_image(
            image
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
            "PROCESSED",
        )

        # ----------------------------------------------------
        # SELECT BETWEEN ORIGINAL AND PROCESSED
        # ----------------------------------------------------
        #
        # For scanned documents, preprocessing is preferred
        # because the user's test demonstrates that it restores
        # decimal points and table quantities.
        #
        # We still compare confidence, but preprocessing receives
        # priority when it has meaningful readable text.
        # ----------------------------------------------------

        original_text = original_result["text"].strip()
        processed_text = processed_result["text"].strip()

        if len(processed_text) >= MIN_TEXT_LENGTH:

            selected_result = processed_result
            selected_source = "processed"

        elif len(original_text) >= MIN_TEXT_LENGTH:

            selected_result = original_result
            selected_source = "original"

        else:

            # Both results are too short.
            # Select the one with higher confidence only so that
            # the error message can contain the most useful output.

            if (
                processed_result["confidence"]
                >= original_result["confidence"]
            ):
                selected_result = processed_result
                selected_source = "processed"
            else:
                selected_result = original_result
                selected_source = "original"

        final_text = selected_result["text"].strip()

        logger.info(
            "[OCR IMAGE] Selected source: %s",
            selected_source,
        )

        logger.info(
            "[OCR IMAGE] Selected config: %s",
            selected_result["config"],
        )

        logger.info(
            "[OCR IMAGE] Selected confidence: %.2f",
            selected_result["confidence"],
        )

        logger.info(
            "[OCR IMAGE] Final text length: %s",
            len(final_text),
        )

        logger.info(
            "[OCR IMAGE FINAL PREVIEW]\n%s",
            final_text[:2000],
        )

        if len(final_text) < MIN_TEXT_LENGTH:

            raise OCRProcessingError(
                "OCR completed but insufficient readable text "
                "was detected in the image."
            )

        return {
            "text": final_text,
            "pages": [
                {
                    "page_number": 1,
                    "text": final_text,
                    "ocr_used": True,
                }
            ],
            "ocr_used": True,
        }

    except OCRProcessingError:
        raise

    except Exception as exc:

        logger.exception(
            "OCR failed for image."
        )

        raise OCRProcessingError(
            f"OCR failed for image: {str(exc)}"
        )


# ============================================================
# MAIN TEXT EXTRACTION DISPATCHER
# ============================================================

def extract_text(
    file_path: str,
) -> dict:
    """
    Extract text from a supported document.

    PDF:
        Native text extraction first.
        OCR fallback if necessary.

    JPG/JPEG/PNG:
        OCR.
    """

    extension = Path(
        file_path
    ).suffix.lower()

    logger.info(
        "[TEXT EXTRACTION] File extension: %s",
        extension,
    )

    if extension == ".pdf":

        return extract_text_from_pdf(
            file_path
        )

    if extension in {
        ".jpg",
        ".jpeg",
        ".png",
    }:

        return ocr_image(
            file_path
        )

    raise OCRProcessingError(
        f"Unsupported file format for text extraction: {extension}"
    )