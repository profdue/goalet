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

st.set_page_config(page_title="Discovery Hunter v23.0", page_icon="🏆", layout="wide")

if SUPABASE_AVAILABLE:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
else:
    supabase = None

# ============================================================================
# GOLD RULES - YOUR VERIFIED PRODUCTION RULES (FALLBACK)
# ============================================================================

GOLD_RULES = [
    {
        'name': '🔥 Elite + Home Adv = OVER/BTTS',
        'condition': lambda d: d.get('elite') and d.get('home_adv_flag', False),
        'over': True,
        'btts': True,
        'home_win': 70,
        'away_win': 20,
        'confidence': 80,
        'matches': 10,
        'emoji': '🔥'
    },
    {
        'name': '🔥 home_da=2 & away_da=3 = OVER/BTTS',
        'condition': lambda d: d.get('home_da_tier') == 2 and d.get('away_da_tier') == 3,
        'over': True,
        'btts': True,
        'home_win': 60,
        'away_win': 20,
        'confidence': 80,
        'matches': 10,
        'emoji': '🔥'
    },
    {
        'name': '🔥 Elite + No Home Adv = AWAY OVER/BTTS',
        'condition': lambda d: d.get('elite') and not d.get('home_adv_flag', True),
        'over': True,
        'btts': True,
        'home_win': 17,
        'away_win': 75,
        'confidence': 75,
        'matches': 12,
        'emoji': '🔥'
    },
    {
        'name': '🔥 home_btts=2 & away_btts=2 = OVER/BTTS',
        'condition': lambda d: d.get('home_btts_tier') == 2 and d.get('away_btts_tier') == 2,
        'over': True,
        'btts': True,
        'home_win': 25,
        'away_win': 63,
        'confidence': 75,
        'matches': 8,
        'emoji': '🔥'
    },
    {
        'name': '❄️ home_btts=3 & away_btts=2 = UNDER',
        'condition': lambda d: d.get('home_btts_tier') == 3 and d.get('away_btts_tier') == 2,
        'under': True,
        'confidence': 89,
        'matches': 9,
        'emoji': '❄️'
    },
    {
        'name': '❄️ UNDER Lock (No Adv + No Pressure)',
        'condition': lambda d: not d.get('home_adv_flag', True) and not d.get('btts_pressure_flag', True),
        'under': True,
        'confidence': 77,
        'matches': 17,
        'emoji': '❄️'
    },
    {
        'name': '❄️ home_da=4 & home_btts=4 = UNDER',
        'condition': lambda d: d.get('home_da_tier') == 4 and d.get('home_btts_tier') == 4,
        'under': True,
        'confidence': 78,
        'matches': 9,
        'emoji': '❄️'
    },
    {
        'name': '❄️ home_btts=4 & away_btts=3 = UNDER',
        'condition': lambda d: d.get('home_btts_tier') == 4 and d.get('away_btts_tier') == 3,
        'under': True,
        'confidence': 75,
        'matches': 8,
        'emoji': '❄️'
    },
    {
        'name': '✈️ Away Win Lock',
        'condition': lambda d: d.get('home_da_tier') == 3 and d.get('away_da_tier') == 2,
        'away_win': 80,
        'home_win': 20,
        'confidence': 80,
        'matches': 10,
        'emoji': '✈️'
    }
]

# ============================================================================
# DATABASE FUNCTIONS FOR PATTERN DISCOVERY
# ============================================================================

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
            # Add readable names for patterns
            df['pattern_name'] = df['pattern_code'].apply(lambda x: decode_pattern_code(x))
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error getting pattern stats: {e}")
        return pd.DataFrame()

def get_gold_pattern_performance():
    """Get performance of gold patterns vs discovery rates"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        # This is a complex join - we'll do it in two steps for simplicity
        gold_result = supabase.table('gold_patterns')\
            .select('*')\
            .eq('active', True)\
            .execute()
        
        if not gold_result.data:
            return pd.DataFrame()
        
        data = []
        for gp in gold_result.data:
            # Get tracking data for this pattern
            track_result = supabase.table('pattern_tracking')\
                .select('*')\
                .eq('pattern_code', gp['pattern_code'])\
                .execute()
            
            if track_result.data and len(track_result.data) > 0:
                pt = track_result.data[0]
                data.append({
                    'pattern_name': gp['pattern_name'],
                    'pattern_code': gp['pattern_code'],
                    'tier': gp.get('confidence_tier', 'GOLD'),
                    'discovery_matches': gp.get('discovery_sample_size', 0),
                    'current_matches': pt.get('total_matches', 0),
                    'discovery_rate': gp.get('discovery_home_win_rate', 0),
                    'current_rate': pt.get('current_home_win_rate', 0),
                    'confidence': pt.get('confidence_score', 0),
                    'trend': pt.get('home_trend', 'STABLE'),
                    'variance': (pt.get('current_home_win_rate', 0) - (gp.get('discovery_home_win_rate') or 0)) if gp.get('discovery_home_win_rate') else 0
                })
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error getting gold performance: {e}")
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

def decode_pattern_code(code):
    """Convert pattern code to readable description"""
    try:
        parts = code.split(',')
        if len(parts) != 4:
            return code
        
        home = "Home Adv" if parts[0] == 'T' else "No Home Adv"
        over = "Over Press" if parts[1] == 'T' else "No Over Press"
        btts = "BTTS Press" if parts[2] == 'T' else "No BTTS Press"
        imp = f"Imp:{parts[3]}"
        
        return f"{home} | {over} | {btts} | {imp}"
    except:
        return code

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
# PREDICTION ENGINE (Enhanced with Database)
# ============================================================================

def analyze_match(data):
    """Analyze match and return predictions - checks database first, falls back to gold rules"""
    
    # Calculate tiers
    home_da_tier = calculate_tier(data['home_da'], 'da')
    away_da_tier = calculate_tier(data['away_da'], 'da')
    home_btts_tier = calculate_tier(data['home_btts'], 'btts')
    away_btts_tier = calculate_tier(data['away_btts'], 'btts')
    home_over_tier = calculate_tier(data['home_over'], 'over')
    away_over_tier = calculate_tier(data['away_over'], 'over')
    
    # Calculate flags (matches what database does)
    home_adv_flag = home_da_tier <= 2 and away_da_tier >= 3
    btts_pressure_flag = (home_btts_tier <= 2 and away_btts_tier <= 2)
    
    # Calculate overs pressure flag (for pattern code)
    overs_pressure_flag = (home_over_tier <= 2 and away_da_tier >= 3) or (away_over_tier <= 2 and home_da_tier >= 3)
    
    # Calculate importance (matches database generated column)
    importance = (1 if data.get('elite', False) else 0) + (1 if data.get('derby', False) else 0) + (1 if data.get('relegation', False) else 0)
    
    # Generate pattern code (matches what database trigger does)
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
        'pattern_code': pattern_code
    }
    
    # FIRST: Check database for this pattern
    db_pattern = get_pattern_prediction(pattern_code)
    matches = []
    
    if db_pattern and db_pattern.get('total_matches', 0) >= 3:
        # Use database pattern
        db_match = {
            'name': f"📊 Database Pattern: {pattern_code}",
            'from_db': True,
            'over': db_pattern.get('current_over_rate', 0) >= 60,
            'under': db_pattern.get('current_over_rate', 0) <= 40,
            'btts': db_pattern.get('current_btts_rate', 0) >= 60,
            'confidence': db_pattern.get('confidence_score', 70),
            'matches': db_pattern.get('total_matches', 0),
            'emoji': '📊',
            'home_win_rate': db_pattern.get('current_home_win_rate', 50),
            'over_rate': db_pattern.get('current_over_rate', 50),
            'btts_rate': db_pattern.get('current_btts_rate', 50)
        }
        matches.append(db_match)
    
    # SECOND: Check gold rules
    for rule in GOLD_RULES:
        try:
            if rule['condition'](enhanced_data):
                # Mark if this is also in database
                rule_copy = rule.copy()
                rule_copy['from_db'] = False
                matches.append(rule_copy)
        except:
            continue
    
    # If no matches at all, use general signals
    if not matches:
        # OVER 2.5 signal
        if (home_over_tier <= 2 and away_over_tier <= 2) or (home_over_tier == 1 or away_over_tier == 1):
            matches.append({
                'name': '📈 OVER 2.5 Signal',
                'over': True,
                'confidence': 70,
                'emoji': '📈',
                'from_db': False
            })
        
        # UNDER 2.5 signal
        if (home_over_tier >= 3 and away_over_tier >= 3) or (home_da_tier <= 2 and away_da_tier <= 2):
            matches.append({
                'name': '📉 UNDER 2.5 Signal',
                'under': True,
                'confidence': 70,
                'emoji': '📉',
                'from_db': False
            })
        
        # BTTS signal
        if home_btts_tier <= 2 and away_btts_tier <= 2:
            matches.append({
                'name': '⚽ BTTS Yes',
                'btts': True,
                'confidence': 75,
                'emoji': '⚽',
                'from_db': False
            })
        
        # Clean sheets possible
        if home_btts_tier >= 3 and away_btts_tier >= 3:
            matches.append({
                'name': '🧤 BTTS No',
                'btts': False,
                'confidence': 70,
                'emoji': '🧤',
                'from_db': False
            })
    
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
# DATABASE FUNCTIONS - FIXED VERSION (NO importance_score)
# ============================================================================

def save_match(data, home_goals=None, away_goals=None):
    if supabase is None:
        return None
    
    try:
        # Build match data - NO importance_score (it's generated by database)
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
            # importance_score is GENERATED - don't include it
            # pattern_code is set by database trigger - don't include it
        }
        
        if home_goals is not None:
            match_data['home_goals'] = home_goals
            match_data['away_goals'] = away_goals
        
        # Insert the match
        result = supabase.table('matches').insert(match_data).execute()
        
        if result.data and len(result.data) > 0:
            match_id = result.data[0]['id']
            st.success(f"✅ Match #{match_id} saved! Database will calculate pattern automatically.")
            return match_id
        else:
            st.error("No data returned from insert")
            return None
            
    except Exception as e:
        st.error(f"Error saving match: {e}")
        return None

def get_rule_performance():
    if supabase is None:
        return {}
    
    try:
        # Try to use the view first
        try:
            result = supabase.table('rule_performance').select('*').execute()
            if result.data:
                rules_data = result.data
            else:
                # Fallback to direct calculation
                matches = supabase.table('matches').select('rule_hits').eq('result_entered', True).execute()
                rules_data = []
                rule_stats = {}
                
                for match in matches.data:
                    rules = match.get('rule_hits')
                    if not rules:
                        continue
                    
                    if isinstance(rules, str):
                        rules = json.loads(rules)
                    
                    for key, rule in rules.items():
                        rule_name = rule.get('name', key)
                        if rule_name not in rule_stats:
                            rule_stats[rule_name] = {'total': 0, 'hits': 0}
                        rule_stats[rule_name]['total'] += 1
                        if rule.get('hit', False):
                            rule_stats[rule_name]['hits'] += 1
                
                for name, stats in rule_stats.items():
                    accuracy = (stats['hits'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    rules_data.append({
                        'rule_name': name,
                        'total_applications': stats['total'],
                        'hits': stats['hits'],
                        'accuracy': round(accuracy, 1)
                    })
        except:
            return {}
        
        # Separate by category using emoji and keyword detection
        over_rules = []
        under_rules = []
        outcome_rules = []
        gray_rules = []
        
        for rule in rules_data:
            name = rule.get('rule_name', '')
            
            # OVER rules - look for 🔥 or OVER or DOUBLE PRESSURE
            if '🔥' in name or 'OVER' in name or 'DOUBLE PRESSURE' in name:
                over_rules.append(rule)
            # UNDER rules - look for ❄️ or UNDER
            elif '❄️' in name or 'UNDER' in name:
                under_rules.append(rule)
            # GRAY zone - look for ⚪ or GRAY
            elif '⚪' in name or 'GRAY' in name:
                gray_rules.append(rule)
            # Everything else is outcome
            else:
                outcome_rules.append(rule)
        
        return {
            'over': sorted(over_rules, key=lambda x: x['accuracy'], reverse=True),
            'under': sorted(under_rules, key=lambda x: x['accuracy'], reverse=True),
            'outcome': sorted(outcome_rules, key=lambda x: x['accuracy'], reverse=True),
            'gray': gray_rules
        }
    except Exception as e:
        st.error(f"Error getting rule performance: {e}")
        return {}

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
    st.title("🏆 Discovery Hunter v23.0")
    st.markdown("### Self-Learning Pattern Discovery • 9 Gold Rules • Database Powered")
    
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
            
            # Show database patterns count
            patterns = get_pattern_stats(3)
            if not patterns.empty:
                st.metric("Active Patterns", len(patterns))
            
            st.markdown("---")
            st.subheader("🏆 Gold Rules")
            for rule in GOLD_RULES[:3]:  # Show top 3
                st.success(f"{rule['emoji']} {rule['name'][:25]}...")
        except Exception as e:
            st.info("No data yet")
        
        st.markdown("---")
        st.markdown("**TIER KEY**")
        st.markdown("1💥 Elite | 2⚡ Strong | 3📊 Average | 4🐢 Weak")
    
    # Main tabs - Added Pattern Discovery and Gold Monitor
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📝 New Match", 
        "📊 Rules Engine", 
        "📈 League Stats", 
        "📋 Recent Matches", 
        "🔮 Upcoming",
        "🔍 Pattern Discovery",
        "🏆 Gold Monitor"
    ])
    
    with tab1:
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
            
            # Show importance score preview (calculated, not stored)
            importance_preview = (1 if elite else 0) + (1 if derby else 0) + (1 if relegation else 0)
            st.caption(f"Importance Score Preview: {importance_preview} (will be auto-generated by database)")
            
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
                # Store match data (NO importance_score - will be generated)
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
                
                # Run analysis
                st.session_state.analysis_result = analyze_match(st.session_state.pending_match)
                st.rerun()
        
        # SHOW PREDICTION RESULTS (before result entry)
        if st.session_state.analysis_result and st.session_state.pending_match:
            data = st.session_state.pending_match
            analysis = st.session_state.analysis_result
            
            st.markdown("---")
            
            # Display pattern code if available
            if 'pattern_code' in analysis:
                st.info(f"📋 Pattern Code: **{analysis['pattern_code']}**")
            
            # Display tiers in a nice format
            col_t1, col_t2, col_t3 = st.columns(3)
            
            with col_t1:
                st.markdown("**🏠 HOME**")
                st.markdown(f"DA: {tier_to_emoji(analysis['home_da_tier'], 'da')} {get_tier_description(analysis['home_da_tier'], 'da')}")
                st.markdown(f"BTTS: {tier_to_emoji(analysis['home_btts_tier'], 'btts')} {get_tier_description(analysis['home_btts_tier'], 'btts')}")
                st.markdown(f"OVER: {tier_to_emoji(analysis['home_over_tier'], 'over')} {get_tier_description(analysis['home_over_tier'], 'over')}")
            
            with col_t2:
                st.markdown("**⚡ FLAGS**")
                if analysis['home_adv_flag']:
                    st.markdown("🏠 **Home Advantage**")
                if analysis['btts_pressure_flag']:
                    st.markdown("⚽ **BTTS Pressure**")
                if data.get('elite', False):
                    st.markdown("⭐ **Elite Match**")
                if data.get('derby', False):
                    st.markdown("🏆 **Derby**")
                if data.get('relegation', False):
                    st.markdown("⚠️ **Relegation Battle**")
                
                # Show importance preview
                importance_val = (1 if data.get('elite', False) else 0) + (1 if data.get('derby', False) else 0) + (1 if data.get('relegation', False) else 0)
                st.markdown(f"📊 **Importance: {importance_val}**")
            
            with col_t3:
                st.markdown("**✈️ AWAY**")
                st.markdown(f"DA: {tier_to_emoji(analysis['away_da_tier'], 'da')} {get_tier_description(analysis['away_da_tier'], 'da')}")
                st.markdown(f"BTTS: {tier_to_emoji(analysis['away_btts_tier'], 'btts')} {get_tier_description(analysis['away_btts_tier'], 'btts')}")
                st.markdown(f"OVER: {tier_to_emoji(analysis['away_over_tier'], 'over')} {get_tier_description(analysis['away_over_tier'], 'over')}")
            
            st.markdown("---")
            
            # PREDICTION SECTION
            st.subheader("🎯 PREDICTION")
            
            if analysis['matches']:
                # Show source indicator
                if analysis.get('has_db_pattern', False):
                    st.success("✅ Using database pattern with historical data")
                
                # Show all matching rules
                for rule in analysis['matches']:
                    confidence = rule.get('confidence', 70)
                    
                    # Different styling for database vs gold rules
                    if rule.get('from_db', False):
                        box_color = "#4CAF5015"  # Database green
                        border_color = "#4CAF50"
                        source_badge = "📊 DB"
                    else:
                        if confidence >= 80:
                            box_color = "#00ff0015"  # Green
                            border_color = "#00ff00"
                        elif confidence >= 75:
                            box_color = "#ffff0015"  # Yellow
                            border_color = "#ffff00"
                        else:
                            box_color = "#ffaa0015"  # Orange
                            border_color = "#ffaa00"
                        source_badge = "🏆 GOLD"
                    
                    with st.container():
                        # Build the HTML safely
                        html_content = f"""
                        <div style="background-color: {box_color}; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid {border_color};">
                            <h3 style="margin:0">{rule['emoji']} {rule['name']} <span style="float:right">{source_badge} | {confidence}%</span></h3>
                            <p style="margin:5px 0 0 0; font-size: 18px;">
                        """
                        
                        # Add outcome indicators
                        outcomes = []
                        if rule.get('over'):
                            outcomes.append("🔥 OVER 2.5")
                        if rule.get('under'):
                            outcomes.append("❄️ UNDER 2.5")
                        if rule.get('btts') == True:
                            outcomes.append("⚽ BTTS Yes")
                        if rule.get('btts') == False:
                            outcomes.append("🧤 BTTS No")
                        if rule.get('home_win_rate', 0) > 50 or rule.get('home_win', 0) > 50:
                            outcomes.append("🏠 HOME WIN")
                        if rule.get('away_win', 0) > 50:
                            outcomes.append("✈️ AWAY WIN")
                        
                        if outcomes:
                            html_content += " ".join(outcomes)
                        else:
                            html_content += "⚖️ NO EDGE"
                        
                        html_content += f"""
                            </p>
                            <p style="margin:5px 0 0 0; color: #888;">
                        """
                        
                        # Add stats
                        stats = []
                        if rule.get('matches'):
                            stats.append(f"Matches: {rule.get('matches')}")
                        if rule.get('home_win_rate'):
                            stats.append(f"Home: {rule.get('home_win_rate')}%")
                        if rule.get('over_rate'):
                            stats.append(f"Over: {rule.get('over_rate')}%")
                        if rule.get('btts_rate'):
                            stats.append(f"BTTS: {rule.get('btts_rate')}%")
                        
                        html_content += " | ".join(stats)
                        html_content += "</p></div>"
                        
                        st.markdown(html_content, unsafe_allow_html=True)
            else:
                # No gold rules matched - show general signals
                st.info("⚠️ No patterns matched. Based on general signals:")
                
                col_s1, col_s2 = st.columns(2)
                
                with col_s1:
                    if analysis['home_over_tier'] <= 2 or analysis['away_over_tier'] <= 2:
                        st.success("📈 **OVER 2.5 Possible**")
                    if analysis['home_btts_tier'] <= 2 and analysis['away_btts_tier'] <= 2:
                        st.success("⚽ **BTTS Likely**")
                
                with col_s2:
                    if analysis['home_over_tier'] >= 3 and analysis['away_over_tier'] >= 3:
                        st.info("📉 **UNDER 2.5 Possible**")
                    if analysis['home_btts_tier'] >= 3 and analysis['away_btts_tier'] >= 3:
                        st.info("🧤 **Clean Sheet Possible**")
            
            # RECOMMENDATION
            st.markdown("---")
            st.subheader("💡 RECOMMENDATION")
            
            # Find best pick
            best_pick = None
            for rule in analysis['matches']:
                if rule.get('confidence', 0) >= 75:
                    best_pick = rule
                    break
            
            if best_pick:
                pick_emoji = "🔒" if best_pick.get('confidence', 0) >= 80 else "✅"
                
                if best_pick.get('over'):
                    st.markdown(f"## {pick_emoji} **BET: OVER 2.5** @ {best_pick.get('confidence', 75)}% confidence")
                elif best_pick.get('under'):
                    st.markdown(f"## {pick_emoji} **BET: UNDER 2.5** @ {best_pick.get('confidence', 75)}% confidence")
                elif best_pick.get('btts') == True:
                    st.markdown(f"## {pick_emoji} **BET: BTTS YES** @ {best_pick.get('confidence', 75)}% confidence")
                elif best_pick.get('btts') == False:
                    st.markdown(f"## {pick_emoji} **BET: BTTS NO** @ {best_pick.get('confidence', 75)}% confidence")
                elif best_pick.get('home_win_rate', 0) > 50 or best_pick.get('home_win', 0) > 50:
                    team = data['home_team']
                    rate = best_pick.get('home_win_rate', best_pick.get('home_win', 75))
                    st.markdown(f"## {pick_emoji} **BET: {team} TO WIN** @ {rate}%")
                elif best_pick.get('away_win', 0) > 50:
                    st.markdown(f"## {pick_emoji} **BET: {data['away_team']} TO WIN** @ {best_pick.get('away_win', 75)}%")
            else:
                if analysis['home_over_tier'] <= 2 and analysis['away_over_tier'] <= 2:
                    st.markdown("## 📈 **CONSIDER: OVER 2.5** (Signal strength: 70%)")
                elif analysis['home_over_tier'] >= 3 and analysis['away_over_tier'] >= 3:
                    st.markdown("## 📉 **CONSIDER: UNDER 2.5** (Signal strength: 70%)")
                else:
                    st.markdown("## ⚖️ **NO CLEAR EDGE** (Avoid or small stake)")
            
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
                
                total = home_goals + away_goals
                
                # Show if prediction was correct
                if analysis['matches']:
                    for rule in analysis['matches']:
                        if rule.get('over'):
                            result_text = "✅ CORRECT" if total >= 3 else "❌ INCORRECT"
                            st.info(f"**Prediction:** OVER 2.5 | **Result:** {total} goals | {result_text}")
                        elif rule.get('under'):
                            result_text = "✅ CORRECT" if total < 3 else "❌ INCORRECT"
                            st.info(f"**Prediction:** UNDER 2.5 | **Result:** {total} goals | {result_text}")
                
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                with col_b2:
                    saved = st.form_submit_button("💾 SAVE MATCH", type="primary", use_container_width=True)
                
                if saved:
                    # Save match (NO importance_score or pattern_code - database handles it)
                    match_id = save_match(data, home_goals, away_goals)
                    if match_id:
                        st.balloons()
                        st.session_state.pending_match = None
                        st.session_state.analysis_result = None
                        st.rerun()
    
    with tab2:
        st.header("📊 Rules Engine")
        st.markdown("### Live Rule Performance")
        
        rules = get_rule_performance()
        
        if rules:
            # OVER RULES
            if rules.get('over'):
                with st.expander("🔥 OVER 2.5 RULES", expanded=True):
                    over_df = pd.DataFrame(rules['over'])
                    if not over_df.empty:
                        st.dataframe(
                            over_df[['rule_name', 'total_applications', 'hits', 'accuracy']], 
                            hide_index=True, 
                            use_container_width=True
                        )
            
            # UNDER RULES
            if rules.get('under'):
                with st.expander("❄️ UNDER 2.5 RULES", expanded=True):
                    under_df = pd.DataFrame(rules['under'])
                    if not under_df.empty:
                        st.dataframe(
                            under_df[['rule_name', 'total_applications', 'hits', 'accuracy']], 
                            hide_index=True, 
                            use_container_width=True
                        )
            
            # OUTCOME RULES
            if rules.get('outcome'):
                with st.expander("🎯 MATCH OUTCOME RULES", expanded=False):
                    outcome_df = pd.DataFrame(rules['outcome'])
                    if not outcome_df.empty:
                        st.dataframe(
                            outcome_df[['rule_name', 'total_applications', 'hits', 'accuracy']], 
                            hide_index=True, 
                            use_container_width=True
                        )
            
            # GRAY ZONE
            if rules.get('gray'):
                with st.expander("⚪ GRAY ZONE (No Edge)", expanded=False):
                    gray_df = pd.DataFrame(rules['gray'])
                    if not gray_df.empty:
                        st.dataframe(
                            gray_df[['rule_name', 'total_applications']], 
                            hide_index=True, 
                            use_container_width=True
                        )
            
            # Summary metrics
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            total_over = sum(r.get('total_applications', 0) for r in rules.get('over', []))
            total_under = sum(r.get('total_applications', 0) for r in rules.get('under', []))
            total_outcome = sum(r.get('total_applications', 0) for r in rules.get('outcome', []))
            total_rules = len(rules.get('over', [])) + len(rules.get('under', [])) + len(rules.get('outcome', []))
            
            col1.metric("Total OVER Applications", total_over)
            col2.metric("Total UNDER Applications", total_under)
            col3.metric("Total OUTCOME Applications", total_outcome)
            col4.metric("Total Rules", total_rules)
        else:
            st.info("No rule data available yet. Add matches to discover patterns.")
    
    with tab3:
        st.header("📈 League Statistics")
        
        stats = get_league_stats()
        if stats:
            data = []
            for league, stat in stats.items():
                data.append({
                    'League': league,
                    'Matches': stat['matches'],
                    'Avg Goals': stat['avg_goals'],
                    'BTTS %': stat['btts_rate'],
                    'Over %': stat['over_rate']
                })
            
            df = pd.DataFrame(data)
            df = df.sort_values('Matches', ascending=False)
            
            st.dataframe(df, hide_index=True, use_container_width=True)
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(df, x='League', y='Avg Goals',
                            title='Average Goals by League',
                            color='Avg Goals',
                            color_continuous_scale='RdYlGn')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(df, x='League', y=['BTTS %', 'Over %'],
                            title='BTTS & Over Rates by League',
                            barmode='group')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No league data available yet. Add completed matches to see statistics.")
    
    with tab4:
        st.header("📋 Recent Matches")
        
        matches = get_recent_matches(20)
        if matches:
            data = []
            for m in matches:
                # Get rule summary
                rules = m.get('rule_hits', {})
                if isinstance(rules, str):
                    try:
                        rules = json.loads(rules)
                    except:
                        rules = {}
                
                rule_count = len(rules) if rules else 0
                gold_count = 0
                if rules:
                    for rule in rules.values():
                        if rule.get('hit') and ('LOCK' in rule.get('name', '') or 'GRAND' in rule.get('name', '')):
                            gold_count += 1
                
                total_goals = m.get('home_goals', 0) + m.get('away_goals', 0)
                
                data.append({
                    'Date': m.get('match_date', '')[-5:] if m.get('match_date') else '?',
                    'Home': m.get('home_team', ''),
                    'Score': f"{m.get('home_goals', 0)}-{m.get('away_goals', 0)}",
                    'Away': m.get('away_team', ''),
                    'League': m.get('league', ''),
                    'Total': total_goals,
                    'Pattern': m.get('pattern_code', '')[:8] if m.get('pattern_code') else '',
                    'Rules': rule_count,
                    '🏆': '🏆' * gold_count if gold_count else ''
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No completed matches yet.")
    
    with tab5:
        st.header("🔮 Upcoming Matches")
        st.markdown("### Matches with Preview Rules")
        
        matches = get_upcoming_matches(20)
        if matches:
            data = []
            for m in matches:
                # Check for preview rules
                rules = m.get('rule_hits', {})
                if isinstance(rules, str):
                    try:
                        rules = json.loads(rules)
                    except:
                        rules = {}
                
                has_preview = False
                if rules:
                    for rule in rules.values():
                        if 'PREVIEW' in rule.get('name', ''):
                            has_preview = True
                            break
                
                data.append({
                    'Date': m.get('match_date', '')[-5:] if m.get('match_date') else '?',
                    'Home': m.get('home_team', ''),
                    'Away': m.get('away_team', ''),
                    'League': m.get('league', ''),
                    'Preview': '🔮' if has_preview else ''
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No upcoming matches.")
    
    with tab6:
        st.header("🔍 Pattern Discovery")
        st.markdown("### Live Patterns from Database (Self-Learning)")
        
        min_matches = st.slider("Minimum Matches", 3, 20, 5, key="pattern_min_matches")
        
        patterns = get_pattern_stats(min_matches)
        
        if not patterns.empty:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Patterns", len(patterns))
            col2.metric("Avg Confidence", f"{patterns['confidence_score'].mean():.1f}%")
            col3.metric("Highest Confidence", f"{patterns['confidence_score'].max():.1f}%")
            col4.metric("Most Matches", int(patterns['total_matches'].max()))
            
            # Display patterns
            st.dataframe(
                patterns[['pattern_code', 'pattern_name', 'total_matches', 
                         'current_home_win_rate', 'current_over_rate', 'current_btts_rate',
                         'confidence_score', 'home_trend']],
                hide_index=True,
                use_container_width=True
            )
            
            # Visualization
            fig = px.scatter(patterns, x='total_matches', y='confidence_score',
                           size='confidence_score', color='home_trend',
                           hover_data=['pattern_code'],
                           title='Pattern Confidence vs Sample Size')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No patterns found with {min_matches}+ matches. Keep adding data!")
    
    with tab7:
        st.header("🏆 Gold Monitor")
        st.markdown("### Tracking Your Verified Gold Patterns")
        
        gold_perf = get_gold_pattern_performance()
        
        if not gold_perf.empty:
            # Highlight degrading patterns
            degrading = gold_perf[abs(gold_perf['variance']) > 10]
            if not degrading.empty:
                st.warning("⚠️ Some gold patterns are showing significant variance!")
            
            # Display gold pattern performance
            st.dataframe(
                gold_perf[['pattern_name', 'tier', 'discovery_matches', 'current_matches',
                          'discovery_rate', 'current_rate', 'variance', 'confidence', 'trend']],
                hide_index=True,
                use_container_width=True
            )
            
            # Visualization
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Discovery Rate',
                x=gold_perf['pattern_name'],
                y=gold_perf['discovery_rate']
            ))
            fig.add_trace(go.Bar(
                name='Current Rate',
                x=gold_perf['pattern_name'],
                y=gold_perf['current_rate']
            ))
            fig.update_layout(title='Gold Patterns: Discovery vs Current Performance',
                            barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No gold patterns found in database.")

if __name__ == "__main__":
    main()
