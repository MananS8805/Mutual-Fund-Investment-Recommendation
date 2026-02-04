"""
Mutual Fund Recommendation Engine
Matches investor profiles to optimal schemes using vector-based similarity
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


class RecommendationEngine:
    """Vectorizes user profiles and schemes, computes similarity matches"""
    
    def __init__(self, dataset_path: str = "data/mf_full_dataset_final.csv"):
        """
        Initialize engine with mutual fund dataset
        
        Args:
            dataset_path: Path to the final MF dataset with features
        """
        self.df_schemes = pd.read_csv(dataset_path)
        self._validate_dataset()
        
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
        
        print(f"✅ Loaded {len(self.df_schemes):,} schemes with complete features")

    def _classify_funds(self):
        """Classify funds into Asset_Class and Risk Grade per strict mapping.

        Asset mapping:
          Equity: Large Cap, Mid Cap, Small Cap, Flexi Cap, Sectoral, Index
          Debt: Liquid, Overnight, Corporate Bond, Ultra Short, Gilt
          Hybrid: Arbitrage, Dynamic Bond, Aggressive Hybrid

        Risk grade: 1 (lowest) to 5 (highest) for filtering rules.
        """
        df = self.df_schemes

        def map_asset(cat: str) -> str:
            if pd.isna(cat):
                return 'Other'
            c = cat.lower()
            # Equity keywords
            if any(k in c for k in ['large cap', 'large', 'mid cap', 'mid', 'small cap', 'small', 'flexi', 'sectoral', 'index']):
                return 'Equity'
            # Debt keywords
            if any(k in c for k in ['liquid', 'overnight', 'corporate bond', 'ultra short', 'gilt']):
                return 'Debt'
            # Hybrid keywords
            if any(k in c for k in ['arbitrage', 'dynamic bond', 'aggressive hybrid', 'hybrid']):
                return 'Hybrid'
            return 'Other'

        def map_risk(cat: str) -> int:
            if pd.isna(cat):
                return 3
            c = cat.lower()
            if any(k in c for k in ['liquid', 'overnight']):
                return 1
            if any(k in c for k in ['ultra short', 'short']):
                return 2
            if any(k in c for k in ['large', 'large cap', 'flexi', 'hybrid', 'dynamic']):
                return 3
            if any(k in c for k in ['mid', 'mid cap', 'small', 'small cap']):
                return 4
            if any(k in c for k in ['sectoral', 'thematic']):
                return 5
            return 3

        df['Asset_Class'] = df['scheme_category'].astype(str).apply(map_asset)
        df['Risk_Grade'] = df['scheme_category'].astype(str).apply(map_risk)
        # ensure min_sip column exists for viability checks
        if 'min_sip' not in df.columns:
            df['min_sip'] = 0.0
    
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

    def _allocate(self, profile: UserProfile, total_amount: Optional[float] = None) -> Dict[str, float]:
        """Allocation layer: determine % to Equity vs Debt based on age and risk.

        If `total_amount` is None, compute annual commitment as monthly_sip * 12.
        Returns allocation percents (0-100).
        """
        if total_amount is None:
            total_amount = profile.monthly_sip * 12.0

        # Base formula
        equity_percent = max(0.0, min(100.0, 110 - profile.age))

        # Risk adjustments per spec
        rt = profile.risk_tolerance.lower()
        if 'high' in rt or 'very high' in rt:
            equity_percent = min(100.0, equity_percent + 10.0)
        if 'low' in rt:
            equity_percent = max(0.0, equity_percent - 20.0)

        # Horizon override: if no equity available later, engine will set 0

        debt_percent = 100.0 - equity_percent

        return {'Equity': equity_percent / 100.0, 'Debt': debt_percent / 100.0, 'total_amount': total_amount}

    def _hard_filter(self, profile: UserProfile, df: pd.DataFrame) -> pd.DataFrame:
        """Apply Hard Filter Layer (Gatekeeper) per blueprint.

        Removes funds incompatible with user's horizon, experience, AUM, and SIP.
        """
        df = df.copy()

        # Constraint A: Investment Horizon (strict rules)
        horizon = profile.investment_horizon
        h = str(horizon).lower()
        # safe lowercase scheme_category for string ops
        cat_lower = df['scheme_category'].fillna('').str.lower()
        if '<1' in h or 'less' in h or h.startswith('1yr') or h.startswith('<1'):
            # Keep ONLY Liquid/Overnight (Asset_Class == Debt and Risk_Grade==1)
            df = df[(df['Asset_Class'] == 'Debt') & (df['Risk_Grade'] == 1)]
        elif '1-3' in h or '1-3yr' in h:
            # Keep ONLY Debt and Arbitrage funds. Remove all Equity.
            df = df[(df['Asset_Class'] == 'Debt') | ((df['Asset_Class'] == 'Hybrid') & cat_lower.str.contains('arbitrage'))]
            df = df[df['Asset_Class'] != 'Equity']
        elif '3-5' in h or '3-5yr' in h:
            # Keep Debt, Hybrid, and Large/Flexi Cap. Remove Mid/Small/Sectoral.
            df = df[(df['Asset_Class'] == 'Debt') | (df['Asset_Class'] == 'Hybrid') | ((df['Asset_Class'] == 'Equity') & cat_lower.str.contains('large|flexi'))]
        else:
            # 5+ years or unknown -> allow all categories
            pass

        # Constraint B: Experience Level
        if str(profile.experience).lower() == 'beginner':
            # Remove Sectoral, Thematic, and Small Cap funds
            df = df[~cat_lower.str.contains('sectoral|thematic|small cap|small')]

        # Constraint C: Viability - AUM check
        df = df[df['aum_cr'] >= 100.0]

        # SIP / Min SIP viability
        if 'min_sip' in df.columns and profile.monthly_sip is not None:
            df = df[df['min_sip'] <= profile.monthly_sip]

        return df

    def _score_and_rank(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute P (performance), C (cost), T (trust) and final weighted score.

        P: Sharpe ratio normalized (use `sharpe_1y_annualized` if present, else approximate)
        C: inverse TER normalized
        T: log(AUM) normalized
        Weights: P=0.4, C=0.3, T=0.3
        """
        df = df.copy()

        # Performance (P) - use sharpe_1y_annualized directly if available
        if 'sharpe_1y_annualized' in df.columns:
            p_raw = df['sharpe_1y_annualized'].fillna(0.0)
        else:
            # fallback: use return_score as proxy
            p_raw = df['return_score'].fillna(0.0)

        # normalize to 0-1
        p_min, p_max = p_raw.min(), p_raw.max()
        df['P'] = (p_raw - p_min) / (p_max - p_min + 1e-9) if p_max > p_min else 0.5

        # Cost (C) - lower expense is better -> invert expense_ratio / estimated_ter
        ter = df['estimated_ter'].fillna(df['estimated_ter'].median())
        c_raw = 1.0 / (ter + 1e-9)
        c_min, c_max = c_raw.min(), c_raw.max()
        df['C'] = (c_raw - c_min) / (c_max - c_min + 1e-9) if c_max > c_min else 0.5

        # Stability (T) - log(AUM)
        aum = df['aum_cr'].clip(lower=1.0)
        t_raw = np.log(aum)
        t_min, t_max = t_raw.min(), t_raw.max()
        df['T'] = (t_raw - t_min) / (t_max - t_min + 1e-9) if t_max > t_min else 0.5

        # Final Z_Score per spec: P=40%, C=30%, T=30%
        df['Z_Score'] = 0.4 * df['P'] + 0.3 * df['C'] + 0.3 * df['T']
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

    def recommend_structured(self, profile: UserProfile, top_equity: int = 3, top_debt: int = 2,
                             invest_amount: Optional[float] = None) -> Dict:
        """Full Filter-Allocate-Rank pipeline producing structured buckets.

        Returns a dict with allocation and top funds per bucket.
        """
        # Ensure classification exists
        self._classify_funds()

        # Vectorize schemes for scoring features
        df_vec = self.vectorize_schemes()

        # Apply hard filters
        df_safe = self._hard_filter(profile, df_vec)

        # Allocation percentages and amount
        alloc = self._allocate(profile, total_amount=invest_amount)

        # Score and rank
        df_scored = self._score_and_rank(df_safe)

        # Split by Asset_Class and pick top candidates using Z_Score
        equity_candidates = df_scored[df_scored['Asset_Class'] == 'Equity'].nlargest(top_equity, 'Z_Score')
        debt_candidates = df_scored[df_scored['Asset_Class'] == 'Debt'].nlargest(top_debt, 'Z_Score')
        # Hybrid bucket (may be empty) - keep for completeness
        hybrid_candidates = df_scored[df_scored['Asset_Class'] == 'Hybrid'].nlargest(0, 'Z_Score')

        # Build output lists
        def build_list(df_subset, score_col='Z_Score'):
            out = []
            for _, r in df_subset.iterrows():
                out.append({
                    'scheme_code': int(r['scheme_code']),
                    'scheme_name': r['scheme_name'],
                    'fund_house': r['fund_house'],
                    'aum_cr': float(r['aum_cr']),
                    'estimated_ter': float(r['estimated_ter']),
                    'cagr_3y': float(r['cagr_3y']) if pd.notna(r['cagr_3y']) else None,
                    'Z_Score': float(r[score_col])
                })
            return out

        equity_list = build_list(equity_candidates)
        debt_list = build_list(debt_candidates)
        hybrid_list = build_list(hybrid_candidates)

        # If no equity candidates remain after hard filters, override allocation per spec
        if len(equity_list) == 0:
            alloc['Equity'] = 0.0
            alloc['Debt'] = 1.0

        # If invest amount is provided, compute allocation amounts
        total_amt = alloc.get('total_amount', profile.monthly_sip * 12.0)
        equity_amt = total_amt * alloc['Equity']
        debt_amt = total_amt * alloc['Debt']

        result = {
            'allocation': {
                'Equity': {'percent': alloc['Equity'], 'amount': equity_amt, 'funds': equity_list},
                'Debt': {'percent': alloc['Debt'], 'amount': debt_amt, 'funds': debt_list},
                'Hybrid': {'funds': hybrid_list}
            },
            'summary': {
                'total_amount': total_amt,
                'equity_percent': alloc['Equity'],
                'debt_percent': alloc['Debt']
            }
        }

        return result

    def recommend(self, profile: UserProfile, top_n: int = 10,
                 min_aum_cr: float = 100.0) -> List[Dict]:
        """Backward-compatible recommend(): flatten structured output into ranked list.

        If the caller expects the new structured API, call `recommend_structured()` directly.
        """
        # Vectorize user profile for explanation generation
        user_vec = self.vectorize_user(profile)
        
        structured = self.recommend_structured(profile, top_equity=top_n, top_debt=0, invest_amount=profile.monthly_sip * 12)
        # Flatten equity then debt
        flattened = []
        rank = 1
        for bucket in ['Equity', 'Debt']:
            for f in structured['allocation'].get(bucket, {}).get('funds', []):
                flattened.append({
                    'rank': rank,
                    'scheme_code': f['scheme_code'],
                    'scheme_name': f['scheme_name'],
                    'fund_house': f['fund_house'],
                    'aum_cr': f['aum_cr'],
                    'estimated_ter': f['estimated_ter'],
                    'cagr_3y': f['cagr_3y'],
                    'match_score': round(f['Z_Score'] * 100, 2),
                    'reason': f"Risk alignment score: {round(f['Z_Score'] * 100, 1)}%"
                })
                rank += 1

        return flattened
    
    def _explain_match(self, user_vec: Dict[str, float], scheme_row: pd.Series) -> str:
        """Generate human-readable explanation for why scheme was recommended"""
        reasons = []
        
        if scheme_row['amc_reputation_norm'] > 0:
            reasons.append("Top 10 AMC")
        
        if scheme_row['direct_plan_norm'] > 0:
            reasons.append("Direct Plan (lower fees)")
        
        if user_vec['risk_score'] < 0.3 and scheme_row['debt_score_norm'] > 0:
            reasons.append("Low-risk profile match")
        elif user_vec['risk_score'] > 0.6 and scheme_row['equity_score_norm'] > 0:
            reasons.append("High-growth match")
        
        if scheme_row['return_score'] > 0.7:
            reasons.append("Strong 3Y returns")
        
        if scheme_row['ter_score'] > 0.8:
            reasons.append("Lower expense ratio")
        
        return " • ".join(reasons) if reasons else "Good fundamental match"
