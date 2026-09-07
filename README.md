# A Hybrid Framework for Detecting Fully AI-Generated Academic Text Using spaCy, ELECTRA, and XGBoost Classification

A thesis project developed at the University of Santo Tomas, College of Information and Computing Sciences, Department of Computer Science, proposing a domain-specific hybrid framework for detecting fully AI-generated academic text.

## Overview

Existing AI-content detection tools (e.g., GPTZero, Turnitin, ZeroGPT) tend to produce high false positive rates when applied to academic writing, frequently misclassifying human-written work as AI-generated. This is largely due to their reliance on general-domain datasets and single-model detection approaches that fail to capture the unique linguistic characteristics of academic text.

This project proposes a hybrid detection framework that combines:

- **spaCy** — for stylometric feature extraction (lexical, syntactic, and sentence-level patterns)
- **ELECTRA** (`google/electra-base-discriminator`) — for semantic embeddings, used as a pre-trained feature extractor
- **XGBoost** — as the final classification layer, fusing both feature sets through late fusion

The goal is to reduce false positive rates on human-written academic text while maintaining strong detection accuracy across academic disciplines.

## Getting Started & Development Setup

Follow these steps to set up your local development environment and run the data ingestion & cleaning pipelines.

### 1. Prerequisites
- **Python 3.11 – 3.13** installed
- **Git** installed
- **VS Code** (recommended editor) with Python and Jupyter extensions

---

### 2. Virtual Environment Setup

Clone the repository and create a Python virtual environment:

```bash
# Clone the repository
git clone https://github.com/n4t5Uuu/Hybrid-AI-Text-Detector.git
cd hybrid-ai-framework

# Create a virtual environment named 'venv'
python -m venv venv
```

#### Activate the Virtual Environment:
- **Windows PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows Command Prompt (CMD)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source venv/bin/activate
  ```

---

### 3. Install Project & Web App Dependencies

#### Python Backend & Data Pipeline Dependencies:
Upgrade `pip` and install all required machine learning & data pipeline libraries (PyTorch, Transformers, spaCy, XGBoost, Kaggle, Jupyter, etc.):

```bash
pip install -r requirements.txt
```

#### Next.js Frontend Dependencies (Web Application):
If you are running or developing the Next.js web application interface:

```bash
# Install Node.js dependencies
npm install

# Start the Next.js local development server
npm run dev
```

---

### 4. Configure API Keys (`.env.local`)

To download Kaggle datasets automatically in `data_ingestion.ipynb`, set up your Kaggle API key:

1. Go to your [Kaggle Account Settings](https://www.kaggle.com/settings/api).
2. Click **Create New Token** or copy your **API Token** (`KGAT_...`).
3. Create a `.env.local` file at the root of the project:
   ```env
   KAGGLE_API_TOKEN=your_kaggle_api_token_here
   ```
*(Note: `.env.local` is listed in `.gitignore` and will never be pushed to GitHub).*

---

### 5. Running the Notebooks in VS Code

1. Open `src/notebooks/data_ingestion.ipynb` in VS Code.
2. In the upper right corner of the notebook editor, click **Select Kernel** -> choose **`venv (Python)`**.
3. Run the cells sequentially to populate:
   - `data/raw/ai/` (GPT-3.5, Claude, Gemini-Pro)
   - `data/raw/human/` (BAWE Corpus)

---

### 6. Git Ignore Rules (`.gitignore`)

The repository [.gitignore](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/.gitignore) automatically ignores large generated datasets, secrets, build artifacts, and virtual environment files. 

Make sure **never** to force-commit any of the following ignored paths:

| Category | Ignored Patterns | Description |
| :--- | :--- | :--- |
| **Secrets & API Keys** | `.env*` (`.env.local`, `.env`) | Protects secret Kaggle API keys and tokens. |
| **Raw & Processed Data** | `data/` (`data/raw/`, `data/processed/`) | All downloaded CSVs, Parquet files, and BAWE zip archives. |
| **Virtual Environments** | `venv/`, `.venv/`, `env/` | Local Python virtual environment folders. |
| **Python Cache & Models** | `__pycache__/`, `*.pyc`, `*.pkl`, `.pytest_cache/` | Compiled Python bytecode and serialized pickle files. |
| **External Repositories** | `MGTBench-2.0/` | Cloned MGTBench benchmark repository. |
| **Build & Node Artifacts** | `node_modules/`, `.next/`, `out/`, `build/`, `.vercel/` | Frontend dependencies and Next.js production builds. |

---

## Development Guidelines

- **Commit Conventions**: See [`docs/COMMIT_CONVENTIONS.md`](docs/COMMIT_CONVENTIONS.md) for commit message format
- **Git Workflow**: See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for branching and PR guidelines
- **Text Cleaning Reference**: See [`docs/TEXT_CLEANING_API.md`](docs/TEXT_CLEANING_API.md) for cleaning functions

## Authors

- Baltazar, Jorge Kollin T.
- Espinoza, Eishiea Mae F.
- Lagazo, Jonah Levi E.
- Olmedo, Alden Alexander F.

**Adviser:** Engr. Bernard C. Fabro, PCpE, MSc.

## System Architecture

End-to-end pipeline for the thesis experiment and the deployed web application. The hybrid path (spaCy + ELECTRA + late fusion + XGBoost) is the proposed model; three baselines use the same XGBoost training procedure on different feature sets only.

```
 1. DATA INGESTION
    BAWE Corpus (Human, label 0)  |  GPT-3.5, Claude 3/3.5, Gemini-Pro (AI, label 1)
                    ↓
 2. TEXT PREPROCESSING & COMBINE
    clean_pipeline per dataset → one unsplit table: text | source | label (~9,000 rows)
    (see Preprocessing below; tokenization is NOT this step)
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
 3. FEATURE EXTRACTION    STANDALONE BASELINES (same combined table, skip fusion)
    spaCy → S (N-dim)      spaCy-only → S
    ELECTRA → E (768-d)    ELECTRA-only → E
                           XGBoost-only → R (preprocessed-text / TF-IDF features)
         ↓
 4. LATE FUSION (hybrid only)
    H = [S | E]  →  N + 768 dimensional vector (hybrid XGBoost input X)
                    ↓
 5. STRATIFIED SPLIT (once, after features)
    70% train | 15% validation (held out) | 15% test
    same row-indices on H, S, E, and R
                    ↓
 6. MODEL DEVELOPMENT (all four models — identical procedure, different X)
    Grid search + 5-fold CV on 70% → pick best params → refit on full 70% → score on 15% val
    Hybrid: X=H  |  spaCy-only: X=S  |  ELECTRA-only: X=E  |  XGBoost-only: X=R
                    ↓
 7. OUTPUTS & INTERPRETATION
    Evaluate all four on the SAME 15% test → Table 6 metrics → paired t-test on FPR (α=0.05)
    Per-text: predict_proba() → Human / Mixed / AI score bands (see below)

    Web app (deployment): single text → clean → spaCy + ELECTRA → fuse → saved hybrid XGBoost → score
```

### Preprocessing (`clean_pipeline`)

Text is **standardized** (not linguistically normalized — no global lowercasing or stemming on the saved corpus). Each dataset is cleaned with `src/utils/cleaning/cleaning_methods.py`, then row-stacked into one table.

**Per-dataset filters:** `is_academic_content` (Claude), `contains_foreign_language`, `clean_markdown_formatting` (Gemini only), drop empty rows, `placeholder_density >= 0.4`, windowed density check.

**`clean_pipeline` order:** `[[URL]]` → `[[CODE]]` → `[[MUSIC]]` → `[[COMPLEXITY]]` → strip references → `[[CITATION]]` → list numbering → `[[EQUATION]]` (three math passes) → merge adjacent tags → mop leftover → strip surrogates.

Full function reference: [`docs/TEXT_CLEANING_API.md`](docs/TEXT_CLEANING_API.md).

### Model development (all four XGBoost models)

Each configuration uses the **same** procedure on its own feature matrix:

1. Take the **70% train** slice only (validation and test unseen during CV).
2. **Grid search + 5-fold cross-validation** on that 70% to select hyperparameters.
3. **Refit** on the full 70% with the best parameters.
4. **Score on 15% validation** to confirm or select the final model.
5. **Final evaluation on 15% test only** — metrics, Table 6, and paired t-test.

Baselines skip **late fusion** only. They do **not** skip XGBoost or hyperparameter tuning.

## Detection Score Interpretation

The model outputs a probability confidence score via XGBoost's `predict_proba()`, interpreted using thresholds adapted from Hadra et al. (2026):

| Score Range | Interpretation |
|---|---|
| 0% – 20% | Human-Written |
| 21% – 79% | Hybrid / Possible AI Assistance |
| 80% – 100% | AI-Generated |

## Datasets

Experimental corpus (~9,000 texts) used in the architecture diagram and thesis methodology:

| Source | Label | Role | Size (approx.) |
|---|---|---|---|
| **BAWE Corpus** | 0 (Human) | Human-written academic essays | ~2,800 |
| **MGTBench-2.0 (`gpt35_new`)** | 1 (AI) | GPT-3.5 generated academic texts | ~2,000 |
| **QuietImpostor / Claude-3** | 1 (AI) | Claude 3 Opus & 3.5 Sonnet | ~700 |
| **Kaggle Gemini-Pro LLM DAIGT** | 1 (AI) | Gemini-Pro generated essays | ~3,500 |

After cleaning, all sources are combined into one table (`text | source | label`). Stratified sampling on label (and discipline) produces a single **70% / 15% / 15%** split applied identically to the hybrid and all baseline feature matrices.

## Methodology

| Step | Description |
|---|---|
| **Ingestion** | Load BAWE (Human) and GPT-3.5, Claude, Gemini-Pro (AI) sources |
| **Preprocessing** | Per-dataset `clean_pipeline` + filters; combine into one labeled table (no split yet) |
| **Feature extraction** | spaCy (`en_core_web_sm`) stylometric vector **S**; ELECTRA (`google/electra-base-discriminator`, frozen) 768-d **E** CLS embedding; simple/TF-IDF **R** for XGBoost-only baseline |
| **Late fusion** | Hybrid only: **H = [S \| E]** (N + 768 dimensions) |
| **Split** | One stratified 70% / 15% val / 15% test; shared row-indices on **H**, **S**, **E**, **R** |
| **Classification** | Four separate XGBoost models; grid search + 5-fold CV on 70%, refit on full 70%, validation check, test evaluation |
| **Baselines** | spaCy-only (**X=S**), ELECTRA-only (**X=E**), XGBoost-only (**X=R**) — same splits, same XGBoost tuning, no late fusion |

**Independent variable:** feature set (stylometric-only, neural-only, hybrid, simple-features).  
**Dependent variable:** false positive rate (primary); accuracy, precision, recall, F1-score, ROC-AUC (secondary).

## Evaluation & Outputs

All four tuned models are evaluated on the **same 15% test set**. Results are reported in **Table 6** (spaCy, ELECTRA, XGBoost, Hybrid):

- Accuracy
- Precision
- Recall
- F1-Score
- ROC-AUC
- Confusion Matrix
- **False Positive Rate (FPR)** — primary metric

A **paired t-test** (α = 0.05) compares Hybrid FPR against each baseline FPR to accept or reject **H₀**.

Per-text **AI detection output** (web app or single inference): binary label (0 = Human-written, 1 = AI-generated) plus `predict_proba()` score interpreted with the score bands in the section above — distinct from batch test-set metrics.

## Hypothesis

- **H₀:** There is no statistically significant difference in the false positive rate (FPR) between the proposed hybrid model and baseline AI detection models.
- **Hₐ:** There is a statistically significant difference in the false positive rate (FPR) between the proposed hybrid model and baseline AI detection models.

## Scope and Limitations

- Designed only for fully AI-generated academic text; does not extend to partially AI-generated or AI-assisted text
- Restricted to English academic texts
- Limited to three LLMs: GPT-3.5, Claude 3 Opus/3.5 Sonnet, and Gemini-Pro
- Performance is dependent on the quality and diversity of training datasets

## Status

This repository reflects an ongoing thesis project currently undergoing panel-review revisions. Chapters 1–3 (Introduction, Review of Related Literature, Methodology) are complete; Chapters 4–5 (Results and Discussion, Conclusion) are pending.

## Institution

University of Santo Tomas
College of Information and Computing Sciences
Department of Computer Science

## License

This project is submitted in partial fulfillment of the requirements for the degree of Bachelor of Science in Computer Science. All rights reserved by the authors unless otherwise specified.
