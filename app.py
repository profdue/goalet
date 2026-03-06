import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# Try to import supabase with error handling
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Supabase module not installed. Database features disabled. Run: pip install supabase")

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v12.0",
    page_icon="🎯",
    layout="wide"
)

# ============================================================================
# SUPABASE FUNCTIONS (only if available)
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
# DATABASE FUNCTIONS (with fallbacks)
# ============================================================================

def save_match(match_input, home_team, away_team, league):
    """Save match to Supabase (with fallback to session state)"""
    
    if supabase is None:
        # Fallback: save to session state
        if 'local_matches' not in st.session_state:
            st.session_state.local_matches = []
        
        match_id = len(st.session_state.local_matches) + 1
        st.session_state.local_matches.append({
            'id': match_id,
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
        })
        return match_id
    
    # Supabase version
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

def update_result(match_id, actual_goals, actual_btts, notes=""):
    """Update match with actual result"""
    
    if supabase is None:
        # Fallback: update session state
        if 'local_matches' in st.session_state:
            for match in st.session_state.local_matches:
                if match['id'] == match_id:
                    match['actual_goals'] = actual_goals
                    match['actual_btts'] = actual_btts
                    match['result_entered'] = True
                    match['notes'] = notes
                    return True
        return False
    
    # Supabase version
    try:
        data = {
            'actual_goals': actual_goals,
            'actual_btts': actual_btts,
            'result_entered': True,
            'notes': notes
        }
        supabase.table('matches').update(data).eq('id', match_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating result: {e}")
        return False

def get_pattern_history(tier_signature, league=None, min_matches=2):
    """Get historical matches with same tier signature"""
    
    if supabase is None:
        # Fallback: check session state
        if 'local_matches' not in st.session_state:
            return []
        
        matches = [m for m in st.session_state.local_matches 
                  if m.get('result_entered', False)]
        
        # Filter by tier signature (would need tier calculation in app)
        # For now, return empty
        return []
    
    # Supabase version
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

def discover_patterns(min_matches=3):
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
                overs = sum(1 for m in matches_list if m.get('actual_goals', 0) >= 3)
                btts = sum(1 for m in matches_list if m.get('actual_btts', False))
                
                insights[sig] = {
                    'total': total,
                    'over_pct': (overs / total) * 100 if total > 0 else 0,
                    'btts_pct': (btts / total) * 100 if total > 0 else 0,
                    'avg_goals': sum(m.get('actual_goals', 0) for m in matches_list) / total if total > 0 else 0
                }
        
        return insights
    except Exception as e:
        st.error(f"Error discovering patterns: {e}")
        return {}

def get_counter_threats(league=None, threshold=45):
    """Identify teams that overperform"""
    
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
        
        # Analyze teams (simplified)
        threats = {}
        # Add your counter threat logic here
        return threats
    except Exception as e:
        return {}

# ============================================================================
# TIER FUNCTIONS
# ============================================================================

def calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over):
    """Calculate tiers manually (fallback when DB doesn't)"""
    
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

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v12.0")
    st.markdown("### Supabase-Powered Pattern Learning")
    
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
            except:
                st.info("No matches in database yet")
        else:
            if 'local_matches' in st.session_state:
                st.metric("Local Matches", len(st.session_state.local_matches))
            else:
                st.info("No local matches")
        
        st.markdown("---")
        st.markdown("**Tiers:** 1💥 2⚡ 3📊 4🐢 5🛡️")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📋 Predict", "🔍 Discover", "📊 League Stats"])
    
    with tab1:
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
            
            # Calculate tiers
            tiers = calculate_tiers(home_da, away_da, home_btts, away_btts, home_over, away_over)
            
            # Display tiers
            st.subheader("🎯 Tier Signature")
            cols = st.columns(6)
            labels = ['H-DA', 'A-DA', 'H-BTTS', 'A-BTTS', 'H-OVER', 'A-OVER']
            cats = ['da', 'da', 'btts', 'btts', 'over', 'over']
            for i, (col, label, cat) in enumerate(zip(cols, labels, cats)):
                emoji = tier_to_emoji(tiers[i], cat)
                col.metric(label, f"{emoji} {tiers[i]}")
            
            # Save to database
            match_id = save_match(match_input, home_team, away_team, league)
            
            if match_id:
                st.session_state['current_match_id'] = match_id
                st.success(f"✅ Match saved (ID: {match_id})")
                
                # Check historical patterns (would need tier_signature from DB)
                st.info("🆕 Pattern learning will work after Supabase is fully configured")
            
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
            
            if st.button("📥 Save Result"):
                if match_id and update_result(match_id, actual_goals, actual_btts, notes):
                    st.success("✅ Result saved!")
                    st.balloons()
    
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
        else:
            st.info("Add more completed matches to discover patterns")
    
    with tab3:
        st.header("📊 League Statistics")
        
        leagues = ['EPL', 'BUNDESLIGA', 'SERIE A', 'LA LIGA', 'SUPER LIG']
        
        for league in leagues:
            matches = get_league_stats(league)
            if matches:
                with st.expander(f"{league} ({len(matches)} matches)"):
                    overs = sum(1 for m in matches if m.get('actual_goals', 0) >= 3)
                    btts = sum(1 for m in matches if m.get('actual_btts', False))
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total", len(matches))
                    if matches:
                        col2.metric("Over 2.5", f"{overs/len(matches)*100:.0f}%")
                        col3.metric("BTTS", f"{btts/len(matches)*100:.0f}%")

if __name__ == "__main__":
    main()
