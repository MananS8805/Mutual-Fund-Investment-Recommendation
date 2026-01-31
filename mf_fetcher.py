import pandas as pd
import requests
import time
import json
import os
from tqdm import tqdm
from typing import Dict
import numpy as np
from pathlib import Path

def fetch_mf_attributes(scheme_code: int, scheme_name: str) -> Dict:
    """Fetch MF data for single scheme"""
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        nav_data = data.get('data', [])
        latest_nav = nav_data[0] if nav_data else {}
        meta = data.get('meta', {})
        scheme_category = meta.get('scheme_category', '')
        
        return {
            'scheme_code': scheme_code,
            'scheme_name': scheme_name,
            'nav': float(latest_nav.get('nav', 0)) if latest_nav.get('nav') else 0,
            'nav_date': latest_nav.get('date', ''),
            'fund_house': meta.get('fund_house', ''),
            'scheme_category': scheme_category,
            'scheme_type': meta.get('scheme_type', ''),
            'isin_growth': meta.get('isin_growth', ''),
            'isin_div_reinvestment': meta.get('isin_div_reinvestment', ''),
            'plan': 'Direct' if 'direct' in scheme_name.lower() else 'Regular',
            'risk_category': 'Debt' if 'debt' in scheme_name.lower() else 
                           'Equity' if any(x in scheme_name.lower() for x in ['equity', 'large cap', 'mid cap', 'small cap']) 
                           else 'Hybrid',
            'status': 'success'
        }
    except Exception as e:
        return {
            'scheme_code': scheme_code,
            'scheme_name': scheme_name,
            'error': str(e),
            'status': 'failed'
        }

def process_all_schemes(data_folder: str = "data", output_file: str = "mf_complete_dataset.csv", 
                       batch_size: int = 1000, resume: bool = True):
    """
    Process ALL 14K schemes with resume capability, progress saving
    """
    input_file = os.path.join(data_folder, "list1.csv")
    checkpoint_file = "checkpoint_progress.json"
    
    # Load schemes
    print("🔄 Loading 14K schemes from data/latestNAV_Reports-1.csv...")
    df = pd.read_csv(input_file)
    df = df[['Scheme Code', 'Scheme NAV Name']].dropna()
    df['Scheme Code'] = df['Scheme Code'].astype(int)
    
    print(f"📊 Total schemes to process: {len(df):,}")
    
    # Resume from checkpoint
    start_idx = 0
    if resume and os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
            start_idx = checkpoint.get('last_processed', 0)
        print(f"📍 Resuming from scheme #{start_idx:,}")
    
    results = []
    successful = failed = 0
    
    for idx in tqdm(range(start_idx, len(df)), desc="Processing schemes"):
        row = df.iloc[idx]
        attrs = fetch_mf_attributes(int(row['Scheme Code']), row['Scheme NAV Name'])
        results.append(attrs)
        
        # Update counters
        if attrs['status'] == 'success':
            successful += 1
        else:
            failed += 1
        
        # Save checkpoint every 100 schemes
        if (idx + 1) % 100 == 0:
            pd.DataFrame(results).to_csv(output_file, index=False)
            with open(checkpoint_file, 'w') as f:
                json.dump({'last_processed': idx + 1, 'successful': successful, 'failed': failed}, f)
            print(f"\n⏳ Progress: {idx+1:,}/{len(df):,} | ✅{successful:,} | ❌{failed:,}")
        
        time.sleep(0.3)  # Respect API rate limits
    
    # Final save
    pd.DataFrame(results).to_csv(output_file, index=False)
    os.remove(checkpoint_file)  # Cleanup
    
    print(f"\n🎉 COMPLETE!")
    print(f"✅ Successful: {successful:,}")
    print(f"❌ Failed: {failed:,}")
    print(f"📁 Output: {output_file}")
    
    return pd.DataFrame(results)

# MAIN EXECUTION
if __name__ == "__main__":
    # Quick test first
    #print("🧪 Quick test with scheme 119551...")
    #test = fetch_mf_attributes(119551, "Aditya Birla Test")
    #print("✅ Test passed:", test['status'])
    
    print("\n🚀 Starting FULL 14K scheme processing...")
    print("⏱️  Estimated time: ~2 hours (with rate limiting)")
    print("💾 Progress auto-saves every 100 schemes")
    
    df_complete = process_all_schemes(
        data_folder="data",
        output_file="mf_complete_dataset.csv"
    )
