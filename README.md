# Caspian Inbox Command

A Gmail-first inbox triage dashboard powered by OpenAI Agents SDK and Caspian.

## Run

1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `.venv\\Scripts\\Activate.ps1`
3. Install packages: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add `OPENAI_API_KEY` and `CASPIAN_API_KEY`.
5. Start the dashboard: `uvicorn app:app --reload`
6. Open http://localhost:8000

The dashboard starts in demo mode. For Gmail, create a Google OAuth Desktop/Web application, download its client JSON as `credentials.json`, add `http://localhost:8000/auth/gmail/callback` as an authorized redirect URI, then click Connect Gmail.

Run Caspian messaging separately with `python caspian/bot.py`. Set `CASPIAN_EMAIL_USERNAME` to a chosen hosted agent address local-part, such as `inbox`; this address is for messaging the agent, not for reading your personal Gmail inbox.
