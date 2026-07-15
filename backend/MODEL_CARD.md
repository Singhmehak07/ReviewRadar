# Model Card — Review Credibility Analyzer

## Model Purpose
The model highlights writing patterns associated with the computer-generated class of text in product reviews. It is designed as an educational and screening tool, not a system that proves whether reviews are fake.

## Model Architecture
*   **Feature Extraction**: TF-IDF (Term Frequency-Inverse Document Frequency) Vectorizer.
*   **Classifier**: Logistic Regression.
*   **Classes**:
    *   `"0"`: Ordinary/Organic (`OR`) writing patterns.
    *   `"1"`: Computer-generated (`CG`) writing patterns.
*   **Risk Thresholds**:
    *   `< 40`: Low risk band.
    *   `>= 40 and < 70`: Moderate risk band.
    *   `>= 70`: High risk band.

## Environment & Artifacts
*   **Serialized Environment**: Python 3.14 (fully compatible with Python 3.11+ runtimes).
*   **Library Dependency**: `scikit-learn==1.7.2`
*   **Model Filenames**:
    *   `risk_model.joblib`: Trained Logistic Regression classifier weights.
    *   `tfidf_vectorizer.joblib`: Serialized TF-IDF vectorizer configuration and vocabulary.

## Inputs
*   Single pasted review text.
*   Batch of pasted review texts (up to 100).
*   CSV file containing a `review_text` column and an optional `rating` column (up to 1000 rows, max 5 MB).
*   Optional star rating (1–5) for rating/text consistency analysis.
*   Conservative copied-text cleaning (removes marketplace UI headers, footers, helpful vote count lines, isolated dates, and isolated star ratings).

## Outputs
*   **Risk Score**: The model's estimated probability (0–100) that the submitted text resembles the computer-generated class in its training data.
*   **Risk Band**: Low, Moderate, or High category with associated descriptive headlines and explanations.
*   **Model-Grounded Phrase Explanations**: Up to 3 words or phrases extracted from the text that contributed positively to the class `"1"` prediction.
*   **Rating/Text Consistency Signal**: Contradiction check flag (compares rating with VADER compound sentiment score).
*   **Exact Duplicate Detection**: Groups and tags matching text submissions in batches.
*   **Batch Aggregate Summary**: Submitted, analyzed, and skipped review counts, average risk score, band, and percentage flagged.

## What the ML Model Measures
*   Learned text/n-gram features present in the TF-IDF vectorizer vocabulary.
*   The Logistic Regression probability of the target class `"1"`.

## Supporting Application Signals
*   **VADER rating/text contradiction**: Sentiment compound score calculated using VADER polarity scores.
*   **Exact duplicate detection**: Compares exact normalized text structures inside submitted batches.
*   *Note*: Supporting signals are displayed as context and do not modify the model probability.

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

## Evaluation
Model evaluation details will be documented after the existing training workflow is cleaned and rerun reproducibly.

## Known Limitations
*   **Short Reviews**: Text with very few words may provide insufficient vocabulary overlap for reliable TF-IDF scoring.
*   **False Positives**: Generic, formulaic genuine reviews (e.g. "Excellent product, fast shipping, highly recommend") may be flagged due to vocabulary overlap with common generated templates.
*   **AI Adaptability**: Advanced or custom-prompted LLMs can generate reviews that avoid learned training set features entirely.
*   **Non-Native English**: Reviews written by non-native English speakers may contain vocabulary patterns that trigger flags, but this must never be assumed to indicate dishonesty or computer-generation.
*   **Sample Context**: Batch and CSV results describe only the submitted sample and do not represent all marketplace reviews for a product.

## Responsible-Use Statement
This system is intended as a review-screening and educational tool. Its predictions should not be used as the sole basis for accusing a reviewer, removing content, or making legal or financial decisions.

## Disclaimer
Highlights suspicious review patterns; does not prove fraud.
