# ReviewRadar Training Datasets

This directory documents the provenance and structure of the dataset used to train the ReviewRadar classifier.

## Dataset Information

- **Name**: Fake Reviews Dataset
- **Original Creators**: Joni Salminen, Chandrashekhar Kandpal, Ahmed Mohamed Kamel, Soon-Gyo Jung, and Bernard J. Jansen
- **Citation**: Salminen, J., Kandpal, C., Kamel, A. M., Jung, S.-G., & Jansen, B. J. Creating and Detecting Fake Reviews of Online Products.
- **Original Source URL**: [Kaggle Dataset](https://www.kaggle.com/datasets/mexwell/fake-reviews-dataset) (or the [OSF repository](https://osf.io/tyue9/))
- **Date Accessed**: July 2026

## Provenance & Splits

The full raw dataset (`fake reviews dataset.csv`) contains approximately 40,000 product reviews across various categories. The training, validation, and test splits (`train.csv`, `validation.csv`, and `test.csv`) are generated artifacts built using a random split ratio (e.g. 70/15/15) during model development.

Because of the dataset's size (~30MB total) and to optimize repository performance, the full raw and split CSV files are **not** committed to Git tracking. They remain local to the development environment.

## Expected Columns & Schema

The dataset follows this structure:

| Column | Type | Description |
| :--- | :--- | :--- |
| `category` | String | Product category (e.g., `Home_and_Kitchen_5`) |
| `rating` | Float | Star rating (integer values 1–5, or float representations like `5.0`) |
| `label` | String | Classification target: `OR` (Organic/Genuine) or `CG` (Computer-Generated) |
| `review_text` | String | The full text of the product review |

## Local Placement Instructions

To reproduce evaluation or run local model training, obtain the dataset files from the original sources listed above, and place them in the following paths:

1.  **Raw Dataset**: `data/raw/fake reviews dataset.csv`
2.  **Splits**: `data/split/train.csv`, `data/split/validation.csv`, `data/split/test.csv`

## License

The dataset is not distributed with this repository. Users must obtain it from the original source and follow the source’s applicable terms and license.
