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
   - `data/raw/ai/` (Gemini, Claude, GPT-3.5, Llama-3, etc.)
   - `data/raw/human/` (arXiv, Wikipedia, Gutenberg, BAWE)

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

## Architecture

```
                     ┌────────────────────┐
                     │  Input Texts        │
                     │  Human: BAWE Corpus  │
                     │  AI: GPT-3.5, Claude,│
                     │       Gemini-Pro      │
                     └─────────┬──────────┘
                               │
                     ┌─────────▼──────────┐
                     │  Text Preprocessing │
                     │  (cleaning,         │
                     │   tokenization)     │
                     └─────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                                  │
      ┌───────▼────────┐              ┌─────────▼─────────┐
      │     spaCy       │              │      ELECTRA        │
      │  Stylometric     │              │  Semantic Embeddings │
      │  Features        │              │  ([CLS] token, 768-d)│
      └───────┬────────┘              └─────────┬─────────┘
              │                                  │
              └────────────────┬─────────────────┘
                               │
                     ┌─────────▼──────────┐
                     │   Late Fusion        │
                     │  (Feature            │
                     │   Concatenation)      │
                     └─────────┬──────────┘
                               │
                     ┌─────────▼──────────┐
                     │  XGBoost Classifier  │
                     │  (Gradient Boosting) │
                     └─────────┬──────────┘
                               │
                     ┌─────────▼──────────┐
                     │   Output             │
                     │  Human-Written /     │
                     │  AI-Generated +      │
                     │  Confidence Score     │
                     └──────────────────────┘
```

## Detection Score Interpretation

The model outputs a probability confidence score via XGBoost's `predict_proba()`, interpreted using thresholds adapted from Hadra et al. (2026):

| Score Range | Interpretation |
|---|---|
| 0% – 20% | Human-Written |
| 21% – 79% | Hybrid / Possible AI Assistance |
| 80% – 100% | AI-Generated |

## Datasets

| Source | Category / Source Type | Size (approx.) |
|---|---|---|
| **BAWE Corpus** | Human-written academic texts | ~2,761 text files |
| **MGTBench-2.0 (Human)** | Human-written reference texts (arXiv, Wikipedia, Gutenberg) | ~83,000 texts |
| **MGTBench-2.0 (AI)** | AI-generated (GPT-3.5, GPT-4o-mini) | ~222,000 texts |
| **QuietImpostor / Claude-3 Dataset** | Claude-generated texts | ~9,000 texts |
| **Kaggle Gemini-Pro LLM DAIGT** | Gemini-Pro generated essays | ~14,000 texts |

Multi-source dataset covering both Human-written and AI-generated text across 16 academic disciplines, split 70% training / 15% validation / 15% test using stratified sampling.

## Methodology

- **Feature Extraction:** spaCy (stylometric) and ELECTRA (semantic), extracted in parallel
- **Fusion Strategy:** Late fusion — each pipeline is processed independently before concatenation at the classification stage
- **Classification:** XGBoost with grid search and 5-fold cross-validation for hyperparameter tuning
- **Baseline Comparison:** Evaluated against three standalone models — spaCy-only, ELECTRA-only, and XGBoost-only — under identical experimental conditions

## Evaluation Metrics

- Accuracy
- Precision
- Recall
- F1-Score
- ROC-AUC
- Confusion Matrix
- **False Positive Rate** (primary metric)

Statistical significance of the false positive rate reduction is assessed using a paired t-test at the 0.05 significance level.

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
