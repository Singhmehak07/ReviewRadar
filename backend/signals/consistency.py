import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ponytail: module-level singleton, one allocation
_analyzer = SentimentIntensityAnalyzer()


def clean_for_sentiment(text: str) -> str:
    """Strip HTML and URLs; keep capitalization and punctuation (VADER needs them)."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = re.sub(r"<[^>]+>", " ", text)           # strip html tags
    text = re.sub(r"http\S+|www\.\S+", " ", text)  # strip urls
    text = re.sub(r"\s+", " ", text).strip()        # collapse whitespace
    return text


def consistency_flag(text: str, rating: int) -> str:
    cleaned = clean_for_sentiment(text)
    if not cleaned:
        return "no_text"
    
    # Truncate text to 5000 characters to avoid VADER performance bottlenecks on long inputs
    if len(cleaned) > 5000:
        cleaned = cleaned[:5000]
        
    analyzer = get_analyzer()
    compound = analyzer.polarity_scores(cleaned)["compound"]
    if (rating >= 4 and compound <= -0.3) or (rating <= 2 and compound >= 0.3):
        return "contradiction"
    if -0.3 < compound < 0.3:
        return "neutral_text"
    return "consistent"

# Backward compatibility aliases for tests
clean_text_for_sentiment = clean_for_sentiment
get_consistency_flag = consistency_flag

def get_analyzer():
    return _analyzer

