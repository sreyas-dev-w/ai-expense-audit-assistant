"""Generate the sample corporate expense policy PDF used to seed the RAG store.

Writes a plain, text-extractable PDF (pypdf reads it back in
``app/services/pdf_extraction_service.py``) using only the standard library,
so the backend does not gain a PDF-authoring dependency for a demo fixture.

    python scripts/generate_sample_policy.py [output.pdf]

Then ingest it:

    POST /api/v1/policies/documents  (multipart file=<output.pdf>)
"""
from __future__ import annotations

import sys
from pathlib import Path

PAGE_WIDTH, PAGE_HEIGHT = 612, 792
MARGIN_X, TOP_Y = 56, 740
FONT_SIZE, LEADING = 10.5, 15.5
MAX_LINES_PER_PAGE = 44

TITLE = "ACME CONSULTING - CORPORATE EXPENSE POLICY (v3.2, FY2026)"

SECTIONS: list[tuple[str, list[str]]] = [
    (
        "1. SCOPE AND GENERAL PRINCIPLES",
        [
            "1.1 This policy governs all business expenses claimed by employees of Acme Consulting",
            "and applies to every expense category: food and meals, travel, accommodation, and other.",
            "1.2 Expenses must be reasonable, necessary, and incurred wholly for business purposes.",
            "1.3 Every claim must state a business purpose. Claims with a blank, generic, or",
            "non-business purpose (for example 'personal', 'misc', or 'n/a') must be rejected.",
            "1.4 An itemised receipt is mandatory for every claim regardless of amount. A claim",
            "without a legible receipt must be flagged for review and may not be approved.",
            "1.5 Claims must be submitted within 30 calendar days of the date the expense was",
            "incurred. Claims older than 30 days require written justification and manager approval.",
            "1.6 The receipt date must fall on or before the submission date. A receipt dated in the",
            "future is a blocking error.",
            "1.7 The claimed amount must match the receipt total. A claimed amount that exceeds the",
            "receipt total is a blocking error and the claim must be rejected.",
            "1.8 Duplicate submissions of the same receipt are prohibited. Where the same merchant,",
            "amount, and date appear on more than one claim, the later claim must be rejected.",
        ],
    ),
    (
        "2. JOB LEVELS AND ENTITLEMENT BANDS",
        [
            "2.1 Entitlements scale with job level. Levels L1 and L2 are junior staff, L3 and L4 are",
            "senior staff and team leads, and L5 and L6 are management and executive grades.",
            "2.2 Where an employee is promoted mid-period, the entitlement applicable on the date the",
            "expense was incurred applies, not the entitlement at the date of submission.",
            "2.3 All limits in this policy are stated in Indian Rupees (INR) and are inclusive of",
            "taxes and service charges unless explicitly stated otherwise.",
            "2.4 Expenses in a foreign currency must be converted at the rate published on the date",
            "of the transaction, and the conversion rate must be noted in the business purpose.",
        ],
    ),
    (
        "3. FOOD AND MEALS",
        [
            "3.1 Per-person, per-meal limits for business meals are as follows:",
            "    L1-L2: INR 600 per person per meal",
            "    L3-L4: INR 1,000 per person per meal",
            "    L5-L6: INR 1,500 per person per meal",
            "3.2 The daily aggregate meal cap is INR 2,500 per employee for L1-L4 and INR 4,000 for",
            "L5-L6, covering all meals claimed on a single calendar day.",
            "3.3 The number of people on the claim must match the receipt. Where the claimed head",
            "count exceeds the number of covers on the receipt, the claim must be flagged.",
            "3.4 Client entertainment meals may exceed the per-person limit by up to 50 percent, but",
            "only when the business purpose names the client and the attending client personnel.",
            "3.5 Alcohol is not reimbursable under any circumstance. Where a receipt itemises",
            "alcohol, the alcohol amount must be deducted before approval and the claim flagged.",
            "3.6 Meals claimed on a weekend or public holiday require an explicit business",
            "justification naming the engagement that required weekend work.",
            "3.7 Team meals for more than 10 attendees require prior written approval from an L5 or",
            "above; without it the claim must be flagged for review.",
        ],
    ),
    (
        "4. TRAVEL",
        [
            "4.1 Air travel class entitlement by job level:",
            "    L1-L4: economy class only",
            "    L5-L6: economy class for flights under 6 hours; business class permitted for",
            "    flights of 6 hours or more",
            "4.2 A business class ticket claimed by an employee at L1-L4 is a blocking policy",
            "violation and the claim must be rejected.",
            "4.3 Domestic air travel must be booked at least 14 days in advance where the itinerary",
            "is known. Bookings made inside 7 days require a documented business reason.",
            "4.4 Rail travel is reimbursed up to AC 2-Tier for L1-L4 and AC 1st Class for L5-L6.",
            "4.5 Road travel by personal vehicle is reimbursed at INR 12 per kilometre. The origin,",
            "destination, and distance must be stated on the claim.",
            "4.6 Taxi and ride-hailing fares are capped at INR 2,500 per single journey. Airport",
            "transfers above this cap require a manager's written justification.",
            "4.7 The travel date on the claim must match the travel date on the ticket or receipt.",
            "A mismatch of more than one day is a blocking error.",
            "4.8 Ticket cancellation and rescheduling fees are reimbursable only when the change was",
            "driven by a client or project requirement, which must be named in the business purpose.",
            "4.9 Personal side trips attached to business travel are not reimbursable. Where an",
            "itinerary includes personal legs, only the business portion may be claimed.",
        ],
    ),
    (
        "5. ACCOMMODATION",
        [
            "5.1 Per-night room rate caps, excluding taxes, by job level and city tier:",
            "    L1-L2: INR 4,000 (tier 1 cities), INR 3,000 (other cities)",
            "    L3-L4: INR 7,000 (tier 1 cities), INR 5,000 (other cities)",
            "    L5-L6: INR 12,000 (tier 1 cities), INR 9,000 (other cities)",
            "5.2 Tier 1 cities are Mumbai, Delhi NCR, Bengaluru, Hyderabad, Chennai, and Pune.",
            "5.3 One room per travelling employee. A claim for more rooms than travellers must be",
            "rejected unless the additional rooms are separately justified and pre-approved.",
            "5.4 The number of nights claimed must equal the difference between the check-out and",
            "check-in dates. Any mismatch is a blocking error.",
            "5.5 The check-out date must be later than the check-in date. Equal or inverted dates",
            "are a blocking error.",
            "5.6 Stays longer than 14 consecutive nights must be converted to a serviced apartment",
            "or long-stay rate and require L5 approval.",
            "5.7 In-room dining, minibar, laundry, spa, and entertainment charges are not",
            "reimbursable and must be excluded from the claimed amount.",
            "5.8 Hotel bookings made through the approved corporate travel desk are exempt from the",
            "advance-booking requirement but remain subject to the per-night caps.",
        ],
    ),
    (
        "6. OTHER EXPENSES",
        [
            "6.1 Office supplies and consumables are reimbursable up to INR 5,000 per claim.",
            "6.2 Software subscriptions and professional tooling require prior approval from the",
            "project lead and must name the project code on the claim.",
            "6.3 Professional membership fees, certifications, and training are reimbursable up to",
            "INR 50,000 per financial year per employee with manager approval.",
            "6.4 Mobile and internet reimbursement is capped at INR 2,000 per month for L1-L4 and",
            "INR 4,000 per month for L5-L6.",
            "6.5 Client gifts are capped at INR 5,000 per recipient per year and must be recorded",
            "with the recipient's name and organisation.",
            "6.6 Fines, penalties, traffic violations, and personal insurance are never reimbursable.",
            "6.7 Any 'other' claim without a specific expense type is incomplete and must be flagged.",
        ],
    ),
    (
        "7. BUDGET, APPROVAL, AND AUDIT",
        [
            "7.1 Every claim is charged to the project's parent account. A claim that exceeds the",
            "account's remaining budget must be flagged for review and escalated before approval.",
            "7.2 Approval authority by claim amount:",
            "    up to INR 10,000: the employee's direct manager",
            "    INR 10,001 to INR 100,000: the direct manager and the project lead",
            "    above INR 100,000: finance review in addition to the above",
            "7.3 An employee may not approve their own claim, nor a claim from which they benefit.",
            "7.4 Approvers must record a decision note explaining the basis of an approval or a",
            "rejection. A decision without a note is not a valid approval record.",
            "7.5 Where a receipt shows signs of alteration, inconsistent fonts, mismatched totals, or",
            "other indicators of tampering, the claim must be flagged as a suspected authenticity",
            "issue and escalated to finance rather than approved or rejected outright.",
            "7.6 Automated audit findings are decision support only. Final approval authority always",
            "rests with the human approver named in section 7.2.",
            "7.7 Records of all claims, receipts, and approval decisions are retained for seven years.",
        ],
    ),
]


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _paginate() -> list[list[str]]:
    lines: list[str] = [TITLE, ""]
    for heading, body in SECTIONS:
        lines.append(heading)
        lines.extend(body)
        lines.append("")

    pages: list[list[str]] = []
    for start in range(0, len(lines), MAX_LINES_PER_PAGE):
        pages.append(lines[start : start + MAX_LINES_PER_PAGE])
    return pages


def _content_stream(lines: list[str]) -> bytes:
    parts = [
        "BT",
        f"/F1 {FONT_SIZE} Tf",
        f"{LEADING} TL",
        f"{MARGIN_X} {TOP_Y} Td",
    ]
    for line in lines:
        parts.append(f"({_escape(line)}) Tj")
        parts.append("T*")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", "replace")


def build_pdf() -> bytes:
    pages = _paginate()
    page_count = len(pages)

    # Object ids: 1 catalog, 2 pages, 3 font, then page/content pairs.
    first_page_id = 4
    page_ids = [first_page_id + i * 2 for i in range(page_count)]
    content_ids = [pid + 1 for pid in page_ids]

    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{pid} 0 R" for pid in page_ids)
            + f"] /Count {page_count} >>"
        ).encode("latin-1"),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }

    for index, page_lines in enumerate(pages):
        stream = _content_stream(page_lines)
        objects[page_ids[index]] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_ids[index]} 0 R >>"
        ).encode("latin-1")
        objects[content_ids[index]] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(out)
        out += f"{obj_id} 0 obj\n".encode("latin-1")
        out += objects[obj_id]
        out += b"\nendobj\n"

    xref_offset = len(out)
    total = max(objects) + 1
    out += f"xref\n0 {total}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for obj_id in range(1, total):
        out += f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("acme_expense_policy.pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(build_pdf())
    print(f"Wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
