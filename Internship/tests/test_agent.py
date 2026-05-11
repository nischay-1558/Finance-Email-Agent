from datetime import date
from pathlib import Path
import tempfile
import unittest

from src.finance_followup_agent import FinanceFollowUpAgent
from src.finance_followup_agent.models import FollowUpAction, InvoiceRecord


def make_invoice(due_date: str) -> InvoiceRecord:
    return InvoiceRecord.from_row(
        {
            "invoice_no": "INV-TEST-001",
            "client_name": "Test Client",
            "contact_name": "Priya Test",
            "contact_email": "priya@example.com",
            "amount_due": "1000",
            "due_date": due_date,
            "follow_up_count": "1",
            "payment_link": "https://pay.example.com/test",
            "account_manager": "Finance Owner",
            "currency": "INR",
        }
    )


class FinanceFollowUpAgentTest(unittest.TestCase):
    def test_stage_mapping(self) -> None:
        agent = FinanceFollowUpAgent()
        self.assertEqual(agent.stage_for(3).stage, 1)
        self.assertEqual(agent.stage_for(10).stage, 2)
        self.assertEqual(agent.stage_for(18).stage, 3)
        self.assertEqual(agent.stage_for(25).stage, 4)
        self.assertEqual(agent.stage_for(35).action, FollowUpAction.FLAG_LEGAL_REVIEW)
        self.assertEqual(agent.stage_for(0).action, FollowUpAction.SKIP_NOT_OVERDUE)


    def test_email_contains_required_dynamic_fields(self) -> None:
        agent = FinanceFollowUpAgent()
        item = agent.process_invoice(make_invoice("2026-05-01"), date(2026, 5, 10))
        self.assertIsNotNone(item.generated_email)
        assert item.generated_email is not None
        combined = item.generated_email.subject + item.generated_email.body
        self.assertIn("INV-TEST-001", combined)
        self.assertIn("Test Client", combined)
        self.assertIn("Priya Test", combined)
        self.assertIn("INR 1,000", combined)
        self.assertIn("01 May 2026", combined)
        self.assertIn("9", combined)
        self.assertIn("https://pay.example.com/test", combined)
        self.assertEqual(item.validation_errors, ())


    def test_run_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tmp_path = Path(temp)
            input_path = tmp_path / "invoices.csv"
            input_path.write_text(
                "invoice_no,client_name,contact_name,contact_email,amount_due,due_date,follow_up_count,payment_link\n"
                "INV-1,Acme,Priya,priya@example.com,1000,2026-05-01,0,https://pay.example.com/1\n",
                encoding="utf-8",
            )
            output_dir = tmp_path / "outputs"
            processed = FinanceFollowUpAgent().run(input_path, output_dir, as_of=date(2026, 5, 10))
            self.assertEqual(len(processed), 1)
            self.assertTrue((output_dir / "audit_log.jsonl").exists())
            self.assertTrue((output_dir / "generated_emails.json").exists())
            self.assertTrue((output_dir / "followup_summary.csv").exists())
            self.assertTrue((output_dir / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
