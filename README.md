# Finance-Email-Agent
This repo contains the finance email agent which is a basic Email agent build as a task for internship test


Project Overview

The Finance Credit Follow-Up Email Agent is an AI-powered automation system designed to assist finance teams in managing overdue invoice collections efficiently.

The agent:

Automatically identifies overdue invoices
Determines the appropriate follow-up stage based on delay
Generates personalized emails with varying tone and urgency
Logs all communications for audit purposes
Escalates long-overdue cases for manual/legal intervention

This solution reduces manual effort, ensures consistent communication, and improves payment collection efficiency (reducing Days Sales Outstanding - DSO).


Setup Instructions
1. Clone the Repository using following commands:
git clone <your-repo-link>
cd finance-email-agent

2.Install Dependencies:
pip install -r requirements.txt

3.Create Environment File

Create a .env file:
OPENAI_API_KEY=your_api_key_here

4.Ensure the file exists:
data/invoices.csv

=> Sample Data: 
invoice_id,client_name,email,amount,due_date,followup_count
INV001,Rajesh Sharma,rajesh@email.com,45000,2026-05-05,0
INV002,Amit Kapoor,amit@email.com,30000,2026-04-28,1
INV003,Neha Verma,neha@email.com,55000,2026-04-20,2

5.Run the Agent:
python main.py

6. Run the Dashboard:
   streamlit run app.py

Agent Architecture Diagram:-
                ┌──────────────────────────┐
                │   Invoice Data (CSV)     │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │ Overdue Detection Logic  │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │ Tone Escalation Engine   │
                │ (Stage 1 → Stage 4)      │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │ LLM Email Generator      │
                │ (Personalized Emails)    │
                └────────────┬─────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌──────────────────────┐            ┌──────────────────────────┐
│ Email Send / Dry Run │            │ Audit Logging System     │
└──────────────────────┘            └──────────────────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │ Escalation Handler       │
                │ (30+ days → Legal)       │
                └──────────────────────────┘


LLM & Framework Choice:
LLM: GPT-4o

Framework: LangChain

Security Mitigations:-
1. Prompt Injection Protection
Use fixed prompt templates (no user-controlled system prompts)
Restrict input fields to structured invoice data only
Validate all inputs before passing to LLM
2. Data Privacy / PII Protection
Avoid sending unnecessary sensitive data to LLM
Mask sensitive fields in logs (emails, names if needed)
Use local processing wherever possible.
3. API Key Security
API keys stored in .env file
.env added to .gitignore
No hardcoding of credentials in source code
4. Hallucination Risk Mitigation
Use structured prompts with explicit fields
Set low temperature for consistent outputs
Validate generated emails before sending/logging
5. Unauthorized Access Control
API endpoints (if deployed) can be protected with authentication
Rate limiting can be implemented for abuse prevention
6. Email Spoofing Prevention
Use verified sender domains (SMTP / SendGrid)
Configure SPF, DKIM, and DMARC
Use dry-run mode during testing to prevent accidental emails

Conclusion:-

This AI agent demonstrates how LLMs can automate real-world financial workflows by combining:

Rule-based logic (overdue detection)
AI-based reasoning (tone generation)
System design (logging + escalation)

It provides a scalable foundation for intelligent finance automation systems.
