#!/usr/bin/env python3
"""
Verification that the classification leak patches work correctly.
Tests: Gold ETF and Bharat Bond FOF are correctly classified as 'Other' and 'Debt'.
"""

import pandas as pd
from recommendation_model import FundRecommender

def test_classification_leaks():
    """Verify that classification leaks are patched."""
    print("\n" + "=" * 80)
    print("CLASSIFICATION LEAK PATCH VERIFICATION")
    print("=" * 80)
    
    engine = FundRecommender('data/mf_full_dataset_final.csv')
    df = engine.df_schemes
    
    # Test 1: Commodity funds (Gold ETF, Silver) should be 'Other'
    print("\nTest 1: Commodity Exclusion (Gold ETF, Silver)")
    print("-" * 80)
    commodity_funds = df[df['scheme_name'].str.contains('gold|silver', case=False, na=False)]
    
    if len(commodity_funds) > 0:
        print(f"Found {len(commodity_funds)} commodity funds:\n")
        all_correct = True
        for idx, row in commodity_funds.iterrows():
            is_other = row['Asset_Class'] == 'Other'
            status = "PASS" if is_other else "FAIL"
            all_correct = all_correct and is_other
            print(f"  [{status}] {row['scheme_name'][:70]}")
            print(f"        Classification: {row['Asset_Class']} (Expected: Other)\n")
        
        if all_correct:
            print("SUCCESS: All commodity funds correctly classified as OTHER!")
        else:
            print("FAILED: Some commodity funds still misclassified!")
    else:
        print("No commodity funds found in dataset.")
    print()
    
    # Test 2: Bharat Bond FOF should be 'Debt'
    print("\nTest 2: Bharat Bond FOF Classification")
    print("-" * 80)
    bharat_funds = df[df['scheme_name'].str.contains('bharat bond', case=False, na=False)]
    
    if len(bharat_funds) > 0:
        print(f"Found {len(bharat_funds)} Bharat Bond funds:\n")
        all_correct = True
        for idx, row in bharat_funds.iterrows():
            is_debt = row['Asset_Class'] == 'Debt'
            status = "PASS" if is_debt else "FAIL"
            all_correct = all_correct and is_debt
            print(f"  [{status}] {row['scheme_name'][:70]}")
            print(f"        Classification: {row['Asset_Class']} (Expected: Debt)\n")
        
        if all_correct:
            print("SUCCESS: All Bharat Bond funds correctly classified as DEBT!")
        else:
            print("FAILED: Some Bharat Bond funds still misclassified!")
    else:
        print("No Bharat Bond funds found in dataset.")
    print()
    
    # Test 3: G-Sec funds should be 'Debt'
    print("\nTest 3: G-Security (G-Sec) Classification")
    print("-" * 80)
    gsec_funds = df[df['scheme_name'].str.contains('g-sec|g-security', case=False, na=False)]
    
    if len(gsec_funds) > 0:
        print(f"Found {len(gsec_funds)} G-Sec funds:\n")
        all_correct = True
        for idx, row in gsec_funds.iterrows():
            is_debt = row['Asset_Class'] == 'Debt'
            status = "PASS" if is_debt else "FAIL"
            all_correct = all_correct and is_debt
            print(f"  [{status}] {row['scheme_name'][:70]}")
            print(f"        Classification: {row['Asset_Class']} (Expected: Debt)\n")
        
        if all_correct:
            print("SUCCESS: All G-Sec funds correctly classified as DEBT!")
        else:
            print("FAILED: Some G-Sec funds still misclassified!")
    else:
        print("No G-Sec funds found in dataset.")
    print()
    
    # Test 4: Overall classification distribution (should be healthy)
    print("\nTest 4: Overall Classification Distribution")
    print("-" * 80)
    class_summary = df['Asset_Class'].value_counts()
    print(f"Total Equity funds:  {class_summary.get('Equity', 0):,}")
    print(f"Total Debt funds:    {class_summary.get('Debt', 0):,}")
    print(f"Total Hybrid funds:  {class_summary.get('Hybrid', 0):,}")
    print(f"Total Other funds:   {class_summary.get('Other', 0):,}")
    print(f"{'─' * 40}")
    print(f"Total schemes:       {len(df):,}")
    
    # Check proportions
    equity_pct = (class_summary.get('Equity', 0) / len(df)) * 100
    debt_pct = (class_summary.get('Debt', 0) / len(df)) * 100
    other_pct = (class_summary.get('Other', 0) / len(df)) * 100
    print(f"\nEquity: {equity_pct:.1f}% | Debt: {debt_pct:.1f}% | Other: {other_pct:.1f}%")
    
    # Sanity check: Other should not be too high (unless many unclassifiable funds)
    if other_pct > 25:
        print(f"\n⚠️  WARNING: 'Other' category is high ({other_pct:.1f}%)")
    else:
        print(f"\n✓ Other category is reasonable ({other_pct:.1f}%)")
    print()
    
    print("=" * 80)
    print("CLASSIFICATION LEAK PATCH VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    test_classification_leaks()
