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

st.set_page_config(page_title="Discovery Hunter v24.0", page_icon="🏆", layout="wide")

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
        
        home = "No Home Advantage" if parts[0] == 'F' else "Home Advantage"
        btts = "BTTS Pressure" if parts[2] == 'T' else "No BTTS Pressure"
        overs = "Overs Pressure" if parts[1] == 'T' else "No Overs Pressure"
        
        importance = {
            '0': 'Low Importance',
            '1': 'Medium Importance',
            '2': 'High Importance'
        }.get(parts[3], f"Importance:{parts[3]}")
        
        # Determine the typical outcome based on pattern
        if pattern_code == 'F,T,F,0':
            outcome = "NO DRAW (Away bias)"
            emoji = "✈️"
        elif pattern_code == 'T,T,T,1':
            outcome = "OVER 2.5 / BTTS (Home bias)"
            emoji = "🔥"
        elif pattern_code == 'F,F,F,0':
            outcome = "HOME WIN (when winner occurs)"
            emoji = "🏠"
        elif pattern_code == 'F,T,T,0':
            outcome = "NO DRAW (Away bias)"
            emoji = "✈️"
        elif pattern_code == 'F,T,T,1':
            outcome = "NO DRAW (Strong Away bias)"
            emoji = "✈️"
        elif pattern_code == 'F,F,T,0':
            outcome = "MIXED - Check stats"
            emoji = "⚖️"
        else:
            outcome = "Track this pattern"
            emoji = "📊"
        
        return {
            'code': pattern_code,
            'description': f"{home} • {btts} • {overs} • {importance}",
            'outcome': outcome,
            'emoji': emoji
        }
    except:
        return {'code': pattern_code, 'description': pattern_code, 'outcome': 'Unknown', 'emoji': '📊'}

# ============================================================================
# ACTIVE RULES DEFINITIONS - With Human-Readable Names
# ============================================================================

ACTIVE_RULES = [
    {
        'id': 1,
        'name': 'GRAND UNDER 2.5',
        'db_name': '🏆 GRAND UNIFIED = UNDER 2.5',
        'display_name': '❄️ GRAND UNDER 2.5',
        'outcome': 'UNDER 2.5 Goals',
        'category': 'legacy',
        'bias': None
    },
    {
        'id': 2,
        'name': 'Elite + Home Adv',
        'db_name': '👑 ELITE HOME = DRAW/AWAY WIN',
        'display_name': '🏠 Elite Home Advantage',
        'outcome': 'NO DRAW (Home Wins Most)',
        'category': 'legacy',
        'bias': 'Home wins 80% when not a draw'
    },
    {
        'id': 3,
        'name': 'F,T,F,0',
        'pattern_code': 'F,T,F,0',
        'display_name': '✈️ No Home Adv + BTTS Pressure = Away Win Likely',
        'outcome': 'NO DRAW (Away Bias)',
        'category': 'flag',
        'bias': 'Away wins 60% when not a draw'
    },
    {
        'id': 4,
        'name': 'home_btts=2 & away_btts=2',
        'db_name': '🎯 HOME ELITE ATTACK = WIN/DRAW',
        'display_name': '🔥 Both Teams Attack = Goals',
        'outcome': 'OVER 2.5 / BTTS',
        'category': 'legacy',
        'bias': 'Away wins 75% when winner occurs'
    },
    {
        'id': 5,
        'name': 'Elite + No Home Adv',
        'db_name': '✈️ AWAY ELITE ATTACK = WINNER',
        'display_name': '✈️ Elite Away Team = Away Win',
        'outcome': 'AWAY WIN Likely',
        'category': 'legacy',
        'bias': 'Away wins 82%'
    },
    {
        'id': 6,
        'name': 'Away Win Lock',
        'db_name': '✈️ [4,3] + AWAY ATTACK = AWAY WIN',
        'display_name': '🔒 Away Win Lock',
        'outcome': 'AWAY WIN',
        'category': 'legacy',
        'bias': 'Away wins 90%'
    },
    {
        'id': 7,
        'name': 'home_da=2 & away_da=3',
        'db_name': '⚠️ TIER2 HOME vs TIER3 AWAY = LOSS',
        'display_name': '🏠 Home Defense Edge = Home Win',
        'outcome': 'HOME WIN / NO DRAW',
        'category': 'legacy',
        'bias': 'Home wins 67%'
    },
    {
        'id': 8,
        'name': 'T,T,T,1',
        'pattern_code': 'T,T,T,1',
        'display_name': '🔥 All Pressure + Medium Importance = Goals',
        'outcome': 'OVER 2.5 / BTTS',
        'category': 'flag',
        'bias': 'Home wins 75% when goals happen'
    },
    {
        'id': 9,
        'name': 'F,F,F,0',
        'pattern_code': 'F,F,F,0',
        'display_name': '🏠 No Flags = Home Win Lock',
        'outcome': 'HOME WIN',
        'category': 'flag',
        'bias': 'Home wins 100% when winner occurs'
    }
]

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_rule_performance():
    """Get actual performance metrics for all active rules"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        # Get all matches with results
        matches = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)\
            .order('match_date', desc=True)\
            .execute()
        
        if not matches.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(matches.data)
        
        # Get pattern tracking data for flag-based rules
        patterns = supabase.table('pattern_tracking')\
            .select('*')\
            .execute()
        
        pattern_df = pd.DataFrame(patterns.data) if patterns.data else pd.DataFrame()
        
        performance_data = []
        
        for rule in ACTIVE_RULES:
            if rule['category'] == 'legacy':
                # Get performance from rule_hits
                rule_matches = []
                for _, match in df.iterrows():
                    rule_hits = match.get('rule_hits', {})
                    if isinstance(rule_hits, str):
                        try:
                            rule_hits = json.loads(rule_hits)
                        except:
                            rule_hits = {}
                    
                    # Check if this rule's db_name appears in rule_hits
                    rule_active = False
                    for hit_key, hit_value in rule_hits.items():
                        if isinstance(hit_value, dict) and hit_value.get('name') == rule['db_name']:
                            rule_active = True
                            break
                    
                    if rule_active:
                        rule_matches.append(match)
                
                if rule_matches:
                    rule_df = pd.DataFrame(rule_matches)
                    total = len(rule_df)
                    
                    # Calculate hits based on rule outcome
                    if 'UNDER' in rule['outcome']:
                        hits = (rule_df['home_goals'] + rule_df['away_goals'] < 3).sum()
                    elif 'OVER' in rule['outcome']:
                        hits = (rule_df['home_goals'] + rule_df['away_goals'] >= 3).sum()
                    elif 'AWAY WIN' in rule['outcome']:
                        hits = (rule_df['away_goals'] > rule_df['home_goals']).sum()
                    elif 'HOME WIN' in rule['outcome']:
                        hits = (rule_df['home_goals'] > rule_df['away_goals']).sum()
                    elif 'NO DRAW' in rule['outcome']:
                        hits = (rule_df['home_goals'] != rule_df['away_goals']).sum()
                    elif 'BTTS' in rule['outcome']:
                        hits = ((rule_df['home_goals'] > 0) & (rule_df['away_goals'] > 0)).sum()
                    else:
                        hits = 0
                    
                    hit_rate = round((hits / total) * 100, 1)
                    
                    performance_data.append({
                        'Rule': rule['display_name'],
                        'Outcome': rule['outcome'],
                        'Bias': rule['bias'] if rule['bias'] else '-',
                        'Matches': total,
                        'Hits': hits,
                        'Hit Rate': f"{hit_rate}%"
                    })
            
            elif rule['category'] == 'flag' and not pattern_df.empty:
                # Get performance from pattern_tracking
                pattern_row = pattern_df[pattern_df['pattern_code'] == rule['pattern_code']]
                if not pattern_row.empty:
                    row = pattern_row.iloc[0]
                    total = row.get('total_matches', 0)
                    
                    if total >= 3:
                        # Calculate hits based on rates
                        if 'OVER' in rule['outcome']:
                            hit_rate = row.get('current_over_rate', 0)
                        elif 'HOME WIN' in rule['outcome']:
                            hit_rate = row.get('current_home_win_rate', 0)
                        else:
                            hit_rate = row.get('confidence_score', 0)
                        
                        hits = round(total * hit_rate / 100) if hit_rate else 0
                        
                        performance_data.append({
                            'Rule': rule['display_name'],
                            'Outcome': rule['outcome'],
                            'Bias': rule['bias'] if rule['bias'] else '-',
                            'Matches': total,
                            'Hits': hits,
                            'Hit Rate': f"{hit_rate:.1f}%" if hit_rate else '0%'
                        })
        
        return pd.DataFrame(performance_data)
    
    except Exception as e:
        st.error(f"Error getting rule performance: {e}")
        return pd.DataFrame()

def get_pattern_stats(min_matches=5):
    """Get patterns from database with confidence scores"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table('pattern_tracking')\
            .select('pattern_code,total_matches,current_home_win_rate,current_over_rate,current_btts_rate,confidence_score,home_trend,is_emerging,is_monitored,last_calculated')\
            .gte('total_matches', min_matches)\
            .order('confidence_score', desc=True)\
            .execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            # Add human-readable descriptions
            df['description'] = df['pattern_code'].apply(lambda x: translate_pattern_code(x)['description'])
            df['prediction'] = df['pattern_code'].apply(lambda x: translate_pattern_code(x)['outcome'])
            df['emoji'] = df['pattern_code'].apply(lambda x: translate_pattern_code(x)['emoji'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error getting pattern stats: {e}")
        return pd.DataFrame()

def get_pattern_prediction(pattern_code):
    """Get prediction from database for a specific pattern"""
    if supabase is None:
        return None
    
    try:
        result = supabase.table('pattern_tracking')\
            .select('*')\
            .eq('pattern_code', pattern_code)\
            .gte('total_matches', 3)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        return None

# ============================================================================
# TIER FUNCTIONS
# ============================================================================

def calculate_tier(value, category):
    """Convert percentage to tier (1-4)"""
    if category == 'da':
        if value >= 75: return 1
        elif value >= 60: return 2
        elif value >= 40: return 3
        else: return 4
    else:  # btts or over
        if value >= 70: return 1
        elif value >= 55: return 2
        elif value >= 40: return 3
        else: return 4

def tier_to_emoji(tier, category):
    emojis = {
        'da': ["💥", "⚡", "📊", "🐢"],
        'btts': ["🎯", "⚽", "🤔", "🧤"],
        'over': ["🔥", "📈", "⚖️", "📉"]
    }
    return emojis[category][tier-1]

def get_tier_description(tier, category):
    if category == 'da':
        return ["Elite Defense", "Strong Defense", "Average Defense", "Weak Defense"][tier-1]
    elif category == 'btts':
        return ["Always Scores", "Usually Scores", "50/50", "Rarely Scores"][tier-1]
    else:
        return ["Goal Fest", "Goals Likely", "50/50", "Goals Unlikely"][tier-1]

# ============================================================================
# PREDICTION ENGINE
# ============================================================================

def analyze_match(data):
    """Analyze match and return predictions"""
    
    # Calculate tiers
    home_da_tier = calculate_tier(data['home_da'], 'da')
    away_da_tier = calculate_tier(data['away_da'], 'da')
    home_btts_tier = calculate_tier(data['home_btts'], 'btts')
    away_btts_tier = calculate_tier(data['away_btts'], 'btts')
    home_over_tier = calculate_tier(data['home_over'], 'over')
    away_over_tier = calculate_tier(data['away_over'], 'over')
    
    # Calculate flags
    home_adv_flag = home_da_tier <= 2 and away_da_tier >= 3
    btts_pressure_flag = (home_btts_tier <= 2 and away_btts_tier <= 2)
    overs_pressure_flag = (home_over_tier <= 2 and away_da_tier >= 3) or (away_over_tier <= 2 and home_da_tier >= 3)
    importance = (1 if data.get('elite', False) else 0) + (1 if data.get('derby', False) else 0) + (1 if data.get('relegation', False) else 0)
    
    # Generate pattern code
    pattern_code = f"{'T' if home_adv_flag else 'F'},{'T' if overs_pressure_flag else 'F'},{'T' if btts_pressure_flag else 'F'},{importance}"
    
    # Enhanced data for rules
    enhanced_data = {
        **data,
        'home_da_tier': home_da_tier,
        'away_da_tier': away_da_tier,
        'home_btts_tier': home_btts_tier,
        'away_btts_tier': away_btts_tier,
        'home_over_tier': home_over_tier,
        'away_over_tier': away_over_tier,
        'home_adv_flag': home_adv_flag,
        'btts_pressure_flag': btts_pressure_flag,
        'overs_pressure_flag': overs_pressure_flag,
        'importance_score': importance,
        'pattern_code': pattern_code
    }
    
    # Check database for this pattern
    db_pattern = get_pattern_prediction(pattern_code)
    matches = []
    
    if db_pattern and db_pattern.get('total_matches', 0) >= 3:
        # Translate the pattern code
        translation = translate_pattern_code(pattern_code)
        
        db_match = {
            'name': translation['display_name'] if 'display_name' in translation else f"{translation['emoji']} {translation['outcome']}",
            'description': translation['description'],
            'outcome': translation['outcome'],
            'emoji': translation['emoji'],
            'from_db': True,
            'confidence': db_pattern.get('confidence_score', 70),
            'matches': db_pattern.get('total_matches', 0),
            'home_win_rate': db_pattern.get('current_home_win_rate', 50),
            'over_rate': db_pattern.get('current_over_rate', 50),
            'btts_rate': db_pattern.get('current_btts_rate', 50)
        }
        matches.append(db_match)
    
    # Also check active rules that might not be in pattern_tracking
    for rule in ACTIVE_RULES:
        if rule['category'] == 'legacy':
            # Legacy rules are handled separately in performance tab
            # For predictions, we'd need to check conditions
            pass
    
    return {
        'matches': matches,
        'home_da_tier': home_da_tier,
        'away_da_tier': away_da_tier,
        'home_btts_tier': home_btts_tier,
        'away_btts_tier': away_btts_tier,
        'home_over_tier': home_over_tier,
        'away_over_tier': away_over_tier,
        'home_adv_flag': home_adv_flag,
        'btts_pressure_flag': btts_pressure_flag,
        'pattern_code': pattern_code,
        'has_db_pattern': db_pattern is not None
    }

# ============================================================================
# DATABASE FUNCTIONS - SAVE MATCH
# ============================================================================

def save_match(data, home_goals=None, away_goals=None):
    if supabase is None:
        return None
    
    try:
        match_data = {
            'home_team': data['home_team'].strip(),
            'away_team': data['away_team'].strip(),
            'league': data['league'],
            'match_date': datetime.now().date().isoformat(),
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
            return result.data[0]['id']
        return None
            
    except Exception as e:
        st.error(f"Error saving match: {e}")
        return None

def get_league_stats():
    if supabase is None:
        return {}
    
    try:
        result = supabase.table('matches')\
            .select('league, home_goals, away_goals, actual_goals, actual_btts')\
            .eq('result_entered', True)\
            .execute()
        
        df = pd.DataFrame(result.data)
        if df.empty:
            return {}
        
        stats = {}
        for league in df['league'].unique():
            league_df = df[df['league'] == league]
            total_matches = len(league_df)
            if total_matches == 0:
                continue
                
            total_goals = league_df['actual_goals'].sum()
            btts_count = league_df['actual_btts'].sum()
            over_count = (league_df['actual_goals'] >= 3).sum()
            
            stats[league] = {
                'matches': total_matches,
                'avg_goals': round(total_goals / total_matches, 2),
                'btts_rate': round((btts_count / total_matches) * 100, 1),
                'over_rate': round((over_count / total_matches) * 100, 1)
            }
        return stats
    except Exception as e:
        st.error(f"Error getting league stats: {e}")
        return {}

def get_recent_matches(limit=20):
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
        st.error(f"Error getting recent matches: {e}")
        return []

def get_upcoming_matches(limit=10):
    if supabase is None:
        return []
    
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', False)\
            .order('match_date', desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        return []

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🏆 Discovery Hunter v24.0")
    st.markdown("### 9 Active Rules • Self-Learning • Real-Time Performance")
    
    if not SUPABASE_AVAILABLE:
        st.error("Supabase module not installed. Run: pip install supabase")
        return
    
    if supabase is None:
        st.error("Supabase connection failed. Check your secrets.")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Live Stats")
        try:
            total = supabase.table('matches').select('*', count='exact').execute()
            completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
            upcoming = supabase.table('matches').select('*', count='exact').eq('result_entered', False).execute()
            
            st.metric("Total Matches", total.count if hasattr(total, 'count') else 0)
            st.metric("Completed", completed.count if hasattr(completed, 'count') else 0)
            st.metric("Upcoming", upcoming.count if hasattr(upcoming, 'count') else 0)
            
            st.markdown("---")
            st.markdown("**BET KEY**")
            st.markdown("🔥 OVER | ❄️ UNDER | 🏠 HOME | ✈️ AWAY | ⚽ BTTS")
            
        except Exception as e:
            st.info("No data yet")
    
    # Main tabs - SIMPLIFIED to 3
    tab1, tab2, tab3 = st.tabs([
        "🏆 ACTIVE RULES",  # Your 9 rules with performance
        "📝 NEW MATCH",      # Enter matches & get predictions
        "🔍 PATTERN DISCOVERY" # New patterns emerging
    ])
    
    # ===== TAB 1: ACTIVE RULES PERFORMANCE =====
    with tab1:
        st.header("🏆 Active Rules Performance")
        st.markdown("### Your 9 Proven Rules - Updated Live")
        
        performance_df = get_rule_performance()
        
        if not performance_df.empty:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Active Rules", len(performance_df))
            col2.metric("Best Hit Rate", performance_df['Hit Rate'].max())
            col3.metric("Total Matches Tracked", performance_df['Matches'].sum())
            
            # Main performance table
            st.dataframe(
                performance_df,
                hide_index=True,
                use_container_width=True
            )
            
            # Visual representation
            fig = px.bar(
                performance_df,
                x='Rule',
                y='Hit Rate',
                color='Hit Rate',
                text='Hit Rate',
                title='Active Rules - Hit Rates',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No performance data available yet. Add matches to see rule performance.")
    
    # ===== TAB 2: NEW MATCH =====
    with tab2:
        st.subheader("Enter New Match Data")
        
        if 'pending_match' not in st.session_state:
            st.session_state.pending_match = None
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None
        
        with st.form("match_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏠 HOME**")
                home_team = st.text_input("Team", key="home_team_input")
                home_da = st.number_input("DA", 0, 100, 50, key="home_da_input")
                home_btts = st.number_input("BTTS %", 0, 100, 50, key="home_btts_input")
                home_over = st.number_input("Over %", 0, 100, 50, key="home_over_input")
            
            with col2:
                st.markdown("**✈️ AWAY**")
                away_team = st.text_input("Team", key="away_team_input")
                away_da = st.number_input("DA", 0, 100, 50, key="away_da_input")
                away_btts = st.number_input("BTTS %", 0, 100, 50, key="away_btts_input")
                away_over = st.number_input("Over %", 0, 100, 50, key="away_over_input")
            
            col3, col4, col5 = st.columns(3)
            with col3:
                elite = st.checkbox("⭐ Elite", key="elite_input")
            with col4:
                derby = st.checkbox("🏆 Derby", key="derby_input")
            with col5:
                relegation = st.checkbox("⚠️ Relegation", key="relegation_input")
            
            league_options = ["EPL", "BUNDESLIGA", "SERIE A", "LA LIGA", "LIGUE 1", "CHAMPIONSHIP", "OTHER LEAGUE"]
            league = st.selectbox("League", league_options, key="league_input")
            
            if league == "OTHER LEAGUE":
                custom_league = st.text_input("Enter League Name", key="custom_league_input")
                if custom_league:
                    league = custom_league.upper()
            
            notes = st.text_input("Notes", key="notes_input")
            
            analyzed = st.form_submit_button("🔍 ANALYZE", use_container_width=True)
        
        if analyzed:
            if not home_team or not away_team:
                st.error("Please enter both team names")
            else:
                st.session_state.pending_match = {
                    'home_team': home_team, 
                    'away_team': away_team, 
                    'league': league,
                    'home_da': home_da, 
                    'away_da': away_da,
                    'home_btts': home_btts, 
                    'away_btts': away_btts,
                    'home_over': home_over, 
                    'away_over': away_over,
                    'elite': elite, 
                    'derby': derby, 
                    'relegation': relegation,
                    'notes': notes
                }
                
                st.session_state.analysis_result = analyze_match(st.session_state.pending_match)
                st.rerun()
        
        # Show prediction results
        if st.session_state.analysis_result and st.session_state.pending_match:
            data = st.session_state.pending_match
            analysis = st.session_state.analysis_result
            
            st.markdown("---")
            st.subheader("🎯 PREDICTION")
            
            if analysis['matches']:
                for match in analysis['matches']:
                    # Create a nice prediction box
                    with st.container():
                        st.markdown(f"""
                        <div style="background-color: #1e3a5f; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #4CAF50;">
                            <h3 style="margin:0; color: white;">{match['emoji']} {match['name']}</h3>
                            <p style="margin:10px 0 5px 0; color: #ddd; font-size: 16px;">{match.get('description', '')}</p>
                            <p style="margin:5px 0; color: white; font-size: 20px; font-weight: bold;">🎯 {match['outcome']}</p>
                            <p style="margin:10px 0 0 0; color: #aaa;">Confidence: {match['confidence']:.1f}% based on {match['matches']} matches</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("No matching patterns found for this match")
            
            # Enter result
            st.markdown("---")
            st.subheader("📥 Enter Result")
            
            with st.form("result_form"):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    home_goals = st.number_input(
                        f"{data['home_team']} Goals", 
                        min_value=0, max_value=20, value=0,
                        key="home_goals_result"
                    )
                with col_r2:
                    away_goals = st.number_input(
                        f"{data['away_team']} Goals", 
                        min_value=0, max_value=20, value=0,
                        key="away_goals_result"
                    )
                
                saved = st.form_submit_button("💾 SAVE MATCH", type="primary", use_container_width=True)
                
                if saved:
                    match_id = save_match(data, home_goals, away_goals)
                    if match_id:
                        st.success(f"✅ Match #{match_id} saved!")
                        st.balloons()
                        st.session_state.pending_match = None
                        st.session_state.analysis_result = None
                        st.rerun()
    
    # ===== TAB 3: PATTERN DISCOVERY =====
    with tab3:
        st.header("🔍 Pattern Discovery")
        st.markdown("### New Patterns Emerging from Data")
        
        min_matches = st.slider("Minimum Matches", 5, 20, 8, key="pattern_min_matches")
        
        patterns = get_pattern_stats(min_matches)
        
        if not patterns.empty:
            st.metric("Emerging Patterns Found", len(patterns))
            
            # Show patterns with human-readable descriptions
            display_df = patterns[['emoji', 'prediction', 'description', 'total_matches', 
                                  'current_home_win_rate', 'current_over_rate', 'current_btts_rate', 
                                  'confidence_score', 'home_trend']].copy()
            
            display_df.columns = ['', 'Prediction', 'Pattern Details', 'Matches', 
                                 'Home Win %', 'Over %', 'BTTS %', 'Confidence', 'Trend']
            
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            
            fig = px.scatter(patterns, x='total_matches', y='confidence_score',
                           size='confidence_score', color='home_trend',
                           hover_data=['prediction'],
                           title='Emerging Patterns - Confidence vs Sample Size')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No patterns found with {min_matches}+ matches. Keep adding data!")

if __name__ == "__main__":
    main()
