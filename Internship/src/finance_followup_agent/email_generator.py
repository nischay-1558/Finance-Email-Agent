from __future__ import annotations

from datetime import date

from .models import GeneratedEmail, InvoiceRecord, ToneStage


class EmailGenerator:
    """Deterministic generator that mirrors the LLM prompt contract for demos."""

    def generate(self, invoice: InvoiceRecord, stage: ToneStage, days_overdue: int, as_of: date) -> GeneratedEmail:
        context = {
            "contact": invoice.contact_name,
            "client": invoice.client_name,
            "invoice": invoice.invoice_no,
            "amount": invoice.formatted_amount(),
            "due_date": invoice.due_date.strftime("%d %b %Y"),
            "days": days_overdue,
            "payment_link": invoice.payment_link,
            "manager": invoice.account_manager,
            "today": as_of.strftime("%d %b %Y"),
        }
        subject, body = _TEMPLATES[stage.stage](context)
        return GeneratedEmail(subject=subject, body=body)


def _stage_1(ctx: dict[str, object]) -> tuple[str, str]:
    subject = f"Quick reminder: Invoice {ctx['invoice']} payment due"
    body = (
        f"Hi {ctx['contact']},\n\n"
        f"I hope you are doing well. This is a friendly reminder for {ctx['client']} that Invoice {ctx['invoice']} "
        f"for {ctx['amount']} was due on {ctx['due_date']} and is now {ctx['days']} day(s) overdue.\n\n"
        f"If the payment has already been processed, please ignore this note. Otherwise, you can complete it here:\n"
        f"{ctx['payment_link']}\n\n"
        f"Thanks,\n{ctx['manager']}"
    )
    return subject, body


def _stage_2(ctx: dict[str, object]) -> tuple[str, str]:
    subject = f"Payment confirmation requested: Invoice {ctx['invoice']}"
    body = (
        f"Dear {ctx['contact']},\n\n"
        f"Our records show that Invoice {ctx['invoice']} for {ctx['client']} remains unpaid in the amount of {ctx['amount']}. "
        f"The invoice was due on {ctx['due_date']} and is currently {ctx['days']} day(s) overdue.\n\n"
        f"Please confirm the expected payment date, or use the payment link below to settle the balance:\n"
        f"{ctx['payment_link']}\n\n"
        f"Regards,\n{ctx['manager']}"
    )
    return subject, body


def _stage_3(ctx: dict[str, object]) -> tuple[str, str]:
    subject = f"IMPORTANT: Outstanding payment for Invoice {ctx['invoice']}"
    body = (
        f"Dear {ctx['contact']},\n\n"
        f"Despite previous reminders, Invoice {ctx['invoice']} for {ctx['amount']} remains unpaid as of {ctx['today']}. "
        f"It is now {ctx['days']} day(s) overdue from the due date of {ctx['due_date']}.\n\n"
        f"We request your immediate attention. Continued non-payment may affect your credit terms with {ctx['client']}. "
        f"Please respond within 48 hours with a payment confirmation or complete payment here:\n"
        f"{ctx['payment_link']}\n\n"
        f"Sincerely,\n{ctx['manager']}"
    )
    return subject, body


def _stage_4(ctx: dict[str, object]) -> tuple[str, str]:
    subject = f"FINAL NOTICE: Invoice {ctx['invoice']} requires immediate action"
    body = (
        f"Dear {ctx['contact']},\n\n"
        f"This is the final automated reminder for Invoice {ctx['invoice']} for {ctx['client']} ({ctx['amount']}). "
        f"The payment was due on {ctx['due_date']} and is now {ctx['days']} day(s) overdue.\n\n"
        f"Please remit payment immediately using the link below or contact us today to resolve the matter. "
        f"If we do not receive payment or a firm response, this account will be escalated for manual finance review.\n"
        f"{ctx['payment_link']}\n\n"
        f"Regards,\n{ctx['manager']}"
    )
    return subject, body


_TEMPLATES = {
    1: _stage_1,
    2: _stage_2,
    3: _stage_3,
    4: _stage_4,
}
