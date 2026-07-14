import joblib
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
tfidf = joblib.load(os.path.join(BASE_DIR, "models", "tfidf_vectorizer.joblib"))
model = joblib.load(os.path.join(BASE_DIR, "models", "risk_model.joblib"))

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"<[^>]+>", " ", text)             # strip html
    text = re.sub(r"http\S+|www\.\S+", " ", text)    # strip urls
    text = re.sub(r"\s+", " ", text)                 # collapse whitespace
    return text.strip()

def assign_risk_band(score):
    if score < 40:
        return "Low"
    elif score < 70:
        return "Moderate"
    return "High"

def predict_review(text):
    cleaned = clean_text(text)
    features = tfidf.transform([cleaned])
    cg_index = list(model.classes_).index("1")
    score = float(model.predict_proba(features)[0][cg_index] * 100)
    rounded_score = float(round(score, 2))
    return {
        "risk_score": rounded_score,
        "risk_band": assign_risk_band(rounded_score),
        "disclaimer": "Highlights suspicious review patterns; does not prove fraud."
    }

if __name__ == "__main__":
    # Test clean_text
    assert clean_text("<p>Hello World http://example.com</p>  ") == "hello world"
    
    # Test predict_review format and types
    res = predict_review("This is a great product!")
    assert isinstance(res, dict)
    assert "risk_score" in res
    assert "risk_band" in res
    assert "disclaimer" in res
    assert isinstance(res["risk_score"], float)
    assert res["risk_band"] in ["Low", "Moderate", "High"]
    assert res["disclaimer"] == "Highlights suspicious review patterns; does not prove fraud."
    print("All backend/predict.py basic self-check assertions passed successfully!")