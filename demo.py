"""
Simple demo of the recommendation model
Shows how to use it with sample data
"""

from recommendation_model import RecommendationEngine, UserProfile


def print_recommendation(rec):
    """Pretty print a recommendation"""
    print(f"\n  #{rec['rank']} - {rec['scheme_name']}")
    print(f"      Scheme Code: {rec['scheme_code']}")
    print(f"      Fund House: {rec['fund_house']}")
    print(f"      Category: {rec['scheme_category']} | Plan: {rec['plan']}")
    print(f"      NAV: ₹{rec['nav']:.2f} | AUM: ₹{rec['aum_cr']:,.0f} Cr")
    print(f"      TER: {rec['estimated_ter']:.3f}% | 3Y CAGR: {rec['cagr_3y']}%")
    print(f"      Match Score: {rec['match_score']} (out of 1.0)")
    print(f"      Why recommended: {rec['reason']}")


def demo():
    """Run recommendation demos for different investor profiles"""
    
    print("\n" + "="*100)
    print("MUTUAL FUND RECOMMENDATION MODEL - LIVE DEMO")
    print("="*100)
    
    try:
        # Initialize engine
        print("\n📊 Loading recommendation engine (14,171 schemes)...")
        engine = RecommendationEngine("data/mf_full_dataset_final.csv")
        print("✅ Engine ready!\n")
    
    except FileNotFoundError:
        print("❌ Error: data/mf_full_dataset_final.csv not found")
        print("   Please run the full pipeline first:")
        print("   1. python mf_fetcher.py")
        print("   2. python build_full_mf_dataset.py")
        print("   3. python calculate_ter.py")
        print("   4. python feature_engineering.py")
        print("   5. python merge.py")
        return
    
    except Exception as e:
        print(f"❌ Error loading engine: {e}")
        return
    
    # ========== PROFILE 1: Young Aggressive Investor ==========
    print("\n" + "="*100)
    print("SCENARIO 1: Young Aggressive Investor")
    print("="*100)
    
    profile1 = UserProfile(
        user_id="aggressive_investor",
        age=28,
        annual_income="25L",
        monthly_sip=15000,
        risk_tolerance="High",
        investment_horizon="10+yr",
        investment_goals=["Wealth Growth", "Retirement"],
        experience="Beginner"
    )
    
    print(f"""
Profile:
  • Age: {profile1.age} years (young with high earning potential)
  • Income: {profile1.annual_income} (₹25 lakhs)
  • Monthly SIP: ₹{profile1.monthly_sip:,}
  • Risk Tolerance: {profile1.risk_tolerance} (can weather market volatility)
  • Investment Horizon: {profile1.investment_horizon} (10+ years)
  • Goals: {', '.join(profile1.investment_goals)}
  • Experience: {profile1.experience}

Recommended Strategy: Equity-heavy portfolio with focus on long-term capital appreciation
    """)
    
    try:
        recs1 = engine.recommend(profile1, top_n=5)
        print(f"\n✅ Top 5 recommendations for aggressive investor:\n")
        for rec in recs1:
            print_recommendation(rec)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # ========== PROFILE 2: Conservative Senior ==========
    print("\n\n" + "="*100)
    print("SCENARIO 2: Conservative Senior Investor")
    print("="*100)
    
    profile2 = UserProfile(
        user_id="conservative_investor",
        age=58,
        annual_income="50L+",
        monthly_sip=20000,
        risk_tolerance="Low",
        investment_horizon="3-5yr",
        investment_goals=["Emergency"],
        experience="Intermediate"
    )
    
    print(f"""
Profile:
  • Age: {profile2.age} years (approaching retirement)
  • Income: {profile2.annual_income} (high net worth)
  • Monthly SIP: ₹{profile2.monthly_sip:,}
  • Risk Tolerance: {profile2.risk_tolerance} (capital preservation priority)
  • Investment Horizon: {profile2.investment_horizon} (short-term)
  • Goals: {', '.join(profile2.investment_goals)}
  • Experience: {profile2.experience}

Recommended Strategy: Debt-heavy portfolio with focus on stability and liquidity
    """)
    
    try:
        recs2 = engine.recommend(profile2, top_n=5)
        print(f"\n✅ Top 5 recommendations for conservative investor:\n")
        for rec in recs2:
            print_recommendation(rec)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # ========== PROFILE 3: Balanced Middle-Aged ==========
    print("\n\n" + "="*100)
    print("SCENARIO 3: Balanced Middle-Aged Investor")
    print("="*100)
    
    profile3 = UserProfile(
        user_id="balanced_investor",
        age=42,
        annual_income="10L",
        monthly_sip=8000,
        risk_tolerance="Moderate",
        investment_horizon="10+yr",
        investment_goals=["Wealth Growth", "Child Edu", "Retirement"],
        experience="Intermediate"
    )
    
    print(f"""
Profile:
  • Age: {profile3.age} years (prime earning years)
  • Income: {profile3.annual_income} (₹10 lakhs)
  • Monthly SIP: ₹{profile3.monthly_sip:,}
  • Risk Tolerance: {profile3.risk_tolerance} (balanced approach)
  • Investment Horizon: {profile3.investment_horizon} (long-term)
  • Goals: {', '.join(profile3.investment_goals)}
  • Experience: {profile3.experience}

Recommended Strategy: 60% Equity / 40% Debt for stability with growth
    """)
    
    try:
        recs3 = engine.recommend(profile3, top_n=5)
        print(f"\n✅ Top 5 recommendations for balanced investor:\n")
        for rec in recs3:
            print_recommendation(rec)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # ========== PROFILE 4: Beginner with Small SIP ==========
    print("\n\n" + "="*100)
    print("SCENARIO 4: Beginner Investor with Small SIP")
    print("="*100)
    
    profile4 = UserProfile(
        user_id="beginner_investor",
        age=23,
        annual_income="5L",
        monthly_sip=1000,
        risk_tolerance="Moderate",
        investment_horizon="10+yr",
        investment_goals=["Wealth Growth"],
        experience="Beginner"
    )
    
    print(f"""
Profile:
  • Age: {profile4.age} years (just started earning)
  • Income: {profile4.annual_income} (₹5 lakhs)
  • Monthly SIP: ₹{profile4.monthly_sip:,} (modest amount)
  • Risk Tolerance: {profile4.risk_tolerance} (learning investor)
  • Investment Horizon: {profile4.investment_horizon} (very long-term)
  • Goals: {', '.join(profile4.investment_goals)}
  • Experience: {profile4.experience} (needs simplicity)

Recommended Strategy: Index/Large-Cap funds for simplicity and low cost
    """)
    
    try:
        recs4 = engine.recommend(profile4, top_n=5)
        print(f"\n✅ Top 5 recommendations for beginner investor:\n")
        for rec in recs4:
            print_recommendation(rec)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # ========== COMPARISON SUMMARY ==========
    print("\n\n" + "="*100)
    print("COMPARISON SUMMARY")
    print("="*100)
    
    print("""
The model recommends different schemes based on:

1. RISK TOLERANCE
   • Low → Debt schemes (Liquid, Bond, Gilt)
   • Moderate → Mix of Debt and Hybrid
   • High/Very High → Equity schemes (Large Cap, Mid Cap, Growth)

2. INVESTMENT HORIZON
   • Short (1-3yr) → Stable debt returns, Liquid funds
   • Long (10+yr) → Focus on high 3Y/5Y CAGR, Equity schemes

3. EXPERIENCE LEVEL
   • Beginner → Index funds, Large Cap, simple categories
   • Expert → Full fund universe, complex strategies

4. FINANCIAL CAPACITY
   • High income & large SIP → Better schemes (lower TER)
   • Low income & small SIP → Cost-efficient options

5. GOALS
   • Wealth Growth → Aggressive equity bias
   • Emergency → Liquid funds for quick access
   • Retirement/Education → Mix based on timeline

Key Features of Each Recommendation:
  ✓ Scheme Code: Unique identifier for transactions
  ✓ Match Score: 0-1 rating (higher = better fit)
  ✓ Reason: Human-readable explanation
  ✓ Returns: 1Y/3Y/5Y performance
  ✓ Expense Ratio: Impact on returns
  ✓ Fund House: AMC reputation & stability
  ✓ Plan Type: Direct (lower cost) vs Regular
""")
    
    # ========== API USAGE ==========
    print("\n" + "="*100)
    print("NEXT STEPS")
    print("="*100)
    
    print("""
To integrate this model:

1. START THE REST API:
   python api.py
   
   Then use via HTTP:
   curl -X POST http://localhost:5000/recommend \\
     -H "Content-Type: application/json" \\
     -d '{"user_id":"...", "age":28, ...}'

2. BATCH PROCESS MULTIPLE USERS:
   from recommendation_model import RecommendationEngine, UserProfile
   
   engine = RecommendationEngine("data/mf_full_dataset_final.csv")
   for user_data in users:
       profile = UserProfile(...)
       recs = engine.recommend(profile, top_n=10)

3. BUILD FRONTEND:
   • React/Vue form for user inputs
   • Call /recommend API endpoint
   • Display recommendations with explanations
   • Track user selections for feedback

4. ENHANCE MODEL:
   • Add user feedback loop
   • Track scheme performance vs recommendations
   • Retrain weights based on outcomes
   • A/B test different matching algorithms

Documentation:
  • QUICK_START.md - 5-minute reference
  • MODEL_USAGE.md - Complete API docs
  • RECOMMENDATION_MODEL_README.md - Full guide
  • IMPLEMENTATION_SUMMARY.md - Architecture details
""")
    
    print("\n" + "="*100)
    print("✅ DEMO COMPLETE")
    print("="*100 + "\n")


if __name__ == "__main__":
    demo()
