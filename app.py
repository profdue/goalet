import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
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

st.set_page_config(page_title="Discovery Hunter v22.0", page_icon="🏆", layout="wide")

if SUPABASE_AVAILABLE:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
else:
    supabase = None

# ============================================================================
# TIER FUNCTIONS
# ============================================================================

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
# DATABASE FUNCTIONS
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
            'elite': data['elite'],
            'derby': data['derby'],
            'relegation': data['relegation'],
            'result_entered': home_goals is not None,
            'discovery_notes': data.get('notes', '')
        }
        
        if home_goals is not None:
            match_data['home_goals'] = home_goals
            match_data['away_goals'] = away_goals
        
        result = supabase.table('matches').insert(match_data).execute()
        return result.data[0]['id']
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
    st.title("🏆 Discovery Hunter v22.0")
    st.markdown("### 22 Active Rules - OVER/UNDER Separated")
    
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
            
            # Show gold rules
            rules = get_rule_performance()
            if rules:
                st.markdown("---")
                st.subheader("🏆 Gold Rules")
                
                # Show OVER gold rules
                for rule in rules.get('over', []):
                    if rule.get('accuracy', 0) == 100:
                        st.success(f"🔥 {rule['rule_name'][:30]}")
                
                # Show UNDER gold rules
                for rule in rules.get('under', []):
                    if rule.get('accuracy', 0) == 100:
                        st.success(f"❄️ {rule['rule_name'][:30]}")
        except Exception as e:
            st.info("No data yet")
        
        st.markdown("---")
        st.markdown("**TIER KEY**")
        st.markdown("1💥 Elite | 2⚡ Strong | 3📊 Average | 4🐢 Weak")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 New Match", "📊 Rules Engine", "📈 League Stats", "📋 Recent Matches", "🔮 Upcoming"])
    
    with tab1:
        st.subheader("Enter New Match Data")
        
        if 'pending_match' not in st.session_state:
            st.session_state.pending_match = None
        
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
            
            submitted = st.form_submit_button("🔍 ANALYZE", use_container_width=True)
        
        if submitted:
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
                st.rerun()
        
        if st.session_state.pending_match:
            data = st.session_state.pending_match
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
                st.info(f"**Preview:** {home_goals}-{away_goals} | Total: {total} | {'OVER' if total>=3 else 'UNDER'} 2.5")
                
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                with col_b2:
                    saved = st.form_submit_button("💾 SAVE MATCH", type="primary", use_container_width=True)
                
                if saved:
                    match_id = save_match(data, home_goals, away_goals)
                    if match_id:
                        st.success(f"✅ Match #{match_id} saved!")
                        st.balloons()
                        st.session_state.pending_match = None
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

if __name__ == "__main__":
    main()
