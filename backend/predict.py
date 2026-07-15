import joblib
import re
import os
from text_cleaning import clean_review_text
from signals.consistency import consistency_flag, sentiment_compound

class EmptyCleanedTextError(ValueError):
    pass

HIGH_RISK_THRESHOLD = 70

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

def get_risk_interpretation(risk_score: float) -> dict:
    if risk_score < 40:
        return {
            "risk_band": "Low",
            "headline": "Few strong computer-generated writing signals were detected.",
            "description": "The writing has low similarity to the computer-generated examples learned by the model. This does not prove that the review was written by a person."
        }
    elif risk_score < 70:
        return {
            "risk_band": "Moderate",
            "headline": "The review contains a mixture of ordinary and suspicious writing signals.",
            "description": "Some writing patterns resemble computer-generated examples, but the evidence is mixed. Review the supporting reasons rather than relying on the score alone."
        }
    else:
        return {
            "risk_band": "High",
            "headline": "The writing strongly resembles computer-generated examples from the model's training data.",
            "description": "This review has been flagged for closer inspection. A high score does not establish how the review was created or whether it is deceptive."
        }

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

def analyze_review(raw_text: str, rating: int | None = None) -> dict:
    cleaning_res = clean_review_text(raw_text)
    cleaned_text = cleaning_res["cleaned_text"]
    if not cleaned_text:
        raise EmptyCleanedTextError("No meaningful review text remained after removing copied interface content.")
        
    # Run prediction
    pred = predict_review(cleaned_text)
    
    # Rating selection
    active_rating = rating
    if active_rating is None:
        active_rating = cleaning_res["extracted_rating"]
        
    # Consistency signal
    flag = None
    consistency_reason = None
    if active_rating is not None:
        flag = consistency_flag(cleaned_text, active_rating)
        if flag == "contradiction":
            # Determine VADER compound
            compound = sentiment_compound(cleaned_text)
            rating_map = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
            rating_word = rating_map.get(active_rating, "star")
            if active_rating >= 4:
                consistency_reason = f"The {rating_word}-star rating conflicts with negative wording."
            else:
                consistency_reason = f"The {rating_word}-star rating conflicts with positive wording."

    # Aggregate reasons
    internal_reasons = []
    if consistency_reason:
        internal_reasons.append({"code": "rating_contradiction", "message": consistency_reason})

    reasons = [r["message"] for r in internal_reasons]
    interp = get_risk_interpretation(pred["risk_score"])
    
    res = {
        "cleaned_text": cleaned_text,
        "risk_score": pred["risk_score"],
        "risk_band": interp["risk_band"],
        "risk_label": "Computer-generated writing risk",
        "interpretation": {
            "headline": interp["headline"],
            "description": interp["description"]
        },
        "reasons": reasons,
        "_reasons": internal_reasons,
        "cleaning": {
            "original_character_count": cleaning_res["original_character_count"],
            "cleaned_character_count": cleaning_res["cleaned_character_count"],
            "removed_noise_lines": cleaning_res["removed_noise_lines"],
            "extracted_rating": cleaning_res["extracted_rating"]
        },
        "disclaimer": pred["disclaimer"]
    }
    
    if flag is not None:
        res["consistency_flag"] = flag
        
    return res

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