# Copilot Instructions: Mutual Fund Investment Recommendation System

## Project Overview

This is a **mutual fund recommendation engine** that processes 14,000+ Indian mutual fund schemes to match them with investor profiles based on risk tolerance, investment horizon, and financial goals.

**Key Principle**: The system balances accessibility (broad fund coverage) with quality (feature engineering for better recommendations).

## Architecture & Data Flow

### Core Pipeline (Sequential Processing)

1. **Data Fetching** (`mf_fetcher.py`): Retrieves scheme metadata and NAV data from mfapi.in API
   - Handles ~14K schemes with resume capability via checkpoint files
   - Returns: scheme_code, NAV, fund_house, scheme_category, risk_category (Equity/Debt/Hybrid)
   - Uses batch processing with tqdm progress tracking

2. **Return Metrics Computation** (`build_full_mf_dataset.py`): Calculates financial metrics
   - Returns: 1Y absolute return, 3Y/5Y CAGR, annualized volatility, Sharpe ratio
   - Uses 252-day lookback for volatility (1 trading year)
   - Handles missing/invalid data gracefully with `_safe_float()` helper

3. **Expense Ratio Estimation** (`calculate_ter.py`): 4-step logic based on SEBI regulatory limits
   - Step 1: Base TER by category (ETF: 0.10%, Index: 0.80%, Equity: 2.10%, Debt: 0.25-1.20%)
   - Step 2: Direct Plan discount (removes distributor commission: -0.05% to -1.10%)
   - Step 3: AUM adjustment (economies of scale: ±0.10-0.30%)
   - Step 4: Safety caps (min 0.05%, max 2.25%)

4. **Feature Engineering** (`feature_engineering.py`): Creates matching scores
   - Binary features: amc_reputation (top 10 AMCs), debt/equity/hybrid_score, direct_plan, category_quality
   - All features designed for vector-based recommendation matching

5. **Data Merge** (`merge.py`): Joins master dataset with performance data

### Data Locations

- **Input**: `data/list1.csv` (14K schemes from MFAPI)
- **Intermediate**: `data/dependent/mf_complete_dataset.csv`, `mf_merged_raw.csv`
- **Final Output**: `data/mf_full_dataset_final.csv`

## Critical Workflows

### Running the Full Pipeline

```bash
# 1. Fetch schemes (with resume from checkpoint)
python mf_fetcher.py

# 2. Build dataset with return metrics
python build_full_mf_dataset.py

# 3. Calculate expense ratios
python calculate_ter.py

# 4. Feature engineering
python feature_engineering.py

# 5. Merge datasets
python merge.py
```

**Note**: Each script is idempotent and can be re-run safely. Checkpoints enable resuming interrupted fetches.

## Key Conventions & Patterns

### 1. Plan Classification
- **Regular vs Direct**: Determined by presence of "direct" keyword in scheme_name (case-insensitive)
- Direct plans have lower expense ratios (distributor commission removed)

### 2. Category Matching
- Categories are SEBI-standardized: use exact keywords from `scheme_category` field
- Common searches: contains('Debt|Bond|Gilt', 'Equity|Large|Mid|Small', 'Liquid|Overnight')
- **Top 10 AMCs** (2025-2026): SBI, ICICI Prudential, HDFC, Nippon India, Kotak Mahindra, Aditya Birla Sun Life, UTI, Axis, Mirae Asset, DSP

### 3. Risk Categorization
```python
if 'debt' in scheme_name.lower():
    risk_category = 'Debt'
elif any(x in scheme_name.lower() for x in ['equity', 'large cap', 'mid cap', 'small cap']):
    risk_category = 'Equity'
else:
    risk_category = 'Hybrid'
```

### 4. Return Metrics Logic
- **CAGR Formula**: (final_nav / initial_nav) ^ (1 / years) - 1
- **Volatility**: Daily returns std dev × √252
- **Sharpe Ratio**: (mean daily return / std dev) × √252
- All metrics use dates on or before the target date (forward-looking bias prevented)

### 5. AUM-Based Features
- Classification tiers: <50Cr (add 0.10%), 5-20K Cr (sub 0.10%), 20-50K Cr (sub 0.20%), >50K Cr (sub 0.30%)
- Used for both TER estimation and economy-of-scale features

## Data Fields to Preserve

Every output CSV should include:
- `scheme_code` (int): Unique identifier
- `scheme_name` (str): Full SEBI-registered name
- `fund_house` (str): AMC name
- `scheme_category` (str): SEBI category
- `plan` (str): 'Direct' or 'Regular'
- `nav` (float): Latest Net Asset Value
- `aum_cr` (float): Assets Under Management in crores (₹)
- `abs_return_1y`, `cagr_3y`, `cagr_5y` (float): Returns
- `estimated_ter` (float): Calculated expense ratio

## External Dependencies

- **mfapi.in**: Live API for 14K+ Indian MF schemes (rate-limited, ~10 requests/sec safe)
- **pandas 2.2.2**: Data manipulation
- **requests 2.32.3**: HTTP client
- **numpy 2.1.1**: Numerical operations
- **openpyxl 3.1.5**: Excel I/O (if needed)

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| API timeout on large batches | Use checkpoint files to resume; adjust batch size in `process_all_schemes()` |
| NaN in financial metrics | `_safe_float()` handles; check raw nav_df for gaps (delisted funds) |
| Scheme category mismatches | Verify exact SEBI category spelling; some schemes use broad category keywords |
| TER calculation negative | Apply safety cap (min 0.05%); likely Direct Plan discount too aggressive |

## Vector Space for Recommendations

Feature matrix dimensions used for ML:
- User profile: age_norm, income_score, sip_norm, risk_score, horizon_norm, goal_vector, exp_score
- Fund profile: amc_reputation, debt_score, equity_score, hybrid_score, direct_plan, category_quality
- Match: Cosine similarity or dot product on normalized vectors

---

**Last Updated**: 2026-02-01 | **Status**: Production pipeline with 14K+ schemes
