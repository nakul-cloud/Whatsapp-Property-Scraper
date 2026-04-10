# App Guide

## Purpose

The app extracts structured real-estate leads from WhatsApp chat text or copied lead blocks. It relies on a rule-based parser first, then optionally uses Groq AI only when several key fields are missing.

## How It Works

1. **Input normalization**: whitespace cleanup and timestamp normalization.
2. **Message split**:
   - WhatsApp timestamp headers like `[09/04, 2:49 pm] Name:`
   - Fallback for date-line lead blocks (e.g. `10.04.2026`)
   - Fallback for tabular/TSV-like rows
3. **Rule-based extraction**: property code, owner, phone, area, address, sizes, price, deposit, etc.
4. **Optional AI fallback**: batches only when important fields are missing.
5. **Validation + audit**: failed messages are tracked for review.

## UI Sections

- **Extracted Leads**: current batch dataframe and CSV download.
- **Analysis**: metrics and colorful charts (timeline, property type, top areas, price distribution).
- **Failed Messages**: audit table and CSV download.
- **Processing Details**: raw meta/debug info from parser.

## Data Columns

The output columns are defined in `parser.py` as `OUTPUT_COLUMNS`. See `docs/CSV_SCHEMA.md` for a full description.

## Environment Variables

- `GROQ_API_KEY` (optional): enables Groq fallback when toggled in UI.
- `GROQ_MODEL` (optional): defaults to `llama-3.1-70b-versatile`.
- `AREAS_FILE` (optional): custom Pune areas file path.

## Running Locally

```powershell
cd "d:\Whatsapp Property Scrapper"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Deployment Options (Recommended)

### Streamlit Community Cloud

- Best for quick, free deployments.
- Connect GitHub repo and select `app.py`.
- Add env vars in the deployment UI.

### Render or Railway

- Start command:
  `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Add env vars in the service dashboard.

## API Server (Optional)

`api.py` exposes a FastAPI wrapper with:

- `POST /api/process` to parse messages
- `POST /api/export_csv` to export CSV from rows

Run locally:

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

- See `docs/TROUBLESHOOTING.md` for parsing and runtime help.
- If charts look empty, confirm `date_stamp`, `area`, and `property_type` exist in the parsed rows.
