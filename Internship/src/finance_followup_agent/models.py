from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any


class FollowUpAction(str, Enum):
    SEND_EMAIL = "send_email"
    FLAG_LEGAL_REVIEW = "flag_legal_review"
    SKIP_NOT_OVERDUE = "skip_not_overdue"


@dataclass(frozen=True)
class ToneStage:
    stage: int
    label: str
    min_days: int
    max_days: int | None
    tone: str
    message_goal: str
    cta: str
    action: FollowUpAction


ESCALATION_MATRIX: tuple[ToneStage, ...] = (
    ToneStage(1, "1st Follow-Up", 1, 7, "Warm & Friendly", "Gentle reminder, assume oversight", "Pay now link / bank details", FollowUpAction.SEND_EMAIL),
    ToneStage(2, "2nd Follow-Up", 8, 14, "Polite but Firm", "Payment still pending; request confirmation", "Confirm payment date", FollowUpAction.SEND_EMAIL),
    ToneStage(3, "3rd Follow-Up", 15, 21, "Formal & Serious", "Escalating concern; mention impact", "Respond within 48 hours", FollowUpAction.SEND_EMAIL),
    ToneStage(4, "4th Follow-Up", 22, 30, "Stern & Urgent", "Final reminder before escalation", "Pay immediately or call us", FollowUpAction.SEND_EMAIL),
    ToneStage(5, "Escalation Flag", 31, None, "Flag for Legal", "Human review required; no auto email", "Assign to finance manager", FollowUpAction.FLAG_LEGAL_REVIEW),
)


@dataclass(frozen=True)
class InvoiceRecord:
    invoice_no: str
    client_name: str
    contact_name: str
    contact_email: str
    amount_due: Decimal
    due_date: date
    follow_up_count: int
    payment_link: str
    account_manager: str = "Finance Team"
    currency: str = "INR"
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "InvoiceRecord":
        required = [
            "invoice_no",
            "client_name",
            "contact_name",
            "contact_email",
            "amount_due",
            "due_date",
            "follow_up_count",
            "payment_link",
        ]
        missing = [name for name in required if not str(row.get(name, "")).strip()]
        if missing:
            raise ValueError(f"Missing required invoice fields: {', '.join(missing)}")

        try:
            amount = Decimal(str(row["amount_due"]).replace(",", "").strip())
        except InvalidOperation as exc:
            raise ValueError(f"Invalid amount_due for invoice {row.get('invoice_no')!r}") from exc

        try:
            parsed_due_date = datetime.strptime(str(row["due_date"]).strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"due_date must be YYYY-MM-DD for invoice {row.get('invoice_no')!r}") from exc

        try:
            follow_up_count = int(row["follow_up_count"])
        except ValueError as exc:
            raise ValueError(f"follow_up_count must be an integer for invoice {row.get('invoice_no')!r}") from exc

        return cls(
            invoice_no=str(row["invoice_no"]).strip(),
            client_name=str(row["client_name"]).strip(),
            contact_name=str(row["contact_name"]).strip(),
            contact_email=str(row["contact_email"]).strip(),
            amount_due=amount,
            due_date=parsed_due_date,
            follow_up_count=follow_up_count,
            payment_link=str(row["payment_link"]).strip(),
            account_manager=str(row.get("account_manager") or "Finance Team").strip(),
            currency=str(row.get("currency") or "INR").strip(),
            raw=dict(row),
        )

    def days_overdue(self, as_of: date) -> int:
        return (as_of - self.due_date).days

    def formatted_amount(self) -> str:
        symbol = "INR " if self.currency.upper() == "INR" else f"{self.currency.upper()} "
        amount = f"{self.amount_due:,.2f}".rstrip("0").rstrip(".")
        return f"{symbol}{amount}"


@dataclass(frozen=True)
class GeneratedEmail:
    subject: str
    body: str


@dataclass(frozen=True)
class ProcessedFollowUp:
    invoice: InvoiceRecord
    days_overdue: int
    stage: ToneStage
    action: FollowUpAction
    generated_email: GeneratedEmail | None
    send_status: str
    validation_errors: tuple[str, ...] = ()

    def to_log_record(self, timestamp: str) -> dict[str, Any]:
        return {
            "timestamp": timestamp,
            "invoice_no": self.invoice.invoice_no,
            "client_name": self.invoice.client_name,
            "contact_email": mask_email(self.invoice.contact_email),
            "amount_due": str(self.invoice.amount_due),
            "due_date": self.invoice.due_date.isoformat(),
            "days_overdue": self.days_overdue,
            "follow_up_count": self.invoice.follow_up_count,
            "stage": self.stage.label,
            "tone": self.stage.tone,
            "action": self.action.value,
            "send_status": self.send_status,
            "validation_errors": list(self.validation_errors),
            "subject": self.generated_email.subject if self.generated_email else "",
        }


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"
