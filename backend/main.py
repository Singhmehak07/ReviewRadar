import os
import io
import re
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from predict import analyze_review, EmptyCleanedTextError, HIGH_RISK_THRESHOLD, get_risk_interpretation
from text_cleaning import clean_review_text

DISCLAIMER = "Highlights suspicious review patterns; does not prove fraud."
BATCH_MESSAGE = "Results describe only the reviews submitted for analysis and may not represent every review for the product."

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_for_duplicate(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", cleaned)
    return cleaned.strip()


def process_batch(reviews_list: list[str], ratings_list: list[Optional[int]] = None) -> dict:
    submitted = len(reviews_list)
    if ratings_list is None:
        ratings_list = [None] * submitted
        
    analyzed_items = []
    skipped = 0
    
    # Pass 1: Clean and filter empty reviews
    for idx, (raw_text, rating) in enumerate(zip(reviews_list, ratings_list)):
        cleaned_res = clean_review_text(raw_text)
        cleaned_text = cleaned_res["cleaned_text"]
        if not cleaned_text:
            skipped += 1
            continue
            
        analyzed_items.append({
            "original_index": idx,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "rating": rating,
            "cleaning": cleaned_res
        })
        
    if not analyzed_items:
        return {
            "message": BATCH_MESSAGE,
            "results": [],
            "summary": {
                "reviews_submitted": submitted,
                "reviews_analyzed": 0,
                "reviews_skipped": skipped,
                "overall_risk_score": 0.0,
                "overall_band": "Low",
                "overall_risk_label": "Average computer-generated writing risk",
                "overall_interpretation": {
                    "headline": "Few strong computer-generated writing signals were detected.",
                    "description": "The writing has low similarity to the computer-generated examples learned by the model. This does not prove that the review was written by a person."
                },
                "flagged_percentage_label": "Percentage of analyzed reviews flagged as likely computer-generated",
                "count_flagged": 0,
                "pct_computer_generated": 0.0,
                "distribution": {"Low": 0, "Moderate": 0, "High": 0},
                "duplicate_reviews": 0,
                "duplicate_groups": 0,
                "sample_notice": BATCH_MESSAGE,
                "message": BATCH_MESSAGE
            },
            "disclaimer": DISCLAIMER
        }
        
    # Pass 2: Detect exact normalized duplicates
    normalized_map = {}
    for i, item in enumerate(analyzed_items):
        norm = normalize_for_duplicate(item["cleaned_text"])
        if norm not in normalized_map:
            normalized_map[norm] = []
        normalized_map[norm].append(i)
        
    duplicate_reviews = 0
    duplicate_groups = 0
    group_id_counter = 1
    dup_assignments = {}
    
    for norm, indices in normalized_map.items():
        if len(indices) > 1:
            group_id = f"dup_{group_id_counter}"
            group_id_counter += 1
            duplicate_groups += 1
            duplicate_reviews += len(indices)
            for idx in indices:
                dup_assignments[idx] = (True, group_id)
        else:
            dup_assignments[indices[0]] = (False, None)
            
    # Fallback strings to remove if duplicate reason is added
    FALLBACKS = {
        "The model found few strong phrase-level indicators associated with computer-generated reviews.",
        "The model found mixed phrase-level evidence and no single pattern was decisive.",
        "The combined writing pattern resembles the model's computer-generated training examples, but no single phrase explains the result on its own."
    }

    # Pass 3: Run analysis & compile results
    results = []
    for i, item in enumerate(analyzed_items):
        res = analyze_review(item["raw_text"], rating=item["rating"])
        
        # Add index, duplicate info
        is_dup, group_id = dup_assignments[i]
        res["review_index"] = item["original_index"]
        res["duplicate"] = is_dup
        res["duplicate_group"] = group_id
        
        if is_dup:
            # Remove fallback reasons
            res["reasons"] = [r for r in res["reasons"] if r not in FALLBACKS]
            res["reasons"].insert(0, "This review is identical to another submitted review.")
            res["reasons"] = res["reasons"][:3]
            
        results.append(res)
        
    # Pass 4: Calculate collective summary
    overall_score = round(sum(r["risk_score"] for r in results) / len(results), 2)
    
    overall_interp = get_risk_interpretation(overall_score)
    
    count_flagged = sum(1 for r in results if r["risk_score"] >= HIGH_RISK_THRESHOLD)
    pct_cg = round((count_flagged / len(results)) * 100, 1)
    
    distribution = {"Low": 0, "Moderate": 0, "High": 0}
    for r in results:
        distribution[r["risk_band"]] += 1
        
    was_were = "was" if count_flagged == 1 else "were"
    headline = f"Analyzed {len(results)} of {submitted} submitted reviews. {count_flagged} of {len(results)} analyzed reviews {was_were} flagged as likely computer-generated."

    summary = {
        "reviews_submitted": submitted,
        "reviews_analyzed": len(results),
        "reviews_skipped": skipped,
        "overall_risk_score": overall_score,
        "overall_band": overall_interp["risk_band"],
        "overall_risk_label": "Average computer-generated writing risk",
        "overall_interpretation": {
            "headline": overall_interp["headline"],
            "description": overall_interp["description"]
        },
        "flagged_percentage_label": "Percentage of analyzed reviews flagged as likely computer-generated",
        "count_flagged": count_flagged,
        "pct_computer_generated": pct_cg,
        "distribution": distribution,
        "duplicate_reviews": duplicate_reviews,
        "duplicate_groups": duplicate_groups,
        "sample_notice": BATCH_MESSAGE,
        "message": BATCH_MESSAGE
    }
    
    return {
        "headline": headline,
        "results": results,
        "summary": summary,
        "disclaimer": DISCLAIMER,
        "message": BATCH_MESSAGE
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(body: AnalyzeIn):
    try:
        return analyze_review(body.text, rating=body.rating)
    except EmptyCleanedTextError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/analyze-batch")
def analyze_batch(body: BatchIn):
    if len(body.reviews) > 100:
        raise HTTPException(status_code=400, detail="Batch size exceeds the maximum limit of 100 reviews.")
    return process_batch(body.reviews)


@app.post("/analyze-csv")
async def analyze_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are allowed.")
        
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")
        
    if "review_text" not in df.columns:
        raise HTTPException(status_code=422, detail="CSV must have a 'review_text' column")
        
    df = df.head(1000)  # cap at 1000 rows
    
    reviews = df["review_text"].fillna("").astype(str).tolist()
    ratings = None
    if "rating" in df.columns:
        ratings = []
        for r in df["rating"]:
            try:
                if pd.notna(r):
                    ratings.append(int(float(r)))
                else:
                    ratings.append(None)
            except (ValueError, TypeError):
                ratings.append(None)
                
    res = process_batch(reviews, ratings)
    if res["summary"]["reviews_analyzed"] == 0:
        raise HTTPException(status_code=400, detail="No valid review text found")
    return res
