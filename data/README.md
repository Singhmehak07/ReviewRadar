# ReviewRadar Training Datasets

This directory contains the split training, validation, and test sets.

## Dataset Information
*   **Source**: Derived from the "Fake Reviews Dataset" (composed of organic and computer-generated product reviews).
*   **License**: Publicly available dataset (under standard open-data redistribution terms).
*   **Redistribution**: Because of its size (~30MB total) and to keep the repository lightweight, the full CSV datasets are excluded from Git tracking and preserved locally.

## Expected Columns
*   `category`: Product category (e.g. `Home_and_Kitchen_5`)
*   `rating`: Star rating (float/int, e.g. `5.0`)
*   `label`: `CG` (computer-generated) or `OR` (organic/genuine)
*   `review_text`: The body of the review.

## Model Training
The classifier is trained using TF-IDF features followed by a Logistic Regression model to distinguish organic reviews from computer-generated text patterns.
