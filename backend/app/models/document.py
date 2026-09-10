from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    document_name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    processing_status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_validation: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extracted_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    validation: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    processing_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
