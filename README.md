# WhatsApp Property Lead Extractor (Streamlit)

Production-ready Streamlit app to extract structured real-estate property lead data from bulk WhatsApp messages (10–50 at once) using a **rule-based parser first**, with optional **Groq AI fallback** only when many important fields are missing.

## Setup (Windows / PowerShell)

Create + activate venv:

```powershell
cd "d:\Whatsapp Property Scrapper"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
streamlit run app.py
```

## Optional environment variables

- `GROQ_API_KEY`: Groq API key (only needed if you enable AI fallback)
- `GROQ_MODEL`: defaults to `llama-3.1-70b-versatile`
- `AREAS_FILE`: optional custom Pune areas file path

Create a `.env` file (optional):

```ini
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-70b-versatile
AREAS_FILE=
```

## Files

- `app.py`: Streamlit UI + CSV export
- `parser.py`: message splitting + rule extraction + validation + optional Groq batching
- `utils.py`: cleaning, price normalization, fuzzy area matching
- `areas_pune.txt`: bundled Pune area list (pipe-separated)

## Documentation

- `docs/DETAILED_IMPLEMENTATION.md`
- `docs/PARSING_RULES.md`
- `docs/CSV_SCHEMA.md`
- `docs/AI_FALLBACK_POLICY.md`
- `docs/VALIDATION_PLAYBOOK.md`
- `docs/TROUBLESHOOTING.md`

