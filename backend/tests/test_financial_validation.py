from app.services.financial_validation_service import (
    validate_financial_document,
)


def test_invoice_validation_pass():

    data = {
        "subtotal": 150.0,
        "tax_amount": 27.0,
        "discount": 0.0,
        "total_amount": 177.0,
        "line_items": [
            {
                "item_code": "TS-001",
                "description": "Notebook",
                "quantity": 2,
                "unit_price": 50.0,
                "amount": 100.0,
            },
            {
                "item_code": "TS-002",
                "description": "Pen",
                "quantity": 5,
                "unit_price": 10.0,
                "amount": 50.0,
            },
        ],
    }

    result = validate_financial_document(
        document_type="invoice",
        data=data,
    )

    assert result["overall_status"] == "PASS"
    assert result["failed_checks"] == 0
    assert result["passed_checks"] == 4


def test_invoice_validation_failure():

    data = {
        "subtotal": 150.0,
        "tax_amount": 27.0,
        "discount": 0.0,
        "total_amount": 200.0,
        "line_items": [
            {
                "item_code": "TS-001",
                "description": "Notebook",
                "quantity": 2,
                "unit_price": 50.0,
                "amount": 100.0,
            },
            {
                "item_code": "TS-002",
                "description": "Pen",
                "quantity": 5,
                "unit_price": 10.0,
                "amount": 50.0,
            },
        ],
    }

    result = validate_financial_document(
        document_type="invoice",
        data=data,
    )

    assert result["overall_status"] == "FAIL"
    assert result["failed_checks"] > 0


def test_cash_flow_validation_pass():

    data = {
        "periods": ["2024"],

        "line_items": [
            {
                "name": "Net cash flows from operating activities",
                "value": 100.0,
                "period": "2024",
            },
            {
                "name": "Net cash flow from / (used) in investing activities",
                "value": -20.0,
                "period": "2024",
            },
            {
                "name": "Net cash flow (used) / from financing activities",
                "value": -30.0,
                "period": "2024",
            },
            {
                "name": "Effect of fluctuation in foreign currency translation reserve",
                "value": 0.0,
                "period": "2024",
            },
            {
                "name": "Net increase in cash and cash equivalents",
                "value": 50.0,
                "period": "2024",
            },
            {
                "name": "Cash and cash equivalents at the beginning of the year",
                "value": 100.0,
                "period": "2024",
            },
            {
                "name": "Cash and cash equivalents at the end of the year",
                "value": 150.0,
                "period": "2024",
            },
        ],
    }

    result = validate_financial_document(
        document_type="cash_flow_statement",
        data=data,
    )

    assert result["overall_status"] == "PASS"
    assert result["failed_checks"] == 0
    assert result["passed_checks"] == 2