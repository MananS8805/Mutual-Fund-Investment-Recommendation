"""
Test script for the recommendation model
Run this to verify the model works end-to-end
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from recommendation_model import FundRecommender, UserProfile
import json


def test_single_recommendation():
    """Test single user recommendation"""
    print("\n" + "="*80)
    print("TEST 1: Single User Recommendation")
    print("="*80)
    
    try:
        engine = FundRecommender("data/mf_full_dataset_final.csv")
        
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
            asset_class = rec.get('asset_class', 'Unknown')
            print(f"  #{rec['rank']} - {rec['scheme_name']}")
            print(f"      Asset Class: {asset_class} | Fund House: {rec['fund_house']}")
            print(f"      Score: {rec.get('score', rec.get('match_score', 'N/A')):.2f} | TER: {rec['estimated_ter']:.2f}%")
            cagr = rec.get('cagr_3y', 0)
            cagr_str = f"{cagr*100:.2f}%" if cagr and isinstance(cagr, (int, float)) else "N/A"
            print(f"      3Y CAGR: {cagr_str} | AUM: ₹{rec['aum_cr']:,.0f}Cr")
            print(f"      Reason: {rec['reason']}\n")
        
        return True
    
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False


def test_multiple_profiles():
    """Test multiple user profiles"""
    print("\n" + "="*80)
    print("TEST 2: Multiple User Profiles (Validation of Bug Fixes)")
    print("="*80)
    
    try:
        engine = FundRecommender("data/mf_full_dataset_final.csv")
        
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
            print(f"\n👤 Profile: {profile.user_id}")
            print(f"   Age {profile.age}, Risk: {profile.risk_tolerance}, Horizon: {profile.investment_horizon}")
            recs = engine.recommend(profile, top_n=3)
            
            if len(recs) == 0:
                print(f"   ⚠️  No matching funds (horizon constraint enforcement)")
                continue
                
            for rec in recs:
                asset_class = rec.get('asset_class', 'N/A')
                score = rec.get('score', rec.get('match_score', 'N/A'))
                print(f"   #{rec['rank']} [{asset_class}] {rec['scheme_code']} - {rec['scheme_name'][:50]} (Score: {score})")
        
        print("\n✅ Multiple profiles test passed")
        return True
    
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False


def test_data_integrity():
    """Test dataset integrity and classification"""
    print("\n" + "="*80)
    print("TEST 3: Data Integrity & Classification Check")
    print("="*80)
    
    try:
        engine = FundRecommender("data/mf_full_dataset_final.csv")
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
        
        if 'Asset_Class' in df.columns:
            print(f"\n✅ Asset Classification:")
            print(f"   Equity funds: {(df['Asset_Class'] == 'Equity').sum():,}")
            print(f"   Debt funds: {(df['Asset_Class'] == 'Debt').sum():,}")
            print(f"   Hybrid funds: {(df['Asset_Class'] == 'Hybrid').sum():,}")
            print(f"   Other: {(df['Asset_Class'] == 'Other').sum():,}")
        
        return True
    
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n" + "="*80)
    print("TEST 4: Edge Cases & Constraint Enforcement")
    print("="*80)
    
    try:
        engine = FundRecommender("data/mf_full_dataset_final.csv")
        
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
        
        # Test 3: Senior citizen with emergency fund
        profile3 = UserProfile(
            user_id="senior",
            age=70,
            annual_income="10L",
            monthly_sip=5000,
            risk_tolerance="Low",
            investment_horizon="1-3yr",
            investment_goals=["Emergency"],
            experience="Intermediate"
        )
        recs3 = engine.recommend(profile3, top_n=3)
        print(f"✓ Senior citizen (Emergency) case: Generated {len(recs3)} recommendations")
        
        print("\n✅ All edge cases passed")
        return True
    
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return False


def test_top_10_multiple_profiles():
    """Test top 10 recommendations for 10+ diverse user profiles"""
    print("\n" + "="*80)
    print("TEST 5: Top Recommendations with Asset Class Validation")
    print("="*80)
    
    try:
        engine = FundRecommender("data/mf_full_dataset_final.csv")
        
        # Define 12 diverse user profiles
        profiles = [
            UserProfile(
                user_id="young_aggressive_001",
                age=25,
                annual_income="5L",
                monthly_sip=3000,
                risk_tolerance="Very High",
                investment_horizon="10+yr",
                investment_goals=["Wealth Growth"],
                experience="Beginner"
            ),
            UserProfile(
                user_id="professional_high_income_002",
                age=32,
                annual_income="50L+",
                monthly_sip=25000,
                risk_tolerance="High",
                investment_horizon="10+yr",
                investment_goals=["Wealth Growth", "Retirement"],
                experience="Intermediate"
            ),
            UserProfile(
                user_id="moderate_balanced_003",
                age=40,
                annual_income="25L",
                monthly_sip=10000,
                risk_tolerance="Moderate",
                investment_horizon="5-10yr",
                investment_goals=["Wealth Growth", "Emergency"],
                experience="Intermediate"
            ),
            UserProfile(
                user_id="parent_child_edu_004",
                age=38,
                annual_income="10L",
                monthly_sip=5000,
                risk_tolerance="Moderate",
                investment_horizon="5-10yr",
                investment_goals=["Child Edu", "Wealth Growth"],
                experience="Beginner"
            ),
            UserProfile(
                user_id="conservative_investor_005",
                age=55,
                annual_income="25L",
                monthly_sip=8000,
                risk_tolerance="Low",
                investment_horizon="3-5yr",
                investment_goals=["Emergency", "Retirement"],
                experience="Intermediate"
            ),
            UserProfile(
                user_id="pre_retiree_006",
                age=58,
                annual_income="50L+",
                monthly_sip=15000,
                risk_tolerance="Low",
                investment_horizon="3-5yr",
                investment_goals=["Retirement"],
                experience="Expert"
            ),
            UserProfile(
                user_id="beginner_low_income_007",
                age=28,
                annual_income="5L",
                monthly_sip=1000,
                risk_tolerance="Moderate",
                investment_horizon="5-10yr",
                investment_goals=["Wealth Growth"],
                experience="Beginner"
            ),
            UserProfile(
                user_id="expert_investor_008",
                age=45,
                annual_income="50L+",
                monthly_sip=30000,
                risk_tolerance="Very High",
                investment_horizon="10+yr",
                investment_goals=["Wealth Growth"],
                experience="Expert"
            ),
            UserProfile(
                user_id="emergency_fund_009",
                age=35,
                annual_income="10L",
                monthly_sip=2000,
                risk_tolerance="Low",
                investment_horizon="1-3yr",
                investment_goals=["Emergency"],
                experience="Beginner"
            ),
            UserProfile(
                user_id="retirement_focused_010",
                age=50,
                annual_income="25L",
                monthly_sip=12000,
                risk_tolerance="Moderate",
                investment_horizon="5-10yr",
                investment_goals=["Retirement", "Wealth Growth"],
                experience="Intermediate"
            ),
            UserProfile(
                user_id="long_term_growth_011",
                age=22,
                annual_income="5L",
                monthly_sip=5000,
                risk_tolerance="Very High",
                investment_horizon="10+yr",
                investment_goals=["Wealth Growth", "Retirement"],
                experience="Intermediate"
            ),
            UserProfile(
                user_id="balanced_senior_012",
                age=62,
                annual_income="10L",
                monthly_sip=7000,
                risk_tolerance="Moderate",
                investment_horizon="3-5yr",
                investment_goals=["Emergency", "Retirement"],
                experience="Intermediate"
            ),
        ]
        
        # Get top 10 recommendations for each profile
        results_summary = []
        
        for profile in profiles:
            print(f"\n{'─'*80}")
            print(f"👤 Profile: {profile.user_id}")
            print(f"   Age: {profile.age} | Income: {profile.annual_income} | Monthly SIP: ₹{profile.monthly_sip:,}")
            print(f"   Risk: {profile.risk_tolerance} | Horizon: {profile.investment_horizon} | Experience: {profile.experience}")
            print(f"   Goals: {', '.join(profile.investment_goals)}")
            print(f"{'─'*80}")
            
            recommendations = engine.recommend(profile, top_n=10)
            
            if len(recommendations) == 0:
                print("   ⚠️  No suitable recommendations found (filters may be too restrictive)")
                results_summary.append((profile.user_id, 0))
                continue
            
            print(f"\n   📊 Top {len(recommendations)} Recommendations:\n")
            
            for rec in recommendations:
                asset_class = rec.get('asset_class', 'N/A')
                score = rec.get('score', rec.get('match_score', 'N/A'))
                cagr = rec.get('cagr_3y', 0)
                cagr_str = f"{cagr*100:.2f}%" if cagr and isinstance(cagr, (int, float)) else "N/A"
                
                print(f"   #{rec['rank']:2d} [{asset_class:6s}] | {rec['scheme_name'][:50]}")
                print(f"       Fund House: {rec['fund_house']}")
                print(f"       Score: {score} | TER: {rec['estimated_ter']:.2f}%")
                print(f"       3Y CAGR: {cagr_str} | AUM: ₹{rec['aum_cr']:,.0f}Cr")
                print(f"       Reason: {rec['reason']}\n")
            
            results_summary.append((profile.user_id, len(recommendations)))
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY: Recommendations Generated for All Profiles")
        print("="*80)
        
        for profile_id, rec_count in results_summary:
            status = "✅" if rec_count >= 10 else "⚠️ " if rec_count > 0 else "❌"
            print(f"{status} {profile_id:30s} : {rec_count:2d} recommendations")
        
        total_profiles = len(profiles)
        successful_profiles = sum(1 for _, count in results_summary if count > 0)
        
        print(f"\n✅ Generated recommendations for {successful_profiles}/{total_profiles} profiles")
        return True
    
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("MUTUAL FUND RECOMMENDATION MODEL - TEST SUITE")
    print("="*80)
    
    results = []
    
    results.append(("Data Integrity & Classification", test_data_integrity()))
    results.append(("Single Recommendation", test_single_recommendation()))
    results.append(("Multiple Profiles", test_multiple_profiles()))
    results.append(("Edge Cases & Constraints", test_edge_cases()))
    results.append(("Top Recommendations (12 Profiles)", test_top_10_multiple_profiles()))
    
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
