import joblib
import re
import os
from text_cleaning import clean_review_text
from signals.consistency import consistency_flag

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
            from signals.consistency import clean_for_sentiment, _analyzer
            c_text = clean_for_sentiment(cleaned_text)
            compound = _analyzer.polarity_scores(c_text)["compound"]
            if active_rating >= 4 and compound <= -0.3:
                consistency_reason = "The positive star rating conflicts with negative wording in the review."
            elif active_rating <= 2 and compound >= 0.3:
                consistency_reason = "The negative star rating conflicts with positive wording in the review."

    # Model contribution reasons
    features = tfidf.transform([cleaned_text])
    coo = features.tocoo()
    
    cg_index = list(model.classes_).index("1")
    coefs = model.coef_[0]
    if cg_index == 0:
        coefs = -coefs
        
    contributions = []
    feature_names = tfidf.get_feature_names_out()
    for col, val in zip(coo.col, coo.data):
        coef = coefs[col]
        contrib = val * coef
        if contrib > 0:
            contributions.append((feature_names[col], contrib))
            
    contributions.sort(key=lambda x: x[1], reverse=True)
    top_features = [feat for feat, contrib in contributions[:3]]
    
    model_reason = None
    if top_features:
        quoted_feats = [f'"{f}"' for f in top_features]
        phrase_list = ", ".join(quoted_feats)
        model_reason = f"The model weighted phrases such as {phrase_list} toward the computer-generated class."

    # Aggregate reasons
    reasons = []
    if consistency_reason:
        reasons.append(consistency_reason)
    if model_reason:
        reasons.append(model_reason)

    # Fallbacks if no evidence is found
    if not reasons:
        score = pred["risk_score"]
        if score < 40:
            reasons.append("The model found few strong phrase-level indicators associated with computer-generated reviews.")
        elif score < 70:
            reasons.append("The model found mixed phrase-level evidence and no single pattern was decisive.")
        else:
            reasons.append("The combined writing pattern resembles the model's computer-generated training examples, but no single phrase explains the result on its own.")
        
    reasons = reasons[:3]
    
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