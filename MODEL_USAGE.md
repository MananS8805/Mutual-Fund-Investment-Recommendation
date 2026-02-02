# Mutual Fund Recommendation Model - Usage Guide

## Overview

The recommendation model takes user financial profiles and recommends the top mutual fund schemes based on:
- Risk tolerance and capacity
- Investment horizon
- Financial goals
- Experience level
- SIP amount and income

## Quick Start

### 1. Verify Prerequisites

Ensure the pipeline has been run to completion:
```bash
python mf_fetcher.py          # Fetch 14K schemes
python build_full_mf_dataset.py  # Compute returns
python calculate_ter.py       # Calculate expense ratios
python feature_engineering.py # Create ML features
python merge.py               # Merge datasets
```

Output should be: `data/mf_full_dataset_final.csv` (14K+ schemes with features)

### 2. Test the Model

```bash
python test_model.py
```

Expected output:
- ✅ Data Integrity Check
- ✅ Single User Recommendation
- ✅ Multiple Profiles
- ✅ Edge Cases

### 3. Use in Python Code

```python
from recommendation_model import RecommendationEngine, UserProfile

# Initialize
engine = RecommendationEngine("data/mf_full_dataset_final.csv")

# Define user profile
profile = UserProfile(
    user_id="user_001",
    age=30,
    annual_income="10L",           # Options: '5L', '10L', '25L', '50L+'
    monthly_sip=5000,              # Range: 500-50,000
    risk_tolerance="Moderate",     # Options: Low, Moderate, High, Very High
    investment_horizon="10+yr",    # Options: 1-3yr, 3-5yr, 5-10yr, 10+yr
    investment_goals=["Wealth Growth", "Retirement"],
    experience="Beginner"          # Options: Beginner, Intermediate, Expert
)

# Get recommendations
recommendations = engine.recommend(profile, top_n=10)

# Access results
for rec in recommendations:
    print(f"{rec['rank']}. {rec['scheme_name']}")
    print(f"   Match Score: {rec['match_score']}")
    print(f"   Scheme Code: {rec['scheme_code']}")
    print(f"   Reason: {rec['reason']}")
```

## API Usage

### Start the API Server

```bash
pip install flask  # If not already installed
python api.py
```

Server runs on `http://localhost:5000`

### Endpoints

#### 1. **POST /recommend** - Single User Recommendation

```bash
curl -X POST http://localhost:5000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "age": 30,
    "annual_income": "10L",
    "monthly_sip": 5000,
    "risk_tolerance": "Moderate",
    "investment_horizon": "10+yr",
    "investment_goals": ["Wealth Growth", "Retirement"],
    "experience": "Beginner",
    "top_n": 10,
    "min_aum_cr": 100.0
  }'
```

**Response:**
```json
{
  "status": "success",
  "user_id": "user_001",
  "timestamp": "2026-02-01T...",
  "total_recommendations": 10,
  "recommendations": [
    {
      "rank": 1,
      "scheme_code": 119551,
      "scheme_name": "HDFC Growth Fund - Regular Growth",
      "fund_house": "HDFC Mutual Fund",
      "scheme_category": "Equity",
      "plan": "Regular",
      "nav": 123.45,
      "aum_cr": 45000,
      "estimated_ter": 1.05,
      "cagr_3y": 0.145,
      "match_score": 0.825,
      "reason": "Top 10 AMC • High-growth match • Strong 3Y returns"
    },
    ...
  ]
}
```

#### 2. **POST /recommend-batch** - Multiple Users

```bash
curl -X POST http://localhost:5000/recommend-batch \
  -H "Content-Type: application/json" \
  -d '{
    "users": [
      {
        "user_id": "user_001",
        "age": 30,
        "annual_income": "10L",
        "monthly_sip": 5000,
        "risk_tolerance": "Moderate",
        "investment_horizon": "10+yr",
        "investment_goals": ["Wealth Growth"],
        "experience": "Beginner",
        "top_n": 5
      },
      {
        "user_id": "user_002",
        "age": 55,
        "annual_income": "50L+",
        "monthly_sip": 20000,
        "risk_tolerance": "Low",
        "investment_horizon": "3-5yr",
        "investment_goals": ["Emergency"],
        "experience": "Intermediate",
        "top_n": 5
      }
    ]
  }'
```

#### 3. **GET /scheme-details/{scheme_code}** - Scheme Details

```bash
curl http://localhost:5000/scheme-details/119551
```

**Response:**
```json
{
  "status": "success",
  "scheme_code": 119551,
  "scheme_name": "HDFC Growth Fund - Regular Growth",
  "fund_house": "HDFC Mutual Fund",
  "scheme_category": "Equity",
  "nav": 123.45,
  "aum_cr": 45000,
  "estimated_ter": 1.05,
  "cagr_1y": 0.15,
  "cagr_3y": 0.145,
  "cagr_5y": 0.128,
  "volatility_1y": 0.15
}
```

#### 4. **GET /stats** - Dataset Statistics

```bash
curl http://localhost:5000/stats
```

**Response:**
```json
{
  "status": "success",
  "total_schemes": 14171,
  "total_aum_cr": 2500000,
  "avg_ter": 1.05,
  "top_10_amcs": 3890,
  "direct_plans": 2100,
  "equity_schemes": 5200,
  "debt_schemes": 4100,
  "hybrid_schemes": 2800
}
```

#### 5. **GET /health** - Health Check

```bash
curl http://localhost:5000/health
```

## Recommendation Logic

### User Profile Vectorization

User inputs are converted to normalized features [0, 1]:

| Feature | Formula | Range |
|---------|---------|-------|
| age_norm | age / 70 | [0, 1] |
| income_score | income_level / 4 | [0, 1] |
| sip_norm | sip / 50000 | [0, 1] |
| risk_score | risk_level / 5 | [0, 1] |
| horizon_norm | horizon_level / 4 | [0, 1] |
| exp_score | experience_level / 3 | [0, 1] |

### Match Score Calculation

Final recommendation score (weighted sum):

```
match_score = 
  0.15 × amc_reputation +
  0.30 × risk_match +
  0.25 × return_match +
  0.15 × ter_score +
  0.10 × complexity_match +
  0.05 × direct_plan_bonus
```

**Risk Match Logic:**
- Low risk tolerance → Prefer debt schemes
- Moderate → Mix of debt and hybrid
- High/Very High → Equity and hybrid schemes

**Return Match Logic:**
- Short horizon (<3yr) → Prefer stable debt returns
- Long horizon (3yr+) → Prefer high historical CAGR

## Valid Input Values

### Income
- `'5L'` - ₹5 lakhs
- `'10L'` - ₹10 lakhs
- `'25L'` - ₹25 lakhs
- `'50L+'` - ₹50+ lakhs

### Risk Tolerance
- `'Low'` - Conservative investor
- `'Moderate'` - Balanced approach
- `'High'` - Growth-oriented
- `'Very High'` - Aggressive investor

### Investment Horizon
- `'1-3yr'` - Short term
- `'3-5yr'` - Medium term
- `'5-10yr'` - Long term
- `'10+yr'` - Very long term

### Experience Level
- `'Beginner'` - Restricted to index/large-cap funds
- `'Intermediate'` - Standard fund universe
- `'Expert'` - Full fund universe available

### Investment Goals
- `'Retirement'` - Equity + Debt allocation
- `'Child Edu'` - Long-term growth + stability
- `'Wealth Growth'` - Aggressive growth
- `'Emergency'` - Liquid funds only

## Output Interpretation

### Match Score Breakdown

Each recommendation includes:
- **rank**: Position in recommendation list (1-10)
- **scheme_code**: Unique fund identifier
- **match_score**: 0-1 score (higher = better fit)
- **reason**: Human-readable explanation of recommendation

### Example Reasons
- "Top 10 AMC" - Fund house is in top 10 by AUM
- "Direct Plan (lower fees)" - Direct plan with cost savings
- "Low-risk profile match" - Aligns with conservative profile
- "Strong 3Y returns" - Historical performance > 70th percentile
- "Lower expense ratio" - TER efficiency

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Recommendation engine not initialized" | Run full pipeline first; verify `data/mf_full_dataset_final.csv` exists |
| "Missing required fields" | Check JSON payload has all 8 required user fields |
| "No recommendations returned" | Lower `min_aum_cr` threshold or adjust profile (e.g., moderate risk instead of very high) |
| "Scheme not found" | Verify scheme_code is 6-digit integer from dataset |
| High API latency | Normal on first request (engine loads 14K schemes into memory) |

## Performance Notes

- **First request latency**: ~2-5 seconds (engine initialization)
- **Subsequent requests**: ~100-200ms per user
- **Batch processing**: 50 users/second average
- **Memory**: ~500MB for full scheme dataset

## Next Steps

1. Integrate with frontend UI for user input collection
2. Add A/B testing framework to measure recommendation quality
3. Implement user feedback loop for model retraining
4. Set up monitoring/alerts for API uptime
5. Create scheduled jobs for daily dataset updates

---

**For questions or issues, refer to the copilot instructions in `.github/copilot-instructions.md`**
