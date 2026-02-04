#!/usr/bin/env python3
"""
Mutual Fund Recommendation Engine - Streamlit Frontend with Live NAV Tracking

This app provides:
1. User profile input via sidebar
2. Personalized mutual fund recommendations
3. Real-time NAV data visualization from mfapi.in
4. Performance comparison charts
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
from recommendation_model import FundRecommender, UserProfile
import time

# ═══════════════════════════════════════════════════════════════════════════
# STREAMLIT PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Mutual Fund Recommendation Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════
# CACHING & INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_resource
def load_recommender():
    """Load and cache the FundRecommender instance."""
    return FundRecommender('data/mf_full_dataset_final.csv')

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_historical_nav(scheme_code: int) -> pd.DataFrame:
    """
    Fetch 1-year historical NAV data from mfapi.in for a given scheme.
    
    Args:
        scheme_code: SEBI scheme code (integer)
    
    Returns:
        DataFrame with columns: date, nav (sorted ascending)
        Empty DataFrame if fetch fails
    """
    try:
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json().get('data', [])
        if not data:
            return pd.DataFrame(columns=['date', 'nav'])
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Parse dates (DD-MM-YYYY format)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y', errors='coerce')
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        
        # Remove rows with invalid dates or NAV
        df = df.dropna(subset=['date', 'nav'])
        
        # Filter for last 365 days
        cutoff_date = datetime.now() - timedelta(days=365)
        df = df[df['date'] >= cutoff_date]
        
        # Sort by date ascending
        df = df.sort_values('date').reset_index(drop=True)
        
        return df if len(df) > 0 else pd.DataFrame(columns=['date', 'nav'])
    
    except Exception as e:
        st.warning(f"⚠️ Could not fetch NAV for scheme {scheme_code}: {str(e)}")
        return pd.DataFrame(columns=['date', 'nav'])

def normalize_nav(nav_series: pd.Series) -> pd.Series:
    """Rebase NAV to 100 for comparison across funds."""
    if len(nav_series) == 0:
        return nav_series
    initial_nav = nav_series.iloc[0]
    return (nav_series / initial_nav * 100)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE TITLE & HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.title("📈 Mutual Fund Recommendation Engine")
st.markdown(
    """
    Get personalized mutual fund recommendations based on your **risk profile**, 
    **investment horizon**, and **financial goals**. 
    View live NAV performance data from the MFAPI.
    """
)

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR: USER PROFILE FORM
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("👤 Your Investment Profile")
    st.markdown("---")
    
    # Age
    age = st.slider(
        "Age",
        min_value=18,
        max_value=80,
        value=35,
        help="Your current age (affects risk tolerance and time horizon)"
    )
    
    # Annual Income
    income_options = ["5L", "10L", "25L", "50L+"]
    income = st.selectbox(
        "Annual Income",
        options=income_options,
        index=1,
        help="Approximate annual household income"
    )
    
    # Monthly SIP
    monthly_sip = st.number_input(
        "Monthly SIP Amount (₹)",
        min_value=500,
        max_value=100000,
        value=5000,
        step=500,
        help="Systematic Investment Plan amount per month"
    )
    
    # Risk Tolerance
    risk_tolerance = st.radio(
        "Risk Tolerance",
        options=["Low", "Moderate", "High", "Very High"],
        index=1,
        help="Your comfort level with market volatility"
    )
    
    # Investment Horizon
    horizon_options = ["1-3yr", "3-5yr", "5-10yr", "10+yr"]
    investment_horizon = st.selectbox(
        "Investment Horizon",
        options=horizon_options,
        index=2,
        help="Time frame for this investment goal"
    )
    
    # Experience Level
    experience = st.radio(
        "Investment Experience",
        options=["Beginner", "Intermediate", "Expert"],
        index=1,
        help="Your experience with mutual fund investing"
    )
    
    # Investment Goals
    goals = st.multiselect(
        "Investment Goals",
        options=["Wealth Growth", "Emergency", "Retirement", "Child Edu"],
        default=["Wealth Growth"],
        help="Select one or more goals for this investment"
    )
    
    st.markdown("---")
    
    # Get Recommendations Button
    get_recommendations = st.button(
        "🎯 Get Recommendations",
        use_container_width=True,
        type="primary"
    )

# ═══════════════════════════════════════════════════════════════════════════
# MAIN LOGIC: LOAD RECOMMENDER & GET RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════
engine = load_recommender()

if get_recommendations:
    # Create user profile
    user_profile = UserProfile(
        user_id=f"user_{age}_{risk_tolerance}",
        age=age,
        annual_income=income,
        monthly_sip=monthly_sip,
        risk_tolerance=risk_tolerance,
        investment_horizon=investment_horizon,
        investment_goals=goals,
        experience=experience
    )
    
    # Get recommendations
    with st.spinner("🔄 Fetching recommendations..."):
        recommendations = engine.recommend(user_profile, top_n=10)
    
    if len(recommendations) == 0:
        st.error("❌ No suitable funds found for your profile. Try adjusting your preferences.")
    else:
        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 1: USER PROFILE SUMMARY
        # ═══════════════════════════════════════════════════════════════════════
        st.header("📋 Your Profile Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Age", f"{age} yrs")
        with col2:
            st.metric("Risk Level", risk_tolerance)
        with col3:
            st.metric("Horizon", investment_horizon)
        with col4:
            st.metric("Monthly SIP", f"₹{monthly_sip:,}")
        with col5:
            st.metric("Goals", len(goals))
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 2: RECOMMENDATIONS TABLE
        # ═══════════════════════════════════════════════════════════════════════
        st.header("💰 Top Recommended Funds")
        
        # Prepare table data
        table_data = []
        for rec in recommendations:
            table_data.append({
                "Rank": rec['rank'],
                "Fund Name": rec['scheme_name'][:60],
                "Asset Class": rec.get('asset_class', 'N/A'),
                "Score": f"{rec.get('score', rec.get('match_score', 0)):.1f}",
                "TER (%)": f"{rec.get('estimated_ter', 0):.2f}",
                "AUM (Cr)": f"₹{rec.get('aum_cr', 0):,.0f}",
                "3Y CAGR (%)": f"{rec.get('cagr_3y', 0)*100:.1f}" if rec.get('cagr_3y') else "N/A",
            })
        
        df_recommendations = pd.DataFrame(table_data)
        st.dataframe(df_recommendations, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 3: NAV PERFORMANCE CHART
        # ═══════════════════════════════════════════════════════════════════════
        st.header("📊 1-Year NAV Performance Comparison")
        st.markdown(
            "Real-time NAV data from MFAPI. Values rebased to 100 for comparison."
        )
        
        # Fetch NAV data with progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        nav_data_dict = {}
        total_funds = len(recommendations)
        
        for idx, rec in enumerate(recommendations):
            scheme_code = int(rec['scheme_code'])
            fund_name_short = rec['scheme_name'][:40]
            
            status_text.text(f"Fetching NAV for {idx + 1}/{total_funds}: {fund_name_short}...")
            progress = (idx + 1) / total_funds
            progress_bar.progress(progress)
            
            # Fetch historical NAV
            nav_df = fetch_historical_nav(scheme_code)
            
            if len(nav_df) > 0:
                nav_df['nav_normalized'] = normalize_nav(nav_df['nav'])
                nav_data_dict[fund_name_short] = nav_df
            
            time.sleep(0.2)  # Rate limiting to avoid API throttling
        
        progress_bar.empty()
        status_text.empty()
        
        # Create performance chart if we have NAV data
        if nav_data_dict:
            chart_data = []
            for fund_name, nav_df in nav_data_dict.items():
                for _, row in nav_df.iterrows():
                    chart_data.append({
                        'date': row['date'],
                        'normalized_nav': row['nav_normalized'],
                        'fund': fund_name
                    })
            
            if chart_data:
                df_chart = pd.DataFrame(chart_data)
                
                # Create Plotly line chart
                fig = px.line(
                    df_chart,
                    x='date',
                    y='normalized_nav',
                    color='fund',
                    title='1-Year NAV Performance (Rebased to 100)',
                    labels={
                        'date': 'Date',
                        'normalized_nav': 'Normalized NAV (Base: 100)',
                        'fund': 'Fund Name'
                    },
                    hover_data={'normalized_nav': ':.2f', 'date': True},
                    markers=False
                )
                
                fig.update_layout(
                    height=500,
                    hovermode='x unified',
                    template='plotly_white',
                    xaxis_title='Date',
                    yaxis_title='Normalized NAV (100 = Start Date)',
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Could not fetch NAV data for any funds. Please try again.")
        else:
            st.warning("⚠️ No NAV data available. The API might be temporarily unavailable.")
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 4: FUND DETAILS
        # ═══════════════════════════════════════════════════════════════════════
        st.header("📄 Fund Details & Explanations")
        
        for idx, rec in enumerate(recommendations, 1):
            with st.expander(f"#{idx} {rec['scheme_name'][:60]}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Fund House", rec.get('fund_house', 'N/A'))
                    st.metric("Plan", rec.get('plan', 'N/A'))
                with col2:
                    st.metric("Category", rec.get('scheme_category', 'N/A')[:40])
                    st.metric("Latest NAV", f"₹{rec.get('nav', 0):.2f}")
                with col3:
                    st.metric("Risk Grade", rec.get('Risk_Grade', 'N/A'))
                    st.metric("Direct Plan", "Yes" if rec.get('direct_plan') else "No")
                
                st.markdown("**Why This Fund?**")
                st.info(rec.get('reason', 'Good fit for your profile'))

# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 12px;'>
    <p>
        📊 <b>Data Source:</b> MFAPI.in (Real-time NAV data)<br>
        🤖 <b>Powered by:</b> FundRecommender ML Engine<br>
        ⚠️ <b>Disclaimer:</b> This is for educational purposes only. 
        Consult a financial advisor before investing.
    </p>
    </div>
    """,
    unsafe_allow_html=True
)
