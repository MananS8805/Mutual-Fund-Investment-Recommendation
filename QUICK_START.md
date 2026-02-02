# Quick Start Guide - Recommendation Model

## 30-Second Setup

```bash
# 1. Ensure full pipeline is complete
python mf_fetcher.py          # Takes ~30 minutes for 14K schemes
python build_full_mf_dataset.py
python calculate_ter.py
python feature_engineering.py
python merge.py

# 2. Test the model
python test_model.py

# 3. Use it!
```

## 3 Ways to Use

### Option 1: Python Direct (Fastest for scripts)

```python
from recommendation_model import RecommendationEngine, UserProfile

engine = RecommendationEngine("data/mf_full_dataset_final.csv")

# Young aggressive investor
profile = UserProfile(
    user_id="user_001",
    age=28,
    annual_income="10L",
    monthly_sip=5000,
    risk_tolerance="High",
    investment_horizon="10+yr",
    investment_goals=["Wealth Growth"],
    experience="Beginner"
)

recs = engine.recommend(profile, top_n=10)
for r in recs:
    print(f"{r['rank']}. {r['scheme_name']} (Score: {r['match_score']})")
```

### Option 2: REST API (For web/mobile apps)

```bash
# Start server
python api.py

# In another terminal:
curl -X POST http://localhost:5000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "age": 28,
    "annual_income": "10L",
    "monthly_sip": 5000,
    "risk_tolerance": "High",
    "investment_horizon": "10+yr",
    "investment_goals": ["Wealth Growth"],
    "experience": "Beginner"
  }'
```

### Option 3: Batch Processing (For batch jobs)

```python
from recommendation_model import RecommendationEngine, UserProfile

engine = RecommendationEngine("data/mf_full_dataset_final.csv")

users = [
    UserProfile("user_1", 25, "5L", 2000, "High", "10+yr", ["Wealth Growth"], "Beginner"),
    UserProfile("user_2", 45, "25L", 10000, "Moderate", "5-10yr", ["Retirement"], "Intermediate"),
    UserProfile("user_3", 60, "50L+", 20000, "Low", "1-3yr", ["Emergency"], "Expert"),
]

for user in users:
    recs = engine.recommend(user, top_n=5)
    print(f"\nUser {user.user_id}: Top {len(recs)} recommendations")
```

## Input Reference

```python
UserProfile(
    user_id="any_string",                    # Unique identifier
    age=int,                                 # 18-70
    annual_income="5L|10L|25L|50L+",        # Income bracket
    monthly_sip=int,                         # 500-50000
    risk_tolerance="Low|Moderate|High|Very High",
    investment_horizon="1-3yr|3-5yr|5-10yr|10+yr",
    investment_goals=[
        "Retirement",      # Equity + Debt mix
        "Child Edu",       # Long-term growth
        "Wealth Growth",   # Aggressive
        "Emergency"        # Liquid funds
    ],
    experience="Beginner|Intermediate|Expert"
)
```

## Output Fields

```python
recommendation = {
    'rank': 1,                           # Position 1-10
    'scheme_code': 119551,               # Unique scheme ID
    'scheme_name': 'HDFC Growth Fund...',
    'fund_house': 'HDFC Mutual Fund',
    'scheme_category': 'Equity|Debt|Hybrid',
    'plan': 'Direct|Regular',
    'nav': 123.45,                       # Current Net Asset Value
    'aum_cr': 45000,                     # Assets in crores
    'estimated_ter': 1.05,               # Total Expense Ratio %
    'cagr_3y': 0.145,                    # 3-year return
    'cagr_5y': 0.128,                    # 5-year return
    'match_score': 0.825,                # 0-1 fit score
    'reason': 'Top 10 AMC • Strong returns • Lower fees'
}
```

## Common Use Cases

### Conservative Senior (Age 60)
```python
profile = UserProfile(
    user_id="conservative",
    age=60,
    annual_income="50L+",
    monthly_sip=10000,
    risk_tolerance="Low",
    investment_horizon="3-5yr",
    investment_goals=["Emergency"],
    experience="Intermediate"
)
engine.recommend(profile, top_n=5)
```

### Aggressive Young (Age 25)
```python
profile = UserProfile(
    user_id="aggressive",
    age=25,
    annual_income="5L",
    monthly_sip=2000,
    risk_tolerance="Very High",
    investment_horizon="10+yr",
    investment_goals=["Wealth Growth", "Retirement"],
    experience="Expert"
)
engine.recommend(profile, top_n=10)
```

### Balanced Middle (Age 40)
```python
profile = UserProfile(
    user_id="balanced",
    age=40,
    annual_income="25L",
    monthly_sip=8000,
    risk_tolerance="Moderate",
    investment_horizon="10+yr",
    investment_goals=["Wealth Growth", "Child Edu"],
    experience="Intermediate"
)
engine.recommend(profile, top_n=10)
```

## API Endpoints (if running Flask)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/recommend` | Single user recommendation |
| POST | `/recommend-batch` | Multiple users at once |
| GET | `/scheme-details/{code}` | Get full scheme info |
| GET | `/stats` | Dataset statistics |
| GET | `/health` | Server health check |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ImportError: recommendation_model | Run from project root: `python recommendation_model.py` |
| FileNotFoundError: mf_full_dataset_final.csv | Run full pipeline first (see Setup section) |
| No recommendations returned | Try lowering `min_aum_cr` or adjusting risk_tolerance |
| Slow on first request | Normal - engine loads 14K schemes (2-5s), subsequent calls are fast |

## Files Created

```
recommendation_model.py      ← Core engine (use this!)
api.py                       ← Flask API wrapper
test_model.py                ← Run to verify
MODEL_USAGE.md               ← Full documentation
IMPLEMENTATION_SUMMARY.md    ← Implementation details
QUICK_START.md              ← This file!
```

## Next: Frontend Integration

The model is ready for:
- ✅ React/Vue form interface
- ✅ Mobile app integration
- ✅ Dashboard analytics
- ✅ Email recommendations
- ✅ A/B testing framework

---

**Questions?** See `MODEL_USAGE.md` for detailed docs or `.github/copilot-instructions.md` for architecture.
