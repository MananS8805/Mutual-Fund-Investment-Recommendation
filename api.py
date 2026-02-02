"""
Flask API for Mutual Fund Recommendations
REST endpoint for AI agents and frontend applications
"""

from flask import Flask, request, jsonify
from recommendation_model import RecommendationEngine, UserProfile
import json
from datetime import datetime

app = Flask(__name__)

# Initialize engine at startup
try:
    engine = RecommendationEngine("data/mf_full_dataset_final.csv")
    print("✅ Recommendation engine loaded successfully")
except Exception as e:
    print(f"❌ Error loading engine: {e}")
    engine = None


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'engine_ready': engine is not None
    })


@app.route('/recommend', methods=['POST'])
def get_recommendations():
    """
    POST /recommend
    
    Request body:
    {
        "user_id": "user_001",
        "age": 30,
        "annual_income": "10L",
        "monthly_sip": 5000,
        "risk_tolerance": "Moderate",
        "investment_horizon": "10+yr",
        "investment_goals": ["Wealth Growth", "Retirement"],
        "experience": "Beginner",
        "top_n": 10,
        "min_aum_cr": 100.0
    }
    
    Response:
    {
        "status": "success",
        "recommendations": [
            {
                "rank": 1,
                "scheme_code": 119551,
                "scheme_name": "...",
                "match_score": 0.825,
                ...
            }
        ]
    }
    """
    
    if not engine:
        return jsonify({
            'status': 'error',
            'message': 'Recommendation engine not initialized'
        }), 500
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'user_id', 'age', 'annual_income', 'monthly_sip',
            'risk_tolerance', 'investment_horizon', 'investment_goals', 'experience'
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Create user profile
        profile = UserProfile(
            user_id=data['user_id'],
            age=int(data['age']),
            annual_income=data['annual_income'],
            monthly_sip=int(data['monthly_sip']),
            risk_tolerance=data['risk_tolerance'],
            investment_horizon=data['investment_horizon'],
            investment_goals=data['investment_goals'],
            experience=data['experience']
        )
        
        # Get recommendations
        top_n = data.get('top_n', 10)
        min_aum = data.get('min_aum_cr', 100.0)
        
        recommendations = engine.recommend(profile, top_n=top_n, min_aum_cr=min_aum)
        
        return jsonify({
            'status': 'success',
            'user_id': profile.user_id,
            'timestamp': datetime.now().isoformat(),
            'total_recommendations': len(recommendations),
            'recommendations': recommendations
        }), 200
    
    except ValueError as ve:
        return jsonify({
            'status': 'error',
            'message': f'Invalid input: {str(ve)}'
        }), 400
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal error: {str(e)}'
        }), 500


@app.route('/recommend-batch', methods=['POST'])
def batch_recommendations():
    """
    POST /recommend-batch
    Process multiple user profiles in one request
    
    Request body:
    {
        "users": [
            { user profile 1 },
            { user profile 2 }
        ]
    }
    """
    
    if not engine:
        return jsonify({
            'status': 'error',
            'message': 'Recommendation engine not initialized'
        }), 500
    
    try:
        data = request.get_json()
        users = data.get('users', [])
        
        if not users:
            return jsonify({
                'status': 'error',
                'message': 'No users provided'
            }), 400
        
        results = []
        for user_data in users:
            profile = UserProfile(
                user_id=user_data['user_id'],
                age=int(user_data['age']),
                annual_income=user_data['annual_income'],
                monthly_sip=int(user_data['monthly_sip']),
                risk_tolerance=user_data['risk_tolerance'],
                investment_horizon=user_data['investment_horizon'],
                investment_goals=user_data['investment_goals'],
                experience=user_data['experience']
            )
            
            recs = engine.recommend(profile, top_n=user_data.get('top_n', 5))
            results.append({
                'user_id': profile.user_id,
                'recommendations': recs
            })
        
        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'batch_size': len(results),
            'results': results
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Batch processing error: {str(e)}'
        }), 500


@app.route('/scheme-details/<int:scheme_code>', methods=['GET'])
def get_scheme_details(scheme_code):
    """Get full details for a specific scheme"""
    
    if not engine:
        return jsonify({'status': 'error', 'message': 'Engine not ready'}), 500
    
    try:
        scheme = engine.df_schemes[engine.df_schemes['scheme_code'] == scheme_code]
        
        if scheme.empty:
            return jsonify({
                'status': 'error',
                'message': f'Scheme {scheme_code} not found'
            }), 404
        
        row = scheme.iloc[0]
        return jsonify({
            'status': 'success',
            'scheme_code': int(row['scheme_code']),
            'scheme_name': row['scheme_name'],
            'fund_house': row['fund_house'],
            'scheme_category': row['scheme_category'],
            'plan': row['plan'],
            'nav': float(row['nav']),
            'aum_cr': float(row['aum_cr']),
            'estimated_ter': float(row['estimated_ter']),
            'cagr_1y': float(row['abs_return_1y']) if pd.notna(row['abs_return_1y']) else None,
            'cagr_3y': float(row['cagr_3y']) if pd.notna(row['cagr_3y']) else None,
            'cagr_5y': float(row['cagr_5y']) if pd.notna(row['cagr_5y']) else None,
            'volatility_1y': float(row['vol_1y_annualized']) if 'vol_1y_annualized' in row and pd.notna(row['vol_1y_annualized']) else None,
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get overall dataset statistics"""
    
    if not engine:
        return jsonify({'status': 'error', 'message': 'Engine not ready'}), 500
    
    df = engine.df_schemes
    return jsonify({
        'status': 'success',
        'total_schemes': len(df),
        'total_aum_cr': float(df['aum_cr'].sum()),
        'avg_ter': float(df['estimated_ter'].mean()),
        'top_10_amcs': int(df['amc_reputation'].sum()),
        'direct_plans': int(df['direct_plan'].sum()),
        'equity_schemes': int(df['equity_score'].sum()),
        'debt_schemes': int(df['debt_score'].sum()),
        'hybrid_schemes': int(df['hybrid_score'].sum()),
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
