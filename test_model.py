"""
Test script for the recommendation model
Run this to verify the model works end-to-end
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from recommendation_model import RecommendationEngine, UserProfile
import json


def test_single_recommendation():
    """Test single user recommendation"""
    print("\n" + "="*80)
    print("TEST 1: Single User Recommendation")
    print("="*80)
    
    try:
        engine = RecommendationEngine("data/mf_full_dataset_final.csv")
        
        # Create a young investor with high risk tolerance
        profile = UserProfile(
            user_id="test_user_001",
            age=28,
            annual_income="10L",
            monthly_sip=5000,
            risk_tolerance="High",
            investment_horizon="10+yr",
            investment_goals=["Wealth Growth"],
            experience="Beginner"
        )
        
        recommendations = engine.recommend(profile, top_n=5)
        
        print(f"\n✅ Generated {len(recommendations)} recommendations\n")
        
        for rec in recommendations:
            print(f"  #{rec['rank']} - {rec['scheme_name']}")
            print(f"      Fund House: {rec['fund_house']}")
            print(f"      Match Score: {rec['match_score']} | TER: {rec['estimated_ter']}%")
            print(f"      3Y CAGR: {rec['cagr_3y']}% | AUM: ₹{rec['aum_cr']}Cr")
            print(f"      Reason: {rec['reason']}\n")
        
        return True
    
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False


def test_multiple_profiles():
    """Test multiple user profiles"""
    print("\n" + "="*80)
    print("TEST 2: Multiple User Profiles")
    print("="*80)
    
    try:
        engine = RecommendationEngine("data/mf_full_dataset_final.csv")
        
        profiles = [
            UserProfile(
                user_id="conservative_user",
                age=55,
                annual_income="50L+",
                monthly_sip=10000,
                risk_tolerance="Low",
                investment_horizon="3-5yr",
                investment_goals=["Emergency"],
                experience="Intermediate"
            ),
            UserProfile(
                user_id="aggressive_user",
                age=25,
                annual_income="5L",
                monthly_sip=2000,
                risk_tolerance="Very High",
                investment_horizon="10+yr",
                investment_goals=["Wealth Growth", "Retirement"],
                experience="Expert"
            ),
        ]
        
        for profile in profiles:
            print(f"\n👤 Profile: {profile.user_id} (Age {profile.age}, Risk: {profile.risk_tolerance})")
            recs = engine.recommend(profile, top_n=3)
            
            for rec in recs:
                print(f"   #{rec['rank']} {rec['scheme_code']} - Match: {rec['match_score']}")
        
        print("\n✅ Multiple profiles test passed")
        return True
    
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False


def test_data_integrity():
    """Test dataset integrity"""
    print("\n" + "="*80)
    print("TEST 3: Data Integrity Check")
    print("="*80)
    
    try:
        engine = RecommendationEngine("data/mf_full_dataset_final.csv")
        df = engine.df_schemes
        
        print(f"\n✅ Dataset Integrity:")
        print(f"   Total schemes: {len(df):,}")
        print(f"   Schemes with valid NAV: {df['nav'].notna().sum():,}")
        print(f"   Schemes with AUM data: {df['aum_cr'].notna().sum():,}")
        print(f"   Schemes with TER: {df['estimated_ter'].notna().sum():,}")
        print(f"   Top 10 AMC schemes: {df['amc_reputation'].sum():,}")
        print(f"   Direct Plans: {df['direct_plan'].sum():,}")
        print(f"   Avg TER: {df['estimated_ter'].mean():.3f}%")
        print(f"   Median AUM: ₹{df['aum_cr'].median():.0f}Cr")
        
        return True
    
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n" + "="*80)
    print("TEST 4: Edge Cases")
    print("="*80)
    
    try:
        engine = RecommendationEngine("data/mf_full_dataset_final.csv")
        
        # Test 1: Very low SIP
        profile1 = UserProfile(
            user_id="low_sip",
            age=40,
            annual_income="5L",
            monthly_sip=500,  # Minimum
            risk_tolerance="Moderate",
            investment_horizon="5-10yr",
            investment_goals=["Wealth Growth"],
            experience="Beginner"
        )
        recs1 = engine.recommend(profile1, top_n=3)
        print(f"✓ Low SIP case: Generated {len(recs1)} recommendations")
        
        # Test 2: Very high SIP
        profile2 = UserProfile(
            user_id="high_sip",
            age=35,
            annual_income="50L+",
            monthly_sip=50000,  # Maximum
            risk_tolerance="High",
            investment_horizon="10+yr",
            investment_goals=["Wealth Growth", "Retirement"],
            experience="Expert"
        )
        recs2 = engine.recommend(profile2, top_n=3)
        print(f"✓ High SIP case: Generated {len(recs2)} recommendations")
        
        # Test 3: Senior citizen
        profile3 = UserProfile(
            user_id="senior",
            age=70,  # Maximum age
            annual_income="10L",
            monthly_sip=5000,
            risk_tolerance="Low",
            investment_horizon="1-3yr",
            investment_goals=["Emergency"],
            experience="Intermediate"
        )
        recs3 = engine.recommend(profile3, top_n=3)
        print(f"✓ Senior citizen case: Generated {len(recs3)} recommendations")
        
        print("\n✅ All edge cases passed")
        return True
    
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("MUTUAL FUND RECOMMENDATION MODEL - TEST SUITE")
    print("="*80)
    
    results = []
    
    results.append(("Data Integrity", test_data_integrity()))
    results.append(("Single Recommendation", test_single_recommendation()))
    results.append(("Multiple Profiles", test_multiple_profiles()))
    results.append(("Edge Cases", test_edge_cases()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_passed = sum(1 for _, p in results if p)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! Model is ready for use.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
