import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import re

# Try to import supabase with error handling
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Supabase module not installed. Database features disabled. Run: pip install supabase")

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v14.0",
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
# TIER FUNCTIONS - DEFINED ONCE AT THE TOP
# ============================================================================

def calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over):
    """Calculate tiers - ONLY returns 1-4"""
    
    def da_tier(value):
        if value >= 70: return 1
        if value >= 55: return 2
        if value >= 40: return 3
        return 4
    
    def btts_tier(value):
        if value >= 65: return 1
        if value >= 55: return 2
        if value >= 45: return 3
        return 4
    
    def over_tier(value):
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
    """Get text description of tier"""
    if category == 'da':
        descriptions = ["Elite Attack", "Strong Attack", "Average Attack", "Weak Attack"]
    elif category == 'btts':
        descriptions = ["Always Scores", "Usually Scores", "50/50", "Rarely Scores"]
    else:
        descriptions = ["Goal Fest", "Goals Likely", "50/50", "Goals Unlikely"]
    return descriptions[tier-1]

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def save_match(match_input, home_team, away_team, league):
    """Save match to Supabase"""
    
    if supabase is None:
        st.error("Supabase not connected")
        return None
    
    try:
        # Calculate tiers using the function above
        tiers = calculate_tiers(
            match_input['home_da'],
            match_input['away_da'],
            match_input['home_btts'],
            match_input['away_btts'],
            match_input['home_over'],
            match_input['away_over']
        )
        
        # Debug - verify tiers are 1-4 only
        for tier in tiers:
            if tier < 1 or tier > 4:
                st.error(f"INVALID TIER CALCULATED: {tiers}")
                return None
        
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
            'result_entered': False,
            'data_quality_flag': False
        }
        
        result = supabase.table('matches').insert(data).execute()
        return result.data[0]['id']
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
        return True
    except Exception as e:
        st.error(f"Error updating result: {e}")
        return False

def get_pattern_history(tier_signature, league=None, min_matches=1):
    """Get historical matches with same tier signature"""
    
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
        
        if len(result.data) >= min_matches:
            return result.data
        return []
    except Exception as e:
        st.error(f"Error querying patterns: {e}")
        return []

def get_league_stats(league):
    """Get all completed matches for a league"""
    
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
    """Auto-discover patterns from database"""
    
    if supabase is None:
        return {}
    
    try:
        result = supabase.table('matches')\
            .select('*')\
            .eq('result_entered', True)\
            .execute()
        
        matches = result.data
        
        # Group by tier signature
        patterns = {}
        for match in matches:
            sig = match.get('tier_signature')
            if not sig:
                continue
            if sig not in patterns:
                patterns[sig] = []
            patterns[sig].append(match)
        
        # Analyze each pattern
        insights = {}
        for sig, matches_list in patterns.items():
            if len(matches_list) >= min_matches:
                total = len(matches_list)
                
                # Over/Under stats
                overs = sum(1 for m in matches_list if m.get('actual_goals', 0) >= 3)
                unders = total - overs
                
                # BTTS/No BTTS stats
                btts_yes = sum(1 for m in matches_list if m.get('actual_btts', False))
                btts_no = total - btts_yes
                
                # Pressure flag accuracy
                high_pressure_btts = [m for m in matches_list if m.get('btts_pressure_flag', False)]
                high_pressure_overs = [m for m in matches_list if m.get('overs_pressure_flag', False)]
                
                btts_pressure_accuracy = 0
                if high_pressure_btts:
                    btts_pressure_accuracy = sum(1 for m in high_pressure_btts if m.get('actual_btts')) / len(high_pressure_btts)
                
                overs_pressure_accuracy = 0
                if high_pressure_overs:
                    overs_pressure_accuracy = sum(1 for m in high_pressure_overs if m.get('actual_goals', 0) >= 3) / len(high_pressure_overs)
                
                # Home advantage impact
                home_adv_matches = [m for m in matches_list if m.get('home_advantage_flag', False)]
                home_adv_win_rate = 0
                if home_adv_matches:
                    home_adv_win_rate = sum(1 for m in home_adv_matches 
                                           if m.get('home_goals', 0) > m.get('away_goals', 0)) / len(home_adv_matches)
                
                insights[sig] = {
                    'total': total,
                    'over_pct': (overs / total) * 100,
                    'under_pct': (unders / total) * 100,
                    'btts_yes_pct': (btts_yes / total) * 100,
                    'btts_no_pct': (btts_no / total) * 100,
                    'avg_goals': sum(m.get('actual_goals', 0) for m in matches_list) / total,
                    'btts_pressure_accuracy': btts_pressure_accuracy * 100,
                    'overs_pressure_accuracy': overs_pressure_accuracy * 100,
                    'home_adv_win_rate': home_adv_win_rate * 100,
                    'matches': matches_list
                }
        
        return insights
    except Exception as e:
        st.error(f"Error discovering patterns: {e}")
        return {}

def get_counter_threats(league=None):
    """Identify teams that consistently score despite low BTTS stats"""
    
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
        
        # Track team performance
        team_stats = {}
        for match in matches:
            # Home team
            if match['home_team'] not in team_stats:
                team_stats[match['home_team']] = {
                    'matches': [],
                    'btts_stat': [],
                    'actual_btts': [],
                    'goals_scored': []
                }
            team_stats[match['home_team']]['btts_stat'].append(match['home_btts'])
            team_stats[match['home_team']]['actual_btts'].append(1 if match['actual_btts'] else 0)
            team_stats[match['home_team']]['goals_scored'].append(match.get('home_goals', 0))
            team_stats[match['home_team']]['matches'].append(match)
            
            # Away team
            if match['away_team'] not in team_stats:
                team_stats[match['away_team']] = {
                    'matches': [],
                    'btts_stat': [],
                    'actual_btts': [],
                    'goals_scored': []
                }
            team_stats[match['away_team']]['btts_stat'].append(match['away_btts'])
            team_stats[match['away_team']]['actual_btts'].append(1 if match['actual_btts'] else 0)
            team_stats[match['away_team']]['goals_scored'].append(match.get('away_goals', 0))
            team_stats[match['away_team']]['matches'].append(match)
        
        # Find counter threats
        threats = {}
        for team, stats in team_stats.items():
            if len(stats['matches']) >= 3:
                avg_stat = np.mean(stats['btts_stat'])
                actual_rate = (sum(stats['actual_btts']) / len(stats['actual_btts'])) * 100
                avg_goals = np.mean(stats['goals_scored'])
                
                if (avg_stat < 50 and actual_rate > 50) or avg_goals > 1.2:
                    threats[team] = {
                        'stat_avg': round(avg_stat, 1),
                        'actual_rate': round(actual_rate, 1),
                        'avg_goals': round(avg_goals, 2),
                        'matches': len(stats['matches']),
                        'diff': round(actual_rate - avg_stat, 1)
                    }
        
        return threats
    except Exception as e:
        st.error(f"Error analyzing counter threats: {e}")
        return {}

def get_pressure_test_results():
    """Analyze how well pressure flags predict outcomes"""
    
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
        
        # Get computed columns from database
        btts_high = [m for m in matches if m.get('btts_pressure_flag', False)]
        btts_low = [m for m in matches if not m.get('btts_pressure_flag', False)]
        overs_high = [m for m in matches if m.get('overs_pressure_flag', False)]
        overs_low = [m for m in matches if not m.get('overs_pressure_flag', False)]
        home_adv = [m for m in matches if m.get('home_advantage_flag', False)]
        no_home_adv = [m for m in matches if not m.get('home_advantage_flag', False)]
        high_importance = [m for m in matches if m.get('importance_score', 0) >= 2]
        low_importance = [m for m in matches if m.get('importance_score', 0) == 0]
        
        results = {
            'btts_pressure': {
                'high_count': len(btts_high),
                'high_btts_rate': sum(1 for m in btts_high if m.get('actual_btts')) / len(btts_high) if btts_high else 0,
                'low_count': len(btts_low),
                'low_btts_rate': sum(1 for m in btts_low if m.get('actual_btts')) / len(btts_low) if btts_low else 0,
            },
            'overs_pressure': {
                'high_count': len(overs_high),
                'high_over_rate': sum(1 for m in overs_high if m.get('actual_goals', 0) >= 3) / len(overs_high) if overs_high else 0,
                'low_count': len(overs_low),
                'low_over_rate': sum(1 for m in overs_low if m.get('actual_goals', 0) >= 3) / len(overs_low) if overs_low else 0,
            },
            'home_advantage': {
                'adv_count': len(home_adv),
                'adv_win_rate': sum(1 for m in home_adv if m.get('home_goals', 0) > m.get('away_goals', 0)) / len(home_adv) if home_adv else 0,
                'no_adv_count': len(no_home_adv),
                'no_adv_win_rate': sum(1 for m in no_home_adv if m.get('home_goals', 0) > m.get('away_goals', 0)) / len(no_home_adv) if no_home_adv else 0,
            },
            'importance': {
                'high_count': len(high_importance),
                'high_avg_goals': sum(m.get('actual_goals', 0) for m in high_importance) / len(high_importance) if high_importance else 0,
                'low_count': len(low_importance),
                'low_avg_goals': sum(m.get('actual_goals', 0) for m in low_importance) / len(low_importance) if low_importance else 0,
            }
        }
        
        return results
    except Exception as e:
        st.error(f"Error running pressure tests: {e}")
        return {}

# ============================================================================
# PREDICTION FUNCTIONS
# ============================================================================

def generate_prediction(history_matches):
    """Generate prediction based on historical patterns"""
    
    if not history_matches:
        return {
            'prediction': "Insufficient Data",
            'confidence': 30,
            'explanation': "No historical matches with this exact pattern yet"
        }
    
    total = len(history_matches)
    overs = sum(1 for m in history_matches if m.get('actual_goals', 0) >= 3)
    btts_yes = sum(1 for m in history_matches if m.get('actual_btts', False))
    
    over_pct = (overs / total) * 100
    btts_pct = (btts_yes / total) * 100
    
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
        'btts_note': f"BTTS: {btts_yes}/{total} ({btts_pct:.0f}%)",
        'stats': {
            'total': total,
            'over': overs,
            'under': total - overs,
            'btts_yes': btts_yes,
            'btts_no': total - btts_yes,
            'avg_goals': sum(m.get('actual_goals', 0) for m in history_matches) / total
        }
    }

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v14.0")
    st.markdown("### Complete Pattern Tracking with Advanced Analytics")
    
    # Show Supabase status
    if not SUPABASE_AVAILABLE:
        st.warning("⚠️ Supabase not installed. Run: `pip install supabase` to enable database features")
    elif supabase is None:
        st.error("❌ Supabase connection failed. Check your secrets.")
    else:
        st.success("✅ Supabase connected")
    
    # Sidebar - Database Stats
    with st.sidebar:
        st.header("📊 Database Stats")
        
        if supabase:
            try:
                total = supabase.table('matches').select('*', count='exact').execute()
                completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
                
                st.metric("Total Matches", total.count if hasattr(total, 'count') else 0)
                st.metric("Completed", completed.count if hasattr(completed, 'count') else 0)
                
                patterns = discover_patterns(min_matches=2)
                st.metric("Discovered Patterns", len(patterns))
                
                # Counter threats
                threats = get_counter_threats()
                if threats:
                    st.subheader("⚠️ Counter Threats")
                    for team, data in list(threats.items())[:3]:
                        st.text(f"• {team}: +{data['diff']}%")
                
                # Quick pressure test summary
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
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Predict", "🔍 Discover Patterns", "📊 League Stats", "⚠️ Counter Threats", "🎯 Pressure Test"])
    
    with tab1:
        col_form, col_result = st.columns([1, 1])
        
        with col_form:
            with st.form("match_input"):
                st.subheader("📋 Enter Match Data")
                
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
                submitted = st.form_submit_button("🎯 GENERATE PREDICTION", use_container_width=True)
        
        with col_result:
            if submitted:
                match_input = {
                    'home_da': home_da,
                    'away_da': away_da,
                    'home_btts': home_btts,
                    'away_btts': away_btts,
                    'home_over': home_over,
                    'away_over': away_over,
                    'elite': elite,
                    'derby': derby,
                    'relegation': relegation
                }
                
                # Calculate tiers
                tiers = calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over)
                
                # Display tiers
                st.subheader("🎯 Tier Signature")
                cols = st.columns(6)
                labels = ['H-DA', 'A-DA', 'H-BTTS', 'A-BTTS', 'H-OVER', 'A-OVER']
                cats = ['da', 'da', 'btts', 'btts', 'over', 'over']
                
                for i, (col, label, cat) in enumerate(zip(cols, labels, cats)):
                    emoji = tier_to_emoji(tiers[i], cat)
                    desc = get_tier_description(tiers[i], cat)
                    col.metric(label, f"{emoji} {tiers[i]}", help=desc)
                
                # Check historical patterns
                tier_sig = str(tiers)
                history = get_pattern_history(tier_sig, league)
                
                if history:
                    prediction = generate_prediction(history)
                    st.subheader("📊 Historical Pattern")
                    
                    col_h1, col_h2, col_h3 = st.columns(3)
                    col_h1.metric("Total Matches", prediction['stats']['total'])
                    col_h2.metric(prediction['prediction'], f"{prediction['confidence']:.0f}%")
                    col_h3.metric("Avg Goals", f"{prediction['stats']['avg_goals']:.1f}")
                    
                    st.info(prediction['explanation'])
                    st.caption(prediction['btts_note'])
                else:
                    st.info("🆕 No historical matches with this exact pattern yet")
                
                # Save to database
                match_id = save_match(match_input, home_team, away_team, league)
                
                if match_id:
                    st.session_state['current_match_id'] = match_id
                    st.session_state['current_home'] = home_team
                    st.session_state['current_away'] = away_team
                    st.success(f"✅ Match saved (ID: {match_id})")
                    
                    # Show result entry form immediately
                    st.markdown("---")
                    st.subheader("📥 ENTER ACTUAL RESULT NOW")
                    
                    with st.form("result_input_immediate"):
                        col_r1, col_r2 = st.columns(2)
                        
                        with col_r1:
                            home_goals = st.number_input(f"{home_team} Goals", 0, 10, 0, key="home_goals_immediate")
                        
                        with col_r2:
                            away_goals = st.number_input(f"{away_team} Goals", 0, 10, 0, key="away_goals_immediate")
                        
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
                        
                        submitted_result = st.form_submit_button("📥 SAVE RESULT", use_container_width=True)
                        
                        if submitted_result:
                            if update_result(match_id, home_goals, away_goals, notes):
                                st.success(f"✅ Result saved!")
                                st.balloons()
                                if 'current_match_id' in st.session_state:
                                    del st.session_state['current_match_id']
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
                    
                    # Show matches
                    with st.expander("View matches"):
                        for m in data['matches']:
                            score = f"{m.get('home_goals', '?')}-{m.get('away_goals', '?')}"
                            st.text(f"• {m['home_team']} {score} {m['away_team']} ({m['league']})")
        else:
            st.info(f"Add at least {min_matches} completed matches with the same tier pattern to discover patterns")
    
    with tab3:
        st.header("📊 League Statistics")
        
        leagues = ['EPL', 'BUNDESLIGA', 'SERIE A', 'LA LIGA', 'SUPER LIG', 'AUSTRIAN', 'CHAMPIONSHIP']
        
        for league in leagues:
            matches = get_league_stats(league)
            if matches:
                with st.expander(f"{league} ({len(matches)} matches)"):
                    # Create a DataFrame for display
                    df_data = []
                    for m in matches:
                        score = f"{m.get('home_goals', '?')}-{m.get('away_goals', '?')}"
                        btts_icon = "✅" if m.get('actual_btts') else "❌"
                        over_icon = "🔥" if m.get('actual_goals', 0) >= 3 else "📉"
                        
                        df_data.append({
                            'Date': m.get('match_date', '')[-5:],
                            'Home': m.get('home_team', ''),
                            'Score': score,
                            'Away': m.get('away_team', ''),
                            'BTTS': btts_icon,
                            'Goals': m.get('actual_goals', 0),
                            'O/U': over_icon
                        })
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # League stats
                    total = len(matches)
                    overs = sum(1 for m in matches if m.get('actual_goals', 0) >= 3)
                    btts_yes = sum(1 for m in matches if m.get('actual_btts', False))
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total", total)
                    col2.metric("Over 2.5", f"{overs}/{total} ({overs/total*100:.0f}%)")
                    col3.metric("BTTS", f"{btts_yes}/{total} ({btts_yes/total*100:.0f}%)")
                    col4.metric("Avg Goals", f"{sum(m.get('actual_goals', 0) for m in matches)/total:.1f}")
    
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
            st.info("Add more completed matches (at least 5-10) to run pressure tests")

if __name__ == "__main__":
    main()
