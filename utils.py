from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from rapidfuzz import fuzz, process


WHITESPACE_RE = re.compile(r"[ \t\u00A0]+")
MULTILINE_BLANK_RE = re.compile(r"\n{3,}")


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = WHITESPACE_RE.sub(" ", text)
    text = MULTILINE_BLANK_RE.sub("\n\n", text)
    return text.strip()


def format_whatsapp_timestamps(text: str) -> str:
    """
    Normalize common WhatsApp timestamp variants into canonical format:
    [dd/mm, h:mm am/pm] Sender:

    Handles examples like:
    - 09/04, 2:49 pm - Easy Prop New:
    - 09/04/2026, 2:49 pm] Easy Prop New:
    - [09/04 2:49 pm] Easy Prop New:
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    line_re = re.compile(
        r"^\s*\[?(?P<date>\d{1,2}/\d{1,2}(?:/\d{2,4})?)\]?"
        r"\s*,?\s*"
        r"(?P<time>\d{1,2}:\d{2}\s*(?:am|pm))"
        r"\s*\]?\s*(?:-|–|—)?\s*"
        r"(?P<sender>[^:\n]{1,120})\s*:\s*$",
        re.IGNORECASE,
    )

    out_lines = []
    for raw_ln in text.split("\n"):
        ln = raw_ln.strip()
        m = line_re.match(ln)
        if not m:
            out_lines.append(raw_ln)
            continue
        date = m.group("date")
        # convert dd/mm/yyyy -> dd/mm
        if date.count("/") == 2:
            date = "/".join(date.split("/")[:2])
        ts = f"[{date}, {normalize_whitespace(m.group('time')).lower()}] {normalize_whitespace(m.group('sender'))}:"
        out_lines.append(ts)
    return "\n".join(out_lines)


def normalize_title(text: str) -> str:
    text = normalize_whitespace(text)
    if not text:
        return ""
    return " ".join(w[:1].upper() + w[1:].lower() if w else "" for w in text.split(" "))


PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?(?:0[\s-]?)?([6-9]\d{9})(?!\d)")


def extract_phone(text: str) -> str:
    if not text:
        return ""
    m = PHONE_RE.search(text)
    return m.group(1) if m else ""


PRICE_RE = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*(?P<suffix>k|lac|lakh|cr|crore)?\b",
    re.IGNORECASE,
)


def parse_price_to_int(text: str) -> Optional[int]:
    """
    Converts strings like '7.5 K', '20k', '1.2 lac', '0.8 cr' to integer rupees.
    Returns None if not parseable.
    """
    if not text:
        return None
    t = normalize_whitespace(text).lower()
    t = t.replace("₹", "").replace("rs.", "").replace("rs", "").replace("/-", "")
    m = PRICE_RE.search(t)
    if not m:
        return None
    num_raw = m.group("num").replace(",", ".")
    try:
        num = float(num_raw)
    except ValueError:
        return None
    suffix = (m.group("suffix") or "").lower()
    mult = 1
    if suffix == "k":
        mult = 1_000
    elif suffix in {"lac", "lakh"}:
        mult = 100_000
    elif suffix in {"cr", "crore"}:
        mult = 10_000_000
    return int(round(num * mult))


def first_non_empty(lines: Iterable[str]) -> str:
    for ln in lines:
        s = normalize_whitespace(ln)
        if s:
            return s
    return ""


def load_pune_areas(
    *,
    preferred_paths: Optional[list[str]] = None,
) -> list[str]:
    """
    Loads a pipe-separated Pune areas list.
    - Uses preferred_paths first (if provided).
    - Falls back to ./areas_pune.txt
    - Supports either '|' separated file or one area per line.
    """
    candidates: list[Path] = []
    if preferred_paths:
        candidates.extend(Path(p) for p in preferred_paths)
    candidates.append(Path(__file__).with_name("areas_pune.txt"))
    candidates.append(Path(__file__).with_name("areas_pune_villages.txt"))

    merged: list[str] = []
    for p in candidates:
        try:
            if not p.exists():
                continue
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        raw = normalize_whitespace(raw)
        if not raw:
            continue

        # split by pipes OR lines
        parts = []
        if "|" in raw:
            parts = [x.strip() for x in raw.split("|")]
        else:
            parts = [x.strip() for x in raw.split("\n")]

        cleaned: list[str] = []
        for part in parts:
            part = normalize_whitespace(part)
            if not part:
                continue
            # drop header-ish lines
            if part.lower() in {"all locations in pune", "abcdefghijklmnoprstuvwy", "abcdefghijklmnoprstuvwxyz"}:
                continue
            cleaned.append(part)

        merged.extend(cleaned)

    # de-dupe while preserving order across all files
    seen = set()
    uniq = []
    for a in merged:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq


@dataclass(frozen=True)
class AreaMatch:
    area: str
    score: int
    method: str  # exact/partial/fuzzy


def best_area_match(text: str, areas: list[str]) -> AreaMatch:
    """
    - Exact/substring match first (case-insensitive).
    - Then fuzzy (rapidfuzz WRatio) as fallback.
    Never returns 'Other' here; caller decides.
    """
    hay = normalize_whitespace(text).lower()
    if not hay or not areas:
        return AreaMatch(area="", score=0, method="none")

    # 1) Exact equality / word-boundary / contains checks
    best: Optional[AreaMatch] = None
    for a in areas:
        al = a.lower()
        if not al:
            continue
        if al == hay:
            return AreaMatch(area=a, score=100, method="exact")
        # Prefer strict word-boundary hits for short areas like "Baner", "Wakad"
        try:
            if re.search(rf"(?<!\w){re.escape(al)}(?!\w)", hay):
                cand = AreaMatch(area=a, score=95, method="partial")
                if best is None or (cand.score, len(al)) > (best.score, len(best.area)):
                    best = cand
                continue
        except re.error:
            pass

        if al in hay:
            # substring hit (multiword areas, punctuation variants)
            cand = AreaMatch(area=a, score=85, method="partial")
            if best is None or (cand.score, len(al)) > (best.score, len(best.area)):
                best = cand

    if best and best.score >= 70:
        return best

    # 2) Fuzzy fallback against tokens and full text
    # Use WRatio for robust matching on messy text.
    res = process.extractOne(hay, areas, scorer=fuzz.WRatio)
    if not res:
        return AreaMatch(area="", score=0, method="none")
    match, score, _idx = res
    return AreaMatch(area=match, score=int(score), method="fuzzy")


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

