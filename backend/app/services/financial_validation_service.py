from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TOLERANCE = 1.0


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_name(name: Any) -> str:
    """
    Normalize a financial statement row name so that
    small formatting differences do not affect matching.
    """

    if name is None:
        return ""

    return (
        str(name)
        .lower()
        .replace("&", "and")
        .replace("’", "'")
        .replace("/", " ")
        .replace("-", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(":", " ")
        .replace(",", " ")
        .replace("  ", " ")
        .strip()
    )


def unwrap_value(value: Any) -> Any:
    """
    Handle Pydantic ExtractedField-like objects as well as
    normal dictionaries and primitive values.
    """

    if value is None:
        return None

    if hasattr(value, "value"):
        return value.value

    if isinstance(value, dict):
        if "value" in value:
            return value["value"]

    return value


def to_number(value: Any) -> float | None:
    """
    Convert extracted financial values into numbers.

    Handles:
    - commas
    - currency symbols
    - percentages
    - parentheses as negative numbers
    - normal negative numbers
    - dash as unavailable
    """

    value = unwrap_value(value)

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if text in {"", "-", "—", "–", "N/A", "NA", "null", "None"}:
        return None

    # Remove common currency symbols
    text = (
        text.replace("₹", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("RM", "")
        .replace("INR", "")
    )

    # Remove commas
    text = text.replace(",", "").strip()

    # Parentheses indicate negative values
    is_negative = (
        text.startswith("(")
        and text.endswith(")")
    )

    if is_negative:
        text = text[1:-1].strip()

    # Remove percentage symbol
    text = text.replace("%", "").strip()

    try:
        number = float(text)

        if is_negative:
            number = -number

        return number

    except (ValueError, TypeError):
        return None


def validation_number(value: Any) -> float | None:
    """
    Convert a value for arithmetic validation.

    Explicit dash values mean zero when the document shows
    a dash in a financial statement.
    """

    value = unwrap_value(value)

    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()

        if text in {"-", "—", "–"}:
            return 0.0

    return to_number(value)


def get_line_items(data: Any) -> list:
    """
    Safely get line_items from Pydantic or dictionary data.
    """

    if hasattr(data, "line_items"):
        return data.line_items or []

    if isinstance(data, dict):
        return data.get("line_items", []) or []

    return []


def get_periods(data: Any) -> list:
    """
    Safely get periods from Pydantic or dictionary data.
    """

    if hasattr(data, "periods"):
        return data.periods or []

    if isinstance(data, dict):
        return data.get("periods", []) or []

    return []


def get_item_name(item: Any) -> str:
    """
    Get line item name.
    """

    if hasattr(item, "name"):
        return item.name or ""

    if isinstance(item, dict):
        return item.get("name", "") or ""

    return ""


def get_item_period(item: Any) -> str | None:
    """
    Get line item period.
    """

    if hasattr(item, "period"):
        return item.period

    if isinstance(item, dict):
        return item.get("period")

    return None


def get_item_value(item: Any) -> Any:
    """
    Get line item value.
    """

    if hasattr(item, "value"):
        return item.value

    if isinstance(item, dict):
        return item.get("value")

    return None


def find_value(
    line_items: list,
    period: str | None,
    aliases: list[str],
) -> Any:
    """
    Find a financial line-item value for a specific period.

    Exact normalized matches are preferred, followed by
    partial matches.
    """

    normalized_aliases = [
        normalize_name(alias)
        for alias in aliases
    ]

    # --------------------------------------------------------
    # First pass: exact match
    # --------------------------------------------------------

    for item in line_items:

        item_period = get_item_period(item)

        if item_period != period:
            continue

        item_name = normalize_name(
            get_item_name(item)
        )

        if item_name in normalized_aliases:
            return get_item_value(item)

    # --------------------------------------------------------
    # Second pass: partial match
    # --------------------------------------------------------

    for item in line_items:

        item_period = get_item_period(item)

        if item_period != period:
            continue

        item_name = normalize_name(
            get_item_name(item)
        )

        for alias in normalized_aliases:

            if alias in item_name:
                return get_item_value(item)

    return None


def create_validation_result(
    check_name: str,
    formula: str,
    input_values: dict,
    calculated_value: float | None,
    reported_value: float | None,
    status: str,
) -> dict:
    """
    Create a consistent validation result.
    """

    variance = None

    if (
        calculated_value is not None
        and reported_value is not None
    ):
        variance = abs(
            calculated_value - reported_value
        )

    return {
        "check_name": check_name,
        "formula": formula,
        "input_values": input_values,
        "calculated_value": calculated_value,
        "reported_value": reported_value,
        "variance": variance,
        "status": status,
    }


def summarize_validations(validations: list[dict]) -> dict:
    """
    Generate overall validation summary.
    """

    total_checks = len(validations)

    passed_checks = sum(
        1
        for item in validations
        if item["status"] == "PASS"
    )

    failed_checks = sum(
        1
        for item in validations
        if item["status"] == "FAIL"
    )

    not_applicable_checks = sum(
        1
        for item in validations
        if item["status"] == "NOT_APPLICABLE"
    )

    if failed_checks > 0:
        overall_status = "FAIL"

    elif (
        total_checks > 0
        and passed_checks == total_checks
    ):
        overall_status = "PASS"

    else:
        overall_status = "NOT_APPLICABLE"

    return {
        "overall_status": overall_status,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "not_applicable_checks": not_applicable_checks,
        "validations": validations,
    }


# ============================================================
# INVOICE VALIDATION
# ============================================================

def validate_invoice(
    data: Any,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict:
    """
    Validate invoice / receipt calculations.

    Checks:
    1. Quantity × unit price ≈ line amount
    2. Sum of line amounts ≈ subtotal
       OR, when subtotal is unavailable, ≈ total
    3. Subtotal - discount + tax ≈ total
    4. Cash received - total ≈ change
    """

    validations = []

    line_items = get_line_items(data)

    # --------------------------------------------------------
    # CHECK 1: Quantity × Unit Price
    # --------------------------------------------------------

    for index, item in enumerate(line_items, start=1):

        quantity = validation_number(
            getattr(item, "quantity", None)
            if hasattr(item, "quantity")
            else item.get("quantity")
        )

        unit_price = validation_number(
            getattr(item, "unit_price", None)
            if hasattr(item, "unit_price")
            else item.get("unit_price")
        )

        amount = validation_number(
            getattr(item, "amount", None)
            if hasattr(item, "amount")
            else item.get("amount")
        )

        if (
            quantity is not None
            and unit_price is not None
            and amount is not None
        ):

            calculated = quantity * unit_price

            status = (
                "PASS"
                if abs(calculated - amount) <= tolerance
                else "FAIL"
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        f"Invoice line item {index} "
                        "quantity × unit price"
                    ),
                    formula="quantity × unit price ≈ line amount",
                    input_values={
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "reported_line_amount": amount,
                    },
                    calculated_value=calculated,
                    reported_value=amount,
                    status=status,
                )
            )

    # --------------------------------------------------------
    # Extract invoice totals
    # --------------------------------------------------------

    def get_invoice_field(field_name: str):

        if hasattr(data, field_name):
            return getattr(data, field_name)

        if isinstance(data, dict):
            return data.get(field_name)

        return None

    subtotal = validation_number(
        get_invoice_field("subtotal")
    )

    discount = validation_number(
        get_invoice_field("discount")
    )

    tax_amount = validation_number(
        get_invoice_field("tax_amount")
    )

    total_amount = validation_number(
        get_invoice_field("total_amount")
    )

    cash_received = validation_number(
        get_invoice_field("cash_received")
    )

    change_amount = validation_number(
        get_invoice_field("change_amount")
    )

    # --------------------------------------------------------
    # Calculate sum of line items
    # --------------------------------------------------------

    line_sum = 0.0
    valid_line_amounts = 0

    for item in line_items:

        amount = validation_number(
            getattr(item, "amount", None)
            if hasattr(item, "amount")
            else item.get("amount")
        )

        if amount is not None:
            line_sum += amount
            valid_line_amounts += 1

    # --------------------------------------------------------
    # CHECK 2: Line sum vs subtotal / total
    # --------------------------------------------------------

    if valid_line_amounts > 0:

        if subtotal is not None:

            calculated = line_sum

            validations.append(
                create_validation_result(
                    check_name="Invoice line items vs subtotal",
                    formula="sum(line item amounts) ≈ subtotal",
                    input_values={
                        "line_item_sum": line_sum,
                        "reported_subtotal": subtotal,
                    },
                    calculated_value=calculated,
                    reported_value=subtotal,
                    status=(
                        "PASS"
                        if abs(calculated - subtotal)
                        <= tolerance
                        else "FAIL"
                    ),
                )
            )

        elif total_amount is not None:

            calculated = line_sum

            validations.append(
                create_validation_result(
                    check_name="Invoice line items vs total",
                    formula="sum(line item amounts) ≈ total",
                    input_values={
                        "line_item_sum": line_sum,
                        "reported_total": total_amount,
                    },
                    calculated_value=calculated,
                    reported_value=total_amount,
                    status=(
                        "PASS"
                        if abs(calculated - total_amount)
                        <= tolerance
                        else "FAIL"
                    ),
                )
            )

    # --------------------------------------------------------
    # CHECK 3: Subtotal - Discount + Tax = Total
    # --------------------------------------------------------

    if (
        subtotal is not None
        and total_amount is not None
    ):

        discount_value = (
            discount
            if discount is not None
            else 0.0
        )

        tax_value = (
            tax_amount
            if tax_amount is not None
            else 0.0
        )

        calculated = (
            subtotal
            - discount_value
            + tax_value
        )

        validations.append(
            create_validation_result(
                check_name="Invoice total reconciliation",
                formula="subtotal - discount + tax ≈ total",
                input_values={
                    "subtotal": subtotal,
                    "discount": discount_value,
                    "tax_amount": tax_value,
                    "reported_total": total_amount,
                },
                calculated_value=calculated,
                reported_value=total_amount,
                status=(
                    "PASS"
                    if abs(calculated - total_amount)
                    <= tolerance
                    else "FAIL"
                ),
            )
        )

    # --------------------------------------------------------
    # CHECK 4: Cash - Total = Change
    # --------------------------------------------------------

    if (
        cash_received is not None
        and total_amount is not None
        and change_amount is not None
    ):

        calculated = (
            cash_received - total_amount
        )

        validations.append(
            create_validation_result(
                check_name="Invoice cash/change reconciliation",
                formula="cash received - total ≈ change",
                input_values={
                    "cash_received": cash_received,
                    "total_amount": total_amount,
                    "reported_change": change_amount,
                },
                calculated_value=calculated,
                reported_value=change_amount,
                status=(
                    "PASS"
                    if abs(calculated - change_amount)
                    <= tolerance
                    else "FAIL"
                ),
            )
        )

    return summarize_validations(validations)


# ============================================================
# BALANCE SHEET VALIDATION
# ============================================================

def validate_balance_sheet(
    data: Any,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict:
    """
    Validate Balance Sheet.

    Checks:
    1. Capital & liabilities components ≈ total capital
       and liabilities.
    2. Asset components ≈ total assets.
    3. Total assets ≈ total capital and liabilities.

    Checks are performed independently for every period.
    """

    line_items = get_line_items(data)
    periods = get_periods(data)

    validations = []

    # --------------------------------------------------------
    # Liability component aliases
    # --------------------------------------------------------

    liability_components = [
        "Capital",
        "Employees stock options outstanding",
        "Employees stock options / units outstanding",
        "Reserves and surplus",
        "Minority interest",
        "Deposits",
        "Borrowings",
        "Other liabilities and provisions",
        "Policyholders' funds",
        "Policyholders’ funds",
    ]

    # --------------------------------------------------------
    # Asset component aliases
    # --------------------------------------------------------

    asset_components = [
        "Cash and balances with Reserve Bank of India",
        "Balances with banks and money at call and short notice",
        "Balances with banks / call money",
        "Investments",
        "Advances",
        "Fixed assets",
        "Other assets",
        "Goodwill on Consolidation",
    ]

    # --------------------------------------------------------
    # Total aliases
    # --------------------------------------------------------

    liability_total_aliases = [
        "Total - Capital and Liabilities",
        "Total Capital and Liabilities",
        "Total Capital & Liabilities",
        "Total (Capital and Liabilities)",
        "Total - Capital & Liabilities",
    ]

    asset_total_aliases = [
        "Total - Assets",
        "Total Assets",
        "Total (Assets)",
        "Total - Asset",
    ]

    for period in periods:

        # ====================================================
        # FIND TOTALS
        # ====================================================

        reported_liability_total = validation_number(
            find_value(
                line_items,
                period,
                liability_total_aliases,
            )
        )

        reported_asset_total = validation_number(
            find_value(
                line_items,
                period,
                asset_total_aliases,
            )
        )

        # ====================================================
        # LIABILITY COMPONENT SUM
        # ====================================================

        liability_values = []

        for component in liability_components:

            value = find_value(
                line_items,
                period,
                [component],
            )

            number = validation_number(value)

            if number is not None:
                liability_values.append(number)

        if (
            reported_liability_total is not None
            and liability_values
        ):

            calculated_liabilities = sum(
                liability_values
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "Balance Sheet liabilities "
                        f"components for {period}"
                    ),
                    formula=(
                        "sum(capital and liability components) "
                        "≈ total capital and liabilities"
                    ),
                    input_values={
                        "component_values": liability_values,
                        "reported_total_capital_and_liabilities":
                            reported_liability_total,
                    },
                    calculated_value=calculated_liabilities,
                    reported_value=reported_liability_total,
                    status=(
                        "PASS"
                        if abs(
                            calculated_liabilities
                            - reported_liability_total
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "Balance Sheet liabilities "
                        f"components for {period}"
                    ),
                    formula=(
                        "sum(capital and liability components) "
                        "≈ total capital and liabilities"
                    ),
                    input_values={
                        "component_values": liability_values,
                        "reported_total_capital_and_liabilities":
                            reported_liability_total,
                    },
                    calculated_value=None,
                    reported_value=reported_liability_total,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # ASSET COMPONENT SUM
        # ====================================================

        asset_values = []

        for component in asset_components:

            value = find_value(
                line_items,
                period,
                [component],
            )

            number = validation_number(value)

            if number is not None:
                asset_values.append(number)

        if (
            reported_asset_total is not None
            and asset_values
        ):

            calculated_assets = sum(
                asset_values
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "Balance Sheet asset "
                        f"components for {period}"
                    ),
                    formula=(
                        "sum(asset components) ≈ total assets"
                    ),
                    input_values={
                        "component_values": asset_values,
                        "reported_total_assets":
                            reported_asset_total,
                    },
                    calculated_value=calculated_assets,
                    reported_value=reported_asset_total,
                    status=(
                        "PASS"
                        if abs(
                            calculated_assets
                            - reported_asset_total
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "Balance Sheet asset "
                        f"components for {period}"
                    ),
                    formula=(
                        "sum(asset components) ≈ total assets"
                    ),
                    input_values={
                        "component_values": asset_values,
                        "reported_total_assets":
                            reported_asset_total,
                    },
                    calculated_value=None,
                    reported_value=reported_asset_total,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # ASSETS = CAPITAL + LIABILITIES
        # ====================================================

        if (
            reported_asset_total is not None
            and reported_liability_total is not None
        ):

            validations.append(
                create_validation_result(
                    check_name=(
                        "Balance Sheet total reconciliation "
                        f"for {period}"
                    ),
                    formula=(
                        "total assets "
                        "≈ total capital and liabilities"
                    ),
                    input_values={
                        "total_assets":
                            reported_asset_total,
                        "total_capital_and_liabilities":
                            reported_liability_total,
                    },
                    calculated_value=reported_asset_total,
                    reported_value=reported_liability_total,
                    status=(
                        "PASS"
                        if abs(
                            reported_asset_total
                            - reported_liability_total
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

    return summarize_validations(validations)


# ============================================================
# PROFIT & LOSS VALIDATION
# ============================================================

def validate_profit_and_loss(
    data: Any,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict:
    """
    Validate Profit & Loss Statement.

    Checks for every period:

    1. Interest earned + other income ≈ total income
    2. Interest expended + operating expenses + provisions
       ≈ total expenditure
    3. Total income - total expenditure
       ≈ consolidated net profit before minority interest
    4. Net profit before minority interest - minority interest
       ≈ group net profit
    5. Appropriation components ≈ total appropriations
    """

    line_items = get_line_items(data)
    periods = get_periods(data)

    validations = []

    # --------------------------------------------------------
    # Actual aliases used by the extracted P&L
    # --------------------------------------------------------

    interest_earned_aliases = [
        "Interest earned",
    ]

    other_income_aliases = [
        "Other income",
    ]

    total_income_aliases = [
        "Total income",
        "Total Income",
    ]

    interest_expended_aliases = [
        "Interest expended",
    ]

    operating_expenses_aliases = [
        "Operating expenses",
    ]

    provisions_aliases = [
        "Provisions and contingencies",
        "Provisions & contingencies",
        "Provisions",
    ]

    total_expenditure_aliases = [
        "Total expenditure",
        "Total Expenditure",
    ]

    net_profit_before_minority_aliases = [
        "Consolidated net profit before minority interest",
        "Net profit before minority interest",
        "Consolidated net profit before minority",
    ]

    minority_interest_aliases = [
        "Minority interest",
        "Less: Minority interest",
    ]

    group_net_profit_aliases = [
        "Group net profit",
        "Net profit attributable to shareholders",
        "Consolidated net profit",
        "Net profit after minority interest",
    ]

    total_appropriation_aliases = [
        "Total appropriations",
        "Total appropriation",
    ]

    appropriation_components = [
        "Transfer to statutory reserve",
        "Transfer to capital reserve",
        "Transfer to revenue reserve",
        "Transfer to general reserve",
        "Transfer to other reserves",
        "Interim dividend",
        "Proposed dividend",
        "Dividend",
        "Other reserves",
    ]

    for period in periods:

        # ====================================================
        # CHECK 1
        # INTEREST EARNED + OTHER INCOME
        # ====================================================

        interest_earned = validation_number(
            find_value(
                line_items,
                period,
                interest_earned_aliases,
            )
        )

        other_income = validation_number(
            find_value(
                line_items,
                period,
                other_income_aliases,
            )
        )

        total_income = validation_number(
            find_value(
                line_items,
                period,
                total_income_aliases,
            )
        )

        if (
            interest_earned is not None
            and other_income is not None
            and total_income is not None
        ):

            calculated = (
                interest_earned
                + other_income
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L total income "
                        f"for {period}"
                    ),
                    formula=(
                        "interest earned + other income "
                        "≈ total income"
                    ),
                    input_values={
                        "interest_earned":
                            interest_earned,
                        "other_income":
                            other_income,
                        "reported_total_income":
                            total_income,
                    },
                    calculated_value=calculated,
                    reported_value=total_income,
                    status=(
                        "PASS"
                        if abs(
                            calculated - total_income
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L total income "
                        f"for {period}"
                    ),
                    formula=(
                        "interest earned + other income "
                        "≈ total income"
                    ),
                    input_values={
                        "interest_earned":
                            interest_earned,
                        "other_income":
                            other_income,
                        "reported_total_income":
                            total_income,
                    },
                    calculated_value=None,
                    reported_value=total_income,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # CHECK 2
        # INTEREST EXPENDED + OPERATING EXPENSES + PROVISIONS
        # ====================================================

        interest_expended = validation_number(
            find_value(
                line_items,
                period,
                interest_expended_aliases,
            )
        )

        operating_expenses = validation_number(
            find_value(
                line_items,
                period,
                operating_expenses_aliases,
            )
        )

        provisions = validation_number(
            find_value(
                line_items,
                period,
                provisions_aliases,
            )
        )

        total_expenditure = validation_number(
            find_value(
                line_items,
                period,
                total_expenditure_aliases,
            )
        )

        if (
            interest_expended is not None
            and operating_expenses is not None
            and provisions is not None
            and total_expenditure is not None
        ):

            calculated = (
                interest_expended
                + operating_expenses
                + provisions
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L total expenditure "
                        f"for {period}"
                    ),
                    formula=(
                        "interest expended + operating expenses "
                        "+ provisions ≈ total expenditure"
                    ),
                    input_values={
                        "interest_expended":
                            interest_expended,
                        "operating_expenses":
                            operating_expenses,
                        "provisions":
                            provisions,
                        "reported_total_expenditure":
                            total_expenditure,
                    },
                    calculated_value=calculated,
                    reported_value=total_expenditure,
                    status=(
                        "PASS"
                        if abs(
                            calculated
                            - total_expenditure
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L total expenditure "
                        f"for {period}"
                    ),
                    formula=(
                        "interest expended + operating expenses "
                        "+ provisions ≈ total expenditure"
                    ),
                    input_values={
                        "interest_expended":
                            interest_expended,
                        "operating_expenses":
                            operating_expenses,
                        "provisions":
                            provisions,
                        "reported_total_expenditure":
                            total_expenditure,
                    },
                    calculated_value=None,
                    reported_value=total_expenditure,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # CHECK 3
        # TOTAL INCOME - TOTAL EXPENDITURE
        # ====================================================

        net_profit_before_minority = validation_number(
            find_value(
                line_items,
                period,
                net_profit_before_minority_aliases,
            )
        )

        if (
            total_income is not None
            and total_expenditure is not None
            and net_profit_before_minority is not None
        ):

            calculated = (
                total_income
                - total_expenditure
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L net profit before minority "
                        f"for {period}"
                    ),
                    formula=(
                        "total income - total expenditure "
                        "≈ consolidated net profit "
                        "before minority interest"
                    ),
                    input_values={
                        "total_income":
                            total_income,
                        "total_expenditure":
                            total_expenditure,
                        "reported_net_profit_before_minority":
                            net_profit_before_minority,
                    },
                    calculated_value=calculated,
                    reported_value=net_profit_before_minority,
                    status=(
                        "PASS"
                        if abs(
                            calculated
                            - net_profit_before_minority
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L net profit before minority "
                        f"for {period}"
                    ),
                    formula=(
                        "total income - total expenditure "
                        "≈ consolidated net profit "
                        "before minority interest"
                    ),
                    input_values={
                        "total_income":
                            total_income,
                        "total_expenditure":
                            total_expenditure,
                        "reported_net_profit_before_minority":
                            net_profit_before_minority,
                    },
                    calculated_value=None,
                    reported_value=net_profit_before_minority,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # CHECK 4
        # MINORITY INTEREST
        # ====================================================

        minority_interest = validation_number(
            find_value(
                line_items,
                period,
                minority_interest_aliases,
            )
        )

        group_net_profit = validation_number(
            find_value(
                line_items,
                period,
                group_net_profit_aliases,
            )
        )

        if (
            net_profit_before_minority is not None
            and minority_interest is not None
            and group_net_profit is not None
        ):

            calculated = (
                net_profit_before_minority
                - minority_interest
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L group net profit "
                        f"for {period}"
                    ),
                    formula=(
                        "net profit before minority "
                        "- minority interest "
                        "≈ group net profit"
                    ),
                    input_values={
                        "net_profit_before_minority":
                            net_profit_before_minority,
                        "minority_interest":
                            minority_interest,
                        "reported_group_net_profit":
                            group_net_profit,
                    },
                    calculated_value=calculated,
                    reported_value=group_net_profit,
                    status=(
                        "PASS"
                        if abs(
                            calculated
                            - group_net_profit
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L group net profit "
                        f"for {period}"
                    ),
                    formula=(
                        "net profit before minority "
                        "- minority interest "
                        "≈ group net profit"
                    ),
                    input_values={
                        "net_profit_before_minority":
                            net_profit_before_minority,
                        "minority_interest":
                            minority_interest,
                        "reported_group_net_profit":
                            group_net_profit,
                    },
                    calculated_value=None,
                    reported_value=group_net_profit,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # CHECK 5
        # APPROPRIATIONS
        # ====================================================

        total_appropriations = validation_number(
            find_value(
                line_items,
                period,
                total_appropriation_aliases,
            )
        )

        appropriation_values = []

        for component in appropriation_components:

            value = find_value(
                line_items,
                period,
                [component],
            )

            number = validation_number(value)

            if number is not None:
                appropriation_values.append(number)

        if (
            total_appropriations is not None
            and appropriation_values
        ):

            calculated = sum(
                appropriation_values
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L appropriations "
                        f"for {period}"
                    ),
                    formula=(
                        "sum(appropriation components) "
                        "≈ total appropriations"
                    ),
                    input_values={
                        "appropriation_components":
                            appropriation_values,
                        "reported_total_appropriations":
                            total_appropriations,
                    },
                    calculated_value=calculated,
                    reported_value=total_appropriations,
                    status=(
                        "PASS"
                        if abs(
                            calculated
                            - total_appropriations
                        ) <= tolerance
                        else "FAIL"
                    ),
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "P&L appropriations "
                        f"for {period}"
                    ),
                    formula=(
                        "sum(appropriation components) "
                        "≈ total appropriations"
                    ),
                    input_values={
                        "appropriation_components":
                            appropriation_values,
                        "reported_total_appropriations":
                            total_appropriations,
                    },
                    calculated_value=None,
                    reported_value=total_appropriations,
                    status="NOT_APPLICABLE",
                )
            )

    return summarize_validations(validations)


# ============================================================
# CASH FLOW STATEMENT VALIDATION
# ============================================================

def validate_cash_flow_statement(
    data: Any,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict:
    """
    Validate Cash Flow Statement.

    Checks for every reported period:

    1. Operating
       + Investing
       + Financing
       + FX adjustment
       ≈ Net increase in cash and cash equivalents

    2. Opening cash
       + Net increase
       + Cash acquired on amalgamation
       ≈ Closing cash
    """

    line_items = get_line_items(data)
    periods = get_periods(data)

    validations = []

    for period in periods:

        # ====================================================
        # CHECK 1
        # NET CASH INCREASE
        # ====================================================

        operating = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Net cash flows from operating activities",
                    "Net cash flow from operating activities",
                ],
            )
        )

        investing = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Net cash flow from / (used) in investing activities",
                    "Net cash flow from investing activities",
                    "Net cash flows from investing activities",
                ],
            )
        )

        financing = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Net cash flow (used) / from financing activities",
                    "Net cash flow from financing activities",
                    "Net cash flows from financing activities",
                ],
            )
        )

        fx_adjustment = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Effect of fluctuation in foreign currency translation reserve",
                    "Effect of fluctuation in foreign currency translation reserves",
                ],
            )
        )

        reported_net_increase = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Net increase in cash and cash equivalents",
                ],
            )
        )

        if (
            operating is not None
            and investing is not None
            and financing is not None
            and fx_adjustment is not None
            and reported_net_increase is not None
        ):

            calculated = (
                operating
                + investing
                + financing
                + fx_adjustment
            )

            status = (
                "PASS"
                if abs(
                    calculated
                    - reported_net_increase
                ) <= tolerance
                else "FAIL"
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "Cash flow net increase "
                        f"for {period}"
                    ),
                    formula=(
                        "operating + investing + financing "
                        "+ FX adjustment ≈ net increase"
                    ),
                    input_values={
                        "period": period,
                        "operating": operating,
                        "investing": investing,
                        "financing": financing,
                        "fx_adjustment": fx_adjustment,
                        "reported_net_increase":
                            reported_net_increase,
                    },
                    calculated_value=calculated,
                    reported_value=reported_net_increase,
                    status=status,
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "Cash flow net increase "
                        f"for {period}"
                    ),
                    formula=(
                        "operating + investing + financing "
                        "+ FX adjustment ≈ net increase"
                    ),
                    input_values={
                        "period": period,
                        "operating": operating,
                        "investing": investing,
                        "financing": financing,
                        "fx_adjustment": fx_adjustment,
                        "reported_net_increase":
                            reported_net_increase,
                    },
                    calculated_value=None,
                    reported_value=reported_net_increase,
                    status="NOT_APPLICABLE",
                )
            )

        # ====================================================
        # CHECK 2
        # OPENING -> CLOSING CASH
        # ====================================================

        opening_cash = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Cash and cash equivalents at the beginning of the year",
                ],
            )
        )

        net_increase = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Net increase in cash and cash equivalents",
                ],
            )
        )

        acquired_on_amalgamation = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Cash and cash equivalents acquired on amalgamation",
                ],
            )
        )

        closing_cash = validation_number(
            find_value(
                line_items,
                period,
                [
                    "Cash and cash equivalents at the end of the year",
                ],
            )
        )

        # ----------------------------------------------------
        # If amalgamation row is absent or '-',
        # treat it as zero.
        # ----------------------------------------------------

        if acquired_on_amalgamation is None:
            acquired_on_amalgamation = 0.0

        if (
            opening_cash is not None
            and net_increase is not None
            and closing_cash is not None
        ):

            calculated_closing = (
                opening_cash
                + net_increase
                + acquired_on_amalgamation
            )

            status = (
                "PASS"
                if abs(
                    calculated_closing
                    - closing_cash
                ) <= tolerance
                else "FAIL"
            )

            validations.append(
                create_validation_result(
                    check_name=(
                        "Cash opening-to-closing "
                        f"reconciliation for {period}"
                    ),
                    formula=(
                        "opening cash + net increase "
                        "+ cash acquired on amalgamation "
                        "≈ closing cash"
                    ),
                    input_values={
                        "period": period,
                        "opening_cash": opening_cash,
                        "net_increase": net_increase,
                        "cash_acquired_on_amalgamation":
                            acquired_on_amalgamation,
                        "reported_closing_cash":
                            closing_cash,
                    },
                    calculated_value=calculated_closing,
                    reported_value=closing_cash,
                    status=status,
                )
            )

        else:

            validations.append(
                create_validation_result(
                    check_name=(
                        "Cash opening-to-closing "
                        f"reconciliation for {period}"
                    ),
                    formula=(
                        "opening cash + net increase "
                        "+ cash acquired on amalgamation "
                        "≈ closing cash"
                    ),
                    input_values={
                        "period": period,
                        "opening_cash": opening_cash,
                        "net_increase": net_increase,
                        "cash_acquired_on_amalgamation":
                            acquired_on_amalgamation,
                        "reported_closing_cash":
                            closing_cash,
                    },
                    calculated_value=None,
                    reported_value=closing_cash,
                    status="NOT_APPLICABLE",
                )
            )

    return summarize_validations(validations)


# ============================================================
# MAIN DISPATCHER
# ============================================================

def validate_financial_document(
    data: Any,
    document_type: str,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict:
    """
    Dispatch validation according to document type.

    Supported:
    - invoice
    - balance_sheet
    - profit_and_loss
    - cash_flow_statement
    """

    document_type = (
        document_type
        .lower()
        .strip()
    )

    if document_type == "invoice":

        return validate_invoice(
            data,
            tolerance=tolerance,
        )

    elif document_type == "balance_sheet":

        return validate_balance_sheet(
            data,
            tolerance=tolerance,
        )

    elif document_type == "profit_and_loss":

        return validate_profit_and_loss(
            data,
            tolerance=tolerance,
        )

    elif document_type == "cash_flow_statement":

        return validate_cash_flow_statement(
            data,
            tolerance=tolerance,
        )

    # --------------------------------------------------------
    # Unsupported financial document type
    # --------------------------------------------------------

    return {
        "overall_status": "NOT_APPLICABLE",
        "total_checks": 0,
        "passed_checks": 0,
        "failed_checks": 0,
        "not_applicable_checks": 0,
        "validations": [],
    }