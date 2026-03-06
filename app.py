import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
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
    page_title="Mismatch Hunter v12.0",
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

def parse_score(score_str):
    """Parse score string like '2-1' into home_goals and away_goals"""
    if not score_str or '-' not in score_str:
        return None, None
    
    try:
        parts = score_str.split('-')
        home = int(parts[0].strip())
        away = int(parts[1].strip())
        return home, away
    except:
        return None, None

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
    """Update match with actual result using home/away goals"""
    
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
            'actual_goals': total_goals,  # keeping for backward compatibility
            'actual_btts': btts,
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
            except Exception as e:
                st.info("No matches in database yet")
        else:
            st.info("Supabase not connected")
        
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
            submitted = st.form_submit_button("🎯 SAVE MATCH & GET PREDICTION", use_container_width=True)
        
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
                st.success(f"✅ Match saved to Supabase (ID: {match_id})")
                
                # Simple prediction based on tiers (you can enhance this)
                if tiers[4] <= 2 or tiers[5] <= 2:  # Any Over Tier 1-2
                    st.info("🔮 PRELIMINARY: Over 2.5 possible")
                if tiers[2] <= 2 and tiers[3] <= 2:  # Both BTTS Tier 1-2
                    st.info("🔮 PRELIMINARY: BTTS likely")
        
        # Learning section - SEPARATE FORM for results
        st.markdown("---")
        st.subheader("📚 Enter Actual Result")
        
        if 'current_match_id' in st.session_state:
            st.info(f"Entering result for match ID: {st.session_state['current_match_id']}")
            
            with st.form("result_input"):
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.markdown("**🏠 HOME GOALS**")
                    home_goals = st.number_input("Home Goals", 0, 10, 0, key="home_goals")
                
                with col_r2:
                    st.markdown("**✈️ AWAY GOALS**")
                    away_goals = st.number_input("Away Goals", 0, 10, 0, key="away_goals")
                
                with col_r3:
                    st.markdown("**📝 NOTES**")
                    notes = st.text_input("Notes (e.g., 'penalty', 'red card', 'late goal')", "")
                
                # Display score preview
                score_display = f"{home_goals} - {away_goals}"
                btts_display = "✅ YES" if (home_goals > 0 and away_goals > 0) else "❌ NO"
                total_goals = home_goals + away_goals
                over_display = "✅ YES" if total_goals >= 3 else "❌ NO"
                
                st.markdown(f"""
                **Score:** {score_display}
                **Total Goals:** {total_goals}
                **BTTS:** {btts_display}
                **Over 2.5:** {over_display}
                """)
                
                submitted_result = st.form_submit_button("📥 SAVE RESULT TO SUPABASE", use_container_width=True)
                
                if submitted_result:
                    if update_result(st.session_state['current_match_id'], home_goals, away_goals, notes):
                        st.success(f"✅ Result {home_goals}-{away_goals} saved to Supabase!")
                        st.balloons()
                        
                        # Clear the match ID from session state
                        del st.session_state['current_match_id']
                        st.rerun()
        else:
            st.info("No active match. Save a match first to enter results.")
    
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
        
        leagues = ['EPL', 'BUNDESLIGA', 'SERIE A', 'LA LIGA', 'SUPER LIG', 'AUSTRIAN']
        
        for league in leagues:
            matches = get_league_stats(league)
            if matches:
                with st.expander(f"{league} ({len(matches)} matches)"):
                    # Create a DataFrame for display
                    df_data = []
                    for m in matches:
                        df_data.append({
                            'Date': m.get('match_date', ''),
                            'Home': m.get('home_team', ''),
                            'Away': m.get('away_team', ''),
                            'Score': f"{m.get('home_goals', '?')}-{m.get('away_goals', '?')}",
                            'BTTS': '✅' if m.get('actual_btts') else '❌',
                            'Goals': m.get('actual_goals', 0)
                        })
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)
                    
                    # Stats
                    overs = sum(1 for m in matches if m.get('actual_goals', 0) >= 3)
                    btts = sum(1 for m in matches if m.get('actual_btts', False))
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total", len(matches))
                    if matches:
                        col2.metric("Over 2.5", f"{overs/len(matches)*100:.0f}%")
                        col3.metric("BTTS", f"{btts/len(matches)*100:.0f}%")

if __name__ == "__main__":
    main()
