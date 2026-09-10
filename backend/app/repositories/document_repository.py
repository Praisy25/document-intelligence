from sqlalchemy.orm import Session

from app.models.document import Document


def create_document(db: Session, **kwargs) -> Document:
    document = Document(**kwargs)

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_all_documents(db: Session):
    return (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .all()
    )


def get_latest_by_name(
    db: Session,
    document_name: str,
):
    return (
        db.query(Document)
        .filter(Document.document_name == document_name)
        .order_by(Document.created_at.desc())
        .first()
    )


def get_by_id(
    db: Session,
    document_id: int,
):
    return (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )
