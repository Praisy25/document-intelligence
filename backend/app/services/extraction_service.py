import json
import logging
import time

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.extraction import (
    FinancialStatementExtraction,
    InvoiceExtraction,
)

class ExtractionError(Exception):
    """Raised when document extraction fails."""
    pass

logger = logging.getLogger(__name__)


# ============================================================
# EXTRACTION SCHEMAS
# ============================================================

def get_extraction_schema(document_type: str):
    """
    Return the Pydantic schema corresponding to the document type.
    """

    if document_type == "invoice":
        return InvoiceExtraction

    if document_type in {
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }:
        return FinancialStatementExtraction

    raise ValueError(
        f"Unsupported document type for extraction: {document_type}"
    )


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_extraction_prompt(
    text: str,
    document_type: str,
    schema,
) -> str:
    """
    Build the extraction prompt sent to Kimi.
    """

    schema_json = json.dumps(
        schema.model_json_schema(),
        indent=2,
    )

    base_rules = """
You are a financial document extraction engine.

Your job is to extract information ONLY from the supplied document text.

STRICT RULES:

1. Extract only information that is actually present in the document.
2. NEVER hallucinate values.
3. NEVER invent missing fields.
4. If a value is missing, unclear, unreadable, or cannot be reliably determined,
   return null.
5. Preserve the original meaning of the document.
6. Do not calculate values unless the schema explicitly requires a derived
   aggregate such as total_items or total_quantity.
7. Do not modify reported financial values to make validation pass.
8. Parentheses normally indicate negative financial values.
9. Preserve decimal precision when possible.
10. For financial statements, preserve the period/year associated with each value.
11. Extract all meaningful visible line items.
12. Return ONLY valid JSON.
13. Do not return markdown.
14. Do not wrap the JSON inside ```json fences.
"""

    if document_type == "invoice":

        document_rules = """
INVOICE / RECEIPT EXTRACTION RULES:

Extract all meaningful visible invoice fields, including where available:

- invoice number
- invoice date
- vendor name
- customer name
- currency
- subtotal
- tax rate
- tax amount
- discount
- total amount
- cash received
- change amount
- total items
- total quantity
- every line item

For every line item, separately extract:

- item_code
- description
- quantity
- unit_price
- amount

Do NOT merge quantity, unit price, and amount.

IMPORTANT TABLE EXTRACTION RULE:

If OCR text contains a table such as:

Item Code Description Qty Unit Price Amount
TS-001 Note book 2 50.00 100.00
TS-002 Pen 5 10.00 50.00

the correct interpretation is:

TS-001:
quantity = 2
unit_price = 50.00
amount = 100.00

TS-002:
quantity = 5
unit_price = 10.00
amount = 50.00

Clearly visible quantities MUST NOT be omitted.

TOTAL ITEMS:

total_items means the number of distinct line-item rows.

Example:

2 rows -> total_items = 2

TOTAL QUANTITY:

total_quantity means the sum of all clearly visible quantities.

Example:

2 + 5 = 7

Do not confuse total_items with total_quantity.

LINE ITEM ACCURACY:

If:

quantity = 2
unit_price = 50
amount = 100

return exactly those values.

Do not change 2 into null simply because the OCR table layout is imperfect.

TAX:

If the document says tax is included in the total but does not separately provide
a tax amount, do not invent a tax amount.

DISCOUNT:

If discount is absent, return null.

CASH / CHANGE:

If cash received and change are explicitly visible, extract them.

Do not calculate cash received or change unless explicitly visible.

Do not repair OCR values merely to make mathematical validation pass.
"""

    elif document_type == "balance_sheet":

        document_rules = """
BALANCE SHEET EXTRACTION RULES:

Extract:

- statement title
- company name
- currency
- all reporting periods
- all meaningful balance sheet line items

For every line item extract:

- name
- value
- period
- evidence

Examples of meaningful items include:

Assets
- fixed assets
- goodwill
- investments
- cash and bank balances
- loans and advances
- inventories
- receivables
- other assets
- total assets

Liabilities
- share capital
- reserves
- deposits
- borrowings
- provisions
- other liabilities
- total liabilities

Do not assume a value belongs to a period based only on row order.

Use the actual year/period heading in the OCR text.

If a value is unreadable or missing, use null.

Do not invent missing values.

Preserve negative values represented using parentheses.
"""

    elif document_type == "profit_and_loss":

        document_rules = """
PROFIT AND LOSS STATEMENT EXTRACTION RULES:

Extract all meaningful visible line items and preserve their reporting period.

Important categories may include:

INCOME:
- interest earned
- other income
- total income

EXPENDITURE:
- interest expended
- operating expenses
- provisions and contingencies
- total expenditure

PROFIT:
- net profit for the year
- minority interest
- consolidated/group profit for the year
- profit and loss account brought forward
- total

APPROPRIATIONS:
- statutory reserve
- tax on dividend
- dividend
- interim dividend
- general reserve
- capital reserve
- investment reserve
- investment fluctuation reserve
- balance carried over to balance sheet
- total

Also extract earnings per share where meaningfully visible.

For every line item preserve:

- exact meaningful name
- numeric value
- period
- evidence

Do not infer missing values.

If OCR introduces minor formatting artifacts, preserve the underlying value only
when it is clearly readable.

Do not alter values merely to force accounting equations to pass.
"""

    elif document_type == "cash_flow_statement":

        document_rules = """
CASH FLOW STATEMENT EXTRACTION RULES:

Extract all meaningful visible line items and reporting periods.

Important categories include:

OPERATING ACTIVITIES:
- net cash flow from operating activities

INVESTING ACTIVITIES:
- net cash flow from / used in investing activities

FINANCING ACTIVITIES:
- net cash flow from / used in financing activities

FOREIGN EXCHANGE:
- effect of foreign exchange / currency translation

NET CHANGE:
- net increase/decrease in cash and cash equivalents

OPENING:
- cash and cash equivalents at beginning of year

CLOSING:
- cash and cash equivalents at end of year

Also extract:

- cash acquired on amalgamation
- proceeds from sale of fixed assets
- purchases of fixed assets
- investments
- borrowings
- dividends
- other meaningful cash flow line items

PARENTHESES:

A value such as:

(3,983.06)

means:

-3983.06

Do not remove the negative sign.

PERIODS:

If the statement contains multiple years, associate each line item with its
correct year.

Do not mix 2024 values with 2023 values.

If a line item contains a dash such as:

-

and it clearly means zero/no amount, it may be represented as 0 only where
the context explicitly indicates the line is a numeric financial item.

Otherwise use null.

Do not invent missing values.

Do not change reported values to make the accounting validation pass.
"""

    else:
        document_rules = ""

    return f"""
{base_rules}

{document_rules}

DOCUMENT TYPE:
{document_type}

REQUIRED JSON SCHEMA:
{schema_json}

DOCUMENT TEXT:
-------------------------
{text}
-------------------------

Return ONLY the JSON object matching the schema.
"""


# ============================================================
# KIMI CLIENT
# ============================================================

def create_client() -> OpenAI:
    """
    Create the OpenAI-compatible Kimi client.
    """

    if settings.llm_provider.lower() != "kimi":
        raise ExtractionError(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )

    if not settings.llm_api_key:
        raise ExtractionError(
            "LLM_API_KEY is not configured."
        )

    logger.info(
        "Creating Kimi client | base_url=%s | model=%s",
        settings.llm_base_url,
        settings.llm_model,
    )

    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,

        # Prevent the Render request from hanging indefinitely.
        timeout=60.0,

        # Retry only once for transient failures.
        max_retries=1,
    )


# ============================================================
# JSON CLEANING
# ============================================================

def clean_json_response(content: str) -> str:
    """
    Remove common markdown/code-fence formatting from the LLM response.
    """

    if not content:
        raise ValueError(
            "Kimi returned an empty response."
        )

    content = content.strip()

    # Remove markdown code fences if the model accidentally returns them.
    if content.startswith("```json"):
        content = content[7:]

    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    return content


# ============================================================
# KIMI EXTRACTION
# ============================================================

def extract_document(
    text: str,
    document_type: str,
):
    """
    Extract structured document data using Kimi.
    """

    logger.info(
        "Starting Kimi extraction | document_type=%s | text_length=%d",
        document_type,
        len(text),
    )

    if not text or not text.strip():
        raise ExtractionError(
            "No readable text was extracted from the document."
        )

    schema = get_extraction_schema(document_type)

    prompt = build_extraction_prompt(
        text=text,
        document_type=document_type,
        schema=schema,
    )

    # --------------------------------------------------------
    # DEBUG LOGGING
    # --------------------------------------------------------

    logger.info("=" * 70)
    logger.info("TEXT SENT TO KIMI")
    logger.info("=" * 70)
    logger.info("\n%s", text)
    logger.info("=" * 70)

    # --------------------------------------------------------
    # CREATE CLIENT
    # --------------------------------------------------------

    client = create_client()

    # --------------------------------------------------------
    # KIMI REQUEST
    # --------------------------------------------------------

    start_time = time.time()

    logger.info(
        "Sending request to Kimi..."
    )

    try:

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial document extraction engine. "
                        "Return only valid JSON matching the requested schema. "
                        "Never hallucinate missing information."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

    except Exception as exc:

        elapsed = time.time() - start_time

        logger.exception(
            "Kimi API request failed after %.2f seconds | error=%s",
            elapsed,
            str(exc),
        )

        raise ExtractionError(
            f"Kimi API request failed: {exc}"
        ) from exc

    # --------------------------------------------------------
    # RESPONSE TIMING
    # --------------------------------------------------------

    elapsed = time.time() - start_time

    logger.info(
        "Kimi response received in %.2f seconds",
        elapsed,
    )

    # --------------------------------------------------------
    # CHECK RESPONSE
    # --------------------------------------------------------

    if not response:
        raise ExtractionError(
            "Kimi returned no response."
        )

    if not response.choices:
        raise ExtractionError(
            "Kimi response contained no choices."
        )

    message = response.choices[0].message

    content = message.content

    if not content:
        raise ExtractionError(
            "Kimi returned an empty message."
        )

    logger.info(
        "Kimi response length=%d",
        len(content),
    )

    logger.info(
        "Kimi response preview: %s",
        content[:500],
    )

    # --------------------------------------------------------
    # CLEAN JSON
    # --------------------------------------------------------

    cleaned_content = clean_json_response(content)

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    try:

        raw_result = json.loads(
            cleaned_content
        )

    except json.JSONDecodeError as exc:

        logger.error(
            "Kimi returned invalid JSON."
        )

        logger.error(
            "Raw Kimi response: %s",
            content,
        )

        raise ExtractionError(
            f"Kimi returned invalid JSON: {exc}"
        ) from exc

    # --------------------------------------------------------
    # PYDANTIC VALIDATION
    # --------------------------------------------------------

    try:

        validated_result = schema.model_validate(
            raw_result
        )

    except ValidationError as exc:

        logger.error(
            "Kimi response failed Pydantic validation."
        )

        logger.error(
            "Validation error: %s",
            exc,
        )

        raise ExtractionError(
            f"Kimi response does not match the expected schema: {exc}"
        ) from exc

    logger.info(
        "Kimi extraction completed successfully | document_type=%s",
        document_type,
    )

    return validated_result