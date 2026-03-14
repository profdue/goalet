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

# ============================================================================
# RULE CHECKING FUNCTIONS
# ============================================================================

def check_rules(data):
    """Check which rules apply to this match"""
    
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
    
    # Check each rule
    active_rules = []
    
    for rule in ACTIVE_RULES:
        rule_active = False
        
        if rule['category'] == 'flag':
            # Flag-based rules check pattern code
            if rule.get('pattern_code') == pattern_code:
                rule_active = True
        
        elif rule['category'] == 'legacy':
            # Legacy rules check specific conditions
            if rule['name'] == 'GRAND UNDER 2.5':
                # Check if both defenses are weak (DA tiers both 4)
                if home_da_tier == 4 and away_da_tier == 4:
                    rule_active = True
            
            elif rule['name'] == 'Elite + Home Adv':
                # Check if home has elite defense and home advantage
                if home_adv_flag and home_da_tier <= 2:
                    rule_active = True
            
            elif rule['name'] == 'home_btts=2 & away_btts=2':
                # Check if both teams have strong attack (BTTS tiers 1-2)
                if home_btts_tier <= 2 and away_btts_tier <= 2:
                    rule_active = True
            
            elif rule['name'] == 'Elite + No Home Adv':
                # Check if away has elite attack and no home advantage
                if not home_adv_flag and away_da_tier <= 2:
                    rule_active = True
            
            elif rule['name'] == 'Away Win Lock':
                # Check specific condition for away win lock
                if home_da_tier == 4 and away_da_tier <= 2:
                    rule_active = True
            
            elif rule['name'] == 'home_da=2 & away_da=3':
                # Check if home has strong defense, away average
                if home_da_tier == 2 and away_da_tier == 3:
                    rule_active = True
        
        if rule_active:
            active_rules.append(rule)
    
    return {
        'active_rules': active_rules,
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
        'pattern_code': pattern_code,
        'rule_count': len(active_rules)
    }

# ============================================================================
# DATABASE FUNCTIONS - SAVE MATCH
# ============================================================================

def save_match(data, home_goals=None, away_goals=None):
    if supabase is None:
        return None
    
    try:
        # Calculate tiers and flags
        home_da_tier = calculate_tier(data['home_da'], 'da')
        away_da_tier = calculate_tier(data['away_da'], 'da')
        home_btts_tier = calculate_tier(data['home_btts'], 'btts')
        away_btts_tier = calculate_tier(data['away_btts'], 'btts')
        home_over_tier = calculate_tier(data['home_over'], 'over')
        away_over_tier = calculate_tier(data['away_over'], 'over')
        
        home_adv_flag = home_da_tier <= 2 and away_da_tier >= 3
        btts_pressure_flag = (home_btts_tier <= 2 and away_btts_tier <= 2)
        overs_pressure_flag = (home_over_tier <= 2 and away_da_tier >= 3) or (away_over_tier <= 2 and home_da_tier >= 3)
        importance = (1 if data.get('elite', False) else 0) + (1 if data.get('derby', False) else 0) + (1 if data.get('relegation', False) else 0)
        
        # Generate pattern code
        pattern_code = f"{'T' if home_adv_flag else 'F'},{'T' if overs_pressure_flag else 'F'},{'T' if btts_pressure_flag else 'F'},{importance}"
        
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
            'home_da_tier': home_da_tier,
            'away_da_tier': away_da_tier,
            'home_btts_tier': home_btts_tier,
            'away_btts_tier': away_btts_tier,
            'home_over_tier': home_over_tier,
            'away_over_tier': away_over_tier,
            'home_advantage_flag': home_adv_flag,
            'btts_pressure_flag': btts_pressure_flag,
            'overs_pressure_flag': overs_pressure_flag,
            'importance_score': importance,
            'pattern_code': pattern_code,
            'elite': data.get('elite', False),
            'derby': data.get('derby', False),
            'relegation': data.get('relegation', False),
            'result_entered': home_goals is not None,
            'discovery_notes': data.get('notes', '')
        }
        
        if home_goals is not None:
            match_data['home_goals'] = home_goals
            match_data['away_goals'] = away_goals
            match_data['actual_goals'] = home_goals + away_goals
            match_data['actual_btts'] = (home_goals > 0 and away_goals > 0)
        
        result = supabase.table('matches').insert(match_data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]['id']
        return None
            
    except Exception as e:
        st.error(f"Error saving match: {e}")
        return None

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
            
            st.metric("Total Matches", total.count if hasattr(total, 'count') else 0)
            st.metric("Completed", completed.count if hasattr(completed, 'count') else 0)
            
            st.markdown("---")
            st.markdown("**BET KEY**")
            st.markdown("🔥 OVER | ❄️ UNDER | 🏠 HOME | ✈️ AWAY | ⚽ BTTS")
            
        except Exception as e:
            st.info("No data yet")
    
    # Main tabs
    tab1, tab2 = st.tabs([
        "📝 NEW MATCH",      # Enter matches & get predictions from rules
        "🏆 RULES"           # Your 9 rules
    ])
    
    # ===== TAB 1: NEW MATCH =====
    with tab1:
        st.subheader("Enter Match Data - Rules Will Auto-Detect")
        
        if 'pending_match' not in st.session_state:
            st.session_state.pending_match = None
        if 'rule_results' not in st.session_state:
            st.session_state.rule_results = None
        
        with st.form("match_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏠 HOME**")
                home_team = st.text_input("Team", key="home_team_input")
                home_da = st.number_input("DA (Dangerous Attacks)", 0, 100, 50, key="home_da_input")
                home_btts = st.number_input("BTTS % (Both Teams to Score)", 0, 100, 50, key="home_btts_input")
                home_over = st.number_input("Over %", 0, 100, 50, key="home_over_input")
            
            with col2:
                st.markdown("**✈️ AWAY**")
                away_team = st.text_input("Team", key="away_team_input")
                away_da = st.number_input("DA (Dangerous Attacks)", 0, 100, 50, key="away_da_input")
                away_btts = st.number_input("BTTS % (Both Teams to Score)", 0, 100, 50, key="away_btts_input")
                away_over = st.number_input("Over %", 0, 100, 50, key="away_over_input")
            
            col3, col4, col5 = st.columns(3)
            with col3:
                elite = st.checkbox("⭐ Elite Match", key="elite_input")
            with col4:
                derby = st.checkbox("🏆 Derby", key="derby_input")
            with col5:
                relegation = st.checkbox("⚠️ Relegation Battle", key="relegation_input")
            
            league = st.text_input("League", "EPL", key="league_input")
            notes = st.text_input("Notes (optional)", key="notes_input")
            
            analyzed = st.form_submit_button("🔍 CHECK RULES", use_container_width=True, type="primary")
        
        if analyzed:
            if not home_team or not away_team:
                st.error("Please enter both team names")
            else:
                match_data = {
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
                
                st.session_state.rule_results = check_rules(match_data)
                st.session_state.pending_match = match_data
                st.rerun()
        
        # Show rule check results
        if st.session_state.rule_results and st.session_state.pending_match:
            data = st.session_state.pending_match
            rules = st.session_state.rule_results
            
            st.markdown("---")
            
            # Show calculated metrics
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("BTTS Pressure", "✅ ACTIVE" if rules['btts_pressure_flag'] else "❌ INACTIVE")
            with col_b:
                st.metric("Overs Pressure", "✅ ACTIVE" if rules['overs_pressure_flag'] else "❌ INACTIVE")
            with col_c:
                imp_text = ["Regular", "Important", "Very Important"][rules['importance_score']]
                st.metric("Importance", f"{rules['importance_score']} - {imp_text}")
            
            st.markdown(f"**Pattern Code:** `{rules['pattern_code']}`")
            st.markdown(f"**Active Rules:** {rules['rule_count']} of 9")
            
            # Show active rules
            if rules['active_rules']:
                st.markdown("---")
                st.subheader("✅ ACTIVE RULES FOUND")
                
                for rule in rules['active_rules']:
                    with st.container():
                        st.markdown(f"""
                        <div style="background-color: #1e3a5f; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #4CAF50;">
                            <h4 style="margin:0; color: white;">{rule['display_name']}</h4>
                            <p style="margin:5px 0; color: #ddd;">🎯 {rule['outcome']}</p>
                            <p style="margin:5px 0; color: #aaa; font-size: 14px;">{rule['bias'] if rule['bias'] else ''}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("No rules activated for this match")
            
            # Enter result
            st.markdown("---")
            st.subheader("📥 Enter Final Score")
            
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
                
                saved = st.form_submit_button("💾 SAVE TO DATABASE", type="primary", use_container_width=True)
                
                if saved:
                    match_id = save_match(data, home_goals, away_goals)
                    if match_id:
                        st.success(f"✅ Match #{match_id} saved!")
                        st.balloons()
                        st.session_state.pending_match = None
                        st.session_state.rule_results = None
                        st.rerun()
    
    # ===== TAB 2: RULES =====
    with tab2:
        st.header("🏆 The 9 Active Rules")
        st.markdown("### These rules automatically detect patterns in your data")
        
        # Display all rules in a grid
        for i in range(0, len(ACTIVE_RULES), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ACTIVE_RULES):
                    rule = ACTIVE_RULES[i + j]
                    with cols[j]:
                        st.markdown(f"""
                        <div style="background-color: #2d2d2d; padding: 15px; border-radius: 8px; height: 200px; margin-bottom: 10px;">
                            <h4 style="margin:0; color: #4CAF50;">{rule['display_name']}</h4>
                            <p style="margin:10px 0; color: white;"><strong>🎯 {rule['outcome']}</strong></p>
                            <p style="margin:10px 0; color: #aaa; font-size: 14px;">{rule['bias'] if rule['bias'] else 'Auto-detects from inputs'}</p>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Show recent matches to demonstrate rules in action
        st.markdown("---")
        st.subheader("📊 Recent Matches")
        
        recent = get_recent_matches(10)
        if recent:
            df = pd.DataFrame(recent)
            display_df = df[['match_date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'pattern_code']].copy()
            display_df.columns = ['Date', 'Home', 'Away', 'H', 'A', 'Pattern']
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        else:
            st.info("No recent matches found")

if __name__ == "__main__":
    main()
