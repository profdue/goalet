import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from supabase import create_client

# ============================================================================
# SUPABASE CONNECTION
# ============================================================================

@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def check_pressure_flags(home_da, away_da, home_btts, away_btts, home_over, away_over):
    """Automatically determine pressure flags based on values"""
    btts_pressure = (home_btts >= 60 and away_btts >= 60)
    overs_pressure = (home_over >= 60 or away_over >= 60)
    return btts_pressure, overs_pressure

def check_rule_hits(match_data):
    """Automatically check which rules apply based on input data"""
    rule_hits = {}
    
    home_da = match_data['home_da']
    away_da = match_data['away_da']
    home_btts = match_data['home_btts']
    away_btts = match_data['away_btts']
    home_over = match_data['home_over']
    away_over = match_data['away_over']
    
    # Calculate tiers (1-4, 1 is best)
    def get_tier(value):
        if value >= 70: return 1
        if value >= 55: return 2
        if value >= 40: return 3
        return 4
    
    home_da_tier = get_tier(home_da)
    away_da_tier = get_tier(away_da)
    home_btts_tier = get_tier(home_btts)
    away_btts_tier = get_tier(away_btts)
    home_over_tier = get_tier(home_over)
    away_over_tier = get_tier(away_over)
    
    # RULE 1: [4,4] DEFENSES = UNDER 2.5
    if home_da_tier == 4 and away_da_tier == 4:
        rule_hits['rule_1'] = {
            'hit': True,
            'name': '🐢 [4,4] DEFENSES = UNDER 2.5',
            'category': 'UNDER'
        }
    
    # RULE 2: AWAY ELITE ATTACK = WINNER
    if away_btts_tier == 1:
        rule_hits['rule_2'] = {
            'hit': True,
            'name': '✈️ AWAY ELITE ATTACK = WINNER',
            'category': 'OUTCOME'
        }
    
    # RULE 7: MIXED DEFENSE = WINNER
    if (home_da_tier in [3,4] and away_da_tier in [1,2]) or (away_da_tier in [3,4] and home_da_tier in [1,2]):
        rule_hits['rule_7'] = {
            'hit': True,
            'name': '🔄 MIXED DEFENSE = WINNER',
            'category': 'OUTCOME'
        }
    
    # RULE 8: WEAK AWAY = UNDER 2.5
    if away_da_tier == 4 and home_da_tier <= 3:
        rule_hits['rule_8'] = {
            'hit': True,
            'name': '🚫 WEAK AWAY = UNDER 2.5',
            'category': 'UNDER'
        }
    
    # RULE 10: TIER2 HOME vs TIER3 AWAY = LOSS
    if home_da_tier == 2 and away_da_tier == 3:
        rule_hits['rule_10'] = {
            'hit': True,
            'name': '⚠️ TIER2 HOME vs TIER3 AWAY = LOSS',
            'category': 'OUTCOME'
        }
    
    # RULE 15: ELITE HOME = DRAW/AWAY WIN
    if home_da_tier == 2 and home_btts_tier <= 2:
        rule_hits['rule_15'] = {
            'hit': True,
            'name': '👑 ELITE HOME = DRAW/AWAY WIN',
            'category': 'OUTCOME'
        }
    
    # RULE 20_HOME: HOME ELITE ATTACK = WIN/DRAW
    if home_btts_tier == 1:
        rule_hits['rule_20_home'] = {
            'hit': True,
            'name': '🎯 HOME ELITE ATTACK = WIN/DRAW',
            'category': 'OUTCOME'
        }
    
    # RULE 20_AWAY: AWAY ELITE ATTACK = WIN/DRAW
    if away_btts_tier == 1:
        rule_hits['rule_20_away'] = {
            'hit': True,
            'name': '🎯 AWAY ELITE ATTACK = WIN/DRAW',
            'category': 'OUTCOME'
        }
    
    # RULE 21: TRIPLE CROWN = OVER 2.5
    if home_over_tier <= 2 and away_over_tier <= 2 and home_da_tier <= 2 and away_da_tier <= 2:
        rule_hits['rule_21'] = {
            'hit': True,
            'name': '🔥 TRIPLE CROWN = OVER 2.5',
            'category': 'OVER'
        }
    
    # RULE 22: GRAND UNIFIED = UNDER 2.5
    if home_da_tier == 4 and away_da_tier == 4 and home_btts_tier == 4 and away_btts_tier == 4:
        rule_hits['rule_22'] = {
            'hit': True,
            'name': '🏆 GRAND UNIFIED = UNDER 2.5',
            'category': 'UNDER'
        }
    
    return rule_hits

def get_importance_score(home_team, away_team, league):
    """Get importance score from database based on teams/league"""
    supabase = init_supabase()
    if not supabase:
        return 0
    
    try:
        # Check if it's a derby
        response = supabase.table('matches')\
            .select('derby')\
            .eq('home_team', home_team)\
            .eq('away_team', away_team)\
            .maybe_single()\
            .execute()
        
        if response.data and response.data.get('derby'):
            return 2
        
        # Check if it's a relegation battle
        response = supabase.table('matches')\
            .select('relegation')\
            .eq('league', league)\
            .maybe_single()\
            .execute()
        
        if response.data and response.data.get('relegation'):
            return 1
            
        return 0
    except:
        return 0

def save_match_data(match_data):
    """Save match data to Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        # Check if match exists
        response = supabase.table('matches')\
            .select('id')\
            .eq('home_team', match_data['home_team'])\
            .eq('away_team', match_data['away_team'])\
            .eq('match_date', match_data['match_date'].isoformat())\
            .execute()
        
        existing = response.data
        
        # Calculate tier based on values
        def calculate_tier(value):
            if value >= 70: return 1
            if value >= 55: return 2
            if value >= 40: return 3
            return 4
        
        if existing:
            # Update existing match
            response = supabase.table('matches')\
                .update({
                    'home_da': match_data['home_da'],
                    'away_da': match_data['away_da'],
                    'home_da_tier': calculate_tier(match_data['home_da']),
                    'away_da_tier': calculate_tier(match_data['away_da']),
                    'home_btts': match_data['home_btts'],
                    'away_btts': match_data['away_btts'],
                    'home_btts_tier': calculate_tier(match_data['home_btts']),
                    'away_btts_tier': calculate_tier(match_data['away_btts']),
                    'home_over': match_data['home_over'],
                    'away_over': match_data['away_over'],
                    'home_over_tier': calculate_tier(match_data['home_over']),
                    'away_over_tier': calculate_tier(match_data['away_over']),
                    'home_goals': match_data['home_goals'],
                    'away_goals': match_data['away_goals'],
                    'actual_goals': match_data['home_goals'] + match_data['away_goals'],
                    'actual_btts': match_data['home_goals'] > 0 and match_data['away_goals'] > 0,
                    'result_entered': True,
                    'btts_pressure_flag': match_data['btts_pressure_flag'],
                    'overs_pressure_flag': match_data['overs_pressure_flag'],
                    'rule_hits': match_data['rule_hits'],
                    'importance_score': match_data['importance_score']
                })\
                .eq('id', existing[0]['id'])\
                .execute()
        else:
            # Insert new match
            response = supabase.table('matches')\
                .insert({
                    'home_team': match_data['home_team'],
                    'away_team': match_data['away_team'],
                    'league': match_data['league'],
                    'match_date': match_data['match_date'].isoformat(),
                    'home_da': match_data['home_da'],
                    'away_da': match_data['away_da'],
                    'home_da_tier': calculate_tier(match_data['home_da']),
                    'away_da_tier': calculate_tier(match_data['away_da']),
                    'home_btts': match_data['home_btts'],
                    'away_btts': match_data['away_btts'],
                    'home_btts_tier': calculate_tier(match_data['home_btts']),
                    'away_btts_tier': calculate_tier(match_data['away_btts']),
                    'home_over': match_data['home_over'],
                    'away_over': match_data['away_over'],
                    'home_over_tier': calculate_tier(match_data['home_over']),
                    'away_over_tier': calculate_tier(match_data['away_over']),
                    'home_goals': match_data['home_goals'],
                    'away_goals': match_data['away_goals'],
                    'actual_goals': match_data['home_goals'] + match_data['away_goals'],
                    'actual_btts': match_data['home_goals'] > 0 and match_data['away_goals'] > 0,
                    'result_entered': True,
                    'btts_pressure_flag': match_data['btts_pressure_flag'],
                    'overs_pressure_flag': match_data['overs_pressure_flag'],
                    'rule_hits': match_data['rule_hits'],
                    'importance_score': match_data['importance_score'],
                    'created_at': datetime.now().isoformat()
                })\
                .execute()
        
        return True
        
    except Exception as e:
        st.error(f"Error saving match: {e}")
        return False

# ============================================================================
# PREDICTION ENGINE
# ============================================================================

class BettingPredictor:
    def __init__(self):
        self.BASELINE_BTTS = 0.50
        self.BASELINE_OVER = 0.48
        
        # Rule weights from database analysis
        self.RULE_WEIGHTS = {
            'rule_15': {
                'btts_lift': 0.190,
                'over_lift': 0.244,
                'confidence': 'HIGH',
                'sample': 29,
                'name': '👑 ELITE HOME = DRAW/AWAY WIN'
            },
            'rule_10': {
                'btts_lift': 0.167,
                'over_lift': 0.253,
                'confidence': 'MEDIUM',
                'sample': 15,
                'name': '⚠️ TIER2 HOME vs TIER3 AWAY = LOSS'
            },
            'rule_21': {
                'btts_lift': 0.214,
                'over_lift': 0.234,
                'confidence': 'MEDIUM',
                'sample': 14,
                'name': '🔥 TRIPLE CROWN = OVER 2.5'
            },
            'rule_7': {
                'btts_lift': -0.138,
                'over_lift': -0.045,
                'confidence': 'HIGH',
                'sample': 69,
                'name': '🔄 MIXED DEFENSE = WINNER'
            },
            'rule_2': {
                'btts_lift': -0.079,
                'over_lift': -0.033,
                'confidence': 'HIGH',
                'sample': 38,
                'name': '✈️ AWAY ELITE ATTACK = WINNER'
            },
            'rule_20_home': {
                'btts_lift': 0.063,
                'over_lift': 0.114,
                'confidence': 'HIGH',
                'sample': 32,
                'name': '🎯 HOME ELITE ATTACK = WIN/DRAW'
            },
            'rule_20_away': {
                'btts_lift': 0.000,
                'over_lift': 0.051,
                'confidence': 'HIGH',
                'sample': 32,
                'name': '🎯 AWAY ELITE ATTACK = WIN/DRAW'
            },
            'rule_1': {
                'btts_lift': 0.028,
                'over_lift': -0.258,
                'confidence': 'HIGH',
                'sample': 36,
                'name': '🐢 [4,4] DEFENSES = UNDER 2.5'
            },
            'rule_22': {
                'btts_lift': 0.000,
                'over_lift': -0.389,
                'confidence': 'HIGH',
                'sample': 22,
                'name': '🏆 GRAND UNIFIED = UNDER 2.5'
            }
        }
        
        self.SYNERGY_BONUS = {
            'OVER': 0.10,
            'UNDER': 0.15,
            'OUTCOME': 0.08
        }
    
    def predict(self, home_da, away_da, home_btts, away_btts, 
                btts_pressure_flag=False, overs_pressure_flag=False,
                rule_hits=None, importance_score=0):
        
        if rule_hits is None:
            rule_hits = {}
        
        btts_prob = self.BASELINE_BTTS
        over_prob = self.BASELINE_OVER
        evidence = []
        rule_categories = {}
        total_weight = 0
        
        # 1. Apply rule hits
        for rule_id, rule_data in rule_hits.items():
            if rule_data.get('hit') == True:
                rule = self.RULE_WEIGHTS.get(rule_id)
                if rule:
                    confidence_weight = 1.0 if rule['confidence'] == 'HIGH' else 0.7 if rule['confidence'] == 'MEDIUM' else 0.4
                    
                    btts_prob += rule['btts_lift'] * confidence_weight
                    over_prob += rule['over_lift'] * confidence_weight
                    total_weight += confidence_weight
                    
                    # Determine category from rule_id
                    category = 'OUTCOME'
                    if rule_id in ['rule_1', 'rule_8', 'rule_22']:
                        category = 'UNDER'
                    elif rule_id in ['rule_21']:
                        category = 'OVER'
                    
                    rule_categories[category] = rule_categories.get(category, 0) + 1
                    
                    evidence.append({
                        'factor': rule['name'],
                        'impact': f"{rule['btts_lift']*100:.1f}% BTTS, {rule['over_lift']*100:.1f}% Over",
                        'confidence': rule['confidence'],
                        'sample_size': rule['sample']
                    })
        
        # 2. Apply synergy bonuses
        for category, count in rule_categories.items():
            if count >= 2 and category in self.SYNERGY_BONUS:
                if category == 'OVER':
                    over_prob += self.SYNERGY_BONUS['OVER']
                    evidence.append({
                        'factor': '✨ OVER SYNERGY',
                        'impact': f"+{self.SYNERGY_BONUS['OVER']*100:.0f}% to Over ({count} OVER rules)",
                        'confidence': 'HIGH'
                    })
                elif category == 'UNDER':
                    over_prob -= self.SYNERGY_BONUS['UNDER']
                    evidence.append({
                        'factor': '🛡️ UNDER SYNERGY',
                        'impact': f"-{self.SYNERGY_BONUS['UNDER']*100:.0f}% to Over ({count} UNDER rules)",
                        'confidence': 'HIGH'
                    })
        
        # 3. Pressure flags
        if btts_pressure_flag:
            btts_prob += 0.12
            evidence.append({
                'factor': 'BTTS Pressure Flag',
                'impact': '+12% to BTTS',
                'confidence': 'HIGH'
            })
        
        if overs_pressure_flag:
            over_prob += 0.10
            evidence.append({
                'factor': 'Overs Pressure Flag',
                'impact': '+10% to Over 2.5',
                'confidence': 'HIGH'
            })
        
        # 4. Attack strength from DA inputs
        avg_attack = ((home_da or 50) + (away_da or 50)) / 200
        btts_prob += (avg_attack - 0.5) * 0.2
        over_prob += (avg_attack - 0.5) * 0.25
        
        # 5. Importance score
        if importance_score >= 2:
            over_prob += 0.10
            btts_prob += 0.05
            evidence.append({
                'factor': 'High Importance Match (Derby/Playoff)',
                'impact': '+10% to Over, +5% to BTTS',
                'confidence': 'HIGH'
            })
        elif importance_score >= 1:
            over_prob += 0.05
            evidence.append({
                'factor': 'Important Match',
                'impact': '+5% to Over',
                'confidence': 'MEDIUM'
            })
        
        # Clamp probabilities
        btts_prob = max(0.10, min(0.90, btts_prob))
        over_prob = max(0.10, min(0.90, over_prob))
        
        # Overall confidence
        if total_weight > 2 or (btts_pressure_flag and overs_pressure_flag):
            overall_confidence = 'HIGH'
        elif total_weight > 1:
            overall_confidence = 'MEDIUM'
        else:
            overall_confidence = 'LOW'
        
        return {
            'btts': {
                'probability': round(btts_prob, 3),
                'edge': round(btts_prob - self.BASELINE_BTTS, 3),
                'confidence': overall_confidence
            },
            'over_2_5': {
                'probability': round(over_prob, 3),
                'edge': round(over_prob - self.BASELINE_OVER, 3),
                'confidence': overall_confidence
            },
            'evidence': evidence[:5],
            'rule_count': len(rule_hits)
        }

# ============================================================================
# UI COMPONENTS
# ============================================================================

def probability_gauge(prob, title, edge=None):
    """Create a probability gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=prob * 100,
        title={'text': title, 'font': {'size': 16}},
        delta={'reference': 50, 'position': "top"} if edge else None,
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "darkblue" if prob > 0.6 else "darkred" if prob < 0.4 else "darkorange"},
            'steps': [
                {'range': [0, 30], 'color': "lightcoral"},
                {'range': [30, 50], 'color': "lightyellow"},
                {'range': [50, 70], 'color': "lightgreen"},
                {'range': [70, 100], 'color': "darkgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    return fig

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Football Betting Predictor",
        page_icon="⚽",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1E3A8A;
            text-align: center;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2563EB;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        .rule-highlight {
            background-color: #EFF6FF;
            padding: 0.5rem;
            border-left: 4px solid #3B82F6;
            margin: 0.5rem 0;
            border-radius: 4px;
        }
        .stButton button {
            width: 100%;
            background-color: #3B82F6;
            color: white;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">⚽ FOOTBALL BETTING PREDICTOR</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Initialize session state
    if 'predictor' not in st.session_state:
        st.session_state.predictor = BettingPredictor()
    
    # Main input form
    with st.form("match_input_form"):
        st.markdown('<div class="sub-header">📝 MANUAL MATCH DATA INPUT</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            home_team = st.text_input("🏠 Home Team", value="", placeholder="e.g., Arsenal")
            match_date = st.date_input("📅 Match Date", datetime.now())
            
        with col2:
            away_team = st.text_input("✈️ Away Team", value="", placeholder="e.g., Chelsea")
            league = st.text_input("🏆 League", value="", placeholder="e.g., PREMIER LEAGUE")
        
        st.markdown("---")
        st.markdown("### ⚡ DANGEROUS ATTACK (DA) - Enter values 0-100")
        
        col1, col2 = st.columns(2)
        
        with col1:
            home_da = st.number_input("Home DA", min_value=0, max_value=100, value=50, step=1,
                                     help="Higher values = more dangerous attacks")
        
        with col2:
            away_da = st.number_input("Away DA", min_value=0, max_value=100, value=50, step=1,
                                     help="Higher values = more dangerous attacks")
        
        st.markdown("---")
        st.markdown("### 🎯 BOTH TEAMS TO SCORE (BTTS)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            btts_prediction = st.radio("BTTS Prediction", ["YES", "NO"], horizontal=True, index=0)
        
        with col2:
            home_btts = st.number_input("Home BTTS %", min_value=0, max_value=100, value=50, step=1,
                                       help="Confidence that Home team will score")
        
        with col3:
            away_btts = st.number_input("Away BTTS %", min_value=0, max_value=100, value=50, step=1,
                                       help="Confidence that Away team will score")
        
        st.markdown("---")
        st.markdown("### ⚽ OVER/UNDER")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            over_line = st.selectbox("Over Line", [0.5, 1.5, 2.5, 3.5, 4.5], index=2)
        
        with col2:
            over_prediction = st.radio("Over/Under", ["OVER", "UNDER"], horizontal=True, index=0)
        
        with col3:
            over_value = st.number_input("Over %", min_value=0, max_value=100, value=50, step=1,
                                       help="Confidence for Over")
        
        st.markdown("---")
        st.markdown("### ⚽ FINAL SCORE (Enter after match)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            home_goals = st.number_input("Home Goals", min_value=0, max_value=20, value=0, step=1)
        
        with col2:
            away_goals = st.number_input("Away Goals", min_value=0, max_value=20, value=0, step=1)
        
        st.markdown("---")
        
        # Submit buttons
        col1, col2 = st.columns(2)
        
        with col1:
            generate_pred = st.form_submit_button("🔮 GENERATE PREDICTION", use_container_width=True)
        
        with col2:
            save_match = st.form_submit_button("💾 SAVE TO DATABASE", use_container_width=True)
    
    # Handle form submission
    if generate_pred:
        with st.spinner("Analyzing match data..."):
            
            # Automatically determine pressure flags
            btts_pressure, overs_pressure = check_pressure_flags(
                home_da, away_da, home_btts, away_btts, over_value, over_value
            )
            
            # Prepare match data for rule checking
            match_check_data = {
                'home_da': home_da,
                'away_da': away_da,
                'home_btts': home_btts,
                'away_btts': away_btts,
                'home_over': over_value,
                'away_over': over_value
            }
            
            # Automatically check which rules apply
            rule_hits = check_rule_hits(match_check_data)
            
            # Get importance score from database
            importance_score = get_importance_score(home_team, away_team, league)
            
            # Generate prediction
            prediction = st.session_state.predictor.predict(
                home_da=float(home_da),
                away_da=float(away_da),
                home_btts=float(home_btts),
                away_btts=float(away_btts),
                btts_pressure_flag=btts_pressure,
                overs_pressure_flag=overs_pressure,
                rule_hits=rule_hits,
                importance_score=importance_score
            )
            
            # Store in session state
            st.session_state.current_prediction = prediction
            st.session_state.auto_detected = {
                'btts_pressure': btts_pressure,
                'overs_pressure': overs_pressure,
                'rule_hits': rule_hits,
                'importance_score': importance_score
            }
            
            st.rerun()
    
    if save_match:
        if not home_team or not away_team:
            st.error("Please enter both team names")
        else:
            # Automatically determine everything for saving
            btts_pressure, overs_pressure = check_pressure_flags(
                home_da, away_da, home_btts, away_btts, over_value, over_value
            )
            
            match_check_data = {
                'home_da': home_da,
                'away_da': away_da,
                'home_btts': home_btts,
                'away_btts': away_btts,
                'home_over': over_value,
                'away_over': over_value
            }
            
            rule_hits = check_rule_hits(match_check_data)
            importance_score = get_importance_score(home_team, away_team, league)
            
            # Prepare match data
            match_data = {
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'league': league.strip() if league else "MANUAL ENTRY",
                'match_date': match_date,
                'home_da': float(home_da),
                'away_da': float(away_da),
                'home_btts': float(home_btts),
                'away_btts': float(away_btts),
                'home_over': float(over_value),
                'away_over': float(over_value),
                'home_goals': int(home_goals),
                'away_goals': int(away_goals),
                'btts_pressure_flag': btts_pressure,
                'overs_pressure_flag': overs_pressure,
                'rule_hits': rule_hits,
                'importance_score': importance_score
            }
            
            # Save to database
            if save_match_data(match_data):
                st.success(f"✅ Match saved successfully!")
    
    # Display prediction and auto-detected info
    if st.session_state.get('current_prediction'):
        st.markdown("---")
        
        # Show auto-detected information
        if st.session_state.get('auto_detected'):
            auto = st.session_state.auto_detected
            
            st.markdown('<div class="sub-header">🔍 AUTO-DETECTED FACTORS</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏁 PRESSURE FLAGS**")
                if auto['btts_pressure']:
                    st.success("✅ BTTS Pressure Flag: ACTIVE")
                else:
                    st.info("BTTS Pressure Flag: Inactive")
                    
                if auto['overs_pressure']:
                    st.success("✅ Overs Pressure Flag: ACTIVE")
                else:
                    st.info("Overs Pressure Flag: Inactive")
            
            with col2:
                st.markdown("**⭐ IMPORTANCE SCORE**")
                if auto['importance_score'] == 2:
                    st.error("🔥 DERBY / PLAYOFF MATCH")
                elif auto['importance_score'] == 1:
                    st.warning("⚠️ Important Match")
                else:
                    st.info("Regular Match")
            
            st.markdown("**📋 ACTIVE RULES**")
            if auto['rule_hits']:
                for rule_id, rule_data in auto['rule_hits'].items():
                    st.markdown(f"""
                    <div class="rule-highlight">
                        <strong>{rule_data['name']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No rules activated for this match")
        
        st.markdown("---")
        
        # Show prediction
        pred = st.session_state.current_prediction
        
        st.markdown('<div class="sub-header">🔮 PREDICTION RESULTS</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(
                probability_gauge(pred['btts']['probability'], "BTTS PROBABILITY"),
                use_container_width=True
            )
            st.metric("Edge vs 50%", f"{pred['btts']['edge']*100:+.1f}%")
        
        with col2:
            st.plotly_chart(
                probability_gauge(pred['over_2_5']['probability'], "OVER 2.5 PROBABILITY"),
                use_container_width=True
            )
            st.metric("Edge vs 48%", f"{pred['over_2_5']['edge']*100:+.1f}%")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            conf_color = {'HIGH': '🟢', 'MEDIUM': '🟡', 'LOW': '🔴'}.get(pred['btts']['confidence'], '⚪')
            st.markdown(f"**BTTS Confidence:** {conf_color} {pred['btts']['confidence']}")
        
        with col2:
            conf_color = {'HIGH': '🟢', 'MEDIUM': '🟡', 'LOW': '🔴'}.get(pred['over_2_5']['confidence'], '⚪')
            st.markdown(f"**Over Confidence:** {conf_color} {pred['over_2_5']['confidence']}")
        
        with col3:
            st.markdown(f"**Active Rules:** {pred['rule_count']}")
        
        if pred['evidence']:
            st.markdown("---")
            st.markdown("### 🕵️ KEY FACTORS")
            for evidence in pred['evidence']:
                conf_icon = {'HIGH': '🟢', 'MEDIUM': '🟡', 'LOW': '🔴'}.get(evidence.get('confidence', 'LOW'), '⚪')
                st.markdown(f"""
                <div class="rule-highlight">
                    <strong>{evidence['factor']}</strong><br>
                    Impact: {evidence['impact']} {conf_icon}<br>
                    <small>Sample: {evidence.get('sample_size', 'N/A')} matches</small>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
