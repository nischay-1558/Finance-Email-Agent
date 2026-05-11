from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from src.finance_followup_agent import FinanceFollowUpAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finance credit follow-up email agent")
    parser.add_argument("--input", default="data/pending_invoices.csv", help="CSV or JSON invoice input path")
    parser.add_argument("--out-dir", default="outputs", help="Directory for generated reports and logs")
    parser.add_argument("--as-of", default=None, help="Run date in YYYY-MM-DD format; defaults to today")
    parser.add_argument("--sender", default="finance@example.com", help="Sender email address")
    parser.add_argument("--send", action="store_true", help="Actually send via localhost SMTP. Default is dry-run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    agent = FinanceFollowUpAgent(sender_email=args.sender, dry_run=not args.send)
    processed = agent.run(Path(args.input), Path(args.out_dir), as_of=as_of)
    sent = sum(1 for item in processed if item.send_status in {"sent", "dry_run_logged"})
    flagged = sum(1 for item in processed if item.send_status == "flagged_for_manual_review")
    skipped = sum(1 for item in processed if item.send_status == "skipped_not_overdue")
    print(f"Processed {len(processed)} records: {sent} email(s), {flagged} legal flag(s), {skipped} skipped.")
    print(f"Outputs written to {Path(args.out_dir).resolve()}")


if __name__ == "__main__":
    main()
