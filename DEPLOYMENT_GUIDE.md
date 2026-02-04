# Mutual Fund Recommendation Engine - Complete Deployment Guide

## Quick Start

### 1. Prerequisites
- Python 3.8+
- Virtual environment activated: `mf_env\Scripts\activate` (Windows) or `source mf_env/bin/activate` (Linux/Mac)
- Dependencies installed: `pip install -r requirements.txt`

### 2. Start the Streamlit App

```bash
# Activate virtual environment
mf_env\Scripts\activate

# Run the app
streamlit run app.py
```

**Output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://<your-ip>:8501
```

Access the app at `http://localhost:8501`

---

## Application Overview

### Features

#### 1. **User Profile Form (Sidebar)**
- **Age:** 18-80 years
- **Annual Income:** ₹100K - ₹1M+
- **Monthly SIP:** ₹500 - ₹1L+
- **Risk Tolerance:** Conservative (1) → Aggressive (5)
- **Investment Horizon:** Emergency → 10+ years
- **Experience Level:** Beginner → Expert
- **Financial Goals:** Multiple checkboxes (Wealth, Retirement, Education, Emergency, Healthcare, Housing)

#### 2. **Recommendation Results**
- **Asset Allocation:** Pie chart showing Equity/Debt/Hybrid/Liquid percentages
- **Top 10 Funds:** Table with scheme details, NAV, returns, expense ratio
- **Risk Score:** User's risk profile summary

#### 3. **Live NAV Performance Chart**
- Fetches real historical NAV data from **mfapi.in** API
- Displays last 365 days of performance
- Rebase to 100 for easy comparison across funds
- Normalized price comparison (Plotly interactive chart)
- Error handling for missing/delayed API data

#### 4. **Fund Details Section**
- Expandable per-fund information
- Asset class, risk grade, AMC reputation
- Fund house and scheme category details
- Performance metrics

---

## System Architecture

### Backend Pipeline (recommendation_model.py)

**5-Stage Recommendation Engine:**

1. **CLASSIFICATION** (Stage 1)
   - Categorizes 6,138+ mutual funds into: Equity, Debt, Hybrid, Other
   - Risk grades: 1 (lowest) to 5 (highest)
   - Priority-based logic: Exclusions → Debt → Hybrid → Equity → Other

2. **HARD FILTERING** (Stage 2)
   - Emergency horizon → Liquid/Debt only
   - 1-3 year horizon → No Equity
   - 3-5 year horizon → Limited Equity
   - Beginners → No Sectoral/Small Cap/Thematic
   - Minimum AUM ≥ 100 Cr

3. **ALLOCATION** (Stage 3)
   - Formula: Equity % = Max(0, 110 - Age) + Risk Adjustment
   - Risk 1 (Conservative): 30% Equity max
   - Risk 5 (Aggressive): 100% Equity possible
   - Age-based degradation (conservative after 60)

4. **RANKING** (Stage 4)
   - Z-score normalization **within each asset class** (fixes ranking bias)
   - Metrics: Returns (CAGR/Absolute), Volatility, Sharpe Ratio, Expense Ratio
   - Weighted scoring per asset class

5. **SELECTION** (Stage 5)
   - Top N funds per asset class
   - Returns ranked list with explanations

### Frontend (Streamlit)

**Components:**
- **Sidebar:** User profile input form
- **Main content:** Profile summary + recommendations table
- **Visualization:** NAV performance chart (Plotly)
- **Details:** Expandable fund information

**Caching Strategy:**
- `@st.cache_resource`: FundRecommender instance (persistent across reruns)
- `@st.cache_data(ttl=3600)`: NAV fetch results (1-hour cache, reduces API calls)

### Data Sources

**Primary Dataset:** `data/mf_full_dataset_final.csv`
- 6,138 mutual fund schemes
- SEBI-registered schemes from India
- Columns: scheme_code, scheme_name, fund_house, nav, aum_cr, cagr_3y, cagr_5y, estimated_ter, asset_class, risk_grade, min_sip

**Live NAV API:** `https://api.mfapi.in/mf/{scheme_code}`
- Historical NAV data (365 days)
- JSON format: `[{date: "DD-MM-YYYY", nav: float}, ...]`
- Rate limit: ~10 requests/sec safe
- Progress bar with 0.2s delay between requests

---

## Configuration

### Streamlit Config (.streamlit/config.toml)

```toml
[browser]
gatherUsageStats = false

[server]
port = 8501
maxUploadSize = 200
enableXsrfProtection = true

[logger]
level = "error"
```

### Environment Variables (Optional)

```bash
# Enable debug logging
set STREAMLIT_LOGGER_LEVEL=debug

# Custom NAV fetch timeout (seconds)
set NAV_FETCH_TIMEOUT=5

# Custom port
streamlit run app.py --server.port=8502
```

---

## API Integration: mfapi.in

### How NAV Fetching Works

1. **Endpoint:** `https://api.mfapi.in/mf/{scheme_code}`
2. **Response:** JSON array of NAV data
3. **Processing:**
   - Parse dates (DD-MM-YYYY)
   - Filter last 365 days
   - Rebase to 100 for comparison
   - Handle missing data gracefully

### Example Request

```python
import requests
scheme_code = 119589  # Example: ICICI Prudential Multi-Asset

response = requests.get(
    f'https://api.mfapi.in/mf/{scheme_code}',
    timeout=5
)

if response.status_code == 200:
    data = response.json()
    nav_df = pd.DataFrame(data['data'])
    nav_df['date'] = pd.to_datetime(nav_df['date'], format='%d-%m-%Y')
    print(nav_df.head())
```

### Error Handling

```python
# If API fails or scheme not found
try:
    df = fetch_historical_nav(scheme_code)
    if df.empty:
        st.warning("NAV data unavailable for this fund")
except Exception as e:
    st.error(f"API Error: {str(e)}")
```

---

## Testing the Application

### 1. Basic Import Test

```bash
python -c "from recommendation_model import FundRecommender; print('✓ OK')"
```

Expected output:
```
[OK] Loaded 6,138 schemes with complete features
[OK] Classification complete: 6138 schemes mapped
✓ OK
```

### 2. Run Test Suite

```bash
python test_model.py
```

Expected output:
```
✓ test_data_integrity
✓ test_single_recommendation
✓ test_multiple_profiles
✓ test_edge_cases
✓ test_top_10_multiple_profiles

All 12 profiles processed successfully with 100% recommendations
```

### 3. Manual Testing

#### Conservative Profile
- Age: 50, Income: 30L, SIP: 10K, Risk: 2, Horizon: 5-10yr
- Expected: 40% Debt, 60% Equity, NO Sectoral funds

#### Aggressive Profile
- Age: 28, Income: 50L, SIP: 50K, Risk: 5, Horizon: 10+yr
- Expected: 80-100% Equity, ALL categories allowed

#### Emergency Fund
- Horizon: Emergency, SIP: 1K
- Expected: 100% Liquid/Debt funds

---

## Troubleshooting

### Issue: Port Already In Use

**Error:** `Port 8501 is not available`

**Solution:**
```bash
# Use different port
streamlit run app.py --server.port=8502

# Or kill existing process
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

### Issue: Module Not Found

**Error:** `ModuleNotFoundError: No module named 'pandas'`

**Solution:**
```bash
# Ensure virtual environment is activated
mf_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Issue: Slow NAV Fetching

**Cause:** API rate limiting or network latency

**Solution:**
- Cache is set to 1 hour (reduces repeated API calls)
- Progress bar shows live status
- Timeout set to 5 seconds per request
- 0.2s delay between requests to avoid throttling

### Issue: Empty Recommendations

**Cause:** User profile too restrictive

**Debug:**
1. Lower risk requirement
2. Increase investment horizon
3. Reduce SIP amount (min_sip constraint)
4. Check "Beginner" experience for sectoral restrictions

---

## Performance Metrics

### Startup Time
- Cold start (first run): ~5-7 seconds (loads 6K+ schemes)
- Warm start (cached): <1 second
- Recommendation generation: ~0.5-1 second
- NAV fetch (per fund): ~0.5-1 second (cached after first fetch)

### Memory Usage
- Base recommender: ~50-100 MB
- Per NAV fetch: ~1-2 MB additional
- Total typical: <200 MB

### API Calls
- Initial app load: 1 call (load_recommender)
- Per recommendation: 0 calls (use cached data)
- Per NAV visualization: 10 calls (1 per recommendation)
- With 1-hour cache: ~12 calls/hour max

---

## Production Deployment

### Option 1: Streamlit Cloud

```bash
# Push code to GitHub
git push origin main

# Deploy via Streamlit Cloud dashboard
# https://share.streamlit.io
```

### Option 2: Local Server (Docker)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

```bash
docker build -t mf-recommendation .
docker run -p 8501:8501 mf-recommendation
```

### Option 3: Cloud VMs (AWS/Azure/GCP)

```bash
# On Ubuntu/Debian VM
sudo apt update && sudo apt install python3-pip
pip install -r requirements.txt
nohup streamlit run app.py --server.port=8501 &
```

---

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | Streamlit frontend | 363 |
| `recommendation_model.py` | Core recommendation engine | 647 |
| `test_model.py` | Test suite (12 profiles) | 410 |
| `data/mf_full_dataset_final.csv` | Master fund dataset | 6,138 schemes |
| `requirements.txt` | Python dependencies | - |
| `UNICODE_FIX_SUMMARY.md` | Recent encoding fix | - |

---

## User Experience Flow

### Step-by-Step

1. **User visits:** http://localhost:8501
2. **App loads:** Recommender initializes (4-5 seconds first run)
3. **User fills form:** Sidebar inputs for profile
4. **Click "Get Recommendations":** Triggers 5-stage engine
5. **Results displayed:**
   - Allocation pie chart
   - Top 10 recommendations table
   - Risk summary
6. **View NAV chart:** Shows 365-day performance comparison (fetches live data)
7. **Expand fund details:** Click "Details" for more info

### Expected Output Example

```
Profile Summary:
- Age: 35, Income: ₹40L, Monthly SIP: ₹25K
- Risk Score: 3.5/5 (Moderate)
- Horizon: 10+ years
- Goals: Wealth, Retirement

Asset Allocation:
- Equity: 75%
- Debt: 20%
- Hybrid: 5%

Top Recommendations:
1. HDFC Equity Fund - Growth ★★★★★ (1.2% TER)
2. ICICI Prudential Value Discovery Fund ★★★★☆ (1.8% TER)
3. Axis Midcap Fund ★★★★★ (1.5% TER)
...
```

---

## Support & Documentation

- **README.md** - Project overview
- **START_HERE.md** - Getting started guide
- **MODEL_USAGE.md** - API reference for FundRecommender
- **QUICK_START.md** - Quick reference
- **TEST_RESULTS_WITH_PROFILES.md** - Test outputs with 12 profiles

---

**Last Updated:** 2026-02-04  
**Version:** 1.0 (Production Ready)  
**Status:** ✅ All Unicode issues resolved, app fully operational

