import json
import logging
from typing import Type

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.extraction import (
    InvoiceExtraction,
    FinancialStatementExtraction,
)

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when LLM-based document extraction fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def get_extraction_schema(
    document_type: str,
) -> Type[BaseModel]:
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

    raise ExtractionError(
        f"Unsupported document type: {document_type}"
    )


def build_extraction_prompt(
    text: str,
    document_type: str,
    schema: Type[BaseModel],
) -> str:
    """
    Build the extraction prompt sent to Kimi.
    """

    schema_json = json.dumps(
        schema.model_json_schema(),
        indent=2,
    )

    prompt = f"""
You are a highly accurate financial document extraction system.

Your task is to extract structured information from the supplied
document text.

DOCUMENT TYPE:
{document_type}

IMPORTANT GENERAL RULES
============================================================

1. Extract only information that is actually present in the supplied
   document text.

2. Do not hallucinate.

3. Do not invent missing values.

4. If a field is missing, unreadable, ambiguous, or cannot be reliably
   determined, return null.

5. Preserve names, numbers, dates, codes, and wording as accurately
   as possible.

6. Do not modify financial numbers to make calculations balance.

7. Financial validation must NEVER influence extraction.

8. Evidence should contain the original source wording as closely as
   possible.

9. Include the page number in evidence whenever possible.

10. For financial numbers:
    - Preserve decimal values.
    - Preserve comma placement.
    - Preserve negative values.
    - Parentheses indicate negative values where applicable.
    - A dash "-" means unavailable/null.
    - Do not add or remove digits.

11. Carefully distinguish similar-looking numbers.

12. If OCR text appears suspicious, do not silently repair a number.
    Return null if the correct value cannot be determined reliably.

13. Return JSON only.

14. Do not wrap the JSON in markdown code fences.

15. Follow the supplied JSON schema exactly.


============================================================
INVOICE / RECEIPT RULES
============================================================

If this is an invoice or receipt:

Extract ALL visible:

- invoice number
- receipt number
- invoice date
- transaction date
- vendor name
- customer name
- currency
- item/product codes
- product descriptions
- quantities
- unit prices
- line amounts
- item count
- total quantity
- subtotal
- discount
- tax/GST rate
- tax/GST amount
- total amount
- cash received
- change
- payment amounts
- other meaningful financial fields


For every line item:

- Extract the product/item code separately.
- Extract the product description separately.
- Extract quantity separately.
- Extract unit price separately.
- Extract line amount separately.


IMPORTANT LINE ITEM EXTRACTION RULES
============================================================

- Carefully identify the table column headers before assigning values.

- Extract quantity whenever a numeric quantity is clearly visible.

- Keep quantity, unit price, and line amount as separate fields.

- Never confuse quantity with unit price.

- Never confuse quantity with line amount.

- Do not return quantity as null when the quantity is clearly visible.

- Do not shift values between quantity, unit price, and amount.

- Preserve the original row and column relationship exactly as visible.

- Do not infer quantity from the line amount.

- Do not infer unit price from the line amount.

- Do not change numbers to make financial validation pass.

- If a quantity is genuinely absent or unreadable, return null.

- If a number is unclear or unreadable, return null instead of guessing.


Example:

TS-001 | Notebook | 2 | 50.00 | 100.00

Extract:

item_code = "TS-001"
description = "Notebook"
quantity = 2
unit_price = 50.00
amount = 100.00

Because:

2 × 50.00 = 100.00


Another example:

TS-002 | Pen | 5 | 10.00 | 50.00

Extract:

item_code = "TS-002"
description = "Pen"
quantity = 5
unit_price = 10.00
amount = 50.00

Because:

5 × 10.00 = 50.00


IMPORTANT:

- Financial validation must NEVER modify extracted values.

- Do not modify a number just to make a calculation pass.

- If the quantity is genuinely unreadable, return null.

- Do not use mathematical calculations to guess a missing quantity.

- Do not use the subtotal or total to reconstruct missing line-item
  values.

- Do not use another line item's quantity, price, or amount to fill
  a missing value.

IMPORTANT OCR TABLE EXTRACTION RULE
============================================================

When the OCR text contains a table header such as:

Item Code Description Qty Unit Price Amount

and a row such as:

TS-001 Note book 2 50.00 100.00

extract:

item_code = "TS-001"
description = "Note book"
quantity = 2
unit_price = 50.00
amount = 100.00

When a row such as:

TS-002 Pen 5 10.00 50.00

is present, extract:

item_code = "TS-002"
description = "Pen"
quantity = 5
unit_price = 10.00
amount = 50.00

The numeric value corresponding to the Qty column is the quantity.
Use the table column headers and row alignment to determine the correct
quantity. Do not assume the quantity is immediately after the
description when the description contains multiple words or when the
OCR layout is rearranged.

The next monetary value is the unit price.

The final monetary value is the line amount.

Do NOT omit a clearly visible quantity.

Do NOT return quantity = null when the quantity is clearly visible.

Do NOT interpret the quantity as part of the description.

Do NOT use calculations to guess a missing quantity.

The quantity must be extracted directly from the OCR row.

Financial validation must NEVER modify extracted values.


Do NOT merge item codes into descriptions.

Do NOT merge prices into descriptions.


IMPORTANT TOTAL QUANTITY RULES
============================================================

- total_items = number of distinct visible line items when clearly
  determinable.

- total_quantity = sum of visible line-item quantities when all
  quantities are available.

- Do not invent total_items.

- Do not invent total_quantity.

- If one or more quantities are genuinely missing or unreadable,
  return total_quantity as null.

- Do not calculate total_quantity from subtotal or total amount.

- Do not infer total_items from the invoice total.

- Preserve the values exactly as visible in the document.


Pay special attention to:

- company names
- invoice/receipt numbers
- dates
- alphanumeric item codes
- currency
- GST/tax information
- cash
- change


If the document says:

CASH RM 100.00

extract:

cash_received = 100.00


If the document says:

CHANGE RM 93.80

extract:

change_amount = 93.80


If the document says:

GST @6%

extract:

tax_rate = 6


If the document says:

GST @6% included in total RM 0.35

extract:

tax_rate = 6
tax_amount = 0.35


Do not assume that tax is added on top of the total if the document
explicitly says tax is included.


IMPORTANT ACCURACY RULES
============================================================

- Read every visible financial number exactly as printed.

- Do NOT add, remove, duplicate, or invent digits.

- Preserve decimal points exactly.

- Preserve comma placement and decimal structure.

- Parentheses indicate negative values where applicable.

- A dash, blank cell, or clearly unavailable value must be returned
  as null.

- Never change an extracted number because another calculation
  suggests a different value.

- Financial validation must never influence extraction.

- If the source text is unclear, return null rather than guessing.

- Evidence.source_text should preserve the original visible wording
  as closely as possible.

- For line items, evidence should preserve the complete visible row
  whenever possible.

- Verify that each quantity, unit price, and amount belongs to the
  correct row.

- Verify that each numeric value belongs to the correct column.

- Never move a value between columns to make validation pass.


============================================================
FINANCIAL STATEMENT RULES
============================================================

If this is a balance sheet, profit and loss statement, or cash flow
statement:

Extract EVERY meaningful visible row.

This includes:

- statement title
- company name
- currency
- reporting periods
- headings
- sub-headings
- individual financial line items
- subtotals
- totals
- assets
- liabilities
- equity/capital
- income
- expenditure
- profit/loss
- cash flow items
- opening balances
- closing balances
- adjustments
- minority interest
- appropriations
- other visible financial fields


============================================================
CRITICAL MULTI-PERIOD TABLE RULES
============================================================

1. Carefully identify the column headers before assigning values to
   periods.

2. Every numeric value MUST be assigned to the correct period/column.

3. Never move a value from one period to another to make a calculation
   balance.

4. If a row contains:

   Goodwill on Consolidation    -    148.79

   and columns:

   As at March 31, 2024
   As at March 31, 2023

   then:

   2024 = null
   2023 = 148.79

5. A dash "-", blank cell, or clearly unavailable value MUST be
   returned as null.

6. Preserve the original row and column relationship exactly as
   visible.

7. Financial validation must NOT influence extraction.

8. Do not change, redistribute, or infer numbers merely to make
   totals reconcile.

9. Before returning JSON, verify each line item's period corresponds
   to the correct visible column.

10. For rows containing two numeric values, first belongs to the first
    period and second belongs to the second period unless the layout
    clearly indicates otherwise.

11. Do not merge values from different periods.

12. Do not copy a value from another row.

13. Do not infer missing comparative values.

14. If a comparative value is shown as "-", return null for that
    period.

15. Preserve the reporting period exactly as represented in the
    document.

16. If the document contains multiple years, each value must remain
    associated with its correct year.

17. For multi-period rows, evidence.source_text MUST preserve the
    complete visible row including values for all periods whenever
    possible.

18. Example:

    Goodwill on Consolidation    -    148.79

    evidence should be:

    "Goodwill on Consolidation - 148.79"

19. Evidence must not be rewritten into a calculated or normalized
    sentence. Preserve original document wording/layout as closely
    as possible.


============================================================
IMPORTANT NUMERIC EXTRACTION RULES
============================================================

20. Read every financial number exactly as visually printed.

21. Do NOT add, remove, duplicate, or invent digits.

22. Preserve exact comma and decimal structure before converting to
    numeric JSON.

23. Parentheses indicate negative values where applicable.

    Example:

    (7,342.84) = -7342.84

24. Dash/em dash/en dash/blank = unavailable/null.

25. Pay special attention to numbers with commas and similar digit
    patterns.

    Do not confuse:

    11,181.71

    with:

    411,181.71

26. Do not insert a digit because another number elsewhere contains it.

27. Re-check every extracted financial number against the source text.

28. Financial statement JSON value must correspond exactly to the
    source.

29. If a number is unclear/unreadable, return null instead of
    guessing.

30. Evidence.source_text preserves the complete visible row including
    commas, parentheses, decimals, dashes, and comparative values.

31. Example:

    Cash and cash equivalents acquired on amalgamation 11,181.71 -

    means:

    2024 = 11181.71
    2023 = null

32. Do NOT interpret:

    11,181.71

    as:

    411,181.71

33. Do NOT modify an extracted number to make validation pass.

34. Validation must never influence extraction.

35. When OCR is suspicious, prefer clearly visible source text or
    return null if the correct value cannot be determined.

36. Verify:

    - digit count
    - comma placement
    - decimal placement
    - sign
    - period assignment

37. Never merge digits from adjacent numbers, rows, or columns.

38. OCR text may contain character recognition errors.

39. Never silently invent or repair a financial number.

40. Preserve decimal points exactly when present in supplied OCR/source
    text.

41. Do not convert:

    50.00 → 5000
    100.00 → 10000
    28.00 → 2800

42. If decimal position cannot be determined reliably from the supplied
    source text, return null instead of guessing.

43. Do not use arithmetic validation to infer or repair an extracted
    value.

44. Validation results must never be used to modify extracted data.

45. When OCR text and evidence appear inconsistent, prefer clearly
    visible source if available; otherwise return null.

46. Verify digit count, comma placement, decimal placement, sign, and
    period assignment before returning the JSON.


============================================================
OUTPUT JSON SCHEMA
============================================================

Return ONLY valid JSON matching this schema:

{schema_json}


============================================================
DOCUMENT TEXT
============================================================

{text}
"""

    return prompt


def create_client() -> OpenAI:
    """
    Create the Kimi OpenAI-compatible client.
    """

    if settings.llm_provider.lower() != "kimi":
        raise ExtractionError(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )

    if not settings.llm_api_key:
        raise ExtractionError(
            "LLM_API_KEY is not configured."
        )

    try:
        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        return client

    except Exception as exc:
        raise ExtractionError(
            f"Failed to initialize Kimi client: {str(exc)}"
        )


def clean_json_response(content: str) -> str:
    """
    Remove accidental markdown code fences from the LLM response.
    """

    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]

    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def extract_document(
    text: str,
    document_type: str,
):
    """
    Extract structured information from OCR/native document text
    using Kimi and validate the result with the appropriate
    Pydantic schema.
    """

    if not text or not text.strip():
        raise ExtractionError(
            "No document text was available for extraction."
        )

    schema = get_extraction_schema(document_type)

    prompt = build_extraction_prompt(
        text=text,
        document_type=document_type,
        schema=schema,
    )

    logger.info(
        "Starting Kimi extraction | document_type=%s | text_length=%s",
        document_type,
        len(text),
    )

    client = create_client()
    logger.info("=" * 70)
    logger.info("TEXT SENT TO KIMI")
    logger.info("=" * 70)
    logger.info("\n%s", text)
    logger.info("=" * 70)

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise financial document "
                        "extraction engine. "
                        "Return valid JSON only. "
                        "Never hallucinate financial values."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

    except Exception as exc:
        logger.exception("Kimi API call failed")

        raise ExtractionError(
            f"Kimi API request failed: {str(exc)}"
        )

    try:
        content = response.choices[0].message.content

        if not content:
            raise ExtractionError(
                "Kimi returned an empty response."
            )

        logger.info(
            "Kimi response received | response_length=%s",
            len(content),
        )

        cleaned_content = clean_json_response(content)

        raw_result = json.loads(cleaned_content)

    except json.JSONDecodeError as exc:
        logger.exception(
            "Kimi returned invalid JSON"
        )

        raise ExtractionError(
            f"Kimi returned invalid JSON: {str(exc)}"
        )

    except ExtractionError:
        raise

    except Exception as exc:
        logger.exception(
            "Failed to parse Kimi response"
        )

        raise ExtractionError(
            f"Failed to parse Kimi response: {str(exc)}"
        )

    try:
        extracted_data = schema.model_validate(raw_result)

    except Exception as exc:
        logger.exception(
            "Kimi response failed Pydantic validation"
        )

        raise ExtractionError(
            f"Extracted data does not match the required schema: "
            f"{str(exc)}"
        )

    logger.info(
        "Kimi extraction completed successfully | document_type=%s",
        document_type,
    )

    return extracted_data