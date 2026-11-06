# Phishing URL Detection

LinkSafe is a FastAPI web application that classifies URLs as **Phishing (`0`)** or **Legitimate (`1`)** using 15 lexical and structural URL features. Users submit a URL and receive the prediction, model confidence, phishing probability, and URL analysis details.

The application analyzes URL text. It does not visit the destination, inspect HTML, or perform live DNS lookups.

## Dataset

Training uses a combined dataset containing **PhiUSIIL** and additional labeled URL collections. The local master file, `dataset_master_semua_fitur.csv`, preserves 98 columns, including source metadata and these feature groups:

| Prefix | Contents |
|---|---|
| `phi_*` | Original PhiUSIIL features |
| `baru_*` | Features from the additional URL datasets |
| `dns_*` | DNS-related values retained in the research data |
| `model_*` | The 15 standardized URL features used by the classifier |

Missing source-specific features are retained rather than automatically filled with zero. Only columns needed for analysis and training are loaded into memory. DNS-related archive columns are not inputs to the deployed model.

PhiUSIIL source: [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+website).

The master CSV is ignored by Git and must be supplied locally for training. The web application needs the saved model and metadata, not the training CSV.

## Notebook workflow

The main notebook is [v2.ipynb](v2.ipynb), organized into six sections:

1. **Data Understanding:** load the master and inspect columns, labels, missing values, and duplicates.
2. **Exploratory Data Analysis:** examine class distribution, URL/domain characteristics, correlations, and source differences. Normalize URLs, discard conflicting labels, and remove duplicate normalized URLs.
3. **Initial Model Experiment:** compare Logistic Regression, Random Forest, and HistGradientBoosting using a random split within development data, with optional Random Forest tuning.
4. **URL Feature Engineering for Deployment:** verify features against the shared extractor and prepare final domain-based partitions.
5. **Final Model Evaluation:** compare candidates on domain-separated validation, optionally tune Random Forest, select the final model, and evaluate it on the reserved test set. Audit results by source and URLs with/without `www`.
6. **Model Saving and Inference Testing:** save the estimator as a pickle file, export JSON metadata, reload it, and test raw URL predictions.

### Splitting, tuning, and model selection

Before the initial experiment, **20% of registered-domain groups are reserved for the final test**. The initial random-split experiment uses only the remaining development data; its tuning results are not automatically transferred to final modeling.

For final modeling, development data is split again by registered domain, allocating 25% of those groups to validation. The target overall group proportions are approximately **60% train / 20% validation / 20% test**. Row proportions can differ because domains contain different numbers of URLs.

Registered domains are identified with `tldextract`: `www.example.com` and `login.example.com` belong to the same group. The notebook asserts zero registered-domain overlap between final partitions.

Candidates are ranked on **validation** by Phishing F1, then Phishing Recall, then ROC-AUC Phishing. The selected configuration is retrained on train + validation and evaluated on the reserved test set. Test scores do not determine the selected model.

Optional Random Forest tuning uses `RandomizedSearchCV` with `GroupKFold` and optimizes **Phishing F1 (`pos_label=0`)**. Final tuning uses only the final training partition. Phishing precision, recall, and F1 refer to label 0; ROC-AUC uses the probability of label 0.

## URL features

[app/feature_extractor.py](app/feature_extractor.py) defines normalization, extraction, and `FEATURE_COLUMNS`. The master stores these features under `model_*`; the notebook removes that prefix when loading them.

```text
URLLength
DomainLength
IsDomainIP
TLDLength
NoOfSubDomain
NoOfLettersInURL
LetterRatioInURL
NoOfDegitsInURL
DegitRatioInURL
NoOfEqualsInURL
NoOfQMarkInURL
NoOfAmpersandInURL
NoOfOtherSpecialCharsInURL
SpacialCharRatioInURL
IsHTTPS
```

Names retain the spelling used by the extractor and model. Normalization adds `http://` when a scheme is absent, lowercases the scheme and network location, and removes a solitary root `/`. The same extractor is used during notebook consistency checks and web predictions.

The backend constructs its input DataFrame in metadata order and checks that the extractor, model, and metadata agree on features and labels.

## Current saved model

The current artifact selects **HistGradientBoosting**. These final test results are recorded in [models/phishing_url_metadata.json](models/phishing_url_metadata.json), with `debug_rows=0`:

| Metric | Final test result |
|---|---:|
| Accuracy | 93.29% |
| Phishing Precision | 98.49% |
| Phishing Recall | 88.32% |
| Phishing F1 | 93.12% |
| ROC-AUC Phishing | 97.08% |

These are test results for the selected model. Candidate comparisons are exported separately from validation results.

The table describes the current artifact snapshot. After retraining, consult the regenerated metadata for updated scores. The web page reads the model name, feature count, and test metrics from metadata at startup.

### Saved artifacts

| File | Purpose |
|---|---|
| `models/phishing_url_model.pkl` | Fitted scikit-learn estimator saved with `pickle.dump` and loaded with `pickle.load` |
| `models/phishing_url_metadata.json` | Feature order, labels, selected model, test metrics, scikit-learn version, and debug sample setting |
| `results/hasil_validasi_model.csv` | Candidate scores on domain-based validation |
| `results/hasil_test_final.csv` | Selected model's final test scores |
| `results/hasil_test_www.csv` | Test audit for URLs with and without `www` |
| `results/hasil_test_per_sumber.csv` | Test audit by source dataset |

Keep model and metadata from the same training run. The PKL contains the estimator itself; metadata is a separate JSON file. Load pickle artifacts only from trusted sources.

## Web application

The backend is [app/main.py](app/main.py); the interface is [app/templates/index.html](app/templates/index.html).

```text
URL form -> Validation and normalization -> 15 features in metadata order
         -> PKL model: predict + predict_proba -> PHISHING or LEGITIMATE
```

The result displays the predicted class, model name, normalized URL, HTTPS use, domain, URL/domain lengths, subdomain count, top-level domain, digits, and special characters.

**Confidence** is the model probability assigned to the predicted class. **Phishing probability** is the probability assigned to label 0. Both are percentages. The home page also displays final test metrics from metadata.

| Route | Input | Response |
|---|---|---|
| `GET /` | None | Scanner page and current model information |
| `POST /predict` | Form field `url` | HTML prediction page, or an inline validation error with HTTP status 400 |

The prediction endpoint accepts form data and returns HTML. Empty or malformed URLs and unsupported schemes receive a validation error.

## Running locally

The current model has been verified with **Python 3.11** and **scikit-learn 1.9.0**. Use an environment compatible with the model's recorded scikit-learn version.

From the project root, create a fresh environment. Example for Windows PowerShell:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install "scikit-learn==1.9.0"
```

If an existing environment uses a different Python version or fails to import scikit-learn, create a fresh environment rather than reusing its binary packages.

Ensure both `models/phishing_url_model.pkl` and `models/phishing_url_metadata.json` are present. If unavailable, run the training notebook first.

```powershell
python -m uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). After retraining, restart the server to reload the model and metadata.

## Running the notebook

Install additional notebook dependencies in the same environment:

```powershell
python -m pip install numpy matplotlib tldextract ipykernel
```

Open the project folder in VS Code, select that environment as the notebook kernel, and open `v2.ipynb`. Place `dataset_master_semua_fitur.csv` in the project root and run all cells in order with the project root as the working directory.

| Setting | Default | Purpose |
|---|---|---|
| `PHISHING_DEBUG_ROWS` environment variable | `0` | Controls `DEBUG_ROWS`; 0 uses all rows, a positive value samples rows for a quick check |
| `RUN_INITIAL_RF_TUNING` | `False` | Enables Random Forest tuning in the exploratory experiment |
| `RUN_RF_TUNING` | `False` | Enables tuning for final domain-based candidates |
| `EXPORT_TRAIN_CSV` | `False` | Exports `dataset_training_15_fitur.csv` containing URL, label, source, `has_www`, and the 15 model features |

For a quick check, set the environment variable in the terminal before starting the notebook kernel:

```powershell
$env:PHISHING_DEBUG_ROWS = "1500"
```

For full training and report results, set it to `"0"`, restart the kernel, and run all cells again. Model-saving cells write to the same paths on every run, including debug runs; use full-data artifacts for the final application and report. Saving also regenerates metadata, and evaluation exports the CSV reports.

## Project structure

```text
Phishing-URL-Detection/
|-- app/
|   |-- feature_extractor.py
|   |-- main.py
|   `-- templates/
|       `-- index.html
|-- models/
|   |-- phishing_url_model.pkl
|   `-- phishing_url_metadata.json
|-- results/
|   |-- hasil_validasi_model.csv
|   |-- hasil_test_final.csv
|   |-- hasil_test_www.csv
|   `-- hasil_test_per_sumber.csv
|-- dataset_master_semua_fitur.csv    # Local training input; ignored by Git
|-- dataset_training_15_fitur.csv     # Optional generated export
|-- v2.ipynb
|-- requirements.txt
|-- .gitignore
`-- README.md
```

## Technology

- **Training:** NumPy, pandas, scikit-learn, Matplotlib, and tldextract.
- **Persistence:** Python's standard-library `pickle` and JSON.
- **Backend:** FastAPI, Uvicorn, and python-multipart.
- **Interface:** HTML, CSS, JavaScript, and Jinja2.
- **Notebook:** Jupyter-compatible kernel in VS Code.

## Limitations

Predictions describe learned URL patterns and are supporting information, not a guarantee that a destination is safe or malicious. HTTPS does not establish legitimacy. The application does not inspect page content, reputation, blacklist status, malware, domain ownership, or live DNS data.

Results can differ across dataset sources, time periods, and URLs with or without `www`; the exported audits help assess those differences. Model probabilities are not a complete measurement of real-world security risk.

This project is intended for educational and research use. Dataset usage remains subject to the terms of each source.
