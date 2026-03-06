import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
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
    page_title="Mismatch Hunter v13.0",
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
# DATABASE FUNCTIONS
# ============================================================================

def save_match(match_input, home_team, away_team, league):
    """Save match to Supabase"""
    
    if supabase is None:
        st.error("Supabase not connected")
        return None
    
    try:
        data = {
            'home_team': home_team,
            'away_team': away_team,
            'league': league,
            'match_date': datetime.now().date().isoformat(),
            'home_da': match_input['home_da'],
            'away_da': match_input['away_da'],
            'home_btts': match_input['home_btts'],
            'away_btts': match_input['away_btts'],
            'home_over': match_input['home_over'],
            'away_over': match_input['away_over'],
            'elite': match_input.get('elite', False),
            'derby': match_input.get('derby', False),
            'relegation': match_input.get('relegation', False),
            'result_entered': False
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
        # Calculate derived fields
        total_goals = home_goals + away_goals
        btts = (home_goals > 0 and away_goals > 0)
        
        data = {
            'home_goals': home_goals,
            'away_goals': away_goals,
            'actual_goals': total_goals,
            'actual_btts': btts,
            'result_entered': True,
            'notes': notes
        }
        
        supabase.table('matches').update(data).eq('id', match_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating result: {e}")
        return False

def get_pattern_history(tier_signature, league=None, min_matches=1):
    """Get historical matches with same tier signature (shows both outcomes)"""
    
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
    """Auto-discover patterns from database (shows both over/under and btts/no btts)"""
    
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
                
                # Goal distribution
                goals_0 = sum(1 for m in matches_list if m.get('actual_goals', 0) == 0)
                goals_1 = sum(1 for m in matches_list if m.get('actual_goals', 0) == 1)
                goals_2 = sum(1 for m in matches_list if m.get('actual_goals', 0) == 2)
                goals_3 = sum(1 for m in matches_list if m.get('actual_goals', 0) == 3)
                goals_4 = sum(1 for m in matches_list if m.get('actual_goals', 0) >= 4)
                
                insights[sig] = {
                    'total': total,
                    'over_pct': (overs / total) * 100 if total > 0 else 0,
                    'under_pct': (unders / total) * 100 if total > 0 else 0,
                    'btts_yes_pct': (btts_yes / total) * 100 if total > 0 else 0,
                    'btts_no_pct': (btts_no / total) * 100 if total > 0 else 0,
                    'avg_goals': sum(m.get('actual_goals', 0) for m in matches_list) / total if total > 0 else 0,
                    'goal_distribution': {
                        '0': goals_0,
                        '1': goals_1,
                        '2': goals_2,
                        '3': goals_3,
                        '4+': goals_4
                    },
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
        
        # Find counter threats (teams that score more than their stats suggest)
        threats = {}
        for team, stats in team_stats.items():
            if len(stats['matches']) >= 3:
                avg_stat = np.mean(stats['btts_stat'])
                actual_rate = (sum(stats['actual_btts']) / len(stats['actual_btts'])) * 100
                avg_goals = np.mean(stats['goals_scored'])
                
                # Counter threat if:
                # 1. Stat says they don't score (avg_stat < 50)
                # 2. But they actually score often (actual_rate > 50)
                # 3. Or they average more than 1 goal per game
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

# ============================================================================
# TIER FUNCTIONS
# ============================================================================

def calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over):
    """Calculate tiers manually"""
    
    def da_tier(da):
        if da >= 80: return 1
        if da >= 65: return 2
        if da >= 50: return 3
        if da >= 35: return 4
        return 5
    
    def btts_tier(btts):
        if btts >= 65: return 1
        if btts >= 55: return 2
        if btts >= 45: return 3
        if btts >= 35: return 4
        return 5
    
    def over_tier(over):
        if over >= 65: return 1
        if over >= 55: return 2
        if over >= 45: return 3
        if over >= 35: return 4
        return 5
    
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
        'da': ["💥", "⚡", "📊", "🐢", "🛡️"],
        'btts': ["🎯", "⚽", "🤔", "🧤", "🚫"],
        'over': ["🔥", "📈", "⚖️", "📉", "💤"]
    }
    return emojis[category][tier-1]

def get_tier_description(tier, category):
    """Get text description of tier"""
    if category == 'da':
        descriptions = ["Elite Attack", "Strong Attack", "Average Attack", "Weak Attack", "Defensive Shell"]
    elif category == 'btts':
        descriptions = ["Always Scores", "Usually Scores", "50/50", "Rarely Scores", "Never Scores"]
    else:
        descriptions = ["Goal Fest", "Goals Likely", "50/50", "Goals Unlikely", "Dead Game"]
    return descriptions[tier-1]

# ============================================================================
# PREDICTION FUNCTIONS
# ============================================================================

def generate_prediction(tiers, history_matches, league, counter_threats=None):
    """Generate prediction based on historical patterns"""
    
    if not history_matches:
        return {
            'type': "🆕 NEW PATTERN",
            'prediction': "Insufficient Data",
            'confidence': 30,
            'explanation': "No historical matches with this exact pattern yet"
        }
    
    total = len(history_matches)
    overs = sum(1 for m in history_matches if m.get('actual_goals', 0) >= 3)
    unders = total - overs
    btts_yes = sum(1 for m in history_matches if m.get('actual_btts', False))
    btts_no = total - btts_yes
    
    over_pct = (overs / total) * 100
    under_pct = (unders / total) * 100
    btts_yes_pct = (btts_yes / total) * 100
    btts_no_pct = (btts_no / total) * 100
    
    # Determine if there's a clear pattern
    if over_pct >= 70:
        prediction = "🔥 OVER 2.5"
        confidence = over_pct
        explanation = f"{overs}/{total} matches went Over 2.5"
    elif under_pct >= 70:
        prediction = "✅ UNDER 2.5"
        confidence = under_pct
        explanation = f"{unders}/{total} matches went Under 2.5"
    else:
        prediction = "⚖️ NO CLEAR EDGE"
        confidence = 50
        explanation = f"Mixed results: {overs} Over, {unders} Under"
    
    # Add BTTS insight
    if btts_yes_pct >= 70:
        btts_note = f"BTTS in {btts_yes}/{total} matches"
    elif btts_no_pct >= 70:
        btts_note = f"No BTTS in {btts_no}/{total} matches"
    else:
        btts_note = f"BTTS {btts_yes}/{total}, No BTTS {btts_no}/{total}"
    
    # Check for counter threat influence
    if counter_threats:
        threat_warning = "⚠️ Counter threat detected - team may score despite stats"
    else:
        threat_warning = ""
    
    return {
        'type': "📊 PATTERN BASED",
        'prediction': prediction,
        'confidence': min(confidence, 95),
        'explanation': explanation,
        'btts_note': btts_note,
        'threat_warning': threat_warning,
        'stats': {
            'total': total,
            'over': overs,
            'under': unders,
            'btts_yes': btts_yes,
            'btts_no': btts_no,
            'avg_goals': sum(m.get('actual_goals', 0) for m in history_matches) / total
        }
    }

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v13.0")
    st.markdown("### Complete Pattern Tracking - Over/Under & BTTS/No BTTS")
    
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
            except Exception as e:
                st.info("No matches in database yet")
        else:
            st.info("Supabase not connected")
        
        st.markdown("---")
        st.markdown("**Tiers:** 1💥 2⚡ 3📊 4🐢 5🛡️")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Predict", "🔍 Discover Patterns", "📊 League Stats", "⚠️ Counter Threats"])
    
    with tab1:
        col_form, col_result = st.columns([1, 1])
        
        with col_form:
            with st.form("match_input"):
                st.subheader("📋 Enter Match Data")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🏠 HOME**")
                    home_team = st.text_input("Home Team", "Bayern")
                    home_da = st.number_input("DA", 0, 100, 60)
                    home_btts = st.number_input("BTTS %", 0, 100, 52)
                    home_over = st.number_input("Over %", 0, 100, 57)
                
                with col2:
                    st.markdown("**✈️ AWAY**")
                    away_team = st.text_input("Away Team", "Dortmund")
                    away_da = st.number_input("DA", 0, 100, 68, key="away_da")
                    away_btts = st.number_input("BTTS %", 0, 100, 61, key="away_btts")
                    away_over = st.number_input("Over %", 0, 100, 100, key="away_over")
                
                col3, col4, col5 = st.columns(3)
                with col3:
                    elite = st.checkbox("⭐ Elite")
                with col4:
                    derby = st.checkbox("🏆 Derby")
                with col5:
                    relegation = st.checkbox("⚠️ Relegation")
                
                league = st.text_input("League", "BUNDESLIGA")
                submitted = st.form_submit_button("🎯 SAVE MATCH", use_container_width=True)
        
        with col_result:
            st.subheader("📚 Enter Actual Result")
            
            if 'current_match_id' in st.session_state:
                st.info(f"Match ID: {st.session_state['current_match_id']}")
                
                with st.form("result_input"):
                    col_r1, col_r2 = st.columns(2)
                    
                    with col_r1:
                        home_goals = st.number_input(f"{home_team} Goals", 0, 10, 0, key="home_goals")
                    
                    with col_r2:
                        away_goals = st.number_input(f"{away_team} Goals", 0, 10, 0, key="away_goals")
                    
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
                        if update_result(st.session_state['current_match_id'], home_goals, away_goals, notes):
                            st.success(f"✅ Result saved!")
                            st.balloons()
                            del st.session_state['current_match_id']
                            st.rerun()
            else:
                st.info("Save a match first to enter results")
        
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
            
            # Display tiers with descriptions
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
                st.subheader("📊 Historical Pattern")
                total = len(history)
                overs = sum(1 for m in history if m.get('actual_goals', 0) >= 3)
                unders = total - overs
                btts_yes = sum(1 for m in history if m.get('actual_btts', False))
                btts_no = total - btts_yes
                
                col_h1, col_h2, col_h3, col_h4 = st.columns(4)
                col_h1.metric("Total Matches", total)
                col_h2.metric("Over 2.5", f"{overs}/{total} ({overs/total*100:.0f}%)")
                col_h3.metric("Under 2.5", f"{unders}/{total} ({unders/total*100:.0f}%)")
                col_h4.metric("Avg Goals", f"{sum(m.get('actual_goals', 0) for m in history)/total:.1f}")
                
                col_b1, col_b2 = st.columns(2)
                col_b1.metric("BTTS Yes", f"{btts_yes}/{total} ({btts_yes/total*100:.0f}%)")
                col_b2.metric("BTTS No", f"{btts_no}/{total} ({btts_no/total*100:.0f}%)")
                
                # Show recent examples
                with st.expander("View historical matches"):
                    for m in history[:5]:
                        score = f"{m.get('home_goals', '?')}-{m.get('away_goals', '?')}"
                        btts_icon = "✅" if m.get('actual_btts') else "❌"
                        over_icon = "🔥" if m.get('actual_goals', 0) >= 3 else "📉"
                        st.text(f"• {m['home_team']} {score} {m['away_team']} | {btts_icon} BTTS | {over_icon} {m.get('actual_goals', 0)} goals")
            else:
                st.info("🆕 No historical matches with this exact pattern yet")
            
            # Save to database
            match_id = save_match(match_input, home_team, away_team, league)
            
            if match_id:
                st.session_state['current_match_id'] = match_id
                st.success(f"✅ Match saved to Supabase (ID: {match_id})")
    
    with tab2:
        st.header("🔍 Pattern Discovery")
        
        patterns = discover_patterns(min_matches=2)
        
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
                    
                    # Goal distribution
                    st.subheader("Goal Distribution")
                    dist = data['goal_distribution']
                    st.bar_chart({
                        '0 Goals': dist['0'],
                        '1 Goal': dist['1'],
                        '2 Goals': dist['2'],
                        '3 Goals': dist['3'],
                        '4+ Goals': dist['4+']
                    })
                    
                    # Show matches
                    with st.expander("View matches"):
                        for m in data['matches']:
                            score = f"{m.get('home_goals', '?')}-{m.get('away_goals', '?')}"
                            st.text(f"• {m['home_team']} {score} {m['away_team']} ({m['league']})")
        else:
            st.info("Add at least 2 completed matches with the same tier pattern to discover patterns")
    
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
                    unders = total - overs
                    btts_yes = sum(1 for m in matches if m.get('actual_btts', False))
                    btts_no = total - btts_yes
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total", total)
                    col2.metric("Over 2.5", f"{overs}/{total} ({overs/total*100:.0f}%)")
                    col3.metric("Under 2.5", f"{unders}/{total} ({unders/total*100:.0f}%)")
                    col4.metric("Avg Goals", f"{sum(m.get('actual_goals', 0) for m in matches)/total:.1f}")
                    
                    col5, col6 = st.columns(2)
                    col5.metric("BTTS Yes", f"{btts_yes}/{total} ({btts_yes/total*100:.0f}%)")
                    col6.metric("BTTS No", f"{btts_no}/{total} ({btts_no/total*100:.0f}%)")
    
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
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.info("""
            **What is a Counter Threat?**
            - BTTS stat says they rarely score (<50%)
            - But actual results show they score often (>50%)
            - These teams are dangerous despite weak stats
            """)
        else:
            st.info("No counter threats detected yet. Need at least 3 matches per team.")

if __name__ == "__main__":
    main()