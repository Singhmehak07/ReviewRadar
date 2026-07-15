"""
Minimal spec-required tests.
One clear test per behaviour — ponytail applies to tests too.
Run from: backend/   →  pytest tests/test_spec.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add backend/ to path

import pytest
from predict import predict_review, assign_risk_band
from signals.consistency import consistency_flag


# ── predict_review: shape + JSON-safety ──────────────────────────────────────

def test_predict_returns_valid_shape():
    r = predict_review("great product")
    assert isinstance(r, dict)
    assert set(r.keys()) >= {"risk_score", "risk_band", "disclaimer"}
    assert isinstance(r["risk_score"], float)          # not np.float64
    assert r["risk_band"] in ("Low", "Moderate", "High")
    assert r["disclaimer"] == "Highlights suspicious review patterns; does not prove fraud."


def test_risk_score_is_native_float():
    r = predict_review("great product")
    # json.dumps would raise TypeError on np.float64
    import json
    json.dumps(r)  # must not raise


# ── assign_risk_band: exact cutoffs ──────────────────────────────────────────

def test_band_39():
    assert assign_risk_band(39) == "Low"

def test_band_40():
    assert assign_risk_band(40) == "Moderate"

def test_band_69():
    assert assign_risk_band(69) == "Moderate"

def test_band_70():
    assert assign_risk_band(70) == "High"


# ── consistency_flag: all four branches ──────────────────────────────────────

def test_flag_no_text():
    assert consistency_flag(4, "") == "no_text"
    assert consistency_flag(4, "   ") == "no_text"

def test_flag_contradiction_high_rating_negative_text():
    assert consistency_flag(5, "Absolutely terrible, worst product ever.") == "contradiction"

def test_flag_contradiction_low_rating_positive_text():
    assert consistency_flag(1, "Absolutely love it! Amazing and wonderful!") == "contradiction"

def test_flag_neutral_text():
    assert consistency_flag(3, "It is a product.") == "neutral_text"

def test_flag_consistent():
    assert consistency_flag(5, "I love this, it's wonderful and fantastic!") == "consistent"
# ── batch summary math ────────────────────────────────────────────────────────

def test_batch_summary_math():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    
    payload = {
        "reviews": [
            "great product love it amazing wonderful",
            "   ",
            "this is a product",
            "",
            "terrible awful horrible garbage worst ever",
            "   \t\n   "
        ]
    }
    
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert "summary" in data
    assert "disclaimer" in data
    
    results = data["results"]
    summary = data["summary"]
    
    # We submitted 6, but 3 are blank/whitespace, so 3 are skipped
    assert len(results) == 3
    assert summary["reviews_submitted"] == 6
    assert summary["reviews_analyzed"] == 3
    assert summary["reviews_skipped"] == 3
    
    assert "overall_risk_score" in summary
    assert "overall_band" in summary
    assert "count_flagged" in summary
    assert "pct_computer_generated" in summary
    assert "distribution" in summary
    
    # Check distribution
    dist = summary["distribution"]
    assert sum(dist.values()) == 3
    
    # Guard check for zero analyzed
    payload_empty = {"reviews": ["", "  ", " \n "]}
    response_empty = client.post("/analyze-batch", json=payload_empty)
    assert response_empty.status_code == 200
    assert response_empty.json()["message"] == "No valid review text found"
    assert response_empty.json()["summary"]["reviews_analyzed"] == 0
    assert response_empty.json()["summary"]["reviews_skipped"] == 3
