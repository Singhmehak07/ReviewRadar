import re
import html
import unicodedata

RATING_REGEXES = [
    r"^\s*([1-5])\s*★+\s*$",        # e.g., "5 ★" or "5★"
    r"^\s*★+\s*([1-5])\s*$",        # e.g., "★ 5"
    r"^\s*([1-5])\s*/\s*5\s*$",      # e.g., "5/5" or "5 / 5"
    r"^\s*([1-5])\s*out of\s*5\s*$", # e.g., "5 out of 5"
    r"^\s*([1-5])\s*stars?\s*$"     # e.g., "5 stars"
]

DATE_REGEXES = [
    r"^\s*\d{1,2}\s+[A-Za-z]{3,10}(?:,)?\s+\d{4}\s*$",      # e.g., "15 Jun, 2026"
    r"^\s*[A-Za-z]{3,10}\s+\d{1,2}(?:,)?\s+\d{4}\s*$",      # e.g., "June 15, 2026"
    r"^\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\s*$"             # e.g., "15/06/2026"
]

HELPFUL_REGEXES = [
    r"^\s*helpful\??\s*\d*\s*$",                            # e.g. "Helpful? 43" or "Helpful"
    r"^\s*\d*\s*helpful\s*$",                               # e.g. "43 helpful"
    r"^\s*\d*\s*people\s*(?:found\s*this\s*|found\s*)helpful\s*$"
]

UI_NOISE_EXACT = {
    "read more", "show more", "helpful", "helpful?", "report abuse", "report",
    "permalink", "share", "certified buyer", "verified purchase", "verified buyer",
    "was this review helpful?", "yes", "no", "comment", "reply", "flag",
    "helpful? yes no", "helpful yes no", "report abuse permalink"
}

def check_isolated_rating(line: str) -> int | None:
    # 1. Pure stars (e.g. ★★★★★)
    if re.match(r"^\s*★{1,5}\s*$", line):
        return len(line.strip())
    # 2. Digit + indicator
    for pattern in RATING_REGEXES:
        m = re.match(pattern, line, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None

def clean_review_text(raw_text: str) -> dict:
    if raw_text is None:
        raw_text = ""
    raw_text = str(raw_text)
    original_char_count = len(raw_text)

    # 1. Decode HTML entities
    text = html.unescape(raw_text)

    # 2. Remove HTML tags safely
    text = re.sub(r"<[^>]+>", " ", text)

    # 3. Normalize Unicode whitespace
    text = unicodedata.normalize("NFKC", text)

    # 4. Remove zero-width and other invisible formatting characters
    text = re.sub(r"[\u200b-\u200d\ufeff\u200e\u200f\u2060\u202a-\u202e]", "", text)

    # Split into lines
    lines = text.splitlines()
    cleaned_lines = []
    removed_noise_lines = []
    extracted_ratings = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for isolated star rating
        rating = check_isolated_rating(stripped)
        if rating is not None:
            extracted_ratings.append(rating)
            removed_noise_lines.append(line)
            continue

        lower_line = stripped.lower()

        # Check exact matches in UI noise
        if lower_line in UI_NOISE_EXACT:
            removed_noise_lines.append(line)
            continue

        # Check prefix/substring for buyer verification info
        if any(term in lower_line for term in ["certified buyer", "verified purchase", "verified buyer"]):
            removed_noise_lines.append(line)
            continue

        # Check isolated dates
        is_date = False
        for pattern in DATE_REGEXES:
            if re.match(pattern, stripped):
                is_date = True
                break
        if is_date:
            removed_noise_lines.append(line)
            continue

        # Check isolated helpful-vote counts
        is_helpful = False
        for pattern in HELPFUL_REGEXES:
            if re.match(pattern, stripped, re.IGNORECASE):
                is_helpful = True
                break
        if is_helpful:
            removed_noise_lines.append(line)
            continue

        # If none of the above, it's meaningful content
        cleaned_lines.append(stripped)

    # Join cleaned lines into clean review text
    joined = []
    for l in cleaned_lines:
        if joined:
            prev = joined[-1]
            if prev and not prev[-1] in ".!?":
                joined[-1] = prev + "."
        joined.append(l)
    cleaned_text = " ".join(joined).strip()
    
    # Normalize repeated spaces
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)

    # Determine extracted_rating (only if unambiguous, i.e., exactly one unique rating value extracted)
    extracted_rating = None
    if len(extracted_ratings) == 1:
        extracted_rating = extracted_ratings[0]
    elif len(extracted_ratings) > 1:
        # If all extracted ratings are identical, it is unambiguous
        if len(set(extracted_ratings)) == 1:
            extracted_rating = extracted_ratings[0]

    return {
        "cleaned_text": cleaned_text,
        "extracted_rating": extracted_rating,
        "removed_noise_lines": removed_noise_lines,
        "original_character_count": original_char_count,
        "cleaned_character_count": len(cleaned_text)
    }
