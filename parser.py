from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from utils import (
    AreaMatch,
    best_area_match,
    extract_phone,
    format_whatsapp_timestamps,
    load_pune_areas,
    normalize_title,
    normalize_whitespace,
    parse_price_to_int,
)


OUTPUT_COLUMNS = [
    "property_id",
    "property_type",
    "special_note",
    "owner_name",
    "owner_contact",
    "area",
    "address",
    "sub_property_type",
    "size",
    "furnishing_status",
    "availability",
    "floor",
    "tenant_preference",
    "additional_details",
    "age",
    "rent_or_sell_price",
    "deposit",
    "date_stamp",
    "rent_sold_out",
]


TIMESTAMP_BOUNDARY_RE = re.compile(
    r"^\[(?:\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*,\s*\d{1,2}:\d{2}\s*(?:am|pm)|\d{1,2}:\d{2}\s*(?:am|pm)\s*,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)\]\s*.*$",
    re.IGNORECASE | re.MULTILINE,
)

TIMESTAMP_DATE_FIRST_RE = re.compile(
    r"^\[(?P<date>\d{1,2}/\d{1,2})(?:/\d{2,4})?,\s*(?P<time>\d{1,2}:\d{2}\s*(?:am|pm))\]\s*(?P<header>.*)$",
    re.IGNORECASE,
)

TIMESTAMP_TIME_FIRST_RE = re.compile(
    r"^\[(?P<time>\d{1,2}:\d{2}\s*(?:am|pm))\s*,\s*(?P<date>\d{1,2}/\d{1,2})(?:/\d{2,4})?\]\s*(?P<header>.*)$",
    re.IGNORECASE,
)

DATE_LINE_START_RE = re.compile(
    r"^\s*[\"']?(?P<date>\d{1,2}[./-]\d{1,2}[./-]\d{2,4})[\"']?\s*(?P<rest>.*)$"
)


def _parse_timestamp_header_line(line: str) -> Optional[Dict[str, str]]:
    line = line.strip()
    m = TIMESTAMP_DATE_FIRST_RE.match(line)
    if m:
        return {
            "date": m.group("date"),
            "time": normalize_whitespace(m.group("time")).lower(),
            "header": normalize_whitespace(m.group("header") or ""),
        }
    m = TIMESTAMP_TIME_FIRST_RE.match(line)
    if m:
        return {
            "date": m.group("date"),
            "time": normalize_whitespace(m.group("time")).lower(),
            "header": normalize_whitespace(m.group("header") or ""),
        }
    return None


def _split_by_date_markers(raw_text: str) -> List[Dict[str, str]]:
    """
    Fallback splitter for copied chat blocks where WhatsApp headers may be
    missing/inconsistent, but each lead begins with a date line like 10.04.2026.
    """
    lines = raw_text.split("\n")
    if not lines:
        return []

    start_markers: List[Tuple[int, str, str]] = []
    for i, ln in enumerate(lines):
        m = DATE_LINE_START_RE.match(ln.strip())
        if not m:
            continue
        rest = normalize_whitespace(m.group("rest") or "")
        lookahead = "\n".join([rest] + lines[i + 1 : i + 6]).lower()
        if any(k in lookahead for k in ["rental property", "resale property", "online property", "property code", "owner"]):
            start_markers.append((i, m.group("date"), rest))

    if not start_markers:
        return []

    msgs: List[Dict[str, str]] = []
    for pos, (sidx, date_line, rest) in enumerate(start_markers):
        eidx = start_markers[pos + 1][0] if pos + 1 < len(start_markers) else len(lines)
        block_lines = lines[sidx:eidx]
        body_lines: List[str] = []
        if rest:
            body_lines.append(rest)
        if len(block_lines) > 1:
            body_lines.extend(block_lines[1:])
        raw_block = normalize_whitespace("\n".join([date_line] + body_lines))
        if not raw_block.strip():
            continue
        body = normalize_whitespace("\n".join(body_lines))
        msgs.append(
            {
                "date_stamp": date_line,
                "header": "",
                "body": body,
                "raw": raw_block,
            }
        )
    return msgs


def split_whatsapp_messages(raw_text: str) -> List[Dict[str, str]]:
    """
    Splits raw WhatsApp text into message chunks using timestamp headers like:
    [09/04, 2:49 pm] Easy Prop New:
    Returns list of {date_stamp, header, body, raw}.
    """
    raw_text = format_whatsapp_timestamps(raw_text)
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw_text:
        return []

    matches = list(TIMESTAMP_BOUNDARY_RE.finditer(raw_text))
    if not matches:
        # fallback 0: date-line based split for copied lead blocks
        date_msgs = _split_by_date_markers(raw_text)
        if date_msgs:
            return date_msgs

        # fallback 1: tabular/TSV-like rows from CRM exports
        tabular_msgs: List[Dict[str, str]] = []
        for ln in raw_text.split("\n"):
            if "\t" not in ln:
                continue
            cells = [c.strip() for c in re.split(r"\t+", ln) if c.strip()]
            if len(cells) < 6:
                continue
            owner = cells[0]
            phone = next((c for c in cells if extract_phone(c)), "")
            sell_or_rent = next((c.lower() for c in cells if c.lower() in {"sell", "rent"}), "")
            numeric_cells = [c for c in cells if re.fullmatch(r"\d{4,}", c)]
            # exclude likely mobile numbers; prefer large non-phone numeric as price
            price = next(
                (
                    c
                    for c in numeric_cells
                    if not (len(c) == 10 and c[0] in {"6", "7", "8", "9"})
                ),
                "",
            )
            bhk_candidate = next((c for c in cells if re.search(r"\b\d+\s*(?:bhk|rk)\b", c, re.IGNORECASE)), "")
            # Clean BHK: extract just the number + unit part
            bhk = ""
            if bhk_candidate:
                bhk_match = re.search(r"(\d+)\s*(?:bhk|rk)\b", bhk_candidate, re.IGNORECASE)
                bhk = f"{bhk_match.group(1)} BHK" if bhk_match else bhk_candidate
            size_candidate = next((c for c in cells if re.search(r"\bsq", c, re.IGNORECASE)), "")
            # Clean size: extract just the numeric + unit part, removing trailing noise like "1785 sq.ft /////"
            size = ""
            if size_candidate:
                size_match = re.search(r"([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(sq\.?\s*ft|sq\s*ft|sqft|sft|sf|sq\.?\s*m|sqm)", size_candidate, re.IGNORECASE)
                size = f"{size_match.group(1)} {size_match.group(2)}".strip() if size_match else size_candidate
            address = next((c for c in cells if "," in c and "pune" in c.lower()), "")
            area = ""
            if address:
                area = address.split(",")[0].strip()
            if not area:
                area = next((c.replace("P-", "").strip() for c in cells if c.lower().startswith("p-")), "")

            synthetic = "\n".join(
                [
                    "*Resale Property*" if sell_or_rent == "sell" else "*Rental Property*",
                    f"Owner Name: {owner}",
                    f"Contact: {phone}" if phone else "",
                    f"Area: {area}" if area else "",
                    f"Address: {address}" if address else "",
                    f"Type: {bhk}" if bhk else "",
                    f"Size: {size}" if size else "",
                    f"Price: {price}" if price else "",
                ]
            )
            tabular_msgs.append({"date_stamp": "", "header": "Tabular Lead", "body": synthetic, "raw": normalize_whitespace(ln)})
        if tabular_msgs:
            return tabular_msgs

        # fallback 2: treat entire text as one message
        return [{"date_stamp": "", "header": "", "body": raw_text, "raw": raw_text}]

    msgs: List[Dict[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        chunk = raw_text[start:end].strip()
        body = raw_text[m.end() : end].strip()
        header_line = raw_text[m.start() : m.end()].strip()
        parsed_header = _parse_timestamp_header_line(header_line)
        if not parsed_header:
            continue
        date_stamp = f"{parsed_header['date']}, {parsed_header['time']}"
        header = parsed_header["header"]
        if not body and not header:
            continue
        if chunk:
            msgs.append(
                {
                    "date_stamp": date_stamp,
                    "header": header,
                    "body": body,
                    "raw": chunk,
                }
            )
    msgs = [m for m in msgs if normalize_whitespace(m.get("raw", ""))]
    # If we got only one chunk, try date-marker split as a stronger fallback.
    if len(msgs) <= 1:
        date_msgs = _split_by_date_markers(raw_text)
        if len(date_msgs) > len(msgs):
            return date_msgs
    return msgs


PROPERTY_CODE_RE = re.compile(
    r"^\s*property\s*(?:code|id)\b\s*[:\-]?[ \t]*([A-Za-z0-9\-_\/]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

OWNER_LINE_RE = re.compile(r"^\s*owner\b\s*[:\-]?\s*(.+)$", re.IGNORECASE)
OWNER_NAME_LINE_RE = re.compile(r"^\s*owner\s*(?:name)?\b\s*[:\-]?\s*(.+)$", re.IGNORECASE)
CONTACT_LINE_RE = re.compile(r"^\s*(?:owner\s*)?(?:mobile|phone|contact|number|no)\b\s*[:\-]?\s*(.+)$", re.IGNORECASE)

SUB_TYPE_RE = re.compile(r"\b(\d+)\s*(bhk|rk)\b", re.IGNORECASE)

SIZE_RE = re.compile(
    r"\b(?:carpet\s*area|super\s*built[-\s]*up(?:\s*area)?|builtup(?:\s*area)?|built\s*up(?:\s*area)?|area|size)\b\s*[:\-]?\s*([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(sq\.?\s*ft|sq\s*ft|sqft|sft|sf|sq\.?\s*m|sqm)?",
    re.IGNORECASE,
)
SIZE_INLINE_RE = re.compile(
    r"\b([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(sq\.?\s*ft|sq\s*ft|sqft|sft|sf|sq\.?\s*m|sqm)\b",
    re.IGNORECASE,
)
SIZE_CARPET_RE = re.compile(r"\b(?:carpet|super\s*built[-\s]*up|builtup|built\s*up)\b\s*[:\-]?\s*([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]+)?)\b", re.IGNORECASE)
SIZE_AFTER_LABEL_RE = re.compile(
    r"\b(?:carpet|super\s*built[-\s]*up|builtup|built\s*up)\s*area?\s*[:\-]?\s*([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]+)?)\b",
    re.IGNORECASE,
)

FURNISHING_RE = re.compile(r"\b(semi\s*furnished|furnished|unfurnished)\b", re.IGNORECASE)

AVAILABILITY_RE = re.compile(r"\b(immediately|available\s*now|ready\s*to\s*move|rtm)\b", re.IGNORECASE)

RENT_RE = re.compile(r"\b(?:rent|price)\b\s*[:\-]?\s*([₹\s0-9.,]+(?:\s*(?:k|lac|lakh|cr|crore))?)\b", re.IGNORECASE)
SELL_PRICE_RE = re.compile(
    r"\b(?:sell|sale|selling|expected|budget|final)\s*(?:price|amount)?\b\s*[:\-]?\s*([₹\s0-9.,]+(?:\s*(?:k|lac|lakh|cr|crore))?)\b",
    re.IGNORECASE,
)
MONEY_FALLBACK_RE = re.compile(r"(₹?\s*\d+(?:[.,]\d+)?\s*(?:k|lac|lakh|cr|crore)?(?:\s*/-)?)", re.IGNORECASE)
DATE_SLASH_RE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
MONEY_TOKEN_RE = re.compile(r"₹?\s*\d+(?:[.,]\d+)?\s*(?:k|lac|lakh|cr|crore)?(?:\s*/-)?", re.IGNORECASE)

DEPOSIT_RE = re.compile(r"\b(?:deposit|dep)\b\s*[:\-]?\s*([₹\s0-9.,]+(?:\s*(?:k|lac|lakh|cr|crore))?)\b", re.IGNORECASE)

FLOOR_LINE_RE = re.compile(r"\bfloor\b\s*[:\-]?\s*([^,;|]+)", re.IGNORECASE)
FLOOR_VALUE_RE = re.compile(r"\b((?:g|gf|ground|upper\s*ground|ug|lower\s*ground|lg|\d{1,2}(?:st|nd|rd|th)?)(?:\s*(?:floor|flr))?)\b", re.IGNORECASE)
ON_FLOOR_RE = re.compile(r"\bon\s+(\d{1,2}(?:st|nd|rd|th)?|g|gf|ground)\s*(?:floor|flr)?\b", re.IGNORECASE)

TENANT_PREF_RE = re.compile(r"\b(?:tenant\s*pref(?:erence)?|preferred)\b\s*[:\-]?\s*(.+)$", re.IGNORECASE)

AGE_RE = re.compile(r"\b(?:age|property\s*age)\b\s*[:\-]?\s*([0-9]{1,2})\s*(?:yrs?|years?)?\b", re.IGNORECASE)


ADDRESS_KEYWORDS = [
    "flat",
    "apt",
    "apartment",
    "society",
    "tower",
    "wing",
    "building",
    "bldg",
    "house",
    "bungalow",
    "villa",
    "lane",
    "road",
    "rd",
    "chowk",
    "near",
    "opp",
    "opposite",
    "behind",
    "phase",
    "nagar",
    "colony",
    "pune",
]


def _looks_like_address_line(ln: str) -> bool:
    l = ln.lower()
    if "," in l:
        return True
    return any(k in l for k in ADDRESS_KEYWORDS)


def _build_rich_address(lines: List[str], area: str) -> str:
    """
    Build a richer address by combining apartment/house/society lines
    around the line that contains detected area.
    """
    if not lines:
        return ""

    area_l = area.lower().strip() if area else ""
    area_idx = -1
    if area_l:
        for i, ln in enumerate(lines):
            if area_l in ln.lower():
                area_idx = i
                break

    # Collect candidates around area line first
    candidates: List[str] = []
    if area_idx >= 0:
        start = max(0, area_idx - 2)
        end = min(len(lines), area_idx + 3)
        for i in range(start, end):
            ln = normalize_whitespace(lines[i])
            if not ln:
                continue
            if _looks_like_address_line(ln):
                candidates.append(ln)

    # If still weak, add global address-like lines
    if len(candidates) < 2:
        for ln in lines:
            ln = normalize_whitespace(ln)
            if not ln:
                continue
            if _looks_like_address_line(ln):
                candidates.append(ln)

    # De-duplicate while preserving order
    dedup: List[str] = []
    seen = set()
    for c in candidates:
        k = c.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(c)

    if not dedup:
        return ""

    # Prefer first 2-3 useful chunks for concise but rich address
    address = ", ".join(dedup[:3])
    address = re.sub(r"\s*,\s*,+", ", ", address).strip(" ,")
    return address[:220]


def _infer_area_from_lines(lines: List[str], areas: List[str]) -> str:
    if not lines or not areas:
        return ""
    # Try most location-like lines first.
    candidates = [ln for ln in lines if _looks_like_address_line(ln)]
    if not candidates:
        candidates = lines
    best_area = ""
    best_score = 0
    for ln in candidates:
        m = best_area_match(ln, areas)
        if m.area and m.score > best_score:
            best_area = m.area
            best_score = m.score
    # Lower threshold slightly for fallback to reduce false "missing area"
    return best_area if best_score >= 55 else ""


def _strip_embedded_timestamps(text: str) -> str:
    # Remove WhatsApp-like timestamp fragments so year values are not treated as prices.
    text = re.sub(
        r"\[?\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*,?\s*\d{1,2}:\d{2}\s*(?:am|pm)\]?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _normalize_size_unit(unit_raw: str) -> str:
    unit = unit_raw.replace(" ", "").lower()
    if unit in {"sqft", "sq.ft", "sft", "sf"}:
        return "sq.ft"
    if unit in {"sqm", "sq.m"}:
        return "sq.m"
    return unit_raw.strip() or "sq.ft"


def _normalize_floor(value: str) -> str:
    v = normalize_whitespace(value).lower()
    v = v.replace("flr", "floor")
    mapping = {
        "g": "Ground Floor",
        "gf": "Ground Floor",
        "ground": "Ground Floor",
        "ug": "Upper Ground Floor",
        "upper ground": "Upper Ground Floor",
        "lg": "Lower Ground Floor",
        "lower ground": "Lower Ground Floor",
    }
    if v in mapping:
        return mapping[v]
    # 3rd floor -> 3rd Floor
    m = re.match(r"^(\d{1,2}(?:st|nd|rd|th)?)\s*floor?$", v)
    if m:
        return f"{m.group(1)} Floor"
    m2 = re.match(r"^(\d{1,2}(?:st|nd|rd|th)?)$", v)
    if m2:
        return f"{m2.group(1)} Floor"
    return normalize_title(value)


def _normalize_furnishing(value: str) -> str:
    v = normalize_whitespace(value).lower().replace("_", " ").replace("-", " ")
    v = re.sub(r"\s+", " ", v).strip()
    if not v:
        return ""
    if "semi" in v and "furnished" in v:
        return "Semi-Furnished"
    if "unfurnished" in v or ("un" in v and "furnished" in v):
        return "Unfurnished"
    if "furnished" in v:
        return "Furnished"
    return normalize_title(value)


def _is_likely_money_line(ln: str) -> bool:
    s = normalize_whitespace(ln)
    if not s:
        return False
    if re.search(r"(bhk|sq|owner|property\s*code|floor|area)", s, re.IGNORECASE):
        return False
    return bool(re.fullmatch(r"[₹\s0-9.,/-]+(?:k|lac|lakh|cr|crore)?", s, flags=re.IGNORECASE))


def _extract_size(lines: List[str]) -> str:
    # Parse line-by-line to avoid crossing into price lines like "1.5 Cr".
    for ln in lines:
        mz = SIZE_RE.search(ln)
        if mz:
            val = mz.group(1).replace(",", "")
            unit = _normalize_size_unit(mz.group(2) or "sq.ft")
            return f"{val} {unit}".strip()
    for ln in lines:
        mi = SIZE_INLINE_RE.search(ln)
        if mi:
            val = mi.group(1).replace(",", "")
            unit = _normalize_size_unit(mi.group(2))
            return f"{val} {unit}".strip()
    for ln in lines:
        mc = SIZE_CARPET_RE.search(ln)
        if mc:
            return f"{mc.group(1).replace(',', '')} sq.ft"
    for ln in lines:
        ml = SIZE_AFTER_LABEL_RE.search(ln)
        if ml:
            return f"{ml.group(1).replace(',', '')} sq.ft"
    return ""


def _extract_prices(lines: List[str], full_text: str) -> Tuple[Optional[int], Optional[int]]:
    rent_val: Optional[int] = None
    dep_val: Optional[int] = None

    # 1) Labeled lines first
    for ln in lines:
        md = DEPOSIT_RE.search(ln)
        if md and dep_val is None:
            dep_val = parse_price_to_int(md.group(1))
        mr = RENT_RE.search(ln) or SELL_PRICE_RE.search(ln)
        if mr and rent_val is None:
            rent_val = parse_price_to_int(mr.group(1))

    # 2) Unlabeled numeric lines (common WhatsApp format: rent line then deposit line)
    money_candidates: List[int] = []
    for ln in lines:
        if not _is_likely_money_line(ln):
            continue
        for mt in MONEY_TOKEN_RE.findall(ln):
            parsed = parse_price_to_int(mt)
            if parsed is None:
                continue
            digits_only = re.sub(r"\D", "", mt)
            if len(digits_only) == 10 and digits_only[0] in {"6", "7", "8", "9"}:
                continue
            # skip 4-digit year-like values
            if 1900 <= parsed <= 2100:
                continue
            money_candidates.append(parsed)

    if rent_val is None and money_candidates:
        rent_val = money_candidates[0]
    if dep_val is None and len(money_candidates) >= 2:
        dep_val = money_candidates[1]

    # 2b) Deposit in month format, e.g. "2 Month", "2 months"
    if dep_val is None and rent_val:
        for ln in lines:
            mmo = re.search(r"\b(\d+(?:\.\d+)?)\s*months?\b", ln, flags=re.IGNORECASE)
            if mmo:
                try:
                    months = float(mmo.group(1))
                    if months > 0:
                        dep_val = int(round(rent_val * months))
                        break
                except ValueError:
                    pass

    # 3) final fallback for rent only, from whole text
    if rent_val is None:
        money_scan_text = _strip_embedded_timestamps(full_text)
        for mm in MONEY_FALLBACK_RE.finditer(money_scan_text):
            value_text = mm.group(1)
            left = money_scan_text[max(0, mm.start() - 25) : mm.start()].lower()
            right = money_scan_text[mm.end() : min(len(money_scan_text), mm.end() + 15)].lower()
            if "deposit" in left or "deposit" in right:
                continue
            if "contact" in left or "mobile" in left or "phone" in left or "owner" in left:
                continue
            if "sq" in right or "sq" in left:
                continue
            digits_only = re.sub(r"\D", "", value_text)
            if len(digits_only) == 10 and digits_only[0] in {"6", "7", "8", "9"}:
                continue
            if digits_only.isdigit() and len(digits_only) == 4 and 1900 <= int(digits_only) <= 2100:
                continue
            if DATE_SLASH_RE.search(value_text):
                continue
            parsed = parse_price_to_int(value_text)
            if parsed is not None and parsed >= 1000:
                rent_val = parsed
                break

    return rent_val, dep_val


def _extract_tenant_preference(lines: List[str], full_text: str) -> str:
    """
    Extract tenant preference from natural WhatsApp phrases such as:
    - Family / Bachelor
    - Family Only
    - Bachelors (Women Only)
    - All
    """
    text = "\n".join(lines) if lines else full_text
    t = text.lower()

    has_all = bool(re.search(r"\ball\b", t))
    has_family = bool(re.search(r"\bfamily\b", t))
    has_bachelor = bool(re.search(r"\bbachelor[s]?\b", t))
    women_only = bool(re.search(r"\b(?:women|ladies)\s*only\b", t))
    men_only = bool(re.search(r"\bmen\s*only\b", t))

    # explicit label still takes priority if present
    mtp = TENANT_PREF_RE.search(text)
    if mtp:
        val = normalize_whitespace(mtp.group(1))
        if val:
            return val

    if has_all:
        return "All"
    if has_family and has_bachelor:
        if women_only:
            return "Family, Bachelors (Women Only)"
        if men_only:
            return "Family, Bachelors (Men Only)"
        return "Family, Bachelors"
    if has_family:
        if re.search(r"\bfamily\s*only\b", t):
            return "Family Only"
        return "Family"
    if has_bachelor:
        if women_only:
            return "Bachelors (Women Only)"
        if men_only:
            return "Bachelors (Men Only)"
        return "Bachelors"
    return ""


def _derive_rent_sold_out(text: str) -> str:
    t = text.lower()
    if "rent out" in t or "rented out" in t or "let out" in t:
        return "Rent Out"
    if "sold out" in t or "sold" in t:
        return "Sold Out"
    return ""


def _suspicious_fields(row: Dict[str, Any], text: str) -> List[str]:
    s: List[str] = []
    rn = row.get("rent_or_sell_price") or 0
    dep = row.get("deposit") or 0
    name = str(row.get("owner_name", "")).strip().lower()
    size = str(row.get("size", "")).strip()

    if name in {"owner", "property code", ""}:
        s.append("owner_name")
    if row.get("property_type") == "Res_rental" and isinstance(rn, int) and rn >= 1_000_000:
        s.append("rent_or_sell_price")
    if row.get("property_type") == "Res_resale" and isinstance(rn, int) and rn <= 100_000:
        s.append("rent_or_sell_price")
    if not size and re.search(r"\bsq\.?\s*ft|sqft|sft|carpet|built\s*up\b", text, re.IGNORECASE):
        s.append("size")
    if not dep and row.get("property_type") == "Res_rental":
        if len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:k|lac|lakh|cr|crore)\b", text, re.IGNORECASE)) >= 2:
            s.append("deposit")
    return s


def _extract_floor(lines: List[str], full_text: str) -> str:
    # 1) Labeled floor lines first (line-safe; do not bleed into next line)
    for ln in lines:
        m = FLOOR_LINE_RE.search(ln)
        if m:
            return _normalize_floor(m.group(1)[:80])

    # 2) "on 5th floor" style
    mo = ON_FLOOR_RE.search(full_text)
    if mo:
        return _normalize_floor(mo.group(1))

    # 3) Standalone floor value lines like "GF", "Ground"
    for ln in lines:
        ll = normalize_whitespace(ln).lower()
        if ll in {"g", "gf", "ground", "ug", "upper ground", "lg", "lower ground"}:
            return _normalize_floor(ll)

    # 4) Inline floor token in relevant lines
    for ln in lines:
        ll = ln.lower()
        if "tower" in ll or "wing" in ll or "floor" in ll or "flr" in ll:
            mv = FLOOR_VALUE_RE.search(ln)
            if mv:
                return _normalize_floor(mv.group(1))
    return ""


def _clean_person_name(name: str) -> str:
    cleaned = normalize_whitespace(name)
    cleaned = re.sub(r"\b(?:owner|contact|mobile|phone|number|no)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\[\]\(\)\-:|,]+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return normalize_title(cleaned)


def _extract_owner_details(lines: List[str], full_text: str) -> Tuple[str, str]:
    """
    Advanced owner extraction:
    - Owner / Owner Name lines
    - Contact/Mobile/Phone lines
    - Split lines where name and phone appear separately
    - Fallback to nearby phone + best candidate person-like text
    """
    owner_name = ""
    owner_contact = ""

    # Pass 1: labeled lines
    for idx, ln in enumerate(lines):
        mo = OWNER_NAME_LINE_RE.match(ln) or OWNER_LINE_RE.match(ln)
        if mo:
            val = mo.group(1).strip()
            ph = extract_phone(val)
            if ph and not owner_contact:
                owner_contact = ph
            val_wo_phone = val
            if ph:
                val_wo_phone = re.sub(re.escape(ph), " ", val_wo_phone)
            cand_name = _clean_person_name(val_wo_phone)
            if cand_name and len(cand_name) >= 2:
                owner_name = cand_name
            # phone may be on next line
            if idx + 1 < len(lines) and not owner_contact:
                owner_contact = extract_phone(lines[idx + 1]) or owner_contact
            break

    for ln in lines:
        mc = CONTACT_LINE_RE.match(ln)
        if mc:
            ph = extract_phone(mc.group(1).strip())
            if ph:
                owner_contact = ph
                break

    # Pass 2: if still missing contact, find first plausible phone in text
    if not owner_contact:
        owner_contact = extract_phone(full_text)

    # Pass 3: if still missing name, infer from line near phone
    if not owner_name:
        for idx, ln in enumerate(lines):
            if owner_contact and owner_contact in ln:
                # same line text around phone
                around = re.sub(re.escape(owner_contact), " ", ln)
                cand = _clean_person_name(around)
                if cand and len(cand) >= 2:
                    owner_name = cand
                    break
                # previous line often contains owner name
                if idx > 0:
                    prev = _clean_person_name(lines[idx - 1])
                    if prev and len(prev.split()) <= 4:
                        owner_name = prev
                        break

    # final guard to avoid garbage names
    if owner_name and re.search(r"\d", owner_name):
        owner_name = re.sub(r"\d+", " ", owner_name).strip()
        owner_name = normalize_title(owner_name)

    return owner_name, owner_contact


def _default_row(date_stamp: str) -> Dict[str, Any]:
    return {
        "property_id": "",
        "property_type": "Res_rental",
        "special_note": "",
        "owner_name": "",
        "owner_contact": "",
        "area": "",
        "address": "",
        "sub_property_type": "",
        "size": "",
        "furnishing_status": "",
        "availability": "",
        "floor": "",
        "tenant_preference": "",
        "additional_details": "",
        "age": "",
        "rent_or_sell_price": None,
        "deposit": None,
        "date_stamp": date_stamp,
        "rent_sold_out": "",
    }


def rule_parse_message(msg: Dict[str, str], areas: List[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns (row, debug) where debug contains intermediate parsing notes.
    """
    date_stamp = msg.get("date_stamp", "")
    text = normalize_whitespace("\n".join([msg.get("header", ""), msg.get("body", "")]))
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    row = _default_row(date_stamp=date_stamp)
    debug: Dict[str, Any] = {"area_match": None, "notes": []}

    # property type
    if re.search(r"\bresale\s*property\b", text, re.IGNORECASE):
        row["property_type"] = "Res_resale"
    elif re.search(r"\brental\s*property\b", text, re.IGNORECASE):
        row["property_type"] = "Res_rental"

    # property_id
    m = PROPERTY_CODE_RE.search(text)
    if m:
        row["property_id"] = m.group(1).strip()

    # owner (advanced extraction)
    owner_name, owner_contact = _extract_owner_details(lines, text)
    row["owner_name"] = owner_name
    row["owner_contact"] = owner_contact

    # sub_property_type
    ms = SUB_TYPE_RE.search(text)
    if ms:
        row["sub_property_type"] = f"{ms.group(1)} {ms.group(2).upper()}"

    # size
    row["size"] = _extract_size(lines)

    # furnishing
    mf = FURNISHING_RE.search(text)
    if mf:
        row["furnishing_status"] = normalize_title(mf.group(1))

    # availability
    ma = AVAILABILITY_RE.search(text)
    if ma:
        av = ma.group(1).lower()
        if av == "rtm":
            row["availability"] = "Ready to move"
        else:
            row["availability"] = normalize_title(av)

    # rent / deposit
    rent_val, dep_val = _extract_prices(lines, text)
    if rent_val is not None:
        row["rent_or_sell_price"] = rent_val
    if dep_val is not None:
        row["deposit"] = dep_val

    # floor
    row["floor"] = _extract_floor(lines, text)

    # age
    mage = AGE_RE.search(text)
    if mage:
        row["age"] = mage.group(1)

    # tenant preference
    row["tenant_preference"] = _extract_tenant_preference(lines, text)[:120]
    row["rent_sold_out"] = _derive_rent_sold_out(text)

    # area + address (major fix)
    area_match = best_area_match(text, areas)
    debug["area_match"] = area_match.__dict__ if isinstance(area_match, AreaMatch) else None
    if area_match.area and area_match.score >= 75:
        row["area"] = area_match.area
    elif area_match.area and area_match.score >= 60:
        # still prefer not returning Other; keep match but flag lower confidence
        row["area"] = area_match.area
        debug["notes"].append(f"Low-confidence area match ({area_match.score})")
    if not row["area"]:
        row["area"] = _infer_area_from_lines(lines, areas)

    # address heuristic: build richer address including apartment/house context
    row["address"] = _build_rich_address(lines, row["area"])
    if not row["address"] and row["area"]:
        row["address"] = row["area"]

    # additional_details: keep full text (trimmed) for CRM traceability
    row["additional_details"] = text[:600]

    return row, debug


IMPORTANT_FIELDS = ["owner_name", "owner_contact", "area", "address", "rent_or_sell_price", "deposit"]


def missing_important_fields(row: Dict[str, Any]) -> List[str]:
    missing = []
    for k in IMPORTANT_FIELDS:
        v = row.get(k, "")
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(k)
        elif k in {"rent_or_sell_price", "deposit"} and (v == "" or v == 0):
            missing.append(k)
    return missing


def _groq_extract_batch(
    *,
    messages: List[Dict[str, str]],
    api_key: str,
    model: str,
    timeout_s: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Calls Groq once for multiple messages. Returns list aligned to messages (same length).
    """
    from groq import Groq  # imported lazily

    client = Groq(api_key=api_key, timeout=timeout_s)

    payload = []
    for i, m in enumerate(messages):
        payload.append(
            {
                "idx": i,
                "text": normalize_whitespace("\n".join([m.get("header", ""), m.get("body", "")])),
            }
        )

    prompt = (
        "You extract real-estate fields from WhatsApp property leads.\n"
        "Return ONLY a valid JSON array. No markdown, no commentary.\n"
        "Each array item must be an object with keys:\n"
        "owner_name, owner_contact, area, address, rent, deposit, tenant_preference, size, floor, rent_sold_out, property_type\n"
        "Output array length must equal input items length; keep order.\n"
        "If a field is unknown, return empty string.\n\n"
        f"INPUT_ITEMS={json.dumps(payload, ensure_ascii=False)}"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    content = (resp.choices[0].message.content or "").strip()
    data = json.loads(content)
    if not isinstance(data, list) or len(data) != len(messages):
        raise ValueError("Groq returned invalid JSON array shape")
    return data


def process_raw_text(
    raw_text: str,
    *,
    enable_ai_fallback: bool = False,
    groq_api_key: str = "",
    groq_model: str = "llama-3.1-70b-versatile",
    area_paths: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    End-to-end pipeline (without any Streamlit code).
    Returns (rows, meta) where meta includes logs and failures.
    """
    areas = load_pune_areas(preferred_paths=area_paths)
    msgs = split_whatsapp_messages(raw_text)

    rows_by_msg_idx: List[Optional[Dict[str, Any]]] = [None] * len(msgs)
    failures: List[Dict[str, Any]] = []
    debugs: List[Dict[str, Any]] = []

    # Rule parse all
    needs_ai: List[int] = []
    suspicious_by_idx: Dict[int, List[str]] = {}
    for idx, msg in enumerate(msgs):
        if not normalize_whitespace(msg.get("raw", "")):
            debugs.append({"idx": idx, "skipped": True, "missing": IMPORTANT_FIELDS[:]})
            continue
        row, debug = rule_parse_message(msg, areas)
        miss = missing_important_fields(row)
        susp = _suspicious_fields(row, normalize_whitespace("\n".join([msg.get("header", ""), msg.get("body", "")])))
        suspicious_by_idx[idx] = susp
        debug["missing"] = miss
        debug["suspicious"] = susp
        debugs.append(
            {
                "idx": idx,
                "date_stamp": msg.get("date_stamp", ""),
                "raw_preview": normalize_whitespace(msg.get("raw", ""))[:400],
                **debug,
            }
        )
        if miss or susp:
            needs_ai.append(idx)
        rows_by_msg_idx[idx] = row

    # AI fallback (batched; on missing or suspicious rows)
    ai_used = False
    if enable_ai_fallback and needs_ai and groq_api_key.strip():
        try:
            batch_msgs = [msgs[i] for i in needs_ai]
            ai_out = _groq_extract_batch(messages=batch_msgs, api_key=groq_api_key, model=groq_model)
            ai_used = True

            for local_i, global_idx in enumerate(needs_ai):
                out = ai_out[local_i] if local_i < len(ai_out) else {}
                if not isinstance(out, dict):
                    continue

                row = rows_by_msg_idx[global_idx]
                if row is None:
                    continue
                suspicious = set(suspicious_by_idx.get(global_idx, []))

                # merge rules: only fill blanks
                if not row.get("owner_name") or "owner_name" in suspicious:
                    row["owner_name"] = normalize_title(str(out.get("owner_name", "")).strip())
                if not row.get("owner_contact") or "owner_contact" in suspicious:
                    row["owner_contact"] = extract_phone(str(out.get("owner_contact", "")).strip()) or str(out.get("owner_contact", "")).strip()
                if not row.get("area") or "area" in suspicious:
                    row["area"] = str(out.get("area", "")).strip()
                if not row.get("address") or "address" in suspicious:
                    row["address"] = normalize_whitespace(str(out.get("address", "")).strip())

                if (not row.get("rent_or_sell_price")) or ("rent_or_sell_price" in suspicious):
                    rp = parse_price_to_int(str(out.get("rent", "")).strip())
                    if rp is not None:
                        row["rent_or_sell_price"] = rp
                if (not row.get("deposit")) or ("deposit" in suspicious):
                    dp = parse_price_to_int(str(out.get("deposit", "")).strip())
                    if dp is not None:
                        row["deposit"] = dp
                if (not row.get("tenant_preference")) or ("tenant_preference" in suspicious):
                    row["tenant_preference"] = normalize_whitespace(str(out.get("tenant_preference", "")).strip())
                if (not row.get("size")) or ("size" in suspicious):
                    row["size"] = normalize_whitespace(str(out.get("size", "")).strip())
                if (not row.get("floor")) or ("floor" in suspicious):
                    row["floor"] = normalize_whitespace(str(out.get("floor", "")).strip())
                if not row.get("rent_sold_out"):
                    row["rent_sold_out"] = normalize_whitespace(str(out.get("rent_sold_out", "")).strip())
                if row.get("property_type") == "Res_rental":
                    ptype = normalize_whitespace(str(out.get("property_type", "")).strip()).lower()
                    if "resale" in ptype or "sell" in ptype:
                        row["property_type"] = "Res_resale"

        except Exception as e:
            failures.append({"stage": "ai_fallback", "error": str(e), "count": len(needs_ai)})

    # Final normalization and strict columns
    final_rows: List[Dict[str, Any]] = []
    seen_property_ids: set[str] = set()
    audit_failed: List[Dict[str, Any]] = []
    for idx, msg in enumerate(msgs):
        r = rows_by_msg_idx[idx]
        if r is None:
            continue
        out = {c: r.get(c, "") for c in OUTPUT_COLUMNS}
        out["owner_name"] = normalize_title(str(out.get("owner_name", "")))
        out["area"] = normalize_whitespace(str(out.get("area", "")))
        out["address"] = normalize_whitespace(str(out.get("address", "")))
        out["furnishing_status"] = _normalize_furnishing(str(out.get("furnishing_status", "")))
        out["availability"] = normalize_title(str(out.get("availability", "")))
        out["floor"] = _normalize_floor(str(out.get("floor", ""))) if str(out.get("floor", "")).strip() else ""
        out["rent_or_sell_price"] = out.get("rent_or_sell_price") or None
        out["deposit"] = out.get("deposit") or None

        # Auto-assign random unique property_id if missing
        pid = normalize_whitespace(str(out.get("property_id", "")))
        if not pid:
            pid = f"PROP-{uuid.uuid4().hex[:10].upper()}"
        while pid in seen_property_ids:
            pid = f"PROP-{uuid.uuid4().hex[:10].upper()}"
        out["property_id"] = pid
        seen_property_ids.add(pid)

        # If still empty, keep blank (do not force "Other")
        final_rows.append(out)

        miss_after = missing_important_fields(out)
        if miss_after:
            audit_failed.append(
                {
                    "idx": idx,
                    "date_stamp": msg.get("date_stamp", ""),
                    "missing_fields": ", ".join(miss_after),
                    "raw_message": normalize_whitespace(msg.get("raw", ""))[:1200],
                }
            )

    meta = {
        "message_count": len(msgs),
        "parsed_count": len(final_rows),
        "ai_used": ai_used,
        "ai_candidates": len(needs_ai),
        "failures": failures,
        "audit_failed": audit_failed,
        "debug": debugs[:200],  # cap
        "areas_loaded": len(areas),
    }
    return final_rows, meta

