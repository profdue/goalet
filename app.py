import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import json

# Try to import supabase with error handling
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Supabase module not installed. Database features disabled. Run: pip install supabase")

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v15.0",
    page_icon="🎯",
    layout="wide"
)

# ============================================================================
# SUPABASE FUNCTIONS
# ============================================================================

if SUPABASE_AVAILABLE:
    @st.cache_resource
    def init_supabase():
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
        except Exception as e:
            st.error(f"Failed to connect to Supabase: {e}")
            return None
    
    supabase = init_supabase()
else:
    supabase = None

# ============================================================================
# TIER FUNCTIONS
# ============================================================================

def calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over):
    """Calculate tiers - ONLY returns 1-4"""
    
    def da_tier(value):
        if value is None: return 4
        if value >= 70: return 1
        if value >= 55: return 2
        if value >= 40: return 3
        return 4
    
    def btts_tier(value):
        if value is None: return 4
        if value >= 65: return 1
        if value >= 55: return 2
        if value >= 45: return 3
        return 4
    
    def over_tier(value):
        if value is None: return 4
        if value >= 65: return 1
        if value >= 55: return 2
        if value >= 45: return 3
        return 4
    
    return [
        da_tier(home_da),
        da_tier(away_da),
        btts_tier(home_btts),
        btts_tier(away_btts),
        over_tier(home_over),
        over_tier(away_over)
    ]

def tier_to_emoji(tier, category):
    emojis = {
        'da': ["💥", "⚡", "📊", "🐢"],
        'btts': ["🎯", "⚽", "🤔", "🧤"],
        'over': ["🔥", "📈", "⚖️", "📉"]
    }
    return emojis[category][tier-1]

def get_tier_description(tier, category):
    if category == 'da':
        descriptions = ["Elite Attack", "Strong Attack", "Average Attack", "Weak Attack"]
    elif category == 'btts':
        descriptions = ["Always Scores", "Usually Scores", "50/50", "Rarely Scores"]
    else:
        descriptions = ["Goal Fest", "Goals Likely", "50/50", "Goals Unlikely"]
    return descriptions[tier-1]

# ============================================================================
# DISCOVERY RULES FUNCTIONS
# ============================================================================

def check_discovery_rules(match):
    """Check which discovery rules apply to a match"""
    if not match.get('result_entered'):
        return {}
    
    home_goals = match.get('home_goals', 0) or 0
    away_goals = match.get('away_goals', 0) or 0
    total_goals = home_goals + away_goals
    
    rules = {}
    
    # Rule 1: [4,4] Opening = ≤2 Goals
    if match.get('home_da_tier') == 4 and match.get('away_da_tier') == 4:
        rules['rule_1'] = {
            'name': '[4,4] Opening = ≤2 Goals',
            'hit': total_goals <= 2
        }
    
    # Rule 2: away_btts_tier = 1 = Winner
    if match.get('away_btts_tier') == 1:
        rules['rule_2'] = {
            'name': 'away_btts_tier = 1 = Winner',
            'hit': home_goals != away_goals
        }
    
    # Rule 3: Importance 2 = ≥3 Goals
    if match.get('importance_score', 0) == 2:
        rules['rule_3'] = {
            'name': 'Importance 2 = ≥3 Goals',
            'hit': total_goals >= 3
        }
    
    # Rule 4: Sum = 22 = Exactly 2 Goals
    tier_sum = sum([
        match.get('home_da_tier', 0) or 0,
        match.get('away_da_tier', 0) or 0,
        match.get('home_btts_tier', 0) or 0,
        match.get('away_btts_tier', 0) or 0,
        match.get('home_over_tier', 0) or 0,
        match.get('away_over_tier', 0) or 0
    ])
    if tier_sum == 22:
        rules['rule_4'] = {
            'name': 'Sum = 22 = Exactly 2 Goals',
            'hit': total_goals == 2
        }
    
    # Rule 5: home_advantage_flag = No Draw
    if match.get('home_advantage_flag', False):
        rules['rule_5'] = {
            'name': 'Home Advantage Flag = No Draw',
            'hit': home_goals != away_goals
        }
    
    # Rule 6: away_btts_tier = 1 OR (away_btts_tier = 2 AND home_btts_tier ≠ 2)
    if (match.get('away_btts_tier') == 1) or \
       (match.get('away_btts_tier') == 2 and match.get('home_btts_tier') != 2):
        rules['rule_6'] = {
            'name': 'Away BTTS Elite = Winner',
            'hit': home_goals != away_goals
        }
    
    # Rule 7: Mixed Defense [4,3] or [3,4] = Winner
    defenses = (match.get('home_da_tier'), match.get('away_da_tier'))
    if defenses in [(4,3), (3,4)]:
        rules['rule_7'] = {
            'name': 'Mixed Defense = Winner',
            'hit': home_goals != away_goals
        }
    
    # Rule 8: Both DA ≤ 45 = Under 2.5
    if (match.get('home_da', 0) or 0) <= 45 and (match.get('away_da', 0) or 0) <= 45:
        rules['rule_8'] = {
            'name': 'Both DA ≤ 45 = Under 2.5',
            'hit': total_goals <= 2
        }
    
    # Rule 9: Both DA ≥ 50 = Goals
    if (match.get('home_da', 0) or 0) >= 50 and (match.get('away_da', 0) or 0) >= 50:
        rules['rule_9'] = {
            'name': 'Both DA ≥ 50 = Goals (3+ avg)',
            'hit': total_goals >= 3
        }
    
    # Rule 10: away_da ≥ 55 = Away Result
    if (match.get('away_da', 0) or 0) >= 55:
        rules['rule_10'] = {
            'name': 'away_da ≥ 55 = Away Wins/Draws',
            'hit': away_goals >= home_goals
        }
    
    return rules

def update_rule_hits(match_id, rules):
    """Update rule_hits JSONB column for a match"""
    if supabase is None:
        return
    
    try:
        supabase.table('matches')\
            .update({'rule_hits': json.dumps(rules)})\
            .eq('id', match_id)\
            .execute()
    except Exception as e:
        st.error(f"Error updating rule hits: {e}")

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def save_match(match_input, home_team, away_team, league, home_goals=None, away_goals=None, notes=""):
    """Save match to Supabase with optional result"""
    
    if supabase is None:
        st.error("Supabase not connected")
        return None
    
    try:
        tiers = calculate_tiers(
            match_input['home_da'],
            match_input['away_da'],
            match_input['home_btts'],
            match_input['away_btts'],
            match_input['home_over'],
            match_input['away_over']
        )
        
        # Calculate flags
        home_advantage_flag = tiers[0] < tiers[1]
        
        # NEW BTTS PRESSURE FLAG FORMULA (Discovery-based)
        btts_pressure_flag = (
            (tiers[2] <= 2 and tiers[1] >= 3) or  # home good offense vs away weak defense
            (tiers[3] <= 2 and tiers[0] >= 3) or  # away good offense vs home weak defense
            match_input.get('elite', False) or 
            match_input.get('derby', False)
        )
        
        # NEW OVERS PRESSURE FLAG FORMULA
        overs_pressure_flag = (
            (tiers[4] <= 2 and tiers[1] >= 3) or  # home over threat vs away weak defense
            (tiers[5] <= 2 and tiers[0] >= 3)     # away over threat vs home weak defense
        )
        
        # Importance score
        importance_score = (
            (1 if match_input.get('elite', False) else 0) +
            (1 if match_input.get('derby', False) else 0) +
            (1 if match_input.get('relegation', False) else 0)
        )
        
        data = {
            'home_team': home_team.strip(),
            'away_team': away_team.strip(),
            'league': league,
            'match_date': datetime.now().date().isoformat(),
            'home_da': match_input['home_da'],
            'away_da': match_input['away_da'],
            'home_btts': match_input['home_btts'],
            'away_btts': match_input['away_btts'],
            'home_over': match_input['home_over'],
            'away_over': match_input['away_over'],
            'home_da_tier': tiers[0],
            'away_da_tier': tiers[1],
            'home_btts_tier': tiers[2],
            'away_btts_tier': tiers[3],
            'home_over_tier': tiers[4],
            'away_over_tier': tiers[5],
            'tier_signature': str(tiers),
            'elite': match_input.get('elite', False),
            'derby': match_input.get('derby', False),
            'relegation': match_input.get('relegation', False),
            'result_entered': home_goals is not None and away_goals is not None,
            'data_quality_flag': False,
            'home_advantage_flag': home_advantage_flag,
            'btts_pressure_flag': btts_pressure_flag,
            'overs_pressure_flag': overs_pressure_flag,
            'importance_score': importance_score,
            'is_home': True,  # Default to True, can be overridden
            'rule_hits': None,
            'discovery_notes': notes if notes else None
        }
        
        # Add result if provided
        if home_goals is not None and away_goals is not None:
            data['home_goals'] = home_goals
            data['away_goals'] = away_goals
            data['notes'] = notes
        
        result = supabase.table('matches').insert(data).execute()
        match_id = result.data[0]['id']
        
        # If result was provided, check discovery rules
        if home_goals is not None and away_goals is not None:
            match_data = data.copy()
            match_data['id'] = match_id
            rules = check_discovery_rules(match_data)
            if rules:
                update_rule_hits(match_id, rules)
        
        return match_id
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return None

def update_result(match_id, home_goals, away_goals, notes=""):
    """Update match with actual result"""
    
    if supabase is None:
        st.error("Supabase not connected")
        return False
    
    try:
        data = {
            'home_goals': home_goals,
            'away_goals': away_goals,
            'result_entered': True,
            'notes': notes
        }
        
        supabase.table('matches').update(data).eq('id', match_id).execute()
        
        # Get the updated match to check rules
        result = supabase.table('matches').select('*').eq('id', match_id).execute()
        if result.data:
            rules = check_discovery_rules(result.data[0])
            if rules:
                update_rule_hits(match_id, rules)
        
        return True
    except Exception as e:
        st.error(f"Error updating result: {e}")
        return False

def safe_get(value, default=0):
    """Safely get value, return default if None"""
    return value if value is not None else default

def safe_bool(value, default=False):
    """Safely get boolean, return default if None"""
    return value if value is not None else default

def get_pattern_history(tier_signature, league=None, min_matches=1):
    if supabase is None:
        return []
    try:
        query = supabase.table('matches')\
            .select('*')\
            .eq('tier_signature', tier_signature)\
            .eq('result_entered', True)
        if league:
            query = query.eq('league', league)
        result = query.order('match_date', desc=True).execute()
        return result.data if len(result.data) >= min_matches else []
    except Exception as e:
        st.error(f"Error querying patterns: {e}")
        return []

def get_league_stats(league):
    if supabase is None:
        return []
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('league', league)\
            .eq('result_entered', True)\
            .order('match_date', desc=True)\
            .execute()
        return result.data
    except Exception as e:
        st.error(f"Error getting league stats: {e}")
        return []

def discover_patterns(min_matches=2):
    if supabase is None:
        return {}
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)\
            .execute()
        matches = result.data
        
        patterns = {}
        for match in matches:
            sig = match.get('tier_signature')
            if not sig:
                continue
            if sig not in patterns:
                patterns[sig] = []
            patterns[sig].append(match)
        
        insights = {}
        for sig, matches_list in patterns.items():
            if len(matches_list) >= min_matches:
                total = len(matches_list)
                overs = sum(1 for m in matches_list if safe_get(m.get('actual_goals')) >= 3)
                btts_yes = sum(1 for m in matches_list if safe_bool(m.get('actual_btts')))
                
                insights[sig] = {
                    'total': total,
                    'over_pct': (overs / total) * 100 if total > 0 else 0,
                    'under_pct': ((total - overs) / total) * 100 if total > 0 else 0,
                    'btts_yes_pct': (btts_yes / total) * 100 if total > 0 else 0,
                    'btts_no_pct': ((total - btts_yes) / total) * 100 if total > 0 else 0,
                    'avg_goals': sum(safe_get(m.get('actual_goals')) for m in matches_list) / total if total > 0 else 0,
                    'matches': matches_list
                }
        return insights
    except Exception as e:
        st.error(f"Error discovering patterns: {e}")
        return {}

def get_counter_threats(league=None):
    if supabase is None:
        return {}
    try:
        query = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)
        if league:
            query = query.eq('league', league)
        result = query.execute()
        matches = result.data
        
        team_stats = {}
        for match in matches:
            for team_key in ['home', 'away']:
                team = match[f'{team_key}_team']
                if team not in team_stats:
                    team_stats[team] = {'btts_stat': [], 'actual_btts': [], 'goals_scored': []}
                team_stats[team]['btts_stat'].append(safe_get(match[f'{team_key}_btts']))
                team_stats[team]['actual_btts'].append(1 if safe_bool(match.get('actual_btts')) else 0)
                team_stats[team]['goals_scored'].append(safe_get(match.get(f'{team_key}_goals')))
        
        threats = {}
        for team, stats in team_stats.items():
            if len(stats['btts_stat']) >= 3:
                avg_stat = np.mean(stats['btts_stat'])
                actual_rate = (sum(stats['actual_btts']) / len(stats['actual_btts'])) * 100
                avg_goals = np.mean(stats['goals_scored'])
                
                if (avg_stat < 50 and actual_rate > 50) or avg_goals > 1.2:
                    threats[team] = {
                        'stat_avg': round(avg_stat, 1),
                        'actual_rate': round(actual_rate, 1),
                        'avg_goals': round(avg_goals, 2),
                        'matches': len(stats['btts_stat']),
                        'diff': round(actual_rate - avg_stat, 1)
                    }
        return threats
    except Exception as e:
        st.error(f"Error analyzing counter threats: {e}")
        return {}

def get_pressure_test_results():
    if supabase is None:
        return {}
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)\
            .execute()
        matches = result.data
        
        if len(matches) < 5:
            return {}
        
        # Safely get boolean flags
        btts_high = [m for m in matches if safe_bool(m.get('btts_pressure_flag'))]
        btts_low = [m for m in matches if not safe_bool(m.get('btts_pressure_flag'))]
        overs_high = [m for m in matches if safe_bool(m.get('overs_pressure_flag'))]
        overs_low = [m for m in matches if not safe_bool(m.get('overs_pressure_flag'))]
        home_adv = [m for m in matches if safe_bool(m.get('home_advantage_flag'))]
        no_home_adv = [m for m in matches if not safe_bool(m.get('home_advantage_flag'))]
        high_importance = [m for m in matches if safe_get(m.get('importance_score')) >= 2]
        low_importance = [m for m in matches if safe_get(m.get('importance_score')) == 0]
        
        return {
            'btts_pressure': {
                'high_count': len(btts_high),
                'high_btts_rate': sum(1 for m in btts_high if safe_bool(m.get('actual_btts'))) / len(btts_high) if btts_high else 0,
                'low_count': len(btts_low),
                'low_btts_rate': sum(1 for m in btts_low if safe_bool(m.get('actual_btts'))) / len(btts_low) if btts_low else 0,
            },
            'overs_pressure': {
                'high_count': len(overs_high),
                'high_over_rate': sum(1 for m in overs_high if safe_get(m.get('actual_goals')) >= 3) / len(overs_high) if overs_high else 0,
                'low_count': len(overs_low),
                'low_over_rate': sum(1 for m in overs_low if safe_get(m.get('actual_goals')) >= 3) / len(overs_low) if overs_low else 0,
            },
            'home_advantage': {
                'adv_count': len(home_adv),
                'adv_win_rate': sum(1 for m in home_adv if safe_get(m.get('home_goals')) > safe_get(m.get('away_goals'))) / len(home_adv) if home_adv else 0,
                'no_adv_count': len(no_home_adv),
                'no_adv_win_rate': sum(1 for m in no_home_adv if safe_get(m.get('home_goals')) > safe_get(m.get('away_goals'))) / len(no_home_adv) if no_home_adv else 0,
            },
            'importance': {
                'high_count': len(high_importance),
                'high_avg_goals': sum(safe_get(m.get('actual_goals')) for m in high_importance) / len(high_importance) if high_importance else 0,
                'low_count': len(low_importance),
                'low_avg_goals': sum(safe_get(m.get('actual_goals')) for m in low_importance) / len(low_importance) if low_importance else 0,
            }
        }
    except Exception as e:
        st.error(f"Error running pressure tests: {e}")
        return {}

def get_discovery_stats():
    """Get statistics on discovery rules"""
    if supabase is None:
        return {}
    
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)\
            .execute()
        matches = result.data
        
        rule_stats = {}
        for match in matches:
            rules = match.get('rule_hits')
            if rules:
                for rule_key, rule_data in rules.items():
                    if rule_key not in rule_stats:
                        rule_stats[rule_key] = {
                            'name': rule_data['name'],
                            'total': 0,
                            'hits': 0
                        }
                    rule_stats[rule_key]['total'] += 1
                    if rule_data['hit']:
                        rule_stats[rule_key]['hits'] += 1
        
        return rule_stats
    except Exception as e:
        st.error(f"Error getting discovery stats: {e}")
        return {}

# ============================================================================
# PREDICTION FUNCTIONS
# ============================================================================

def generate_prediction(history_matches):
    if not history_matches:
        return None
    
    total = len(history_matches)
    overs = sum(1 for m in history_matches if safe_get(m.get('actual_goals')) >= 3)
    btts_yes = sum(1 for m in history_matches if safe_bool(m.get('actual_btts')))
    
    over_pct = (overs / total) * 100 if total > 0 else 0
    
    if over_pct >= 70:
        prediction = "🔥 OVER 2.5"
        confidence = over_pct
        explanation = f"{overs}/{total} matches went Over 2.5"
    elif over_pct <= 30:
        prediction = "✅ UNDER 2.5"
        confidence = 100 - over_pct
        explanation = f"{total-overs}/{total} matches went Under 2.5"
    else:
        prediction = "⚖️ NO CLEAR EDGE"
        confidence = 50
        explanation = f"Mixed results: {overs} Over, {total-overs} Under"
    
    return {
        'prediction': prediction,
        'confidence': min(confidence, 95),
        'explanation': explanation,
        'btts_note': f"BTTS: {btts_yes}/{total} ({(btts_yes/total)*100:.0f}%)" if total > 0 else "BTTS: No data",
        'stats': {
            'total': total,
            'over': overs,
            'under': total - overs,
            'btts_yes': btts_yes,
            'btts_no': total - btts_yes,
            'avg_goals': sum(safe_get(m.get('actual_goals')) for m in history_matches) / total if total > 0 else 0
        }
    }

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v15.0")
    st.markdown("### Complete Pattern Tracking with Discovery Engine")
    
    if not SUPABASE_AVAILABLE:
        st.warning("⚠️ Supabase not installed. Run: `pip install supabase` to enable database features")
    elif supabase is None:
        st.error("❌ Supabase connection failed. Check your secrets.")
    else:
        st.success("✅ Supabase connected")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Database Stats")
        if supabase:
            try:
                total = supabase.table('matches').select('*', count='exact').execute()
                completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
                
                total_count = total.count if hasattr(total, 'count') else 0
                completed_count = completed.count if hasattr(completed, 'count') else 0
                
                st.metric("Total Matches", total_count)
                st.metric("Completed", completed_count)
                
                if total_count > 0:
                    patterns = discover_patterns(min_matches=2)
                    st.metric("Discovered Patterns", len(patterns))
                
                threats = get_counter_threats()
                if threats:
                    st.subheader("⚠️ Counter Threats")
                    for team, data in list(threats.items())[:3]:
                        st.text(f"• {team}: +{data['diff']}%")
                
                if completed_count >= 5:
                    pressure_results = get_pressure_test_results()
                    if pressure_results:
                        st.subheader("🎯 Pressure Test")
                        btts_diff = pressure_results['btts_pressure']['high_btts_rate'] - pressure_results['btts_pressure']['low_btts_rate']
                        st.metric("BTTS Flag Accuracy", f"{btts_diff*100:.0f}% better")
            except Exception as e:
                st.info("No matches in database yet")
        else:
            st.info("Supabase not connected")
        
        st.markdown("---")
        st.markdown("**Tiers:** 1💥 2⚡ 3📊 4🐢")
        st.markdown("**Discovery Rules:** Tracked in tab 6")
    
    # Main tabs - ADDED DISCOVERY TAB
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Predict", 
        "🔍 Discover Patterns", 
        "📊 League Stats", 
        "⚠️ Counter Threats", 
        "🎯 Pressure Test",
        "📈 Discovery Engine"
    ])
    
    with tab1:
        st.subheader("📋 Enter Match Data")
        
        # Initialize session state for this tab
        if 'show_result_entry' not in st.session_state:
            st.session_state.show_result_entry = False
        
        with st.form("match_input_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏠 HOME**")
                home_team = st.text_input("Home Team", "Parma")
                home_da = st.number_input("DA", 0, 100, 39)
                home_btts = st.number_input("BTTS %", 0, 100, 38)
                home_over = st.number_input("Over %", 0, 100, 35)
            
            with col2:
                st.markdown("**✈️ AWAY**")
                away_team = st.text_input("Away Team", "Cagliari")
                away_da = st.number_input("DA", 0, 100, 29, key="away_da")
                away_btts = st.number_input("BTTS %", 0, 100, 46, key="away_btts")
                away_over = st.number_input("Over %", 0, 100, 46, key="away_over")
            
            col3, col4, col5 = st.columns(3)
            with col3:
                elite = st.checkbox("⭐ Elite")
            with col4:
                derby = st.checkbox("🏆 Derby")
            with col5:
                relegation = st.checkbox("⚠️ Relegation")
            
            league = st.text_input("League", "SERIE A")
            
            generate_clicked = st.form_submit_button("🎯 GENERATE PREDICTION", use_container_width=True)
        
        # Handle GENERATE PREDICTION click
        if generate_clicked:
            # Calculate tiers
            tiers = calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over)
            
            # Store in session state
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
                'tiers': tiers
            }
            st.session_state.show_result_entry = True
        
        # Show TIER SIGNATURE if we have pending match
        if st.session_state.get('pending_match'):
            st.markdown("---")
            st.subheader("🎯 TIER SIGNATURE")
            
            tiers = st.session_state.pending_match['tiers']
            col_t1, col_t2, col_t3, col_t4, col_t5, col_t6 = st.columns(6)
            labels = ['HOME DA', 'AWAY DA', 'HOME BTTS', 'AWAY BTTS', 'HOME OVER', 'AWAY OVER']
            cats = ['da', 'da', 'btts', 'btts', 'over', 'over']
            
            for i, (col, label, cat) in enumerate(zip([col_t1, col_t2, col_t3, col_t4, col_t5, col_t6], labels, cats)):
                emoji = tier_to_emoji(tiers[i], cat)
                desc = get_tier_description(tiers[i], cat)
                col.metric(label, f"{emoji} TIER {tiers[i]}", help=desc)
            
            # Show flags
            col_f1, col_f2, col_f3 = st.columns(3)
            
            # Calculate flags for display
            home_adv_flag = tiers[0] < tiers[1]
            
            # New BTTS formula
            btts_flag = (
                (tiers[2] <= 2 and tiers[1] >= 3) or
                (tiers[3] <= 2 and tiers[0] >= 3) or
                elite or derby
            )
            
            # New Overs formula
            overs_flag = (
                (tiers[4] <= 2 and tiers[1] >= 3) or
                (tiers[5] <= 2 and tiers[0] >= 3)
            )
            
            col_f1.metric("Home Advantage", "✅" if home_adv_flag else "❌", 
                         help="home_da_tier < away_da_tier")
            col_f2.metric("BTTS Pressure", "✅" if btts_flag else "❌",
                         help="Good offense vs weak defense OR Elite/Derby")
            col_f3.metric("Overs Pressure", "✅" if overs_flag else "❌",
                         help="High over threat vs weak defense")
            
            # Check historical patterns
            tier_sig = str(tiers)
            history = get_pattern_history(tier_sig, st.session_state.pending_match['league'])
            
            if history:
                prediction = generate_prediction(history)
                if prediction:
                    st.markdown("---")
                    st.subheader("📊 HISTORICAL PATTERN")
                    
                    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
                    col_h1.metric("Matches", prediction['stats']['total'])
                    col_h2.metric("Prediction", prediction['prediction'])
                    col_h3.metric("Confidence", f"{prediction['confidence']:.0f}%")
                    col_h4.metric("Avg Goals", f"{prediction['stats']['avg_goals']:.1f}")
                    
                    st.info(prediction['explanation'])
                    st.caption(prediction['btts_note'])
                    
                    with st.expander("View historical matches"):
                        for m in history[:5]:
                            home = m.get('home_team', '?')
                            away = m.get('away_team', '?')
                            home_score = m.get('home_goals', '?')
                            away_score = m.get('away_goals', '?')
                            score = f"{home_score if home_score is not None else '?'}-{away_score if away_score is not None else '?'}"
                            btts_icon = "✅" if m.get('actual_btts') else "❌"
                            goals = m.get('actual_goals')
                            goals_display = goals if goals is not None else '?'
                            over_icon = "🔥" if goals is not None and goals >= 3 else "📉" if goals is not None else "❓"
                            st.text(f"• {home} {score} {away} | {btts_icon} BTTS | {over_icon} {goals_display} goals")
            else:
                st.markdown("---")
                st.info("🆕 No historical matches with this exact pattern yet")
        
        # SHOW RESULT ENTRY FORM IMMEDIATELY after GENERATE PREDICTION
        if st.session_state.get('show_result_entry') and st.session_state.get('pending_match'):
            st.markdown("---")
            st.subheader("📥 ENTER ACTUAL RESULT")
            
            with st.form("result_entry_form"):
                col_r1, col_r2 = st.columns(2)
                
                with col_r1:
                    home_goals = st.number_input(f"{st.session_state.pending_match['home_team']} Goals", 0, 10, 0)
                
                with col_r2:
                    away_goals = st.number_input(f"{st.session_state.pending_match['away_team']} Goals", 0, 10, 0)
                
                notes = st.text_input("Notes (penalty, red card, etc.)", "")
                
                # Show preview
                total_goals = home_goals + away_goals
                btts = "✅ YES" if (home_goals > 0 and away_goals > 0) else "❌ NO"
                over = "✅ YES" if total_goals >= 3 else "❌ NO"
                
                st.markdown(f"""
                **Preview:**
                - Score: {home_goals} - {away_goals}
                - Total Goals: {total_goals}
                - BTTS: {btts}
                - Over 2.5: {over}
                """)
                
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                with col_b2:
                    submitted_result = st.form_submit_button("💾 SAVE MATCH WITH RESULT", use_container_width=True, type="primary")
                
                if submitted_result:
                    # Save to database with result
                    match_input = {
                        'home_da': st.session_state.pending_match['home_da'],
                        'away_da': st.session_state.pending_match['away_da'],
                        'home_btts': st.session_state.pending_match['home_btts'],
                        'away_btts': st.session_state.pending_match['away_btts'],
                        'home_over': st.session_state.pending_match['home_over'],
                        'away_over': st.session_state.pending_match['away_over'],
                        'elite': st.session_state.pending_match['elite'],
                        'derby': st.session_state.pending_match['derby'],
                        'relegation': st.session_state.pending_match['relegation']
                    }
                    
                    match_id = save_match(
                        match_input,
                        st.session_state.pending_match['home_team'],
                        st.session_state.pending_match['away_team'],
                        st.session_state.pending_match['league'],
                        home_goals,
                        away_goals,
                        notes
                    )
                    
                    if match_id:
                        st.success(f"✅ Match saved with result! (ID: {match_id})")
                        st.balloons()
                        # Clear session state
                        st.session_state.show_result_entry = False
                        if 'pending_match' in st.session_state:
                            del st.session_state.pending_match
                        st.rerun()
    
    with tab2:
        st.header("🔍 Pattern Discovery")
        min_matches = st.slider("Minimum matches per pattern", 2, 5, 2)
        patterns = discover_patterns(min_matches=min_matches)
        
        if patterns:
            for sig, data in patterns.items():
                with st.expander(f"Pattern {sig} ({data['total']} matches)"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Over 2.5", f"{data['over_pct']:.0f}%")
                    col2.metric("Under 2.5", f"{data['under_pct']:.0f}%")
                    col3.metric("Avg Goals", f"{data['avg_goals']:.1f}")
                    
                    col4, col5 = st.columns(2)
                    col4.metric("BTTS Yes", f"{data['btts_yes_pct']:.0f}%")
                    col5.metric("BTTS No", f"{data['btts_no_pct']:.0f}%")
                    
                    with st.expander("View matches"):
                        for m in data['matches']:
                            home = m.get('home_team', '?')
                            away = m.get('away_team', '?')
                            home_score = m.get('home_goals', '?')
                            away_score = m.get('away_goals', '?')
                            score = f"{home_score if home_score is not None else '?'}-{away_score if away_score is not None else '?'}"
                            st.text(f"• {home} {score} {away} ({m.get('league', '?')})")
        else:
            st.info(f"Add at least {min_matches} completed matches with the same tier pattern to discover patterns")
    
    with tab3:
        st.header("📊 League Statistics")
        leagues = ['EPL', 'BUNDESLIGA', 'SERIE A', 'LA LIGA', 'SUPER LIG', 'AUSTRIAN', 'CHAMPIONSHIP']
        
        for league in leagues:
            matches = get_league_stats(league)
            if matches:
                with st.expander(f"{league} ({len(matches)} matches)"):
                    df_data = []
                    for m in matches:
                        home = m.get('home_team', '?')
                        away = m.get('away_team', '?')
                        home_score = m.get('home_goals')
                        away_score = m.get('away_goals')
                        score = f"{home_score if home_score is not None else '?'}-{away_score if away_score is not None else '?'}"
                        btts_icon = "✅" if m.get('actual_btts') else "❌"
                        goals = m.get('actual_goals')
                        goals_display = goals if goals is not None else '?'
                        over_icon = "🔥" if goals is not None and goals >= 3 else "📉" if goals is not None else "❓"
                        
                        df_data.append({
                            'Date': m.get('match_date', '')[-5:] if m.get('match_date') else '?',
                            'Home': home,
                            'Score': score,
                            'Away': away,
                            'BTTS': btts_icon,
                            'Goals': goals_display,
                            'O/U': over_icon
                        })
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    total = len(matches)
                    overs = sum(1 for m in matches if m.get('actual_goals') is not None and m.get('actual_goals') >= 3)
                    btts_yes = sum(1 for m in matches if m.get('actual_btts'))
                    total_goals = sum(m.get('actual_goals') for m in matches if m.get('actual_goals') is not None)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total", total)
                    col2.metric("Over 2.5", f"{overs}/{total} ({overs/total*100:.0f}%)" if total > 0 else "0/0")
                    col3.metric("BTTS", f"{btts_yes}/{total} ({btts_yes/total*100:.0f}%)" if total > 0 else "0/0")
                    col4.metric("Avg Goals", f"{total_goals/total:.1f}" if total > 0 and total_goals > 0 else "0.0")
    
    with tab4:
        st.header("⚠️ Counter Threat Teams")
        st.markdown("Teams that score more than their BTTS% suggests")
        
        threats = get_counter_threats()
        
        if threats:
            data = []
            for team, stats in threats.items():
                data.append({
                    'Team': team,
                    'Matches': stats['matches'],
                    'BTTS Stat': f"{stats['stat_avg']}%",
                    'Actual BTTS': f"{stats['actual_rate']}%",
                    'Difference': f"+{stats['diff']}%",
                    'Avg Goals': stats['avg_goals']
                })
            
            df = pd.DataFrame(data)
            df = df.sort_values('Difference', ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.info("""
            **What is a Counter Threat?**
            - BTTS stat says they rarely score (<50%)
            - But actual results show they score often (>50%)
            - These teams are dangerous despite weak stats
            """)
        else:
            st.info("No counter threats detected yet. Need at least 3 matches per team.")
    
    with tab5:
        st.header("🎯 Pressure Test")
        st.markdown("### How well do our computed flags predict outcomes?")
        st.markdown("**New Formula:** Good offense vs weak defense OR Elite/Derby")
        
        if supabase:
            try:
                completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
                completed_count = completed.count if hasattr(completed, 'count') else 0
                
                if completed_count >= 5:
                    pressure_results = get_pressure_test_results()
                    
                    if pressure_results:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("BTTS Pressure Flag")
                            btts = pressure_results['btts_pressure']
                            
                            fig = go.Figure(data=[
                                go.Bar(name='High Pressure', x=['BTTS Rate'], y=[btts['high_btts_rate']*100],
                                      marker_color='green', text=[f"{btts['high_btts_rate']*100:.1f}%"],
                                      textposition='outside'),
                                go.Bar(name='Low Pressure', x=['BTTS Rate'], y=[btts['low_btts_rate']*100],
                                      marker_color='red', text=[f"{btts['low_btts_rate']*100:.1f}%"],
                                      textposition='outside')
                            ])
                            fig.update_layout(title=f"BTTS Rate by Pressure Flag (High: {btts['high_count']}, Low: {btts['low_count']})",
                                             yaxis_title="Percentage")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            diff = (btts['high_btts_rate'] - btts['low_btts_rate']) * 100
                            if diff > 10:
                                st.success(f"✅ BTTS Pressure Flag is working! +{diff:.1f}% difference")
                            elif diff < -10:
                                st.warning(f"⚠️ BTTS Pressure Flag is inverted! {diff:.1f}% difference")
                            else:
                                st.info(f"📊 BTTS Pressure Flag shows {diff:.1f}% difference")
                        
                        with col2:
                            st.subheader("Overs Pressure Flag")
                            overs = pressure_results['overs_pressure']
                            
                            fig = go.Figure(data=[
                                go.Bar(name='High Pressure', x=['Over 2.5 Rate'], y=[overs['high_over_rate']*100],
                                      marker_color='green', text=[f"{overs['high_over_rate']*100:.1f}%"],
                                      textposition='outside'),
                                go.Bar(name='Low Pressure', x=['Over 2.5 Rate'], y=[overs['low_over_rate']*100],
                                      marker_color='red', text=[f"{overs['low_over_rate']*100:.1f}%"],
                                      textposition='outside')
                            ])
                            fig.update_layout(title=f"Over 2.5 Rate by Pressure Flag (High: {overs['high_count']}, Low: {overs['low_count']})",
                                             yaxis_title="Percentage")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            diff = (overs['high_over_rate'] - overs['low_over_rate']) * 100
                            if diff > 10:
                                st.success(f"✅ Overs Pressure Flag is working! +{diff:.1f}% difference")
                            elif diff < -10:
                                st.warning(f"⚠️ Overs Pressure Flag is inverted! {diff:.1f}% difference")
                            else:
                                st.info(f"📊 Overs Pressure Flag shows {diff:.1f}% difference")
                        
                        st.markdown("---")
                        
                        col3, col4 = st.columns(2)
                        
                        with col3:
                            st.subheader("Home Advantage Flag")
                            home = pressure_results['home_advantage']
                            
                            fig = go.Figure(data=[
                                go.Bar(name='Home Advantage', x=['Home Win Rate'], y=[home['adv_win_rate']*100],
                                      marker_color='blue', text=[f"{home['adv_win_rate']*100:.1f}%"],
                                      textposition='outside'),
                                go.Bar(name='No Advantage', x=['Home Win Rate'], y=[home['no_adv_win_rate']*100],
                                      marker_color='orange', text=[f"{home['no_adv_win_rate']*100:.1f}%"],
                                      textposition='outside')
                            ])
                            fig.update_layout(title=f"Home Win Rate by Advantage Flag (Adv: {home['adv_count']}, No Adv: {home['no_adv_count']})",
                                             yaxis_title="Percentage")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col4:
                            st.subheader("Importance Score Impact")
                            imp = pressure_results['importance']
                            
                            fig = go.Figure(data=[
                                go.Bar(name='High Importance', x=['Avg Goals'], y=[imp['high_avg_goals']],
                                      marker_color='purple', text=[f"{imp['high_avg_goals']:.1f}"],
                                      textposition='outside'),
                                go.Bar(name='Low Importance', x=['Avg Goals'], y=[imp['low_avg_goals']],
                                      marker_color='gray', text=[f"{imp['low_avg_goals']:.1f}"],
                                      textposition='outside')
                            ])
                            fig.update_layout(title=f"Average Goals by Importance (High: {imp['high_count']}, Low: {imp['low_count']})",
                                             yaxis_title="Goals")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Unable to calculate pressure test results")
                else:
                    st.info(f"Need at least 5 completed matches to run pressure tests. Currently have {completed_count}.")
            except Exception as e:
                st.error(f"Error in pressure test: {e}")
        else:
            st.info("Supabase not connected")
    
    with tab6:
        st.header("📈 Discovery Engine")
        st.markdown("### Live Tracking of 100% Rules")
        
        rule_stats = get_discovery_stats()
        
        if rule_stats:
            # Display perfect rules first
            perfect_rules = []
            other_rules = []
            
            for rule_key, stats in rule_stats.items():
                accuracy = (stats['hits'] / stats['total']) * 100
                rule_data = {
                    'Rule': stats['name'],
                    'Record': f"{stats['hits']}/{stats['total']}",
                    'Accuracy': f"{accuracy:.1f}%",
                    'Matches': stats['total']
                }
                if accuracy == 100:
                    perfect_rules.append(rule_data)
                else:
                    other_rules.append(rule_data)
            
            if perfect_rules:
                st.success("🎯 **Perfect Rules Still Holding:**")
                df_perfect = pd.DataFrame(perfect_rules)
                st.dataframe(df_perfect, use_container_width=True, hide_index=True)
            
            if other_rules:
                st.markdown("---")
                st.subheader("Other Rules")
                df_other = pd.DataFrame(other_rules)
                st.dataframe(df_other, use_container_width=True, hide_index=True)
            
            # Overall stats
            st.markdown("---")
            total_rule_applications = sum(s['total'] for s in rule_stats.values())
            total_rule_hits = sum(s['hits'] for s in rule_stats.values())
            overall_accuracy = (total_rule_hits / total_rule_applications) * 100 if total_rule_applications > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Rule Applications", total_rule_applications)
            col2.metric("Total Hits", total_rule_hits)
            col3.metric("Overall Accuracy", f"{overall_accuracy:.1f}%")
            
        else:
            st.info("No rule data available yet. Complete more matches to track discovery rules.")
        
        # Show recent matches with rule hits
        st.markdown("---")
        st.subheader("Recent Rule-Breaking Matches")
        
        try:
            result = supabase.table('matches')\
                .select('*')\
                .eq('result_entered', True)\
                .not_.is_('rule_hits', 'null')\
                .order('match_date', desc=True)\
                .limit(10)\
                .execute()
            
            if result.data:
                for match in result.data:
                    rules = match.get('rule_hits', {})
                    if rules:
                        failed_rules = [r['name'] for r in rules.values() if not r['hit']]
                        if failed_rules:
                            score = f"{match.get('home_goals', 0)}-{match.get('away_goals', 0)}"
                            st.warning(f"**{match['home_team']} {score} {match['away_team']}** broke: {', '.join(failed_rules[:2])}")
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
