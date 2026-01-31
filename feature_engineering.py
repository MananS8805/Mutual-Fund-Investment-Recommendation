import pandas as pd

# Load & Clean (14,171 schemes)
df = pd.read_csv("mf_complete_dataset.csv")
df = df[df['status'] == 'success'].copy()

# ✅ UPDATED: Top 10 AMCs by AUM (2025-2026)
top_10_amcs = [
    'SBI', 'ICICI Prudential', 'HDFC', 'Nippon India', 
    'Kotak Mahindra', 'Aditya Birla Sun Life', 'UTI', 
    'Axis', 'Mirae Asset', 'DSP'
]

# 1. AMC Reputation (Top 10 = 1 point)
df['amc_reputation'] = df['fund_house'].str.contains(
    '|'.join(top_10_amcs), case=False, na=False
).astype(int)

# 2. Debt Score (Conservative friendly)
df['debt_score'] = df['scheme_category'].str.contains(
    'Debt|Corporate|Liquid|Banking|PSU|Gilt', case=False, na=False
).astype(int)

# 3. Equity Score (Growth oriented)
df['equity_score'] = df['scheme_category'].str.contains(
    'Equity|Large|Mid|Small|Flexi|Multi', case=False, na=False
).astype(int)

# 4. Hybrid Score (Balanced)
df['hybrid_score'] = df['scheme_category'].str.contains(
    'Hybrid|Balanced|Arbitrage|Conservative', case=False, na=False
).astype(int)

# 5. Direct Plan Bonus
df['direct_plan'] = (df['plan'] == 'Direct').astype(int)

# 6. Category Quality Score (SEBI standardized)
df['category_quality'] = df['scheme_category'].str.contains(
    'Large Cap|Flexi Cap|Corporate Bond|Banking', case=False, na=False
).astype(int)

print("📊 Dataset Analysis:")
print(f"Total schemes: {len(df):,}")
print(f"Top 10 AMCs coverage: {df['amc_reputation'].mean()*100:.1f}%")
print(f"Debt schemes: {df['debt_score'].sum():,} ({df['debt_score'].mean()*100:.1f}%)")
print(f"Equity schemes: {df['equity_score'].sum():,} ({df['equity_score'].mean()*100:.1f}%)")

df.to_csv("mf_ready_for_ml.csv", index=False)
print("✅ ML-ready dataset saved!")
