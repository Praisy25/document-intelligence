import json
from pathlib import Path

from app.core.database import SessionLocal
from app.models.document import Document


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "sample_outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def document_to_response(document: Document) -> dict:
    return {
        "document_name": document.document_name,
        "document_type": document.document_type,
        "processing_status": document.processing_status,
        "file_validation": document.file_validation,
        "extracted_data": document.extracted_data,
        "validation": document.validation,
        "processing_metadata": document.processing_metadata,
        "error": (
            {
                "code": document.processing_metadata.get("error_code"),
                "message": document.processing_metadata.get("error_message"),
            }
            if document.processing_status == "FAILED"
            and document.processing_metadata
            else None
        ),
    }


def save_json(filename: str, data: dict):
    output_path = OUTPUT_DIR / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Created: {output_path}")


def get_latest_successful(db, document_type: str):
    return (
        db.query(Document)
        .filter(
            Document.document_type == document_type,
            Document.processing_status == "EXTRACTED",
        )
        .order_by(Document.created_at.desc())
        .first()
    )


def get_latest_scanned_invoice(db):
    return (
        db.query(Document)
        .filter(
            Document.document_name == "scanned_invoice_test.png",
            Document.processing_status == "EXTRACTED",
        )
        .order_by(Document.created_at.desc())
        .first()
    )


def get_latest_failure(db, filename: str):
    return (
        db.query(Document)
        .filter(
            Document.document_name == filename,
            Document.processing_status == "FAILED",
        )
        .order_by(Document.created_at.desc())
        .first()
    )


def main():

    db = SessionLocal()

    try:

        # --------------------------------------------------
        # Invoice
        # --------------------------------------------------

        invoice = get_latest_successful(
            db,
            "invoice",
        )

        if invoice:
            save_json(
                "invoice.json",
                document_to_response(invoice),
            )

        # --------------------------------------------------
        # Balance Sheet
        # --------------------------------------------------

        balance_sheet = get_latest_successful(
            db,
            "balance_sheet",
        )

        if balance_sheet:
            save_json(
                "balance_sheet.json",
                document_to_response(balance_sheet),
            )

        # --------------------------------------------------
        # Profit & Loss
        # --------------------------------------------------

        profit_loss = get_latest_successful(
            db,
            "profit_and_loss",
        )

        if profit_loss:
            save_json(
                "profit_and_loss.json",
                document_to_response(profit_loss),
            )

        # --------------------------------------------------
        # Cash Flow Statement
        # --------------------------------------------------

        cash_flow = get_latest_successful(
            db,
            "cash_flow_statement",
        )

        if cash_flow:
            save_json(
                "cash_flow_statement.json",
                document_to_response(cash_flow),
            )

        # --------------------------------------------------
        # Scanned Invoice
        # --------------------------------------------------

        scanned_invoice = get_latest_scanned_invoice(db)

        if scanned_invoice:
            save_json(
                "scanned_invoice.json",
                document_to_response(scanned_invoice),
            )

        # --------------------------------------------------
        # Unsupported file failure
        # --------------------------------------------------

        unsupported = get_latest_failure(
            db,
            "unsupported_document.docx",
        )

        if unsupported:
            save_json(
                "failure_unsupported_file.json",
                document_to_response(unsupported),
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
