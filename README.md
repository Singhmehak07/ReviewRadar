# ReviewRadar — Explainable Review Credibility Analyzer

ReviewRadar is an explainable machine-learning review credibility analyzer. It highlights writing patterns associated with computer-generated reviews to assist users in screening and educational review analysis.

## Core Capabilities

1.  **Single-Review Analysis**: Analyzes a pasted review and returns an estimated risk score along with a plain-language interpretation and model-grounded reasons.
2.  **Batch & CSV Analysis**: Processes lists or uploaded files of reviews (up to 100 in batches and 1000 in CSVs) to provide aggregate credibility statistics and sample-level summaries.
3.  **Conservative Text Cleaning**: Automatically identifies and removes marketplace UI clutter, isolated star ratings, dates, and vote count lines before evaluation to maintain text cleanliness.
4.  **Explainable Evidence Reporting**: Highlights positive TF-IDF and Logistic Regression feature contributions, reports rating/text consistency flags, and groups duplicate review texts.

## Technical Architecture

*   **Model**: TF-IDF Vectorization followed by a Logistic Regression Classifier.
*   **Explainability**: Identifies positive word and phrase contributions toward class `"1"` (the computer-generated writing pattern class) to display as plain-language reasons.
*   **Secondary Signals**: Computes VADER sentiment polarity to flag star rating conflicts.
*   **Responsible Interpretation**: Separates scores into Low, Moderate, and High bands, providing structured, non-accusatory summaries.

## Disclaimer
Highlights suspicious review patterns; does not prove fraud.
