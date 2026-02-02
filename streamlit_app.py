import streamlit as st
import pandas as pd
import numpy as np
from recommendation_model import RecommendationEngine, UserProfile
import plotly.graph_objects as go
import plotly.express as px

# Set page config
st.set_page_config(
    page_title="Mutual Fund Recommendation Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #1f77b4;
    }
    .recommendation-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .score-high {
        color: #2ecc71;
        font-weight: bold;
    }
    .score-medium {
        color: #f39c12;
        font-weight: bold;
    }
    .score-low {
        color: #e74c3c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🎯 Mutual Fund Recommendation Engine")
st.markdown("---")

# Load the model and dataset
@st.cache_resource
def load_recommendation_engine():
    """Load the recommendation engine once"""
    engine = RecommendationEngine(dataset_path="data/mf_full_dataset_final.csv")
    return engine

# Load engine
try:
    engine = load_recommendation_engine()
    st.session_state.engine = engine
except Exception as e:
    st.error(f"❌ Error loading recommendation engine: {str(e)}")
    st.stop()

# Sidebar for user inputs
st.sidebar.header("👤 Your Investment Profile")
st.sidebar.markdown("---")

col1, col2 = st.sidebar.columns(2)

with col1:
    age = st.number_input(
        "Age (years)",
        min_value=18,
        max_value=80,
        value=35,
        help="Your current age"
    )

with col2:
    income = st.selectbox(
        "Annual Income",
        options=["< ₹5 Lakhs", "₹5-10 Lakhs", "₹10-20 Lakhs", "₹20-50 Lakhs", "> ₹50 Lakhs"],
        help="Your annual income bracket"
    )

col3, col4 = st.sidebar.columns(2)

with col3:
    monthly_sip = st.number_input(
        "Monthly SIP (₹)",
        min_value=0,
        max_value=500000,
        value=10000,
        step=1000,
        help="Monthly investment amount"
    )

with col4:
    risk_tolerance = st.selectbox(
        "Risk Tolerance",
        options=["Very Low", "Low", "Moderate", "High", "Very High"],
        help="Your comfort level with market volatility"
    )

col5, col6 = st.sidebar.columns(2)

with col5:
    investment_horizon = st.selectbox(
        "Investment Horizon",
        options=["1-3 years", "3-5 years", "5-10 years", "10+ years"],
        help="How long you plan to invest"
    )

with col6:
    investment_goals = st.selectbox(
        "Investment Goals",
        options=["Wealth Creation", "Retirement Planning", "Child Education", "General Savings"],
        help="Your primary investment objective"
    )

experience = st.sidebar.selectbox(
    "Investment Experience",
    options=["Beginner", "Intermediate", "Advanced"],
    help="Your experience with investments"
)

st.sidebar.markdown("---")

# Create user profile
user_profile = UserProfile(
    user_id="user_" + str(hash(f"{age}_{income}_{monthly_sip}")),
    age=age,
    annual_income=income,
    monthly_sip=monthly_sip,
    risk_tolerance=risk_tolerance,
    investment_horizon=investment_horizon,
    investment_goals=[investment_goals],
    experience=experience
)

# Get recommendations button
if st.sidebar.button("🔍 Get Recommendations", use_container_width=True, type="primary"):
    st.session_state.show_results = True
else:
    st.session_state.show_results = False

# Main content area
if st.session_state.show_results:
    # Display user profile summary
    st.header("📋 Your Profile Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Age", f"{age} years")
    
    with col2:
        st.metric("Monthly SIP", f"₹{monthly_sip:,}")
    
    with col3:
        st.metric("Risk", risk_tolerance)
    
    with col4:
        st.metric("Horizon", investment_horizon)
    
    with col5:
        st.metric("Experience", experience)
    
    st.markdown("---")
    
    # Get recommendations
    with st.spinner("🔄 Analyzing funds and generating recommendations..."):
        try:
            # Use the new structured FAR API to retrieve allocation and top funds
            structured = engine.recommend_structured(
                user_profile,
                top_equity=3,
                top_debt=2,
                invest_amount=monthly_sip * 12
            )

            st.success("✅ Generated structured allocation and top funds")
            st.markdown("---")

            # Allocation summary
            st.header("📐 Recommended Allocation")
            alloc = structured.get('allocation', {})
            col1, col2 = st.columns(2)
            with col1:
                eq_pct = alloc.get('Equity', {}).get('percent', 0.0)
                eq_amt = alloc.get('Equity', {}).get('amount', 0.0)
                st.metric("Equity %", f"{eq_pct*100:.0f}%")
                st.metric("Equity Amount (₹)", f"₹{eq_amt:,.0f}")
            with col2:
                debt_pct = alloc.get('Debt', {}).get('percent', 0.0)
                debt_amt = alloc.get('Debt', {}).get('amount', 0.0)
                st.metric("Debt %", f"{debt_pct*100:.0f}%")
                st.metric("Debt Amount (₹)", f"₹{debt_amt:,.0f}")

            st.markdown("---")

            # Build flat recommendations list for the legacy UI components
            flat = []
            user_vec = engine.vectorize_user(user_profile)
            # precompute vectorized scheme features (normalized) for explanations
            vec_df = engine.vectorize_schemes()

            def enrich_and_append(entry, rank):
                # entry contains scheme_code and Z_Score
                code = entry.get('scheme_code')
                scheme_row = engine.df_schemes[engine.df_schemes['scheme_code'] == int(code)]
                if len(scheme_row) == 0:
                    return
                row = scheme_row.iloc[0]
                # prefer the vectorized row (contains normalized fields) for explanations
                vec_row = vec_df[vec_df['scheme_code'] == int(code)]
                if len(vec_row) > 0:
                    reason = engine._explain_match(user_vec, vec_row.iloc[0])
                else:
                    reason = engine._explain_match(user_vec, row)
                flat.append({
                    'rank': rank,
                    'scheme_code': int(row['scheme_code']),
                    'scheme_name': row.get('scheme_name', 'N/A'),
                    'fund_house': row.get('fund_house', 'N/A'),
                    'nav': float(row.get('nav')) if 'nav' in row and pd.notna(row.get('nav')) else None,
                    'plan': row.get('plan', 'N/A'),
                    'cagr_3y': float(row.get('cagr_3y')) if 'cagr_3y' in row and pd.notna(row.get('cagr_3y')) else None,
                    'estimated_ter': float(row.get('estimated_ter')) if 'estimated_ter' in row and pd.notna(row.get('estimated_ter')) else None,
                    'aum_cr': float(row.get('aum_cr')) if 'aum_cr' in row and pd.notna(row.get('aum_cr')) else None,
                    'match_score': float(entry.get('Z_Score', 0.0)),
                    'reason': reason
                })

            rank = 1
            for f in alloc.get('Equity', {}).get('funds', []):
                enrich_and_append(f, rank); rank += 1
            for f in alloc.get('Debt', {}).get('funds', []):
                enrich_and_append(f, rank); rank += 1

            # Sort flat list by match_score and take top 10
            flat_sorted = sorted(flat, key=lambda x: x.get('match_score', 0.0), reverse=True)
            top_10 = flat_sorted[:10]
            # Re-assign ranks 1..N
            for i, item in enumerate(top_10, start=1):
                item['rank'] = i

            # Now reuse the legacy display (cards, table, comparison) but feed from `top_10`
            st.header("🏆 Top 10 Recommended Funds")
            tab1, tab2, tab3 = st.tabs(["📊 Card View", "📋 Table View", "📈 Comparison"])

            with tab1:
                for rec in top_10:
                    idx = rec['rank']
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        with st.container():
                            st.markdown(f"### #{idx} - {rec['scheme_name'][:50]}")
                            score = rec['match_score']
                            if score >= 0.8:
                                score_class = "score-high"
                                score_emoji = "🟢"
                            elif score >= 0.65:
                                score_class = "score-medium"
                                score_emoji = "🟡"
                            else:
                                score_class = "score-low"
                                score_emoji = "🔴"
                            st.markdown(f"{score_emoji} **Match Score**: <span class='{score_class}'>{score:.2f}/1.00</span>", unsafe_allow_html=True)
                            detail_col1, detail_col2, detail_col3 = st.columns(3)
                            with detail_col1:
                                st.metric("Fund House", rec['fund_house'])
                                st.metric("Scheme Code", rec['scheme_code'])
                            with detail_col2:
                                st.metric("Latest NAV", f"₹{rec['nav']:.2f}" if rec['nav'] is not None else "N/A")
                                st.metric("Plan Type", rec['plan'])
                            with detail_col3:
                                st.metric("3Y CAGR", f"{rec['cagr_3y']:.2f}%" if rec['cagr_3y'] is not None else "N/A")
                                st.metric("Expense Ratio", f"{rec['estimated_ter']:.2f}%" if rec['estimated_ter'] is not None else "N/A")
                            st.metric("AUM", f"₹{rec['aum_cr']:.0f} Cr" if rec['aum_cr'] is not None else "N/A")
                            st.markdown("**Why this fund?**")
                            st.info(rec['reason'])
                    with col2:
                        fig = go.Figure(data=[go.Scatterpolar(r=[rec['match_score'] * 100], theta=['Match Score'], fill='toself', marker_color='#1f77b4')])
                        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=200, margin=dict(l=20, r=20, t=20, b=20))
                        st.plotly_chart(fig, use_container_width=True, key=f"score_chart_{idx}")

            with tab2:
                df_recommendations = pd.DataFrame([
                    {
                        "Rank": r['rank'],
                        "Scheme Name": r['scheme_name'][:40],
                        "Fund House": r['fund_house'],
                        "Scheme Code": r['scheme_code'],
                        "Match Score": f"{r['match_score']:.2f}",
                        "NAV": f"₹{r['nav']:.2f}" if r['nav'] is not None else "N/A",
                        "3Y CAGR": f"{r['cagr_3y']:.2f}%" if r['cagr_3y'] is not None else "N/A",
                        "TER": f"{r['estimated_ter']:.2f}%" if r['estimated_ter'] is not None else "N/A",
                        "AUM (Cr)": f"₹{r['aum_cr']:.0f}" if r['aum_cr'] is not None else "N/A"
                    }
                    for r in top_10
                ])
                st.dataframe(df_recommendations, use_container_width=True, hide_index=True, height=600)
                csv = df_recommendations.to_csv(index=False)
                st.download_button(label="📥 Download as CSV", data=csv, file_name="fund_recommendations.csv", mime="text/csv", use_container_width=True)

            with tab3:
                st.subheader("Compare Top Funds")
                # reuse previous comparison widget but based on flat
                col1, col2, col3 = st.columns(3)
                with col1:
                    metric_x = st.selectbox("X-Axis", options=["Match Score", "3Y CAGR (%)", "Expense Ratio (%)", "AUM (Cr)"], key="x_metric")
                with col2:
                    metric_y = st.selectbox("Y-Axis", options=["Match Score", "3Y CAGR (%)", "Expense Ratio (%)", "AUM (Cr)"], key="y_metric", index=1)
                with col3:
                    metric_size = st.selectbox("Bubble Size", options=["Match Score", "3Y CAGR (%)", "Expense Ratio (%)", "AUM (Cr)"], key="size_metric", index=3)

                def get_metric_value(rec, metric):
                    if metric == "Match Score":
                        return rec['match_score']
                    elif metric == "3Y CAGR (%)":
                        return rec['cagr_3y'] if rec['cagr_3y'] is not None else 0
                    elif metric == "Expense Ratio (%)":
                        return rec['estimated_ter'] if rec['estimated_ter'] is not None else 0
                    elif metric == "AUM (Cr)":
                        return rec['aum_cr'] if rec['aum_cr'] is not None else 0
                    return 0

                top_items = top_10[:5]
                df_scatter = pd.DataFrame([
                    {
                        "Scheme": r['scheme_name'][:30],
                        metric_x: get_metric_value(r, metric_x),
                        metric_y: get_metric_value(r, metric_y),
                        "Size": get_metric_value(r, metric_size),
                        "Fund House": r['fund_house']
                    }
                    for r in top_items
                ])
                fig = px.scatter(df_scatter, x=metric_x, y=metric_y, size="Size", hover_data=["Scheme", "Fund House"], color="Fund House", title=f"{metric_x} vs {metric_y}", height=500)
                st.plotly_chart(fig, use_container_width=True, key="comparison_scatter")

            # Insights
            st.markdown("---")
            st.header("💡 Key Insights")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_score = np.mean([r['match_score'] for r in flat]) if flat else 0
                st.metric("Average Match Score", f"{avg_score:.2f}/1.00")
            with col2:
                top_fund_house = flat[0]['fund_house'] if flat else "N/A"
                st.metric("Top Recommended Fund House", top_fund_house)
            with col3:
                avg_ter = np.mean([r['estimated_ter'] for r in flat if r['estimated_ter'] is not None]) if flat else 0
                st.metric("Avg Expense Ratio", f"{avg_ter:.2f}%")
            with col4:
                valid_cagrs = [r['cagr_3y'] for r in flat if r['cagr_3y'] is not None]
                st.metric("Avg 3Y CAGR", f"{np.mean(valid_cagrs):.2f}%" if valid_cagrs else "N/A")

            # Composition pie
            st.subheader("📊 Fund Composition by Bucket")
            risk_counts = {
                'Equity Funds': len(alloc.get('Equity', {}).get('funds', [])),
                'Debt Funds': len(alloc.get('Debt', {}).get('funds', [])),
                'Hybrid Funds': len(alloc.get('Hybrid', {}).get('funds', []))
            }
            fig_pie = go.Figure(data=[go.Pie(labels=list(risk_counts.keys()), values=list(risk_counts.values()), hole=0.3, marker=dict(colors=['#3498db', '#2ecc71', '#f39c12']))])
            fig_pie.update_layout(height=400, title="Fund Bucket Distribution")
            st.plotly_chart(fig_pie, use_container_width=True, key="fund_distribution_pie")

        except Exception as e:
            st.error(f"❌ Error generating recommendations: {str(e)}")
            import traceback
            st.write(traceback.format_exc())

else:
    # Welcome message when no results shown
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.info("""
        ## 👋 Welcome to MF Recommendation Engine
        
        **How it works:**
        1. Fill in your profile on the left sidebar
        2. Click "Get Recommendations"
        3. View personalized fund recommendations
        
        **What we analyze:**
        - Your age and investment horizon
        - Risk tolerance and financial goals
        - Monthly investment capacity
        - Your investment experience level
        
        Based on these factors, our AI model matches you with the best-suited mutual funds from a database of 6,000+ schemes.
        """)
    
    with col2:
        st.success("""
        ## ✨ Why Choose Us?
        
        ✅ **AI-Powered**: Machine learning model for accurate matching
        
        ✅ **Comprehensive**: 14,000+ mutual fund schemes analyzed
        
        ✅ **Personalized**: Recommendations tailored to your profile
        
        ✅ **Transparent**: Clear reasons for each recommendation
        
        ✅ **Real-time Data**: Latest NAV and performance metrics
        
        ✅ **Educational**: Detailed fund information and insights
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 12px; margin-top: 20px;'>
    <p>Mutual Fund Recommendation Engine | Built with ❤️ using Streamlit & Machine Learning</p>
    <p>Disclaimer: This tool provides recommendations based on your profile. Please consult a financial advisor before investing.</p>
</div>
""", unsafe_allow_html=True)
