import sys
import os
import pytest

# Add parent directory to path so that backend files can be imported properly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from predict import analyze_review, predict_review, model, tfidf

def test_rating_contradictions_format():
    # 5-star rating with negative wording
    res1 = analyze_review("This is absolutely terrible and horrible garbage product.", rating=5)
    assert any(r == "The five-star rating conflicts with negative wording." for r in res1["reasons"])

    # 1-star rating with positive wording
    res2 = analyze_review("This is wonderful, excellent quality, highly recommend!", rating=1)
    assert any(r == "The one-star rating conflicts with positive wording." for r in res2["reasons"])

def test_no_model_phrases_or_fallbacks():
    # Ensure no phrases or fallbacks are present
    res = analyze_review("Standard product, normal delivery.")
    assert len(res["reasons"]) == 0

def test_risk_scores_remain_identical():
    text = "Great product, highly recommend!"
    pred = predict_review(text)
    res = analyze_review(text)
    assert res["risk_score"] == pred["risk_score"]
    assert len(res["reasons"]) == 0

def test_no_model_changes():
    assert list(model.classes_) == ["0", "1"]
    assert model.coef_.shape[0] == 1
