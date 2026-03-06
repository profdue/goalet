import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import numpy as np

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v12.0",
    page_icon="🎯",
    layout="wide"
)

# Initialize Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def save_match(match_input, home_team, away_team, league):
    """Save match to Supabase (tiers auto-calculated by trigger)"""
    
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
    
    try:
        result = supabase.table('matches').insert(data).execute()
        return result.data[0]['id']
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return None

def update_result(match_id, actual_goals, actual_btts, notes=""):
    """Update match with actual result"""
    
    data = {
        'actual_goals': actual_goals,
        'actual_btts': actual_btts,
        'result_entered': True,
        'notes': notes
    }
    
    try:
        supabase.table('matches').update(data).eq('id', match_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating result: {e}")
        return False

def get_pattern_history(tier_signature, league=None, min_matches=2):
    """Get historical matches with same tier signature"""
    
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

def get_league_stats(league):
    """Get all completed matches for a league"""
    
    result = supabase.table('matches')\
        .select('*')\
        .eq('league', league)\
        .eq('result_entered', True)\
        .order('match_date', desc=True)\
        .execute()
    
    return result.data

def discover_patterns(min_matches=3):
    """Auto-discover patterns from database"""
    
    # Get all completed matches
    result = supabase.table('matches')\
        .select('*')\
        .eq('result_entered', True)\
        .execute()
    
    matches = result.data
    
    # Group by tier signature
    patterns = {}
    for match in matches:
        sig = match['tier_signature']
        if sig not in patterns:
            patterns[sig] = []
        patterns[sig].append(match)
    
    # Analyze each pattern
    insights = {}
    for sig, matches_list in patterns.items():
        if len(matches_list) >= min_matches:
            total = len(matches_list)
            overs = sum(1 for m in matches_list if m['actual_goals'] >= 3)
            btts = sum(1 for m in matches_list if m['actual_btts'])
            
            # Group by league
            league_stats = {}
            for match in matches_list:
                league = match['league']
                if league not in league_stats:
                    league_stats[league] = {'total': 0, 'overs': 0, 'btts': 0}
                league_stats[league]['total'] += 1
                if match['actual_goals'] >= 3:
                    league_stats[league]['overs'] += 1
                if match['actual_btts']:
                    league_stats[league]['btts'] += 1
            
            insights[sig] = {
                'total': total,
                'over_pct': (overs / total) * 100,
                'btts_pct': (btts / total) * 100,
                'avg_goals': sum(m['actual_goals'] for m in matches_list) / total,
                'league_stats': league_stats,
                'recent_matches': matches_list[:5]
            }
    
    return insights

def get_counter_threats(league=None, threshold=45):
    """Identify teams that overperform"""
    
    query = supabase.table('matches')\
        .select('*')\
        .eq('result_entered', True)
    
    if league:
        query = query.eq('league', league)
    
    result = query.execute()
    matches = result.data
    
    team_stats = {}
    for match in matches:
        for team in [match['home_team'], match['away_team']]:
            if team not in team_stats:
                team_stats[team] = {'matches': [], 'btts_stat': [], 'actual_btts': []}
            
            # Get BTTS stat for this team
            if team == match['home_team']:
                team_stats[team]['btts_stat'].append(match['home_btts'])
            else:
                team_stats[team]['btts_stat'].append(match['away_btts'])
            
            team_stats[team]['actual_btts'].append(1 if match['actual_btts'] else 0)
            team_stats[team]['matches'].append(match)
    
    threats = {}
    for team, stats in team_stats.items():
        if len(stats['matches']) >= 3:
            avg_stat = np.mean(stats['btts_stat'])
            actual_rate = (sum(stats['actual_btts']) / len(stats['actual_btts'])) * 100
            
            if actual_rate > avg_stat + 15 and avg_stat < 50:
                threats[team] = {
                    'stat_avg': round(avg_stat, 1),
                    'actual_rate': round(actual_rate, 1),
                    'diff': round(actual_rate - avg_stat, 1),
                    'matches': len(stats['matches'])
                }
    
    return threats

# ============================================================================
# TIER FUNCTIONS (for display only - DB handles calculation)
# ============================================================================

def tier_to_emoji(tier, category):
    emojis = {
        'da': ["💥", "⚡", "📊", "🐢", "🛡️"],
        'btts': ["🎯", "⚽", "🤔", "🧤", "🚫"],
        'over': ["🔥", "📈", "⚖️", "📉", "💤"]
    }
    return emojis[category][tier-1]

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v12.0")
    st.markdown("### Supabase-Powered Pattern Learning")
    
    # Sidebar - Database Stats
    with st.sidebar:
        st.header("📊 Database Stats")
        
        # Get quick stats
        total = supabase.table('matches').select('*', count='exact').execute()
        completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
        
        st.metric("Total Matches", total.count if hasattr(total, 'count') else 0)
        st.metric("Completed", completed.count if hasattr(completed, 'count') else 0)
        
        # Discovered patterns
        patterns = discover_patterns(min_matches=2)
        st.metric("Discovered Patterns", len(patterns))
        
        # Counter threats
        threats = get_counter_threats()
        if threats:
            st.subheader("⚠️ Counter Threats")
            for team, data in list(threats.items())[:3]:
                st.text(f"{team}: +{data['diff']}%")
        
        st.markdown("---")
        st.markdown("**Tiers:** 1💥 2⚡ 3📊 4🐢 5🛡️")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📋 Predict", "🔍 Discover", "📊 League Stats"])
    
    with tab1:
        # Your existing prediction form
        with st.form("match_input"):
            st.subheader("📋 Enter Match Data")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏠 HOME**")
                home_team = st.text_input("Home Team", "")
                home_da = st.number_input("DA", 0, 100, 50)
                home_btts = st.number_input("BTTS %", 0, 100, 50)
                home_over = st.number_input("Over %", 0, 100, 50)
            
            with col2:
                st.markdown("**✈️ AWAY**")
                away_team = st.text_input("Away Team", "")
                away_da = st.number_input("DA", 0, 100, 50, key="away_da")
                away_btts = st.number_input("BTTS %", 0, 100, 50, key="away_btts")
                away_over = st.number_input("Over %", 0, 100, 50, key="away_over")
            
            col3, col4, col5 = st.columns(3)
            with col3:
                elite = st.checkbox("⭐ Elite")
            with col4:
                derby = st.checkbox("🏆 Derby")
            with col5:
                relegation = st.checkbox("⚠️ Relegation")
            
            league = st.text_input("League", "")
            submitted = st.form_submit_button("🎯 GET PREDICTION", use_container_width=True)
        
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
            
            # Save to database
            match_id = save_match(match_input, home_team, away_team, league)
            
            if match_id:
                st.session_state['current_match_id'] = match_id
                st.success(f"✅ Match saved to database (ID: {match_id})")
                
                # Get the saved match to display tiers
                saved = supabase.table('matches').select('*').eq('id', match_id).execute()
                if saved.data:
                    match = saved.data[0]
                    tiers = [
                        match['home_da_tier'],
                        match['away_da_tier'],
                        match['home_btts_tier'],
                        match['away_btts_tier'],
                        match['home_over_tier'],
                        match['away_over_tier']
                    ]
                    
                    # Display tiers
                    st.subheader("🎯 Tier Signature")
                    cols = st.columns(6)
                    labels = ['H-DA', 'A-DA', 'H-BTTS', 'A-BTTS', 'H-OVER', 'A-OVER']
                    cats = ['da', 'da', 'btts', 'btts', 'over', 'over']
                    for i, (col, label, cat) in enumerate(zip(cols, labels, cats)):
                        emoji = tier_to_emoji(tiers[i], cat)
                        col.metric(label, f"{emoji} {tiers[i]}")
                    
                    # Check historical patterns
                    history = get_pattern_history(match['tier_signature'], league)
                    
                    if history:
                        st.subheader("📊 Historical Pattern")
                        overs = sum(1 for m in history if m['actual_goals'] >= 3)
                        btts = sum(1 for m in history if m['actual_btts'])
                        
                        st.info(f"""
                        **{len(history)} matches with this exact pattern:**
                        - Over 2.5: {overs}/{len(history)} ({overs/len(history)*100:.0f}%)
                        - BTTS: {btts}/{len(history)} ({btts/len(history)*100:.0f}%)
                        - Avg goals: {sum(m['actual_goals'] for m in history)/len(history):.1f}
                        """)
                        
                        # Show recent examples
                        with st.expander("View historical matches"):
                            for m in history[:3]:
                                btts_text = "✅ BTTS" if m['actual_btts'] else "❌ No BTTS"
                                st.text(f"{m['home_team']} {m['actual_goals']}-? {m['away_team']} - {btts_text}")
                    else:
                        st.info("🆕 No historical matches with this exact pattern yet")
            
            # Learning section
            st.markdown("---")
            st.subheader("📚 Enter Result")
            
            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                actual_goals = st.number_input("Actual Goals", 0, 10, 2)
            with col_l2:
                actual_btts = st.checkbox("BTTS Happened?")
            with col_l3:
                notes = st.text_input("Notes (optional)", "")
            
            if st.button("📥 Save Result to Database"):
                if update_result(match_id, actual_goals, actual_btts, notes):
                    st.success("✅ Result saved! Database updated.")
                    st.balloons()
                    st.rerun()
    
    with tab2:
        st.header("🔍 Pattern Discovery")
        
        patterns = discover_patterns(min_matches=2)
        
        if patterns:
            for sig, data in patterns.items():
                with st.expander(f"Pattern {sig} ({data['total']} matches)"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Over 2.5", f"{data['over_pct']:.0f}%")
                    col2.metric("BTTS", f"{data['btts_pct']:.0f}%")
                    col3.metric("Avg Goals", f"{data['avg_goals']:.1f}")
                    
                    if data['league_stats']:
                        st.subheader("By League")
                        for league, stats in data['league_stats'].items():
                            st.text(f"{league}: {stats['total']} matches - Over: {stats['overs']/stats['total']*100:.0f}%")
                    
                    st.subheader("Recent Examples")
                    for m in data['recent_matches'][:3]:
                        btts_text = "✅" if m['actual_btts'] else "❌"
                        st.text(f"{m['home_team']} {m['actual_goals']}-? {m['away_team']} ({m['league']}) {btts_text}")
        else:
            st.info("Add more completed matches to discover patterns")
    
    with tab3:
        st.header("📊 League Statistics")
        
        leagues = ['EPL', 'BUNDESLIGA', 'SERIE A', 'LA LIGA', 'SUPER LIG']
        
        for league in leagues:
            matches = get_league_stats(league)
            if matches:
                with st.expander(f"{league} ({len(matches)} matches)"):
                    overs = sum(1 for m in matches if m['actual_goals'] >= 3)
                    btts = sum(1 for m in matches if m['actual_btts'])
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total", len(matches))
                    col2.metric("Over 2.5", f"{overs/len(matches)*100:.0f}%")
                    col3.metric("BTTS", f"{btts/len(matches)*100:.0f}%")

if __name__ == "__main__":
    main()
