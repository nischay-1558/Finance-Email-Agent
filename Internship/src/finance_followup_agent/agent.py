from __future__ import annotations

import csv
import json
import smtplib
from dataclasses import asdict
from datetime import date, datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from .email_generator import EmailGenerator
from .models import ESCALATION_MATRIX, FollowUpAction, InvoiceRecord, ProcessedFollowUp, ToneStage


class FinanceFollowUpAgent:
    def __init__(self, sender_email: str = "finance@example.com", dry_run: bool = True) -> None:
        self.sender_email = sender_email
        self.dry_run = dry_run
        self.generator = EmailGenerator()

    def run(self, input_path: Path, output_dir: Path, as_of: date | None = None) -> list[ProcessedFollowUp]:
        as_of = as_of or date.today()
        output_dir.mkdir(parents=True, exist_ok=True)
        records = self.load_records(input_path)
        processed = [self.process_invoice(record, as_of) for record in records]
        self.write_outputs(processed, output_dir)
        return processed

    def load_records(self, input_path: Path) -> list[InvoiceRecord]:
        suffix = input_path.suffix.lower()
        if suffix == ".csv":
            with input_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        elif suffix == ".json":
            rows = json.loads(input_path.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise ValueError("JSON input must be a list of invoice records.")
        else:
            raise ValueError("Supported input formats: .csv and .json. Convert Excel exports to CSV for this prototype.")
        return [InvoiceRecord.from_row(row) for row in rows]

    def process_invoice(self, invoice: InvoiceRecord, as_of: date) -> ProcessedFollowUp:
        days_overdue = invoice.days_overdue(as_of)
        stage = self.stage_for(days_overdue)
        if stage.action == FollowUpAction.SKIP_NOT_OVERDUE:
            return ProcessedFollowUp(invoice, days_overdue, stage, stage.action, None, "skipped_not_overdue")
        if stage.action == FollowUpAction.FLAG_LEGAL_REVIEW:
            return ProcessedFollowUp(invoice, days_overdue, stage, stage.action, None, "flagged_for_manual_review")

        generated = self.generator.generate(invoice, stage, days_overdue, as_of)
        validation_errors = tuple(self.validate_email(invoice, days_overdue, generated.subject, generated.body))
        send_status = "validation_failed"
        if not validation_errors:
            send_status = "dry_run_logged" if self.dry_run else self.send_email(invoice, generated.subject, generated.body)
        return ProcessedFollowUp(invoice, days_overdue, stage, stage.action, generated, send_status, validation_errors)

    def stage_for(self, days_overdue: int) -> ToneStage:
        if days_overdue <= 0:
            return ToneStage(0, "Not Overdue", 0, 0, "None", "No follow-up required", "No action", FollowUpAction.SKIP_NOT_OVERDUE)
        for stage in ESCALATION_MATRIX:
            if days_overdue >= stage.min_days and (stage.max_days is None or days_overdue <= stage.max_days):
                return stage
        raise RuntimeError("Unable to determine escalation stage.")

    def validate_email(self, invoice: InvoiceRecord, days_overdue: int, generated_subject: str, generated_body: str) -> Iterable[str]:
        combined = f"{generated_subject}\n{generated_body}"
        required_values = [
            invoice.client_name,
            invoice.contact_name,
            invoice.invoice_no,
            invoice.formatted_amount(),
            invoice.due_date.strftime("%d %b %Y"),
            str(days_overdue),
            invoice.payment_link,
        ]
        for value in required_values:
            if value and value not in combined:
                yield f"Missing required dynamic value: {value}"
        forbidden = ["{{", "}}", "[client", "[invoice", "lorem ipsum"]
        for token in forbidden:
            if token.lower() in combined.lower():
                yield f"Potential placeholder/generic content found: {token}"

    def send_email(self, invoice: InvoiceRecord, subject: str, body: str) -> str:
        message = EmailMessage()
        message["From"] = self.sender_email
        message["To"] = invoice.contact_email
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP("localhost") as smtp:
            smtp.send_message(message)
        return "sent"

    def write_outputs(self, processed: list[ProcessedFollowUp], output_dir: Path) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        audit_path = output_dir / "audit_log.jsonl"
        outbox_path = output_dir / "generated_emails.json"
        csv_path = output_dir / "followup_summary.csv"
        report_path = output_dir / "report.html"

        audit_records = [item.to_log_record(timestamp) for item in processed]
        audit_path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in audit_records), encoding="utf-8")

        outbox = []
        for item in processed:
            if item.generated_email:
                outbox.append(
                    {
                        "to": item.invoice.contact_email,
                        "invoice_no": item.invoice.invoice_no,
                        "stage": item.stage.label,
                        "tone": item.stage.tone,
                        "subject": item.generated_email.subject,
                        "body": item.generated_email.body,
                        "send_status": item.send_status,
                    }
                )
        outbox_path.write_text(json.dumps(outbox, indent=2, ensure_ascii=False), encoding="utf-8")

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(audit_records[0].keys()) if audit_records else ["timestamp"])
            writer.writeheader()
            writer.writerows(audit_records)

        report_path.write_text(render_html_report(processed, timestamp, self.dry_run), encoding="utf-8")


def render_html_report(processed: list[ProcessedFollowUp], timestamp: str, dry_run: bool) -> str:
    rows = []
    for item in processed:
        subject = item.generated_email.subject if item.generated_email else ""
        rows.append(
            "<tr>"
            f"<td>{item.invoice.invoice_no}</td>"
            f"<td>{item.invoice.client_name}</td>"
            f"<td>{item.invoice.formatted_amount()}</td>"
            f"<td>{item.days_overdue}</td>"
            f"<td>{item.stage.label}</td>"
            f"<td>{item.stage.tone}</td>"
            f"<td>{item.action.value}</td>"
            f"<td>{item.send_status}</td>"
            f"<td>{subject}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finance Follow-up Agent Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #596579; margin-bottom: 24px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #edf4ff; }}
    tr:nth-child(even) {{ background: #fafbfc; }}
  </style>
</head>
<body>
  <h1>Finance Follow-up Agent Report</h1>
  <div class="meta">Generated {timestamp} · Mode: {"Dry run" if dry_run else "Live SMTP"}</div>
  <table>
    <thead>
      <tr><th>Invoice</th><th>Client</th><th>Amount</th><th>Days Overdue</th><th>Stage</th><th>Tone</th><th>Action</th><th>Status</th><th>Subject</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""


def processed_to_dicts(items: list[ProcessedFollowUp]) -> list[dict[str, object]]:
    return [asdict(item) for item in items]
