"""
Comprehensive specification-required tests.
Run from backend/ directory:
    pytest tests/test_spec.py -v
"""
import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path so that backend files can be imported properly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from predict import predict_review, assign_risk_band, analyze_review, EmptyCleanedTextError
from signals.consistency import consistency_flag
from text_cleaning import clean_review_text
from main import app, normalize_for_duplicate

client = TestClient(app)


# ── 1. Text Cleaner Tests ───────────────────────────────────────────────────

def test_cleaner_html_decoding_and_tag_removal():
    raw = "<p>This is &amp; feels like a <b>great</b> product!</p>"
    res = clean_review_text(raw)
    assert res["cleaned_text"] == "This is & feels like a great product!"

def test_cleaner_removes_exact_ui_noise_lines():
    raw = (
        "5 ★\n"
        "Wonderful product\n"
        "Certified Buyer, New Delhi\n"
        "15 Jun, 2026\n"
        "The stand feels stable and supports my laptop well.\n"
        "Read More\n"
        "Helpful? 43\n"
        "Permalink\n"
        "Report Abuse"
    )
    res = clean_review_text(raw)
    # Checks that UI noise is removed, but genuine sentences are preserved.
    assert "Wonderful product. The stand feels stable and supports my laptop well." in res["cleaned_text"]
    assert "Read More" not in res["cleaned_text"]
    assert "Helpful? 43" not in res["cleaned_text"]
    assert "Permalink" not in res["cleaned_text"]
    assert "Report Abuse" not in res["cleaned_text"]
    assert res["extracted_rating"] == 5
    assert len(res["removed_noise_lines"]) > 0

def test_cleaner_preserves_helpful_in_genuine_sentence():
    raw = "This stand has been very helpful for work. I highly recommend it."
    res = clean_review_text(raw)
    assert res["cleaned_text"] == "This stand has been very helpful for work. I highly recommend it."
    assert len(res["removed_noise_lines"]) == 0

def test_cleaner_handles_empty_and_whitespace_input():
    assert clean_review_text("")["cleaned_text"] == ""
    assert clean_review_text("   \n\t   ")["cleaned_text"] == ""
    assert clean_review_text(None)["cleaned_text"] == ""


# ── 2. Single-Review Analysis Tests ─────────────────────────────────────────

def test_single_review_shape_and_types():
    res = analyze_review("Absolutely wonderful and outstanding purchase!")
    assert isinstance(res, dict)
    assert "cleaned_text" in res
    assert "risk_score" in res
    assert "risk_band" in res
    assert "reasons" in res
    assert "cleaning" in res
    assert "disclaimer" in res
    assert isinstance(res["risk_score"], float)
    assert isinstance(res["reasons"], list)
    assert len(res["reasons"]) <= 3
    assert res["disclaimer"] == "Highlights suspicious review patterns; does not prove fraud."

def test_single_review_reasons_contain_no_fraud_claims():
    res = analyze_review("Outstanding quality, highly recommend, best product ever.")
    for reason in res["reasons"]:
        assert "fake" not in reason.lower()
        assert "fraud" not in reason.lower()
        assert "lying" not in reason.lower()
        assert "dishonest" not in reason.lower()

def test_single_review_empty_cleaned_text_rejection():
    # If no text remains after cleaning, raise EmptyCleanedTextError
    with pytest.raises(EmptyCleanedTextError):
        analyze_review("Helpful? 43\nRead More")

def test_single_review_endpoint_rejects_empty():
    response = client.post("/analyze", json={"text": "Helpful? 43\nRead More"})
    assert response.status_code == 400
    assert "No meaningful review text remained" in response.json()["detail"]


# ── 3. Batch Analysis Tests ─────────────────────────────────────────────────

def test_batch_counts_flagged_skipped_distribution():
    payload = {
        "reviews": [
            "This is a great product, highly recommend!",
            "   ",
            "Awesome product. Best purchase ever. Must buy.",
            "",
            "This is a standard product that works reasonably well.",
            "   \t\n   "
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    summary = data["summary"]
    results = data["results"]
    
    assert summary["reviews_submitted"] == 6
    assert summary["reviews_analyzed"] == 3
    assert summary["reviews_skipped"] == 3
    
    # Check distribution
    dist = summary["distribution"]
    assert sum(dist.values()) == summary["reviews_analyzed"]
    
    # Check pct_computer_generated calculation
    flagged = summary["count_flagged"]
    analyzed = summary["reviews_analyzed"]
    expected_pct = round((flagged / analyzed) * 100, 1)
    assert summary["pct_computer_generated"] == expected_pct

def test_batch_division_by_zero_guard():
    # If all entries are empty, avoid dividing by zero
    payload = {"reviews": ["", "  ", "\n"]}
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "No valid review text found"
    assert data["summary"]["reviews_analyzed"] == 0
    assert data["summary"]["reviews_skipped"] == 3

def test_batch_duplicate_detection_and_reasons():
    payload = {
        "reviews": [
            "Awesome product! Highly recommend.",
            "Awesome product! Highly recommend.", # exact duplicate
            "This is a completely unique review.",
            "Awesome product! Highly recommend.  " # exact normalized duplicate (whitespace trailing)
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    results = data["results"]
    summary = data["summary"]
    
    assert summary["duplicate_reviews"] == 3
    assert summary["duplicate_groups"] == 1
    
    # Verify duplicates flag & reasons
    assert results[0]["duplicate"] is True
    assert results[1]["duplicate"] is True
    assert results[3]["duplicate"] is True
    assert results[2]["duplicate"] is False
    
    assert results[0]["duplicate_group"] == "dup_1"
    assert results[1]["duplicate_group"] == "dup_1"
    assert results[3]["duplicate_group"] == "dup_1"
    
    assert "identical to another submitted review" in results[0]["reasons"][0]

def test_batch_original_index_preservation():
    payload = {
        "reviews": [
            "Review index 0",
            "   ", # index 1 skipped
            "Review index 2"
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    results = data["results"]
    assert results[0]["review_index"] == 0
    assert results[1]["review_index"] == 2

def test_batch_size_limit_rejection():
    # Exceeds the limit of 100
    payload = {"reviews": ["test"] * 101}
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 400
    assert "exceeds the maximum limit of 100 reviews" in response.json()["detail"]


# ── 4. Star-Rating Cutoffs and Risk Bands ───────────────────────────────────

def test_band_39():
    assert assign_risk_band(39) == "Low"

def test_band_40():
    assert assign_risk_band(40) == "Moderate"

def test_band_69():
    assert assign_risk_band(69) == "Moderate"

def test_band_70():
    assert assign_risk_band(70) == "High"
