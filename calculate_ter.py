import pandas as pd
import os

# --- Configuration ---
INPUT_FOLDER = 'data'
INPUT_FILE = 'mf_full_dataset_all_with_aum.csv'
OUTPUT_FILE = 'mf_full_dataset_final.csv'

# Construct Paths
input_path = os.path.join(INPUT_FOLDER, INPUT_FILE)
output_path = os.path.join(INPUT_FOLDER, OUTPUT_FILE)

def estimate_expense_ratio(row):
    """
    Calculates Estimated Expense Ratio based on:
    1. Scheme Category (Equity/Debt/Liquid/Index)
    2. Plan Type (Direct vs Regular)
    3. AUM Size (Economies of Scale)
    """
    # Safe Extraction of Values
    name = str(row.get('scheme_name', '')).title()
    category = str(row.get('scheme_category', '')).title()
    plan = str(row.get('plan', '')).title()
    
    # Handle AUM (Default to 0 if missing)
    try:
        aum = float(row.get('aum_cr', 0))
        if pd.isna(aum): aum = 0
    except:
        aum = 0

    # ---------------------------------------------------------
    # STEP 1: Determine BASE Expense Ratio (Regular Plan Benchmark)
    # ---------------------------------------------------------
    base_ter = 2.10  # Default fallback for Active Equity/Hybrid

    # Passive Funds
    if 'Etf' in category or 'Exchange Traded' in category:
        base_ter = 0.10
    elif 'Index' in category:
        base_ter = 0.80
    
    # Liquid & Overnight (Lowest Cost Debt)
    elif 'Liquid' in category or 'Overnight' in category:
        base_ter = 0.25
        
    # Short Term Debt
    elif any(x in category for x in ['Ultra Short', 'Low Duration', 'Money Market']):
        base_ter = 0.80
        
    # Other Debt (Long Term / Corporate / Gilt)
    elif 'Debt' in category or 'Bond' in category or 'Gilt' in category:
        base_ter = 1.20
        
    # Arbitrage (Hybrid)
    elif 'Arbitrage' in category:
        base_ter = 1.00
        
    # Fund of Funds
    elif 'Fof' in category or 'Fund Of Fund' in category:
        base_ter = 0.50

    # ---------------------------------------------------------
    # STEP 2: Apply DIRECT PLAN Discount
    # ---------------------------------------------------------
    # Check if 'Direct' is in plan name or scheme name
    is_direct = 'Direct' in plan or 'Direct' in name

    if is_direct:
        if base_ter > 1.80:
            base_ter -= 1.10  # Equity: ~2.10 -> ~1.00
        elif base_ter >= 1.00:
            base_ter -= 0.60  # Long Debt: ~1.20 -> ~0.60
        elif base_ter >= 0.50:
            base_ter -= 0.40  # Short Debt: ~0.80 -> ~0.40
        else:
            base_ter -= 0.05  # Liquid/ETF: ~0.25 -> ~0.20

    # ---------------------------------------------------------
    # STEP 3: Apply AUM Adjustment (Economies of Scale)
    # ---------------------------------------------------------
    if aum > 50000:       # Huge Funds (> 50k Cr)
        base_ter -= 0.30
    elif aum > 20000:     # Large Funds (> 20k Cr)
        base_ter -= 0.20
    elif aum > 5000:      # Mid-Sized Funds (> 5k Cr)
        base_ter -= 0.10
    elif aum > 0 and aum < 50: # Tiny Funds (< 50 Cr) often cost more
        base_ter += 0.10

    # ---------------------------------------------------------
    # STEP 4: Safety Caps
    # ---------------------------------------------------------
    base_ter = max(0.05, base_ter) # Minimum Floor
    base_ter = min(2.25, base_ter) # Maximum Cap

    return round(base_ter, 2)

# --- Main Execution Block ---
if __name__ == "__main__":
    print(f"Reading from: {input_path}")
    try:
        # Load Data
        df = pd.read_csv(input_path)
        
        # Apply Logic
        print("Calculating Expense Ratios...")
        df['expense_ratio'] = df.apply(estimate_expense_ratio, axis=1)
        
        # Save Result
        df.to_csv(output_path, index=False)
        print(f"Success! Processed {len(df)} rows.")
        print(f"Saved to: {output_path}")
        
    except FileNotFoundError:
        print(f"Error: Could not find file at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")