import streamlit as st
import pandas as pd
from datetime import datetime

# Supabase connection
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Run: pip install supabase")

st.set_page_config(
    page_title="⚽ Football Intelligence", 
    page_icon="⚽", 
    layout="wide"
)

if SUPABASE_AVAILABLE:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
else:
    supabase = None

# ============================================================================
# TIER FUNCTIONS (Your original logic)
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

def get_tier_description(tier, category):
    if category == 'da':
        return ["Elite", "Strong", "Average", "Weak"][tier-1]
    else:
        return ["Elite Attack", "Strong Attack", "Average", "Weak Attack"][tier-1]

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

@st.cache_data(ttl=60)
def get_pattern_stats(pattern_code):
    """Get historical stats for a pattern"""
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
    except:
        return None

@st.cache_data(ttl=300)
def get_da_stats():
    """Get historical stats for each DA combination"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            home_da_tier,
            away_da_tier,
            COUNT(*) as matches,
            ROUND(AVG(CASE WHEN home_goals > away_goals THEN 1 ELSE 0 END) * 100, 1) as home_win_pct,
            ROUND(AVG(CASE WHEN home_goals < away_goals THEN 1 ELSE 0 END) * 100, 1) as away_win_pct,
            ROUND(AVG(CASE WHEN home_goals = away_goals THEN 1 ELSE 0 END) * 100, 1) as draw_pct,
            ROUND(AVG(CASE WHEN home_goals > 0 AND away_goals > 0 THEN 1 ELSE 0 END) * 100, 1) as btts_pct,
            ROUND(AVG(CASE WHEN home_goals + away_goals >= 3 THEN 1 ELSE 0 END) * 100, 1) as over_pct,
            ROUND(AVG(home_goals + away_goals), 2) as avg_goals
        FROM matches
        WHERE result_entered = true
        GROUP BY home_da_tier, away_da_tier
        ORDER BY home_da_tier, away_da_tier
        """
        result = supabase.table('matches').select('*').execute()
        # In a real app, you'd execute the raw query
        # For now, we'll use a simplified version
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def save_match(data, home_goals=None, away_goals=None):
    """Save match to database"""
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
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        st.error(f"Error saving match: {e}")
        return None

# ============================================================================
# PREDICTION FUNCTION - DA FIRST
# ============================================================================

def predict_match(match_data):
    """Make prediction based on DA first, then pattern"""
    
    # Get DA tiers
    home_da_tier = match_data['home_da_tier']
    away_da_tier = match_data['away_da_tier']
    
    # DA-first prediction
    if home_da_tier == 4 and away_da_tier == 4:
        primary = "UNDER 2.5"
        reasoning = "Both defenses weak - historically low scoring"
    elif home_da_tier == 1 and away_da_tier == 4:
        primary = "HOME WIN"
        reasoning = "Elite home defense vs weak away"
    elif home_da_tier == 4 and away_da_tier == 1:
        primary = "AWAY WIN"
        reasoning = "Weak home vs elite away defense"
    elif home_da_tier <= 2 and away_da_tier >= 3:
        primary = "HOME ADVANTAGE"
        reasoning = "Stronger home defense"
    elif away_da_tier <= 2 and home_da_tier >= 3:
        primary = "AWAY ADVANTAGE"
        reasoning = "Stronger away defense"
    elif home_da_tier == 3 and away_da_tier == 3:
        primary = "BALANCED"
        reasoning = "Equal average defenses - no clear edge"
    else:
        primary = "TRACK PATTERN"
        reasoning = "Let pattern history decide"
    
    # Get pattern stats for confirmation
    pattern_code = match_data.get('pattern_code')
    pattern_stats = get_pattern_stats(pattern_code) if pattern_code else None
    
    return {
        'primary': primary,
        'reasoning': reasoning,
        'pattern_code': pattern_code,
        'pattern_stats': pattern_stats
    }

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.title("⚽ Football Intelligence")
    st.markdown("### DA-First • Pattern-Confirmed")
    
    # Initialize session state
    if 'current_match' not in st.session_state:
        st.session_state.current_match = None
    if 'prediction' not in st.session_state:
        st.session_state.prediction = None
    
    # Input form
    with st.form("match_form"):
        st.subheader("Enter Match Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏠 HOME**")
            home_team = st.text_input("Home Team", key="home_team")
            home_da = st.number_input("Home DA", 0, 100, 50, key="home_da")
            home_btts = st.number_input("Home BTTS %", 0, 100, 50, key="home_btts")
            home_over = st.number_input("Home Over %", 0, 100, 50, key="home_over")
        
        with col2:
            st.markdown("**✈️ AWAY**")
            away_team = st.text_input("Away Team", key="away_team")
            away_da = st.number_input("Away DA", 0, 100, 50, key="away_da")
            away_btts = st.number_input("Away BTTS %", 0, 100, 50, key="away_btts")
            away_over = st.number_input("Away Over %", 0, 100, 50, key="away_over")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            elite = st.checkbox("⭐ Elite Match")
        with col4:
            derby = st.checkbox("🏆 Derby")
        with col5:
            relegation = st.checkbox("⚠️ Relegation")
        
        league = st.text_input("League", "OTHER")
        notes = st.text_input("Notes (optional)")
        
        submitted = st.form_submit_button("🔮 PREDICT", use_container_width=True)
        
        if submitted and home_team and away_team:
            # Calculate tiers
            home_da_tier = calculate_tier(home_da, 'da')
            away_da_tier = calculate_tier(away_da, 'da')
            home_btts_tier = calculate_tier(home_btts, 'btts')
            away_btts_tier = calculate_tier(away_btts, 'btts')
            home_over_tier = calculate_tier(home_over, 'over')
            away_over_tier = calculate_tier(away_over, 'over')
            
            # Calculate flags (your original logic)
            home_adv_flag = home_da_tier < away_da_tier
            btts_pressure = (home_btts_tier <= 2 and away_da_tier >= 3) or (away_btts_tier <= 2 and home_da_tier >= 3) or elite or derby
            overs_pressure = (home_over_tier <= 2 and away_da_tier >= 3) or (away_over_tier <= 2 and home_da_tier >= 3)
            importance = (1 if elite else 0) + (1 if derby else 0) + (1 if relegation else 0)
            
            # Pattern code
            pattern_code = f"{'T' if home_adv_flag else 'F'},{'T' if overs_pressure else 'F'},{'T' if btts_pressure else 'F'},{importance}"
            
            # Store match data
            st.session_state.current_match = {
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
                'notes': notes,
                'home_da_tier': home_da_tier,
                'away_da_tier': away_da_tier,
                'home_btts_tier': home_btts_tier,
                'away_btts_tier': away_btts_tier,
                'importance': importance,
                'pattern_code': pattern_code
            }
            
            # Get prediction
            st.session_state.prediction = predict_match(st.session_state.current_match)
    
    # Display prediction if available
    if st.session_state.current_match and st.session_state.prediction:
        match = st.session_state.current_match
        pred = st.session_state.prediction
        
        st.markdown("---")
        
        # DA Tier Display
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("Home DA Tier", f"{match['home_da_tier']} - {get_tier_description(match['home_da_tier'], 'da')}")
        with col_d2:
            st.metric("Away DA Tier", f"{match['away_da_tier']} - {get_tier_description(match['away_da_tier'], 'da')}")
        with col_d3:
            st.metric("Matchup", f"{match['home_da_tier']} vs {match['away_da_tier']}")
        
        # Prediction Card
        st.markdown(f"""
        <div style="background-color: #1e3a5f; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2 style="color: white;">🎯 {pred['primary']}</h2>
            <p style="color: #ddd;">{pred['reasoning']}</p>
            <p style="color: #aaa;">Pattern: {pred['pattern_code']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Pattern Stats if available
        if pred['pattern_stats']:
            stats = pred['pattern_stats']
            st.subheader("📊 Pattern History")
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Matches", stats.get('total_matches', 0))
            col_s2.metric("Home Win", f"{stats.get('current_home_win_rate', 0)}%")
            col_s3.metric("BTTS", f"{stats.get('current_btts_rate', 0)}%")
            col_s4.metric("Over", f"{stats.get('current_over_rate', 0)}%")
        
        # Enter Result
        st.markdown("---")
        st.subheader("📥 Enter Result")
        
        col_r1, col_r2, col_r3 = st.columns([1, 1, 2])
        
        with col_r1:
            home_goals = st.number_input(f"{match['home_team']} Goals", 0, 10, 0, key="home_goals")
        
        with col_r2:
            away_goals = st.number_input(f"{match['away_team']} Goals", 0, 10, 0, key="away_goals")
        
        with col_r3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 SAVE", type="primary", use_container_width=True):
                saved = save_match(match, home_goals, away_goals)
                if saved:
                    st.success(f"✅ Saved! {match['home_team']} {home_goals}-{away_goals} {match['away_team']}")
                    st.balloons()
                    st.cache_data.clear()
                    st.session_state.current_match = None
                    st.session_state.prediction = None
                    st.rerun()

if __name__ == "__main__":
    main()
