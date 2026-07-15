import os
import io
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from predict import predict_review
from signals.consistency import consistency_flag
from scraper.reviews_api import fetch_reviews, detect_marketplace, UnsupportedMarketplace, BlockedError

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
    max_reviews: Optional[int] = 30  # Default to 30 per spec


# ── Helpers ───────────────────────────────────────────────────────────────────

HIGH_RISK_THRESHOLD = 70

def _summarize(results: list[dict]) -> dict:
    count = len(results)
    avg = round(sum(r["risk_score"] for r in results) / count, 2) if count else 0.0
    band_counts: dict[str, int] = {"Low": 0, "Moderate": 0, "High": 0}
    for r in results:
        band_counts[r["risk_band"]] = band_counts.get(r["risk_band"], 0) + 1
    return {"count": count, "avg_risk_score": avg, "band_counts": band_counts}


def _summarize_batch(results: list[dict], submitted_count: int, analyzed_count: int, skipped_count: int) -> dict:
    if not analyzed_count:
        return {
            "reviews_submitted": submitted_count,
            "reviews_analyzed": 0,
            "reviews_skipped": skipped_count,
            "overall_risk_score": 0.0,
            "overall_band": "Low",
            "count_flagged": 0,
            "pct_computer_generated": 0.0,
            "distribution": {"Low": 0, "Moderate": 0, "High": 0}
        }
        
    overall_score = round(sum(r["risk_score"] for r in results) / analyzed_count, 2)
    
    if overall_score < 40:
        overall_band = "Low"
    elif overall_score < 70:
        overall_band = "Moderate"
    else:
        overall_band = "High"
        
    count_flagged = sum(1 for r in results if r["risk_score"] >= HIGH_RISK_THRESHOLD)
    pct_cg = round((count_flagged / analyzed_count) * 100, 1)
    
    distribution = {"Low": 0, "Moderate": 0, "High": 0}
    for r in results:
        distribution[r["risk_band"]] += 1
        
    return {
        "reviews_submitted": submitted_count,
        "reviews_analyzed": analyzed_count,
        "reviews_skipped": skipped_count,
        "overall_risk_score": overall_score,
        "overall_band": overall_band,
        "count_flagged": count_flagged,
        "pct_computer_generated": pct_cg,
        "distribution": distribution
    }


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
    submitted = len(body.reviews)
    analyzed_reviews = []
    skipped = 0
    for r in body.reviews:
        if r and r.strip():
            analyzed_reviews.append(r)
        else:
            skipped += 1
            
    if not analyzed_reviews:
        return {
            "message": "No valid review text found",
            "results": [],
            "summary": {
                "reviews_submitted": submitted,
                "reviews_analyzed": 0,
                "reviews_skipped": skipped,
                "overall_risk_score": 0.0,
                "overall_band": "Low",
                "count_flagged": 0,
                "pct_computer_generated": 0.0,
                "distribution": {"Low": 0, "Moderate": 0, "High": 0}
            },
            "disclaimer": DISCLAIMER
        }
        
    results = [predict_review(text) for text in analyzed_reviews]
    summary = _summarize_batch(results, submitted, len(results), skipped)
    return {
        "results": results,
        "summary": summary,
        "disclaimer": DISCLAIMER
    }



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
    # Detect marketplace
    mp = detect_marketplace(body.url)
    if not mp:
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Supported site is Flipkart."
        )
    if mp != "flipkart":
        raise HTTPException(
            status_code=400,
            detail=f"{mp.capitalize()} support is coming soon."
        )

    # Fetch reviews via local Playwright
    try:
        raw_reviews = await fetch_reviews(body.url, max_results=body.max_reviews or 30)
    except BlockedError:
        return {
            "message": "Flipkart blocked this request; run locally / try paste-CSV",
            "results": [],
            "summary": {
                "count": 0,
                "avg_risk_score": 0.0,
                "band_counts": {"Low": 0, "Moderate": 0, "High": 0}
            }
        }
    except UnsupportedMarketplace as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraper failed: {e}")

    # Empty reviews check
    if not raw_reviews:
        return {
            "message": "No reviews found — try paste/CSV",
            "results": [],
            "summary": {
                "count": 0,
                "avg_risk_score": 0.0,
                "band_counts": {"Low": 0, "Moderate": 0, "High": 0}
            }
        }

    results = []
    for rev in raw_reviews:
        res = predict_review(rev["text"])
        if rev.get("rating") is not None:
            res["consistency_flag"] = consistency_flag(rev["rating"], rev["text"])
        results.append(res)

    return {
        "results": results,
        "summary": _summarize(results)
    }
