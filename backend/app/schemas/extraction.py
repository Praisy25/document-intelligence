from typing import Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """
    Evidence supporting an extracted value.
    """

    source_text: Optional[str] = None
    page_number: Optional[int] = None


class ExtractedField(BaseModel):
    """
    Generic extracted field.

    Value can be text, integer, or decimal.
    If the information is missing or unreadable, value must be null.
    """

    value: Optional[str | float | int] = None
    evidence: Optional[Evidence] = None


class LineItem(BaseModel):
    """
    Invoice / receipt line item.
    """

    item_code: Optional[str] = None

    description: Optional[str] = None

    quantity: Optional[float] = None

    unit_price: Optional[float] = None

    amount: Optional[float] = None

    evidence: Optional[Evidence] = None


class InvoiceExtraction(BaseModel):
    """
    Structured invoice / receipt extraction.
    """

    invoice_number: ExtractedField = Field(
        default_factory=ExtractedField
    )

    invoice_date: ExtractedField = Field(
        default_factory=ExtractedField
    )

    vendor_name: ExtractedField = Field(
        default_factory=ExtractedField
    )

    customer_name: ExtractedField = Field(
        default_factory=ExtractedField
    )

    currency: ExtractedField = Field(
        default_factory=ExtractedField
    )

    subtotal: ExtractedField = Field(
        default_factory=ExtractedField
    )

    tax_rate: ExtractedField = Field(
        default_factory=ExtractedField
    )

    tax_amount: ExtractedField = Field(
        default_factory=ExtractedField
    )

    discount: ExtractedField = Field(
        default_factory=ExtractedField
    )

    total_amount: ExtractedField = Field(
        default_factory=ExtractedField
    )

    cash_received: ExtractedField = Field(
        default_factory=ExtractedField
    )

    change_amount: ExtractedField = Field(
        default_factory=ExtractedField
    )

    total_items: ExtractedField = Field(
        default_factory=ExtractedField
    )

    total_quantity: ExtractedField = Field(
        default_factory=ExtractedField
    )

    line_items: list[LineItem] = Field(
        default_factory=list
    )


class FinancialLineItem(BaseModel):
    """
    Financial statement row.
    """

    name: str

    value: Optional[float] = None

    period: Optional[str] = None

    evidence: Optional[Evidence] = None


class FinancialStatementExtraction(BaseModel):
    """
    Balance sheet / P&L / cash flow extraction.
    """

    statement_title: Optional[str] = None

    company_name: Optional[str] = None

    currency: Optional[str] = None

    periods: list[str] = Field(
        default_factory=list
    )

    line_items: list[FinancialLineItem] = Field(
        default_factory=list
    )