"""
FastAPI Backend for WhatsApp Property Lead Extractor
Provides the same logic as app.py but as REST API endpoints
"""

from __future__ import annotations

import csv
import io
import json
import pandas as pd
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from parser import OUTPUT_COLUMNS, process_raw_text
from utils import env, normalize_whitespace


# ============= Pydantic Models =============
class ProcessRequest(BaseModel):
    raw_text: str
    enable_ai: bool = False
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    area_path: Optional[str] = None


class ProcessResponse(BaseModel):
    rows: list[dict]
    meta: dict
    csv_data: str
    message: str


class AnalysisResponse(BaseModel):
    total_leads: int
    unique_contacts: int
    avg_price: float
    data_quality: float
    property_types: dict
    top_areas: list[dict]


class CombinedCacheRequest(BaseModel):
    action: str  # "add", "reset", "export"
    rows: Optional[list[dict]] = None


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes using csv module for better quoting"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=df.columns, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writeheader()
    for _, row in df.iterrows():
        writer.writerow(row.to_dict())
    return buf.getvalue().encode("utf-8")


def normalize_df_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize data types in DataFrame"""
    out = df.copy()
    for col in ["rent_or_sell_price", "deposit"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    return out


def apply_na_for_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply N/A formatting to text columns and clean problematic whitespace"""
    out = df.copy()
    numeric_cols = {"rent_or_sell_price", "deposit"}
    for col in out.columns:
        if col in numeric_cols:
            out[col] = out[col].astype("object").fillna("N/A").astype(str).replace("nan", "N/A")
            continue
        out[col] = out[col].astype("string").fillna("N/A")
        out[col] = out[col].replace({"": "N/A", "nan": "N/A", "<NA>": "N/A"})
        # Clean tabs, carriage returns, and excessive whitespace from text columns
        out[col] = out[col].str.replace(r"[\t\r\n]+", " ", regex=True)
        out[col] = out[col].str.replace(r"\s{2,}", " ", regex=True)
    return out


def merge_combined_rows(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Merge rows avoiding duplicates"""
    merged = list(existing)
    seen = {
        (
            str(r.get("property_id", "")),
            str(r.get("owner_contact", "")),
            str(r.get("date_stamp", "")),
        )
        for r in merged
    }
    for r in incoming:
        key = (
            str(r.get("property_id", "")),
            str(r.get("owner_contact", "")),
            str(r.get("date_stamp", "")),
        )
        if key in seen:
            continue
        merged.append(r)
        seen.add(key)
    return merged


# ============= FastAPI App Setup =============
load_dotenv()

app = FastAPI(
    title="WhatsApp Property Lead Extractor API",
    description="Backend API for processing WhatsApp property leads",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for combined rows (replace with database in production)
combined_cache: list[dict] = []


# ============= API Endpoints =============
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}


@app.post("/api/process-messages", response_model=ProcessResponse)
async def process_messages(request: ProcessRequest):
    """
    Process WhatsApp messages and extract property leads
    
    Args:
        raw_text: Raw WhatsApp chat text
        enable_ai: Whether to use AI fallback (Groq)
        groq_api_key: Groq API key (if enable_ai=True)
        groq_model: Groq model to use
        area_path: Path to custom areas file
    
    Returns:
        Extracted rows, metadata, and CSV data
    """
    try:
        raw_text = normalize_whitespace(request.raw_text)
        if not raw_text:
            raise HTTPException(status_code=400, detail="Please provide WhatsApp messages")

        # Process the text
        rows, meta = process_raw_text(
            raw_text,
            enable_ai_fallback=request.enable_ai,
            groq_api_key=request.groq_api_key or env("GROQ_API_KEY", ""),
            groq_model=request.groq_model or env("GROQ_MODEL", "llama-3.1-70b-versatile"),
            area_paths=[request.area_path] if request.area_path and request.area_path.strip() else None,
        )

        # Convert to DataFrame for CSV output
        # Ensure all rows have all columns from OUTPUT_COLUMNS
        cleaned_rows = []
        for row in rows:
            cleaned_row = {col: row.get(col, "") for col in OUTPUT_COLUMNS}
            cleaned_rows.append(cleaned_row)
        
        df = pd.DataFrame(cleaned_rows, columns=OUTPUT_COLUMNS)
        df = normalize_df_types(df)
        df_display = apply_na_for_text_columns(df)
        csv_bytes = df_to_csv_bytes(df_display)
        csv_data = csv_bytes.decode("utf-8")

        # Update combined cache
        global combined_cache
        combined_cache = merge_combined_rows(combined_cache, rows)

        return ProcessResponse(
            rows=rows,
            meta=meta,
            csv_data=csv_data,
            message=f"Processed {len(rows)} leads successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_data(rows: list[dict]):
    """
    Generate analysis metrics from extracted rows
    
    Args:
        rows: List of extracted property lead dictionaries
    
    Returns:
        Analysis metrics and statistics
    """
    try:
        if not rows:
            raise HTTPException(status_code=400, detail="No rows provided")

        # Ensure all rows have all columns from OUTPUT_COLUMNS
        cleaned_rows = []
        for row in rows:
            cleaned_row = {col: row.get(col, "") for col in OUTPUT_COLUMNS}
            cleaned_rows.append(cleaned_row)
        
        df = pd.DataFrame(cleaned_rows, columns=OUTPUT_COLUMNS)
        df = normalize_df_types(df)
        df_display = apply_na_for_text_columns(df)

        # Calculate metrics
        total_leads = len(df)
        
        unique_contacts = (
            df_display["owner_contact"].astype(str).replace("N/A", pd.NA).dropna().nunique()
            if "owner_contact" in df_display.columns else 0
        )
        
        avg_price = int(pd.to_numeric(df["rent_or_sell_price"], errors="coerce").dropna().mean()) \
            if "rent_or_sell_price" in df.columns else 0
        
        # Data quality calculation
        critical_cols = ["owner_contact", "area", "address", "rent_or_sell_price", "deposit"]
        filled = 0
        total = 0
        for c in critical_cols:
            if c not in df_display.columns:
                continue
            col = df_display[c].astype(str).str.strip()
            filled += (~col.isin(["N/A", "", "nan", "<NA>"])).sum()
            total += len(col)
        data_quality = (filled / total * 100) if total else 0.0

        # Property type distribution
        property_types = {}
        if "property_type" in df_display.columns:
            vc = df_display["property_type"].astype("string").fillna("N/A").value_counts()
            property_types = {str(k): int(v) for k, v in vc.items() if k != "N/A"}

        # Top areas
        top_areas = []
        if "area" in df_display.columns:
            vc = df_display["area"].astype(str).replace("N/A", pd.NA).dropna().value_counts().head(10)
            top_areas = [{"area": str(k), "count": int(v)} for k, v in vc.items()]

        return AnalysisResponse(
            total_leads=total_leads,
            unique_contacts=unique_contacts,
            avg_price=avg_price,
            data_quality=data_quality,
            property_types=property_types,
            top_areas=top_areas
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download")
async def download_csv(rows: list[dict]):
    """
    Generate CSV file from extracted rows
    
    Args:
        rows: List of extracted property lead dictionaries
    
    Returns:
        CSV data as string
    """
    try:
        if not rows:
            raise HTTPException(status_code=400, detail="No rows provided")

        # Ensure all rows have all columns from OUTPUT_COLUMNS
        cleaned_rows = []
        for row in rows:
            cleaned_row = {col: row.get(col, "") for col in OUTPUT_COLUMNS}
            cleaned_rows.append(cleaned_row)
        
        df = pd.DataFrame(cleaned_rows, columns=OUTPUT_COLUMNS)
        df = normalize_df_types(df)
        df_display = apply_na_for_text_columns(df)
        csv_bytes = df_to_csv_bytes(df_display)
        csv_data = csv_bytes.decode("utf-8")

        return {"csv_data": csv_data, "filename": "property_leads.csv"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache")
async def get_combined_cache():
    """Get all rows in combined cache"""
    global combined_cache
    return {
        "cache_size": len(combined_cache),
        "rows": combined_cache
    }


@app.post("/api/cache/manage")
async def manage_cache(request: CombinedCacheRequest):
    """
    Manage combined cache
    
    Actions:
    - "add": Add rows to cache
    - "reset": Clear cache
    - "export": Export cache as CSV
    """
    global combined_cache

    try:
        if request.action == "reset":
            combined_cache = []
            return {"message": "Cache reset successfully", "cache_size": 0}

        elif request.action == "add":
            if not request.rows:
                raise HTTPException(status_code=400, detail="No rows provided")
            combined_cache = merge_combined_rows(combined_cache, request.rows)
            return {"message": f"Added {len(request.rows)} rows", "cache_size": len(combined_cache)}

        elif request.action == "export":
            if not combined_cache:
                raise HTTPException(status_code=400, detail="Cache is empty")
            
            # Ensure all rows have all columns from OUTPUT_COLUMNS
            cleaned_rows = []
            for row in combined_cache:
                cleaned_row = {col: row.get(col, "") for col in OUTPUT_COLUMNS}
                cleaned_rows.append(cleaned_row)
            
            df = pd.DataFrame(cleaned_rows, columns=OUTPUT_COLUMNS)
            df = normalize_df_types(df)
            df_display = apply_na_for_text_columns(df)
            csv_bytes = df_to_csv_bytes(df_display)
            csv_data = csv_bytes.decode("utf-8")
            return {"csv_data": csv_data, "filename": "combined_leads.csv"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= Run the app =============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
