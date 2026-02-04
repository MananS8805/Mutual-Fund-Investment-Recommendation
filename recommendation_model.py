"""
Mutual Fund Recommendation Engine
Matches investor profiles to optimal schemes using vector-based similarity and
separate ranking of Equity/Debt buckets to prevent recommendation bias.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class UserProfile:
    """Represents investor's profile and preferences"""
    user_id: str
    age: int
    annual_income: str  # '5L', '10L', '25L', '50L+'
    monthly_sip: int
    risk_tolerance: str  # 'Low', 'Moderate', 'High', 'Very High'
    investment_horizon: str  # '1-3yr', '3-5yr', '5-10yr', '10+yr'
    investment_goals: List[str]  # ['Retirement', 'Child Edu', 'Wealth Growth', 'Emergency']
    experience: str  # 'Beginner', 'Intermediate', 'Expert'


class FundRecommender:
    """
    Fixed Mutual Fund Recommender with separate Equity/Debt ranking.
    
    Implements three-stage pipeline:
    1. CLASSIFICATION: Bucket schemes into Asset Classes
    2. FILTERING: Apply hard horizon/goal/experience constraints
    3. RANKING: Score and rank WITHIN each asset class separately
    """
    
    def __init__(self, dataset_path: str = "data/mf_full_dataset_final.csv"):
        """
        Initialize with mutual fund dataset and classify funds.
        
        Args:
            dataset_path: Path to the final MF dataset
        """
        self.df_schemes = pd.read_csv(dataset_path)
        self._validate_dataset()
        self._classify_funds()  # Must run after validation
        
    def _validate_dataset(self):
        """Ensure required columns exist and add missing features"""
        required_cols = [
            'scheme_code', 'scheme_name', 'fund_house', 'scheme_category',
            'plan', 'cagr_3y'
        ]
        missing = [col for col in required_cols if col not in self.df_schemes.columns]
        if missing:
            raise ValueError(f"Dataset missing columns: {missing}")
        
        # Map/create missing columns based on available data
        if 'nav' not in self.df_schemes.columns and 'latest_nav' in self.df_schemes.columns:
            self.df_schemes['nav'] = self.df_schemes['latest_nav']
        
        if 'estimated_ter' not in self.df_schemes.columns and 'expense_ratio' in self.df_schemes.columns:
            self.df_schemes['estimated_ter'] = self.df_schemes['expense_ratio']
        
        if 'aum_cr' not in self.df_schemes.columns:
            self.df_schemes['aum_cr'] = 100.0  # Default to 100Cr if missing
        
        # Create binary features if missing
        if 'amc_reputation' not in self.df_schemes.columns:
            top_10_amcs = ['SBI', 'ICICI Prudential', 'HDFC', 'Nippon India', 
                          'Kotak Mahindra', 'Aditya Birla Sun Life', 'UTI', 
                          'Axis', 'Mirae Asset', 'DSP']
            self.df_schemes['amc_reputation'] = self.df_schemes['fund_house'].str.contains(
                '|'.join(top_10_amcs), case=False, na=False
            ).astype(int)
        
        if 'debt_score' not in self.df_schemes.columns:
            self.df_schemes['debt_score'] = self.df_schemes['scheme_category'].str.contains(
                'Debt|Corporate|Liquid|Banking|PSU|Gilt', case=False, na=False
            ).astype(int)
        
        if 'equity_score' not in self.df_schemes.columns:
            self.df_schemes['equity_score'] = self.df_schemes['scheme_category'].str.contains(
                'Equity|Large|Mid|Small|Flexi|Multi', case=False, na=False
            ).astype(int)
        
        if 'hybrid_score' not in self.df_schemes.columns:
            self.df_schemes['hybrid_score'] = self.df_schemes['scheme_category'].str.contains(
                'Hybrid|Balanced|Arbitrage|Conservative', case=False, na=False
            ).astype(int)
        
        if 'direct_plan' not in self.df_schemes.columns:
            self.df_schemes['direct_plan'] = (self.df_schemes['plan'] == 'Direct').astype(int)
        
        if 'category_quality' not in self.df_schemes.columns:
            self.df_schemes['category_quality'] = self.df_schemes['scheme_category'].str.contains(
                'Large Cap|Flexi Cap|Corporate Bond|Banking', case=False, na=False
            ).astype(int)
        
        # Ensure nav and ter exist
        if 'nav' not in self.df_schemes.columns:
            self.df_schemes['nav'] = 100.0  # Default NAV
        
        if 'estimated_ter' not in self.df_schemes.columns:
            self.df_schemes['estimated_ter'] = 1.0  # Default TER
        
        # Remove rows with missing critical features
        self.df_schemes = self.df_schemes.dropna(subset=['scheme_code', 'scheme_name', 'cagr_3y'], how='any')
        
        # Fill NaN in numeric columns with defaults
        self.df_schemes['cagr_3y'] = self.df_schemes['cagr_3y'].fillna(0.0)
        self.df_schemes['cagr_5y'] = self.df_schemes['cagr_5y'].fillna(0.0)
        self.df_schemes['aum_cr'] = self.df_schemes['aum_cr'].fillna(100.0)
        self.df_schemes['estimated_ter'] = self.df_schemes['estimated_ter'].fillna(1.0)
        self.df_schemes['nav'] = self.df_schemes['nav'].fillna(100.0)
        
        print(f"[OK] Loaded {len(self.df_schemes):,} schemes with complete features")

    def _classify_funds(self):
        """
        STAGE 1: CLASSIFICATION
        Bucket schemes into Asset Classes and Risk Grades per strict SEBI categories.
        
        FIX FOR "DEBT DISGUISED AS EQUITY" BUG:
        - PRIORITY 1: Check DEBT keywords FIRST (must catch "Bond Index", "SDL", "Target Maturity")
        - PRIORITY 2: Check HYBRID keywords
        - PRIORITY 3: Check EQUITY keywords (Index is only safe to check here)
        - Default: Other
        
        Asset_Class mapping:
          - Debt: Liquid, Overnight, Corporate Bond, Ultra Short, Gilt, Bond Index, SDL, Target Maturity,
                  Money Market, Floater, Credit Risk, Banking, PSU
          - Hybrid: Arbitrage, Dynamic Bond, Aggressive Hybrid
          - Equity: Large Cap, Mid Cap, Small Cap, Flexi Cap, Sectoral, Index (only if NOT Debt)
        
        Risk_Grade (1-5): Used for filtering constraints
          1 = Lowest (Liquid, Overnight)
          2 = Low (Ultra Short, Money Market)
          3 = Medium (Large Cap, Flexi, Hybrid, Dynamic)
          4 = High (Mid Cap, Small Cap)
          5 = Highest (Sectoral, Thematic)
        """
        df = self.df_schemes.copy()

        def _classify_row(row) -> str:
            """
            Classify fund into Asset_Class using name + category (strict priority order).
            Returns: 'Equity', 'Debt', 'Hybrid', or 'Other'
            
            Priority order:
            1. EXCLUSIONS: Commodities and other non-financial assets
            2. DEBT: Bond funds, govt securities, money market
            3. HYBRID: Balanced, arbitrage funds
            4. EQUITY: Stock-based funds
            5. DEFAULT: Other
            """
            name = str(row.get('scheme_name', '')).lower()
            category = str(row.get('scheme_category', '')).lower()
            combined = f"{name} {category}"
            
            # STEP 0: EXCLUSIONS (Non-financial assets)
            # FIX: Filter out commodities that masquerade as equity
            exclusion_keywords = ['gold', 'silver', 'commodity', 'real estate', 'reits']
            if any(k in combined for k in exclusion_keywords):
                return 'Other'
            
            # STEP A: DEBT KEYWORDS FIRST (check NAME for critical indicators, then combined)
            # FIX: Add 'bharat bond' to catch Debt FoF; check name first for specificity
            if any(k in name for k in ['bond', 'sdl', 'g-sec', 'g-security', 'bharat bond']):
                return 'Debt'
            
            # Comprehensive debt keyword list (category-based fallback)
            debt_keywords = [
                'liquid', 'overnight', 'corporate bond', 'ultra short', 'gilt',
                'bond index',  # FIX: Catch "Edelweiss NIFTY PSU Bond Plus SDL Index"
                'bond plus',   # Handles "PSU Bond Plus" patterns
                'sdl',         # Sovereign Development Loan
                'target maturity',
                'money market',
                'floater',
                'credit risk',
                'banking',
                'psu bond',    # PSU-specific bonds
                'short duration',  # Short duration funds are debt
                'bharat bond',  # FIX: FOF based on Bharat Bond bonds
                'fof',         # Fund of Funds (often debt-based)
            ]
            if any(k in combined for k in debt_keywords):
                return 'Debt'
            
            # STEP B: HYBRID KEYWORDS
            hybrid_keywords = ['arbitrage', 'dynamic bond', 'hybrid', 'balanced']
            if any(k in combined for k in hybrid_keywords):
                return 'Hybrid'
            
            # STEP C: EQUITY KEYWORDS (NOW safe to check 'Index')
            equity_keywords = [
                'large cap', 'mid cap', 'small cap', 'flexi', 'flexi cap',
                'sectoral', 'thematic', 'index',
                'growth', 'dividend',
                'multi-cap', 'multicap'
            ]
            if any(k in combined for k in equity_keywords):
                return 'Equity'
            
            # STEP D: DEFAULT
            return 'Other'

        def _risk_grade(category: str) -> int:
            """Assign risk grade 1-5 for filtering."""
            if pd.isna(category):
                return 3
            c = str(category).lower()
            
            if any(k in c for k in ['liquid', 'overnight']):
                return 1  # Safest
            if any(k in c for k in ['ultra short', 'short duration', 'money market']):
                return 2  # Low risk
            if any(k in c for k in ['large cap', 'flexi', 'hybrid', 'dynamic', 'bond']):
                return 3  # Medium
            if any(k in c for k in ['mid cap', 'small cap']):
                return 4  # Higher
            if any(k in c for k in ['sectoral', 'thematic']):
                return 5  # Highest
            return 3

        # Apply classification using both scheme_name and scheme_category
        self.df_schemes['Asset_Class'] = df.apply(_classify_row, axis=1)
        self.df_schemes['Risk_Grade'] = df['scheme_category'].astype(str).apply(_risk_grade)
        
        # Ensure min_sip exists
        if 'min_sip' not in self.df_schemes.columns:
            self.df_schemes['min_sip'] = 0.0
        
        print(f"[OK] Classification complete: {len(self.df_schemes)} schemes mapped")
    
    def vectorize_user(self, profile: UserProfile) -> Dict[str, float]:
        """
        Convert user profile to numerical feature vector
        
        Returns:
            Dictionary with normalized feature scores [0,1]
        """
        # 1. Age Normalization (18-70)
        age_norm = profile.age / 70.0
        
        # 2. Income Score (SIP purchasing power)
        income_map = {'5L': 1, '10L': 2, '25L': 3, '50L+': 4}
        income_score = income_map.get(profile.annual_income, 2) / 4.0
        
        # 3. SIP Normalization (500-50K)
        sip_norm = min(profile.monthly_sip / 50000.0, 1.0)
        
        # 4. Risk Score (Low=1, Moderate=2.5, High=4, Very High=5)
        risk_map = {'Low': 1, 'Moderate': 2.5, 'High': 4, 'Very High': 5}
        risk_score = risk_map.get(profile.risk_tolerance, 2.5) / 5.0
        
        # 5. Investment Horizon (1-3yr=1, 3-5yr=2, 5-10yr=3, 10+yr=4)
        horizon_map = {'1-3yr': 1, '3-5yr': 2, '5-10yr': 3, '10+yr': 4}
        horizon_norm = horizon_map.get(profile.investment_horizon, 2) / 4.0
        
        # 6. Experience Score (Beginner=1, Intermediate=2, Expert=3)
        exp_map = {'Beginner': 1, 'Intermediate': 2, 'Expert': 3}
        exp_score = exp_map.get(profile.experience, 2) / 3.0
        
        # 7. Goal Vector (binary indicators for each goal)
        goal_weights = {
            'Retirement': 1.0,      # Equity-heavy + Debt for stability
            'Child Edu': 0.8,       # Long-term growth + stability
            'Wealth Growth': 1.0,   # Equity-heavy
            'Emergency': 0.0        # Liquid funds only
        }
        goal_score = sum(goal_weights.get(g, 0) for g in profile.investment_goals) / len(profile.investment_goals) if profile.investment_goals else 0.5
        goal_score = min(goal_score / 1.0, 1.0)  # Normalize to [0,1]
        
        return {
            'age_norm': age_norm,
            'income_score': income_score,
            'sip_norm': sip_norm,
            'risk_score': risk_score,
            'horizon_norm': horizon_norm,
            'exp_score': exp_score,
            'goal_score': goal_score
        }

    def _compute_allocation(self, profile: UserProfile) -> Dict[str, float]:
        """
        ALLOCATION STRATEGY
        Calculate target Equity % based on age, risk tolerance, and horizon.
        
        Formula:
          Base: Target_Equity_Pct = 110 - Age
          Adjust for Risk: +10% if High/VeryHigh, -20% if Low
          Override for Horizon: 0% if horizon < 3yr
        """
        # Base formula: 110 - Age (range: 40-110% for ages 0-70)
        target_equity_pct = 110 - profile.age
        
        # Risk adjustments
        risk_tol = str(profile.risk_tolerance).lower()
        if 'high' in risk_tol or 'very high' in risk_tol:
            target_equity_pct += 10.0
        elif 'low' in risk_tol:
            target_equity_pct -= 20.0
        
        # Horizon override: short horizons must have 0% equity
        horizon = str(profile.investment_horizon).lower()
        if any(x in horizon for x in ['<1', 'less', '1yr', '1-3', '3yr-5yr']):
            # For Emergency/1-3yr, force 0% equity
            if 'emergency' in [g.lower() for g in profile.investment_goals]:
                target_equity_pct = 0.0
            elif any(x in horizon for x in ['<1', 'less', '1yr', '1-3']):
                target_equity_pct = 0.0
        
        # Clamp to [0, 100]
        target_equity_pct = max(0.0, min(100.0, target_equity_pct))
        
        return {
            'equity_pct': target_equity_pct / 100.0,
            'debt_pct': (100.0 - target_equity_pct) / 100.0
        }

    def _hard_filter(self, profile: UserProfile) -> pd.DataFrame:
        """
        STAGE 2: FILTERING (Gatekeeper Layer)
        Apply strict constraints based on horizon, goals, and experience.
        
        Returns only schemes that are SAFE for the investor's profile.
        """
        df = self.df_schemes.copy()
        cat_lower = df['scheme_category'].fillna('').str.lower()
        
        # --- HORIZON CONSTRAINTS (Strict) ---
        horizon = str(profile.investment_horizon).lower()
        
        if 'emergency' in profile.investment_goals:
            # Rule: Emergency goals → ONLY Liquid/Overnight
            df = df[(df['Asset_Class'] == 'Debt') & (df['Risk_Grade'] == 1)]
            print(f"🚨 Emergency goal detected: Filtered to {len(df)} Liquid/Overnight funds")
        
        elif any(x in horizon for x in ['<1', 'less', '1yr', '1-3']):
            # Rule: 1-3yr horizon → ONLY Debt and Arbitrage. NO Equity.
            df = df[
                (df['Asset_Class'] == 'Debt') |
                ((df['Asset_Class'] == 'Hybrid') & cat_lower.str.contains('arbitrage', na=False))
            ]
            print(f"[FILTER] 1-3yr horizon: Filtered to {len(df)} Debt/Arbitrage funds")
        
        elif any(x in horizon for x in ['3-5', '3yr-5yr']):
            # Rule: 3-5yr horizon → Debt + Hybrid + Large/Flexi Cap. NO Mid/Small/Sectoral.
            mask_debt = df['Asset_Class'] == 'Debt'
            mask_hybrid = df['Asset_Class'] == 'Hybrid'
            mask_large_flexi = (df['Asset_Class'] == 'Equity') & cat_lower.str.contains('large|flexi', na=False)
            
            df = df[mask_debt | mask_hybrid | mask_large_flexi]
            print(f"📊 3-5yr horizon: Filtered to {len(df)} funds (Debt/Hybrid/Large Cap)")
        
        else:
            # 5-10yr or 10+yr → Allow all categories
            print(f"[HORIZON] Long horizon ({horizon}): All categories allowed")
        
        # --- EXPERIENCE CONSTRAINTS ---
        if str(profile.experience).lower() == 'beginner':
            # Rule: Beginners → Remove Sectoral, Thematic, Small Cap
            df = df[~cat_lower.str.contains('sectoral|thematic|small cap|small', na=False)]
            print(f"[EXPERIENCE] Beginner investor: Filtered to {len(df)} funds (removed Sectoral/Small Cap)")
        
        # --- VIABILITY CONSTRAINTS ---
        # Minimum AUM: 100 Cr
        aum_before = len(df)
        df = df[df['aum_cr'] >= 100.0]
        print(f"[AUM] AUM >= 100Cr: {aum_before:,} -> {len(df):,} funds")
        
        # Minimum SIP viability
        if 'min_sip' in df.columns and profile.monthly_sip is not None:
            df = df[df['min_sip'] <= profile.monthly_sip]
        
        return df.copy()

    def _score_funds_within_class(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        STAGE 3: RANKING (Within Asset Class)
        Score funds SEPARATELY within their Asset_Class (Equity vs Debt).
        This prevents lower-cost Debt funds from outranking higher-risk Equity funds.
        
        Scoring Formula (for each asset class):
          Score = (0.4 × Sharpe) + (0.4 × (1/TER)) + (0.2 × Log(AUM))
        
        Uses Z-Score normalization within each asset class ONLY.
        """
        df = df.copy()
        
        # Define scoring components
        # 1. Sharpe Ratio (if available, else approximate from 3Y CAGR)
        if 'sharpe_1y_annualized' in df.columns:
            sharpe = df['sharpe_1y_annualized'].fillna(0.0)
        else:
            # Fallback: scale 3Y CAGR to sharpe-like range (divide by volatility proxy)
            sharpe = df['cagr_3y'].fillna(0.0) / 0.15  # Assume 15% volatility
        
        # 2. Cost (Inverse TER - lower TER = higher score)
        ter = df['estimated_ter'].fillna(df['estimated_ter'].median())
        inv_ter = 1.0 / (ter + 1e-9)
        
        # 3. Trust (Log of AUM)
        aum = df['aum_cr'].clip(lower=1.0)
        log_aum = np.log(aum)
        
        # Normalize WITHIN each Asset_Class using Z-Score
        def _z_score_within_class(series: pd.Series, asset_class: str) -> pd.Series:
            """Z-score normalize within asset class only."""
            class_data = series[df['Asset_Class'] == asset_class]
            mean = class_data.mean()
            std = class_data.std()
            if std == 0 or std < 1e-9:
                return (series - mean) / (1e-9)  # Avoid division by zero
            return (series - mean) / std
        
        # Calculate Z-scores per asset class
        df['Sharpe_Z'] = df.groupby('Asset_Class', group_keys=False).apply(
            lambda x: _z_score_within_class(sharpe.loc[x.index], x['Asset_Class'].iloc[0])
        )
        df['InvTER_Z'] = df.groupby('Asset_Class', group_keys=False).apply(
            lambda x: _z_score_within_class(inv_ter.loc[x.index], x['Asset_Class'].iloc[0])
        )
        df['LogAUM_Z'] = df.groupby('Asset_Class', group_keys=False).apply(
            lambda x: _z_score_within_class(log_aum.loc[x.index], x['Asset_Class'].iloc[0])
        )
        
        # Combine into final score: 0.4×Sharpe + 0.4×InvTER + 0.2×LogAUM
        df['Score'] = (0.4 * df['Sharpe_Z'] + 
                       0.4 * df['InvTER_Z'] + 
                       0.2 * df['LogAUM_Z'])
        
        # Normalize to [0, 100] for user readability
        score_min = df['Score'].min()
        score_max = df['Score'].max()
        if score_max > score_min:
            df['Score_Normalized'] = 100 * (df['Score'] - score_min) / (score_max - score_min)
        else:
            df['Score_Normalized'] = 50.0  # All equal
        
        return df
    
    def vectorize_schemes(self) -> pd.DataFrame:
        """
        Create normalized feature vectors for all schemes
        
        Returns:
            DataFrame with scheme vectors
        """
        df = self.df_schemes.copy()
        
        # Normalize fund features to [0,1]
        df['amc_reputation_norm'] = df['amc_reputation'].astype(float)
        df['debt_score_norm'] = df['debt_score'].astype(float)
        df['equity_score_norm'] = df['equity_score'].astype(float)
        df['hybrid_score_norm'] = df['hybrid_score'].astype(float)
        df['direct_plan_norm'] = df['direct_plan'].astype(float)
        df['category_quality_norm'] = df['category_quality'].astype(float)
        
        # Normalize TER (lower is better) - invert
        ter_min = df['estimated_ter'].min()
        ter_max = df['estimated_ter'].max()
        df['ter_score'] = 1.0 - (df['estimated_ter'] - ter_min) / (ter_max - ter_min + 1e-6)
        
        # Normalize returns (higher is better, but cap outliers)
        cagr_3y_clipped = df['cagr_3y'].clip(-0.5, 0.5)  # Cap at ±50%
        df['return_score'] = (cagr_3y_clipped + 0.5) / 1.0  # Map [-0.5, 0.5] to [0, 1]
        
        return df
    
    def compute_match_score(self, user_vector: Dict[str, float], 
                           scheme_row: pd.Series) -> float:
        """
        Compute similarity between user profile and scheme
        Weighted dot product of normalized vectors
        
        Returns:
            Match score [0, 1]
        """
        # Risk alignment: user risk tolerance matches scheme profile
        if user_vector['risk_score'] < 0.3:  # Low risk
            risk_match = scheme_row['debt_score_norm']
        elif user_vector['risk_score'] < 0.6:  # Moderate
            risk_match = (scheme_row['debt_score_norm'] + scheme_row['hybrid_score_norm']) / 2
        else:  # High/Very High
            risk_match = max(scheme_row['equity_score_norm'], scheme_row['hybrid_score_norm'])
        
        # Time horizon alignment
        if user_vector['horizon_norm'] < 0.4:  # Short term (1-3yr)
            # Prefer debt/liquid funds with stable returns
            return_match = 0.5
            horizon_weight = 0.4
        else:  # Long term (3yr+)
            # Prefer schemes with good historical returns
            return_match = scheme_row['return_score']
            horizon_weight = 0.6
        
        # Experience filter: Beginners prefer simpler funds
        if user_vector['exp_score'] < 0.4:  # Beginner
            complexity_match = scheme_row['category_quality_norm']
        else:
            complexity_match = 1.0  # Expert can handle any
        
        # Composite score (weighted average)
        weights = {
            'amc_reputation': 0.15,
            'risk_match': 0.30,
            'return_match': 0.25,
            'ter': 0.15,
            'complexity': 0.10,
            'direct_plan': 0.05
        }

        score = (
            weights['amc_reputation'] * scheme_row.get('amc_reputation_norm', 0.0) +
            weights['risk_match'] * risk_match +
            weights['return_match'] * return_match +
            weights['ter'] * scheme_row.get('ter_score', 0.0) +
            weights['complexity'] * complexity_match +
            weights['direct_plan'] * scheme_row.get('direct_plan_norm', 0.0)
        )

        return score

    def recommend(self, profile: UserProfile, top_n: int = 5) -> List[Dict]:
        """
        MAIN RECOMMENDATION PIPELINE
        Implements complete Filter → Allocate → Rank → Select logic.
        
        Returns top N recommendations as ranked list with explanations.
        """
        print(f"\n{'='*70}")
        print(f"🎯 RECOMMENDATION REQUEST: {profile.user_id}")
        print(f"{'='*70}")
        print(f"Profile: Age {profile.age}, Risk {profile.risk_tolerance}, "
              f"Horizon {profile.investment_horizon}")
        
        # ===== STAGE 1: FILTER =====
        df_filtered = self._hard_filter(profile)
        if len(df_filtered) == 0:
            print("[ERROR] No schemes match your constraints!")
            return []
        
        # ===== STAGE 2: ALLOCATE =====
        alloc = self._compute_allocation(profile)
        print(f"\n💼 Target Allocation:")
        print(f"   • Equity: {alloc['equity_pct']*100:.1f}%")
        print(f"   • Debt: {alloc['debt_pct']*100:.1f}%")
        
        # ===== STAGE 3: SCORE (SEPARATE BY ASSET CLASS) =====
        df_scored = self._score_funds_within_class(df_filtered)
        
        # ===== STAGE 4: SELECT TOP FUNDS =====
        recommendations = []
        
        # Get Equity recommendations (if allocation allows)
        if alloc['equity_pct'] > 0.01:
            equity_funds = df_scored[df_scored['Asset_Class'] == 'Equity'].nlargest(3, 'Score')
            print(f"\n[EQUITY] TOP EQUITY FUNDS ({len(equity_funds)} found):")
            for i, (_, row) in enumerate(equity_funds.iterrows(), 1):
                rec = {
                    'rank': i,
                    'asset_class': 'Equity',
                    'scheme_code': int(row['scheme_code']),
                    'scheme_name': row['scheme_name'],
                    'fund_house': row['fund_house'],
                    'scheme_category': row['scheme_category'],
                    'plan': row.get('plan', 'N/A'),
                    'nav': float(row.get('nav', 0)),
                    'aum_cr': float(row['aum_cr']),
                    'estimated_ter': float(row['estimated_ter']),
                    'cagr_3y': float(row.get('cagr_3y', 0)) if pd.notna(row.get('cagr_3y')) else None,
                    'score': round(row['Score_Normalized'], 1),
                    'reason': self._explain_fund(row, profile)
                }
                recommendations.append(rec)
                print(f"  {i}. {row['scheme_name'][:50]} (Score: {rec['score']})")
        
        # Get Debt recommendations
        debt_count = 2 if alloc['equity_pct'] > 0.01 else 3  # If no equity, show more debt
        debt_funds = df_scored[df_scored['Asset_Class'] == 'Debt'].nlargest(debt_count, 'Score')
        print(f"\n📉 TOP DEBT FUNDS ({len(debt_funds)} found):")
        for i, (_, row) in enumerate(debt_funds.iterrows(), 1):
            rec = {
                'rank': len(recommendations) + i,
                'asset_class': 'Debt',
                'scheme_code': int(row['scheme_code']),
                'scheme_name': row['scheme_name'],
                'fund_house': row['fund_house'],
                'scheme_category': row['scheme_category'],
                'plan': row.get('plan', 'N/A'),
                'nav': float(row.get('nav', 0)),
                'aum_cr': float(row['aum_cr']),
                'estimated_ter': float(row['estimated_ter']),
                'cagr_3y': float(row.get('cagr_3y', 0)) if pd.notna(row.get('cagr_3y')) else None,
                'score': round(row['Score_Normalized'], 1),
                'reason': self._explain_fund(row, profile)
            }
            recommendations.append(rec)
            print(f"  {i}. {row['scheme_name'][:50]} (Score: {rec['score']})")
        
        print(f"\n[SUCCESS] Generated {len(recommendations)} recommendations")
        print(f"{'='*70}\n")
        
        return recommendations[:top_n]
    
    def _explain_fund(self, row: pd.Series, profile: UserProfile) -> str:
        """Generate human-readable explanation for recommendation."""
        reasons = []
        
        # AUM stability
        if row['aum_cr'] >= 1000:
            reasons.append("Large AUM (stability)")
        elif row['aum_cr'] >= 100:
            reasons.append("Healthy AUM")
        
        # Cost efficiency
        ter = row['estimated_ter']
        if ter < 0.5:
            reasons.append("Low expense ratio")
        elif ter < 1.0:
            reasons.append("Reasonable costs")
        
        # Performance
        if row.get('cagr_3y', 0) and row['cagr_3y'] > 0.15:
            reasons.append("Strong 3Y returns")
        
        # AMC quality
        top_amcs = ['SBI', 'ICICI', 'HDFC', 'Nippon', 'Kotak', 'Aditya Birla', 'UTI', 'Axis', 'Mirae', 'DSP']
        if any(amc in row['fund_house'] for amc in top_amcs):
            reasons.append("Top-10 AMC")
        
        # Direct plan benefit
        if 'direct' in str(row.get('plan', '')).lower():
            reasons.append("Direct Plan (lower fees)")
        
        return " • ".join(reasons) if reasons else "Strong fundamental match"


# Backward compatibility alias
RecommendationEngine = FundRecommender

