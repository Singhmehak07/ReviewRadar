# Model Card — Review Credibility Analyzer

## Model Purpose
The model highlights writing patterns associated with the computer-generated class of text in product reviews. It is designed as an educational and screening tool, not a system that proves whether reviews are fake.

## Model Architecture
*   **Feature Extraction**: TF-IDF (Term Frequency-Inverse Document Frequency) Vectorizer.
*   **Classifier**: Logistic Regression.
*   **Classes**:
    *   `"0"`: Ordinary/Organic writing patterns.
    *   `"1"`: Computer-generated writing patterns.
*   **Risk Thresholds**:
    *   `< 40`: Low risk band.
    *   `>= 40 and < 70`: Moderate risk band.
    *   `>= 70`: High risk band.

## Inputs
*   Single pasted review text.
*   Batch of pasted review texts (up to 100).
*   CSV file containing a `review_text` column and an optional `rating` column (up to 1000 rows).
*   Optional star rating (1–5) for rating/text consistency analysis.
*   Conservative copied-text cleaning (removes marketplace UI headers, footers, helpful vote count lines, isolated dates, and isolated star ratings).

## Outputs
*   **Risk Score**: The model's estimated probability (0–100) that the submitted text resembles the computer-generated class in its training data.
*   **Risk Band**: Low, Moderate, or High category with associated descriptive headlines and explanations.
*   **Model-Grounded Phrase Explanations**: Up to 3 words or phrases extracted from the text that contributed positively to the class `"1"` prediction.
*   **Rating/Text Consistency Signal**: Contradiction check flag (compares rating with VADER compound sentiment score).
*   **Exact Duplicate Detection**: Groups and tags matching text submissions in batches.
*   **Batch Aggregate Summary**: Submitted, analyzed, and skipped review counts, average risk score, band, and percentage flagged.

## What the Model Measures
*   Learned text/n-gram features present in the TF-IDF vectorizer vocabulary.
*   Optional rating/text contradiction (using VADER sentiment polarity).
*   Exact duplicate text inside submitted batches.
*   *Note*: Contradictions and duplicates are supporting evidence signals and do not modify or override the machine learning model's probability score.

## What the Model Does Not Measure
This model does not have access to, and does not measure:
*   Reviewer identity or account credentials.
*   Purchase verification status.
*   Reviewer posting history or account creation date.
*   Review publication timing or metadata.
*   Coordinated reviewer networks or botnets.
*   Marketplace behavior or click-through rates.
*   IP address or device fingerprinting.
*   Perplexity, burstiness, or lexical variety metrics.
*   Definitive AI authorship or intent of fraud.

## Known Limitations
*   **Short Reviews**: Text with very few words may provide insufficient vocabulary overlap for reliable TF-IDF scoring.
*   **False Positives**: Generic, formulaic genuine reviews (e.g. "Excellent product, fast shipping, highly recommend") may be flagged due to vocabulary overlap with common generated templates.
*   **AI Adaptability**: Advanced or custom-prompted LLMs can generate reviews that avoid learned training set features entirely.
*   **Non-Native English**: Reviews written by non-native English speakers may contain vocabulary patterns that trigger flags, but this must never be assumed to indicate dishonesty or computer-generation.
*   **Sample Context**: Batch and CSV results describe only the submitted sample and do not represent all marketplace reviews for a product.

## Research Context
Research has identified several possible linguistic and behavioral indicators of fake reviews, such as repetitive or redundant language, lower variation in writing structure, formulaic or predictable phrasing, emotional exaggeration, rating/text inconsistency, duplicate content, and reviewer behavioral patterns.

> [!NOTE]
> This implementation displays only evidence directly calculated from its TF-IDF model, rating/text consistency check, and exact duplicate detection.

## Responsible-Use Statement
This system is intended as a review-screening and educational tool. Its predictions should not be used as the sole basis for accusing a reviewer, removing content, or making legal or financial decisions.

## Disclaimer
Highlights suspicious review patterns; does not prove fraud.
