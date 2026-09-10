from app.schemas.extraction import (
    InvoiceExtraction,
    FinancialStatementExtraction,
)


def test_invoice_schema():

    invoice = InvoiceExtraction(
        invoice_number={
            "value": "INV-001"
        },
        vendor_name={
            "value": "Test Supplies Pvt Ltd"
        },
        subtotal={
            "value": 150.0
        },
        total_amount={
            "value": 177.0
        },
        line_items=[
            {
                "item_code": "TS-001",
                "description": "Notebook",
                "quantity": 2,
                "unit_price": 50.0,
                "amount": 100.0,
            }
        ],
    )

    assert invoice.invoice_number.value == "INV-001"
    assert invoice.vendor_name.value == "Test Supplies Pvt Ltd"
    assert invoice.line_items[0].quantity == 2
    assert invoice.line_items[0].unit_price == 50.0
    assert invoice.line_items[0].amount == 100.0


def test_financial_statement_schema():

    statement = FinancialStatementExtraction(
        statement_title="Balance Sheet",
        company_name="Test Company",
        currency="INR",
        periods=["2024", "2023"],
        line_items=[
            {
                "name": "Total Assets",
                "value": 1000.0,
                "period": "2024",
            }
        ],
    )

    assert statement.statement_title == "Balance Sheet"
    assert statement.currency == "INR"
    assert len(statement.periods) == 2
    assert statement.line_items[0].value == 1000.0