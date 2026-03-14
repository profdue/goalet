import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import json

# Supabase connection
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Run: pip install supabase")

st.set_page_config(
    page_title="⚽ Betting Intelligence v24.0", 
    page_icon="🏆", 
    layout="wide"
)

if SUPABASE_AVAILABLE:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
else:
    supabase = None

# ============================================================================
# PATTERN CODE TRANSLATION
# ============================================================================

def translate_pattern_code(pattern_code):
    """Convert pattern code like 'F,T,F,0' to human-readable description"""
    try:
        parts = pattern_code.split(',')
        if len(parts) != 4:
            return pattern_code
        
        home = "🏠 Home Advantage" if parts[0] == 'T' else "✈️ No Home Advantage"
        btts = "⚽ BTTS Pressure" if parts[2] == 'T' else "🧤 No BTTS Pressure"
        overs = "🔥 Overs Pressure" if parts[1] == 'T' else "❄️ No Overs Pressure"
        
        importance = {
            '0': 'Low Importance',
            '1': 'Medium Importance',
            '2': 'High Importance'
        }.get(parts[3], f"Importance:{parts[3]}")
        
        # Pattern descriptions based on actual performance data
        pattern_descriptions = {
            'T,T,T,1': {
                'name': '🔥 Triple Threat',
                'outcome': 'OVER 2.5 / BTTS / HOME WIN',
                'description': 'All pressures + medium importance = goal fest with home advantage'
            },
            'T,F,F,1': {
                'name': '🏠 Fortress Home',
                'outcome': 'HOME WIN (Low Scoring)',
                'description': 'Home advantage only = defensive home wins'
            },
            'F,T,T,2': {
                'name': '⚽ Away Goal Fest',
                'outcome': 'AWAY WIN / BTTS / OVER 2.5',
                'description': 'Away bias + importance = guaranteed goals'
            },
            'T,T,T,2': {
                'name': '💥 Perfect Storm',
                'outcome': 'OVER 2.5 / BTTS',
                'description': 'High stakes + all pressures = goal explosion'
            },
            'F,F,F,0': {
                'name': '⚖️ Balanced',
                'outcome': 'BTTS Likely',
                'description': 'No clear advantage = both teams score'
            },
            'T,T,T,0': {
                'name': '🎯 Pressure Cooker',
                'outcome': 'HOME WIN / BTTS',
                'description': 'All pressures but low stakes = home win with goals'
            },
            'F,T,T,0': {
                'name': '✈️ Away Attack',
                'outcome': 'NO DRAW (Away Bias)',
                'description': 'Away pressure = away win or loss'
            },
            'T,F,T,1': {
                'name': '🏠⚽ Home BTTS',
                'outcome': 'BTTS / HOME WIN',
                'description': 'Home advantage + BTTS pressure = home goals'
            }
        }
        
        default = {
            'name': f"{pattern_code} Pattern",
            'outcome': 'Track this pattern',
            'description': f"{home} • {btts} • {overs} • {importance}"
        }
        
        pattern_info = pattern_descriptions.get(pattern_code, default)
        
        return {
            'code': pattern_code,
            'name': pattern_info['name'],
            'description': pattern_info['description'],
            'outcome': pattern_info['outcome'],
            'flags': f"{home} • {btts} • {overs} • {importance}"
        }
    except:
        return {
            'code': pattern_code, 
            'name': pattern_code, 
            'description': pattern_code, 
            'outcome': 'Unknown',
            'flags': pattern_code
        }

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_gold_patterns():
    """Get promoted gold patterns with their stats"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table('gold_patterns')\
            .select('*')\
            .eq('status', 'ACTIVE')\
            .order('confidence_tier', desc=True)\
            .execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            # Add human-readable descriptions
            df['display_name'] = df['pattern_code'].apply(
                lambda x: translate_pattern_code(x)['name']
            )
            df['outcome'] = df['pattern_code'].apply(
                lambda x: translate_pattern_code(x)['outcome']
            )
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error getting gold patterns: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_pattern_prediction(pattern_code):
    """Get prediction from pattern_tracking for a specific pattern"""
    if supabase is None:
        return None
    
    try:
        result = supabase.table('pattern_tracking')\
            .select('*')\
            .eq('pattern_code', pattern_code)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        return None

def save_match(data, home_goals=None, away_goals=None):
    """Save match to database with result if provided"""
    if supabase is None:
        return None
    
    try:
        match_data = {
            'home_team': data['home_team'].strip(),
            'away_team': data['away_team'].strip(),
            'league': data['league'],
            'match_date': data.get('match_date', datetime.now().date().isoformat()),
            'home_da': data['home_da'],
            'away_da': data['away_da'],
            'home_btts': data['home_btts'],
            'away_btts': data['away_btts'],
            'home_over': data['home_over'],
            'away_over': data['away_over'],
            'elite': data.get('elite', False),
            'derby': data.get('derby', False),
            'relegation': data.get('relegation', False),
            'result_entered': home_goals is not None,
            'discovery_notes': data.get('notes', '')
        }
        
        if home_goals is not None:
            match_data['home_goals'] = home_goals
            match_data['away_goals'] = away_goals
        
        result = supabase.table('matches').insert(match_data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
            
    except Exception as e:
        st.error(f"Error saving match: {e}")
        return None

@st.cache_data(ttl=60)
def get_emerging_patterns(min_confidence=30):
    """Get emerging patterns from pattern_tracking"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table('pattern_tracking')\
            .select('*')\
            .eq('is_emerging', True)\
            .gte('confidence_score', min_confidence)\
            .order('confidence_score', desc=True)\
            .execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            df['display_name'] = df['pattern_code'].apply(
                lambda x: translate_pattern_code(x)['name']
            )
            df['outcome'] = df['pattern_code'].apply(
                lambda x: translate_pattern_code(x)['outcome']
            )
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def get_recent_matches(limit=20):
    """Get recent matches with results"""
    if supabase is None:
        return []
    
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)\
            .order('match_date', desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        return []

# ============================================================================
# PREDICTION ENGINE
# ============================================================================

def get_prediction_from_db(pattern_code):
    """Get prediction stats from pattern_tracking"""
    pattern_stats = get_pattern_prediction(pattern_code)
    
    if pattern_stats:
        return {
            'confidence': pattern_stats.get('confidence_score', 50),
            'matches': pattern_stats.get('total_matches', 0),
            'home_win_rate': pattern_stats.get('current_home_win_rate', 50),
            'over_rate': pattern_stats.get('current_over_rate', 50),
            'btts_rate': pattern_stats.get('current_btts_rate', 50),
            'is_emerging': pattern_stats.get('is_emerging', False)
        }
    return None

def analyze_match(match_data):
    """Analyze match and return prediction with database stats"""
    
    # Calculate pattern code (matches what DB trigger does)
    home_adv_flag = match_data.get('home_adv_flag', False)
    overs_flag = match_data.get('overs_pressure_flag', False)
    btts_flag = match_data.get('btts_pressure_flag', False)
    importance = match_data.get('importance_score', 0)
    
    pattern_code = f"{'T' if home_adv_flag else 'F'},{'T' if overs_flag else 'F'},{'T' if btts_flag else 'F'},{importance}"
    
    # Get pattern info
    pattern_info = translate_pattern_code(pattern_code)
    
    # Get database stats if available
    db_stats = get_prediction_from_db(pattern_code)
    
    # Build prediction
    prediction = {
        'pattern_code': pattern_code,
        'pattern_name': pattern_info['name'],
        'pattern_description': pattern_info['description'],
        'predicted_outcome': pattern_info['outcome'],
        'flags': pattern_info['flags'],
        'has_db_stats': db_stats is not None
    }
    
    if db_stats:
        prediction.update({
            'confidence': db_stats['confidence'],
            'sample_size': db_stats['matches'],
            'historical_home_win': db_stats['home_win_rate'],
            'historical_over': db_stats['over_rate'],
            'historical_btts': db_stats['btts_rate'],
            'is_emerging': db_stats['is_emerging']
        })
    else:
        # Default stats for new patterns
        prediction.update({
            'confidence': 50,
            'sample_size': 0,
            'historical_home_win': 50,
            'historical_over': 50,
            'historical_btts': 50,
            'is_emerging': False
        })
    
    return prediction

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🏆 Betting Intelligence Platform v24.0")
    st.markdown("### Self-Learning Pattern Recognition • Live Performance Tracking")
    
    if not SUPABASE_AVAILABLE or supabase is None:
        st.error("Supabase connection failed. Check your secrets and installation.")
        return
    
    # Sidebar stats
    with st.sidebar:
        st.header("📊 Live Stats")
        try:
            total = supabase.table('matches').select('*', count='exact').execute()
            gold = supabase.table('gold_patterns').select('*', count='exact').eq('status', 'ACTIVE').execute()
            emerging = supabase.table('pattern_tracking').select('*', count='exact').eq('is_emerging', True).execute()
            
            st.metric("Total Matches", total.count if hasattr(total, 'count') else 0)
            st.metric("Gold Patterns", gold.count if hasattr(gold, 'count') else 0)
            st.metric("Emerging Patterns", emerging.count if hasattr(emerging, 'count') else 0)
            
            st.markdown("---")
            st.markdown("**🎯 BETTING KEY**")
            st.markdown("🔥 OVER 2.5 | ❄️ UNDER 2.5")
            st.markdown("🏠 HOME WIN | ✈️ AWAY WIN | ⚖️ DRAW")
            st.markdown("⚽ BTTS | 🧤 NO BTTS")
            
        except Exception as e:
            st.info("No data yet")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 NEW MATCH", 
        "🏆 GOLD PATTERNS", 
        "📈 EMERGING PATTERNS",
        "📊 RECENT RESULTS"
    ])
    
    # ===== TAB 1: NEW MATCH =====
    with tab1:
        st.header("🔍 Enter New Match")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("match_form"):
                # Teams
                col_home, col_away = st.columns(2)
                with col_home:
                    st.markdown("**🏠 HOME**")
                    home_team = st.text_input("Team Name", key="home_team")
                with col_away:
                    st.markdown("**✈️ AWAY**")
                    away_team = st.text_input("Team Name", key="away_team")
                
                # Stats
                col1a, col1b, col1c = st.columns(3)
                with col1a:
                    st.markdown("**Defensive Action (DA)**")
                    home_da = st.number_input("Home DA", 0, 100, 50, key="home_da")
                    away_da = st.number_input("Away DA", 0, 100, 50, key="away_da")
                
                with col1b:
                    st.markdown("**BTTS %**")
                    home_btts = st.number_input("Home BTTS", 0, 100, 50, key="home_btts")
                    away_btts = st.number_input("Away BTTS", 0, 100, 50, key="away_btts")
                
                with col1c:
                    st.markdown("**Over 2.5 %**")
                    home_over = st.number_input("Home Over", 0, 100, 50, key="home_over")
                    away_over = st.number_input("Away Over", 0, 100, 50, key="away_over")
                
                # Match context
                col2a, col2b, col2c = st.columns(3)
                with col2a:
                    elite = st.checkbox("⭐ Elite Match")
                with col2b:
                    derby = st.checkbox("🏆 Derby")
                with col2c:
                    relegation = st.checkbox("⚠️ Relegation Battle")
                
                # League
                league = st.selectbox(
                    "League",
                    ["EPL", "LA LIGA", "BUNDESLIGA", "SERIE A", "LIGUE 1", "CHAMPIONSHIP", "OTHER"],
                    key="league"
                )
                
                if league == "OTHER":
                    custom_league = st.text_input("Enter League Name")
                    if custom_league:
                        league = custom_league.upper()
                
                notes = st.text_input("Match Notes (optional)", key="notes")
                
                analyze_btn = st.form_submit_button("🔮 ANALYZE MATCH", use_container_width=True)
        
        with col2:
            st.markdown("**📋 Quick Tips**")
            st.info("""
            **DA (Defensive Action)** - Higher = Better defense
            - 75+ = Elite (Tier 1)
            - 60-74 = Strong (Tier 2)
            - 40-59 = Average (Tier 3)
            - <40 = Weak (Tier 4)
            
            **BTTS/Over %** - Higher = More likely
            - 70+ = Elite Attack
            - 55-69 = Strong Attack
            - 40-54 = Average
            - <40 = Weak Attack
            """)
        
        # Analysis and results section
        if 'match_analyzed' not in st.session_state:
            st.session_state.match_analyzed = None
        
        if analyze_btn:
            if not home_team or not away_team:
                st.error("Please enter both team names")
            else:
                # Calculate flags (matching database logic)
                home_da_tier = 1 if home_da >= 75 else 2 if home_da >= 60 else 3 if home_da >= 40 else 4
                away_da_tier = 1 if away_da >= 75 else 2 if away_da >= 60 else 3 if away_da >= 40 else 4
                home_btts_tier = 1 if home_btts >= 70 else 2 if home_btts >= 55 else 3 if home_btts >= 40 else 4
                away_btts_tier = 1 if away_btts >= 70 else 2 if away_btts >= 55 else 3 if away_btts >= 40 else 4
                home_over_tier = 1 if home_over >= 70 else 2 if home_over >= 55 else 3 if home_over >= 40 else 4
                away_over_tier = 1 if away_over >= 70 else 2 if away_over >= 55 else 3 if away_over >= 40 else 4
                
                match_data = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league,
                    'match_date': datetime.now().date().isoformat(),
                    'home_da': home_da,
                    'away_da': away_da,
                    'home_btts': home_btts,
                    'away_btts': away_btts,
                    'home_over': home_over,
                    'away_over': away_over,
                    'elite': elite,
                    'derby': derby,
                    'relegation': relegation,
                    'notes': notes,
                    'home_adv_flag': home_da_tier < away_da_tier,
                    'btts_pressure_flag': (home_btts_tier <= 2 and away_da_tier >= 3) or (away_btts_tier <= 2 and home_da_tier >= 3) or elite or derby,
                    'overs_pressure_flag': (home_over_tier <= 2 and away_da_tier >= 3) or (away_over_tier <= 2 and home_da_tier >= 3),
                    'importance_score': (1 if elite else 0) + (1 if derby else 0) + (1 if relegation else 0)
                }
                
                prediction = analyze_match(match_data)
                st.session_state.match_analyzed = {
                    'match_data': match_data,
                    'prediction': prediction
                }
        
        # Display prediction if available
        if st.session_state.match_analyzed:
            match_data = st.session_state.match_analyzed['match_data']
            pred = st.session_state.match_analyzed['prediction']
            
            st.markdown("---")
            
            # Prediction card
            col_pred1, col_pred2 = st.columns([2, 1])
            
            with col_pred1:
                confidence_color = "green" if pred['confidence'] >= 70 else "orange" if pred['confidence'] >= 50 else "red"
                
                st.markdown(f"""
                <div style="background-color: #1e3a5f; padding: 25px; border-radius: 10px; border-left: 5px solid #4CAF50;">
                    <h2 style="color: white; margin: 0;">{pred['pattern_name']}</h2>
                    <p style="color: #ddd; font-size: 18px; margin: 10px 0;">{pred['pattern_description']}</p>
                    <p style="color: #ffd700; font-size: 24px; font-weight: bold; margin: 10px 0;">🎯 {pred['predicted_outcome']}</p>
                    <p style="color: #ddd; font-size: 14px;">{pred['flags']}</p>
                    <div style="background-color: #2a4a7a; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h3 style="color: white; margin: 0 0 10px 0;">📊 Pattern History</h3>
                        <div style="display: flex; gap: 20px;">
                            <div><span style="color: #ddd;">Confidence:</span> <span style="color: {confidence_color}; font-weight: bold; font-size: 20px;">{pred['confidence']:.1f}%</span></div>
                            <div><span style="color: #ddd;">Sample:</span> <span style="color: white; font-weight: bold;">{pred['sample_size']} matches</span></div>
                        </div>
                        <div style="display: flex; gap: 20px; margin-top: 10px;">
                            <div><span style="color: #ddd;">🏠 Home Win:</span> <span style="color: white;">{pred['historical_home_win']:.1f}%</span></div>
                            <div><span style="color: #ddd;">🔥 Over 2.5:</span> <span style="color: white;">{pred['historical_over']:.1f}%</span></div>
                            <div><span style="color: #ddd;">⚽ BTTS:</span> <span style="color: white;">{pred['historical_btts']:.1f}%</span></div>
                        </div>
                    </div>
                    <p style="color: #aaa; font-size: 12px; margin: 10px 0 0 0;">Pattern Code: {pred['pattern_code']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_pred2:
                st.markdown("**📋 Match Context**")
                context_data = {
                    "League": match_data['league'],
                    "Home DA Tier": "T1" if match_data['home_da'] >= 75 else "T2" if match_data['home_da'] >= 60 else "T3" if match_data['home_da'] >= 40 else "T4",
                    "Away DA Tier": "T1" if match_data['away_da'] >= 75 else "T2" if match_data['away_da'] >= 60 else "T3" if match_data['away_da'] >= 40 else "T4",
                    "Importance": ["Low", "Medium", "High"][min(match_data['importance_score'], 2)],
                    "Home Advantage": "✅" if match_data['home_adv_flag'] else "❌",
                    "BTTS Pressure": "✅" if match_data['btts_pressure_flag'] else "❌",
                    "Overs Pressure": "✅" if match_data['overs_pressure_flag'] else "❌"
                }
                
                for key, value in context_data.items():
                    st.markdown(f"**{key}:** {value}")
            
            # Enter result
            st.markdown("---")
            st.subheader("📥 Enter Match Result")
            
            col_res1, col_res2, col_res3 = st.columns([1, 1, 2])
            
            with col_res1:
                home_goals = st.number_input(f"{match_data['home_team']} Goals", 0, 20, 0, key="home_goals_result")
            
            with col_res2:
                away_goals = st.number_input(f"{match_data['away_team']} Goals", 0, 20, 0, key="away_goals_result")
            
            with col_res3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 SAVE MATCH & UPDATE PATTERNS", type="primary", use_container_width=True):
                    saved_match = save_match(match_data, home_goals, away_goals)
                    
                    if saved_match:
                        st.success(f"✅ Match #{saved_match['id']} saved! Pattern tracking updated automatically.")
                        st.balloons()
                        
                        # Clear cache to refresh data
                        st.cache_data.clear()
                        st.session_state.match_analyzed = None
                        st.rerun()
    
    # ===== TAB 2: GOLD PATTERNS =====
    with tab2:
        st.header("🏆 Gold Patterns - Proven & Promoted")
        
        gold_patterns = get_gold_patterns()
        
        if not gold_patterns.empty:
            # Summary metrics
            col_g1, col_g2, col_g3 = st.columns(3)
            col_g1.metric("Total Gold Patterns", len(gold_patterns))
            col_g2.metric("HIGH Confidence", len(gold_patterns[gold_patterns['confidence_tier'] == 'HIGH']))
            col_g3.metric("PLATINUM Tier", len(gold_patterns[gold_patterns['confidence_tier'].isin(['PLATINUM', 'HIGH'])]))
            
            # Display gold patterns
            for _, pattern in gold_patterns.iterrows():
                with st.container():
                    tier_color = {
                        'PLATINUM': '#e5e4e2',
                        'HIGH': '#ffd700',
                        'MEDIUM': '#c0c0c0',
                        'LOW': '#cd7f32'
                    }.get(pattern.get('confidence_tier', 'LOW'), '#ffffff')
                    
                    st.markdown(f"""
                    <div style="background-color: #1e3a5f; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid {tier_color};">
                        <div style="display: flex; justify-content: space-between;">
                            <h3 style="color: white; margin: 0;">{pattern.get('display_name', pattern['pattern_code'])}</h3>
                            <span style="background-color: {tier_color}; color: black; padding: 5px 10px; border-radius: 5px; font-weight: bold;">{pattern.get('confidence_tier', 'NEW')}</span>
                        </div>
                        <p style="color: #ffd700; font-size: 18px; margin: 10px 0;">🎯 {pattern.get('outcome', 'Unknown')}</p>
                        <p style="color: #ddd;">{pattern.get('pattern_name', '')}</p>
                        <div style="display: flex; gap: 20px; margin-top: 10px;">
                            <div><span style="color: #aaa;">Matches:</span> <span style="color: white;">{pattern.get('discovery_sample_size', 0)}</span></div>
                            <div><span style="color: #aaa;">Home Win:</span> <span style="color: white;">{pattern.get('discovery_home_win_rate', 0):.1f}%</span></div>
                            <div><span style="color: #aaa;">Over 2.5:</span> <span style="color: white;">{pattern.get('discovery_over_rate', 0):.1f}%</span></div>
                            <div><span style="color: #aaa;">BTTS:</span> <span style="color: white;">{pattern.get('discovery_btts_rate', 0):.1f}%</span></div>
                        </div>
                        <p style="color: #aaa; font-size: 12px; margin-top: 10px;">Code: {pattern['pattern_code']} | Promoted: {pattern.get('promotion_date', 'Unknown')[:10]}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No gold patterns promoted yet. Add more matches to discover patterns!")
    
    # ===== TAB 3: EMERGING PATTERNS =====
    with tab3:
        st.header("📈 Emerging Patterns - Under Review")
        
        min_confidence = st.slider("Minimum Confidence", 0, 100, 30, key="emerging_conf")
        emerging = get_emerging_patterns(min_confidence)
        
        if not emerging.empty:
            for _, pattern in emerging.iterrows():
                with st.container():
                    confidence = pattern.get('confidence_score', 0)
                    conf_color = "green" if confidence >= 70 else "orange" if confidence >= 50 else "red"
                    
                    st.markdown(f"""
                    <div style="background-color: #2a2a4a; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #ffd700;">
                        <h3 style="color: white; margin: 0;">{pattern.get('display_name', pattern['pattern_code'])}</h3>
                        <p style="color: #ffd700; font-size: 16px;">🎯 {pattern.get('outcome', 'Tracking')}</p>
                        <div style="display: flex; gap: 30px; margin: 15px 0;">
                            <div><span style="color: #aaa;">Confidence:</span> <span style="color: {conf_color}; font-weight: bold;">{confidence:.1f}%</span></div>
                            <div><span style="color: #aaa;">Matches:</span> <span style="color: white;">{pattern.get('total_matches', 0)}</span></div>
                            <div><span style="color: #aaa;">Home Win:</span> <span style="color: white;">{pattern.get('current_home_win_rate', 0):.1f}%</span></div>
                            <div><span style="color: #aaa;">Over 2.5:</span> <span style="color: white;">{pattern.get('current_over_rate', 0):.1f}%</span></div>
                            <div><span style="color: #aaa;">BTTS:</span> <span style="color: white;">{pattern.get('current_btts_rate', 0):.1f}%</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Chart
            fig = px.scatter(
                emerging, 
                x='total_matches', 
                y='confidence_score',
                size='confidence_score',
                color='current_home_win_rate',
                hover_data=['pattern_code', 'current_over_rate', 'current_btts_rate'],
                title='Emerging Patterns - Confidence vs Sample Size'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No emerging patterns with confidence >= {min_confidence}%")
    
    # ===== TAB 4: RECENT RESULTS =====
    with tab4:
        st.header("📊 Recent Match Results")
        
        recent = get_recent_matches(50)
        
        if recent:
            df = pd.DataFrame(recent)
            
            # Summary stats
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Matches", len(df))
            col_r2.metric("Avg Goals", f"{df['actual_goals'].mean():.2f}")
            col_r3.metric("BTTS Rate", f"{df['actual_btts'].mean() * 100:.1f}%")
            col_r4.metric("Over 2.5 Rate", f"{(df['actual_goals'] >= 3).mean() * 100:.1f}%")
            
            # Display recent matches
            display_df = df[['match_date', 'home_team', 'away_team', 'home_goals', 'away_goals', 
                           'actual_goals', 'actual_btts', 'pattern_code']].copy()
            
            display_df['result'] = display_df.apply(
                lambda x: f"{int(x['home_goals'])}-{int(x['away_goals'])}", axis=1
            )
            display_df['btts'] = display_df['actual_btts'].apply(lambda x: "✅" if x else "❌")
            
            st.dataframe(
                display_df[['match_date', 'home_team', 'away_team', 'result', 'actual_goals', 'btts', 'pattern_code']],
                hide_index=True,
                use_container_width=True
            )
            
            # Pattern performance chart
            pattern_perf = df.groupby('pattern_code').agg({
                'id': 'count',
                'actual_btts': 'mean',
                'actual_goals': lambda x: (x >= 3).mean()
            }).round(3) * 100
            
            pattern_perf.columns = ['Matches', 'BTTS %', 'Over %']
            pattern_perf = pattern_perf[pattern_perf['Matches'] >= 3].sort_values('BTTS %', ascending=False).head(10)
            
            if not pattern_perf.empty:
                st.subheader("🔥 Hot Patterns (Last 50 Matches)")
                st.dataframe(pattern_perf, use_container_width=True)
        else:
            st.info("No recent matches with results")

if __name__ == "__main__":
    main()
