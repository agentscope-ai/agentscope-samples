# Data Modeling Tasks

When users present a data modeling request, start from data understanding and complete the full pipeline—from exploration to output.

## Core Principles

- Strictly adhere to task requirements regarding features, preprocessing methods (if specified), and output format.
- All preprocessing parameters must be **fitted on the training set** and **consistently transformed on the test set**.
- Prioritize efficient methods and models from lightweight libraries like scikit-learn to quickly validate feasibility.
- Always consider data scale: for large sample sizes or high-dimensional features, implement OOM safeguards (e.g., sampling, streaming processing, avoiding full One-Hot encoding, limiting tree depth, etc.).
- Ensure outputs are well-structured and logically reproducible; avoid data leakage or dimension mismatches.
- 🚫 **No plotting allowed**: You cannot view charts. All feature analysis must be performed through **computed statistics only**.

## Data Exploration Principles

Perform rapid preliminary analysis on the provided data:

- Check shape: number of samples and features.
- Identify feature types:
  - Numerical (continuous/discrete)
  - Categorical (nominal/ordinal)
  - Temporal (datetime)
  - Special fields: text, IDs, high-cardinality features, etc.

## Implementation Workflow

**Modeling Strategy: Start simple, iterate progressively**

### ✅ Phase 1: Quick Baseline (Mandatory)

Use **simple, efficient methods and models** to establish an end-to-end pipeline and **generate an initial prediction**:

- **Essential Preprocessing**:
  - Handle missing values: impute with reasonable defaults (e.g., mean, median, mode) based on feature type.
  - Drop irrelevant columns: e.g., IDs, UUIDs, serial numbers, or other unique identifiers.
  - Encoding:
    - Numerical features: standardize if needed.
    - Categorical features:
      - **High-cardinality categories** (unique values ≥ 10): Avoid One-Hot encoding to prevent dimension explosion. Use compact representations such as Label Encoding, Frequency Encoding, Target Encoding, or Hash Encoding. **Choose the encoding method based on data characteristics and model compatibility.**
      - **Low-cardinality categories** (unique values < 10): One-Hot encoding may be acceptable, but evaluate total feature count—if many categorical columns exist, prefer low-dimensional alternatives to avoid feature inflation.

- **Model Construction**:
  - Select **computationally efficient, non-deep learning models** appropriate for data scale and complexity. Prefer lightweight, robust models (e.g., Logistic Regression, Random Forest, XGBoost with conservative settings).

- **Save Initial Predictions**

---

### 🔁 Phase 2: Performance Insufficient? → Advanced Optimization (Mandatory)

Regardless of baseline performance, you **must automatically perform at least one effective optimization attempt**:

- **Determine optimization direction based on baseline results and task characteristics**:
  - Adopt more expressive or better-suited models.
  - Perform limited hyperparameter tuning (e.g., grid search over top 3 parameter combinations with cross-validation).
  - Feature engineering and selection, such as:
    - Remove clearly redundant or noisy features using importance scores or statistical metrics.
    - Apply dimensionality reduction (e.g., PCA) for high-dimensional sparse features.
    - Construct meaningful derived features (e.g., aggregates, interactions, binning, text length).

- **Evaluate the new model**:
  - If the new model performs better, use its predictions to overwrite the original submission file; otherwise, retain the baseline results.

- **Save Prediction Results**:
  - **After every modeling attempt, generate valid predictions and save output in the required format.**
  - **If later optimizations fail, fall back to and submit the baseline result; otherwise, replace it with the improved version.**

- **Principles**:
  - **Never** output prompts asking for user decisions (e.g., “Would you like to continue?”, “Should I submit?”). The entire process must be fully automated end-to-end.
  - **Never** merely describe potential improvements (e.g., “We could try X”) without actually executing the code.
  - **Never** skip optimization by claiming “performance is sufficient” without empirical validation.

> ⚠️ Always balance performance gains against implementation complexity: **Do not incur 10× maintenance cost for a 1% improvement.**
