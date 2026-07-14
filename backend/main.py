import os
import asyncio
import io
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from predict import predict_review
from signals.consistency import consistency_flag
from scraper.flipkart import fetch_reviews

DISCLAIMER = "Highlights suspicious review patterns; does not prove fraud."

app = FastAPI(title="Review Credibility Analyzer")

# CORS — origins from env, default "*"
_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in _origins.split(",")] if _origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Input models ──────────────────────────────────────────────────────────────

class AnalyzeIn(BaseModel):
    text: str
    rating: Optional[int] = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must not be empty")
        return v


class BatchIn(BaseModel):
    reviews: list[str]


class UrlIn(BaseModel):
    url: str
    max_reviews: Optional[int] = 50


# ── Helpers ───────────────────────────────────────────────────────────────────

def _summarize(results: list[dict]) -> dict:
    count = len(results)
    avg = round(sum(r["risk_score"] for r in results) / count, 2) if count else 0.0
    band_counts: dict[str, int] = {"Low": 0, "Moderate": 0, "High": 0}
    for r in results:
        band_counts[r["risk_band"]] = band_counts.get(r["risk_band"], 0) + 1
    return {"count": count, "avg_risk_score": avg, "band_counts": band_counts}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(body: AnalyzeIn):
    result = predict_review(body.text)
    if body.rating is not None:
        result["consistency_flag"] = consistency_flag(body.rating, body.text)
    return result


@app.post("/analyze-batch")
def analyze_batch(body: BatchIn):
    results = [predict_review(text) for text in body.reviews]
    return {"results": results, "summary": _summarize(results)}


@app.post("/analyze-csv")
async def analyze_csv(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")

    if "review_text" not in df.columns:
        raise HTTPException(status_code=422, detail="CSV must have a 'review_text' column")

    df = df.head(1000)  # ponytail: cap at 1000 rows per spec
    results = []
    for _, row in df.iterrows():
        text = str(row["review_text"])
        if not text.strip():
            continue
        res = predict_review(text)
        if "rating" in df.columns and pd.notna(row.get("rating")):
            try:
                res["consistency_flag"] = consistency_flag(int(row["rating"]), text)
            except (ValueError, TypeError):
                pass
        results.append(res)

    return {"results": results, "summary": _summarize(results)}


@app.post("/analyze-url")
async def analyze_url(body: UrlIn):
    try:
        raw_reviews = await fetch_reviews(body.url, body.max_reviews or 50)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")

    if not raw_reviews:
        raise HTTPException(
            status_code=502,
            detail="No reviews scraped. Flipkart selectors may need updating.",
        )

    results = []
    for rev in raw_reviews:
        res = predict_review(rev["text"])
        if rev.get("rating") is not None:
            res["consistency_flag"] = consistency_flag(rev["rating"], rev["text"])
        results.append(res)

    return {
        "product_url": body.url,
        "analyzed": len(results),
        "results": results,
        "summary": _summarize(results),
    }
