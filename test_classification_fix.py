#!/usr/bin/env python3
"""
Quick verification that the _classify_funds bug fix works correctly.
Tests: Bond Index funds should be classified as DEBT, not EQUITY.
"""

import pandas as pd
from recommendation_model import FundRecommender

def test_classification_fix():
    """Verify that 'Debt Disguised as Equity' bug is fixed."""
    print("\n" + "=" * 80)
    print("BUG FIX VERIFICATION: Debt Disguised as Equity")
    print("=" * 80)
    
    engine = FundRecommender('data/mf_full_dataset_final.csv')
    df = engine.df_schemes
    
    # Test 1: Check for Bond Index funds (should be Debt)
    print("\nTest 1: Bond Index Classification")
    print("-" * 80)
    bond_index_funds = df[df['scheme_name'].str.contains('bond', case=False, na=False)]
    bond_index_funds = bond_index_funds[bond_index_funds['scheme_name'].str.contains('index', case=False, na=False)]
    
    if len(bond_index_funds) > 0:
        print(f"Found {len(bond_index_funds)} Bond Index funds:\n")
        all_correct = True
        for idx, row in bond_index_funds.iterrows():
            is_debt = row['Asset_Class'] == 'Debt'
            status = "PASS" if is_debt else "FAIL"
            all_correct = all_correct and is_debt
            print(f"  [{status}] {row['scheme_name'][:65]}")
            print(f"        Classification: {row['Asset_Class']}\n")
        
        if all_correct:
            print("SUCCESS: All Bond Index funds correctly classified as DEBT!")
        else:
            print("FAILED: Some Bond Index funds still misclassified!")
        print()
    else:
        print("No Bond Index funds found - checking SDL funds...")
    
    # Test 2: Check SDL funds (should be Debt)
    print("\nTest 2: SDL (Sovereign Development Loan) Classification")
    print("-" * 80)
    sdl_funds = df[df['scheme_name'].str.contains('sdl', case=False, na=False)]
    
    if len(sdl_funds) > 0:
        print(f"Found {len(sdl_funds)} SDL funds:\n")
        all_correct = True
        for idx, row in sdl_funds.iterrows():
            is_debt = row['Asset_Class'] == 'Debt'
            status = "PASS" if is_debt else "FAIL"
            all_correct = all_correct and is_debt
            print(f"  [{status}] {row['scheme_name'][:65]}")
            print(f"        Classification: {row['Asset_Class']}\n")
        
        if all_correct:
            print("SUCCESS: All SDL funds correctly classified as DEBT!")
        else:
            print("FAILED: Some SDL funds still misclassified!")
        print()
    
    # Test 3: Overall classification distribution
    print("\nTest 3: Overall Classification Distribution")
    print("-" * 80)
    class_summary = df['Asset_Class'].value_counts()
    print(f"Total Equity funds:  {class_summary.get('Equity', 0):,}")
    print(f"Total Debt funds:    {class_summary.get('Debt', 0):,}")
    print(f"Total Hybrid funds:  {class_summary.get('Hybrid', 0):,}")
    print(f"Total Other funds:   {class_summary.get('Other', 0):,}")
    print(f"{'─' * 40}")
    print(f"Total schemes:       {len(df):,}")
    print()
    
    # Test 4: Verify Index funds that should be Equity (not Bond-related)
    print("\nTest 4: Regular Index Funds (Non-Bond)")
    print("-" * 80)
    regular_index = df[df['scheme_name'].str.contains('index', case=False, na=False)]
    regular_index = regular_index[~regular_index['scheme_name'].str.contains('bond|psu', case=False, na=False)]
    
    print(f"Found {len(regular_index)} regular Index funds (non-Bond):")
    equity_count = (regular_index['Asset_Class'] == 'Equity').sum()
    print(f"  Classified as Equity: {equity_count}/{len(regular_index)}")
    print(f"  Status: {'PASS' if equity_count == len(regular_index) else 'FAIL'}")
    print()
    
    print("=" * 80)
    print("CLASSIFICATION FIX VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    test_classification_fix()
