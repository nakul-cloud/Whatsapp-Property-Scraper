import io
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import Response

from app import apply_na_for_text_columns, normalize_df_types
from parser import OUTPUT_COLUMNS, process_raw_text
from utils import normalize_whitespace

app = FastAPI(title="WhatsApp Property Lead Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    raw_text: str
    enable_ai_fallback: bool = False
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    area_path: Optional[str] = None

class ExportCsvRequest(BaseModel):
    rows: List[Dict[str, Any]]

@app.post("/api/process")
def process_messages(req: ProcessRequest):
    raw = normalize_whitespace(req.raw_text)
    if not raw:
        return {"rows": [], "meta": {"debug": "Empty text"}}

    rows, meta = process_raw_text(
        raw,
        enable_ai_fallback=req.enable_ai_fallback,
        groq_api_key=req.groq_api_key,
        groq_model=req.groq_model,
        area_paths=[req.area_path] if req.area_path and req.area_path.strip() else None,
    )
    return {"rows": rows, "meta": meta}

@app.post("/api/export_csv")
def export_csv(req: ExportCsvRequest):
    df = pd.DataFrame(req.rows, columns=OUTPUT_COLUMNS)
    df = normalize_df_types(df) if not df.empty else df
    df_display = apply_na_for_text_columns(df) if not df.empty else df

    buf = io.StringIO()
    df_display.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")
    
    return Response(content=csv_bytes, media_type="text/csv")
