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
        st.error(f"Error: {e}")
        return None

def get_rule_performance():
    if supabase is None:
        return []
    
    try:
        result = supabase.table('matches')\
            .select('rule_hits')\
            .eq('result_entered', True)\
            .not_.is_('rule_hits', 'null')\
            .execute()
        
        rule_stats = {}
        rule_order = [
            'rule_21', 'rule_22', 'rule_18', 'rule_13', 'rule_1',  # 100% rules
            'rule_2', 'rule_5', 'rule_6', 'rule_7', 'rule_16',      # 80-90% rules
            'rule_3', 'rule_8', 'rule_15', 'rule_20_home', 'rule_20_away', 'rule_17',  # 70-80% rules
            'rule_10', 'rule_14'                                      # Monitor/Gray Zone
        ]
        
        rule_names = {
            'rule_1': '[4,4] Opening = ≤2 Goals',
            'rule_2': 'away_btts_tier = 1 = Winner',
            'rule_3': 'Importance 2 = ≥3 Goals',
            'rule_5': 'Home Advantage Flag = No Draw',
            'rule_6': 'away_da≥55 + home_adv=false = Away unbeaten',
            'rule_7': 'Mixed Defense = Winner',
            'rule_8': 'away_da≤40 + home_da≥45 = Away no win',
            'rule_10': 'home_tier2 vs away_tier3 = Home Loss',
            'rule_13': '[3,3,3] Opening = Under 2.5',
            'rule_14': 'Gray Zone (4+ tiers = 3) - No Edge',
            'rule_15': 'Elite Home = Draw/Away Win',
            'rule_16': 'Elite Away Win',
            'rule_17': 'Championship Mixed Defense = Home Win',
            'rule_18': '[3,4] + home_btts≤2 = Home Win',
            'rule_19': '[4,3] + away_btts≤2 = Away Win',
            'rule_20_home': 'Home Tier 1 Attack = Home Win/Draw',
            'rule_20_away': 'Away Tier 1 Attack = Away Win/Draw',
            'rule_21': '🔥 DOUBLE PRESSURE = OVER 2.5 LOCK',
            'rule_22': '🏆 GRAND UNIFIED UNDER RULE'
        }
        
        for match in result.data:
            rules = match.get('rule_hits')
            if not rules:
                continue
            
            if isinstance(rules, str):
                rules = json.loads(rules)
            
            for key, rule in rules.items():
                if key not in rule_stats:
                    rule_stats[key] = {
                        'name': rule_names.get(key, rule.get('name', key)),
                        'total': 0,
                        'hits': 0
                    }
                rule_stats[key]['total'] += 1
                if rule.get('hit', False):
                    rule_stats[key]['hits'] += 1
        
        # Format for display in rule order
        result_data = []
        for key in rule_order:
            if key in rule_stats:
                stats = rule_stats[key]
                accuracy = (stats['hits'] / stats['total'] * 100) if stats['total'] > 0 else 0
                result_data.append({
                    'rule_key': key,
                    'rule_name': stats['name'],
                    'total_apps': stats['total'],
                    'hits': stats['hits'],
                    'accuracy': round(accuracy, 1)
                })
        
        return result_data
    except Exception as e:
        st.error(f"Error getting rule performance: {e}")
        return []

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
            total_goals = league_df['actual_goals'].sum()
            btts_count = league_df['actual_btts'].sum()
            over_count = (league_df['actual_goals'] >= 3).sum()
            
            stats[league] = {
                'matches': total_matches,
                'avg_goals': round(total_goals / total_matches, 2) if total_matches > 0 else 0,
                'btts_rate': round((btts_count / total_matches) * 100, 1) if total_matches > 0 else 0,
                'over_rate': round((over_count / total_matches) * 100, 1) if total_matches > 0 else 0
            }
        return stats
    except Exception as e:
        st.error(f"Error: {e}")
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
        st.error(f"Error: {e}")
        return []

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🏆 Discovery Hunter v22.0")
    st.markdown("### 22 Active Rules - 2 Gold Locks Discovered!")
    
    if not SUPABASE_AVAILABLE or supabase is None:
        st.error("Supabase not connected")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Live Stats")
        try:
            total = supabase.table('matches').select('*', count='exact').execute()
            completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
            
            st.metric("Total Matches", total.count)
            st.metric("Completed", completed.count)
            
            rules = get_rule_performance()
            gold_rules = [r for r in rules if r['accuracy'] == 100 and r['total_apps'] >= 5]
            if gold_rules:
                st.success(f"🎯 Gold Rules: {len(gold_rules)}")
                for rule in gold_rules[:2]:
                    st.metric(rule['rule_name'][:20], f"{rule['accuracy']}%", f"{rule['hits']}/{rule['total_apps']}")
        except:
            st.info("No data yet")
        
        st.markdown("---")
        st.markdown("**TIER KEY**")
        st.markdown("1💥 Elite | 2⚡ Strong | 3📊 Average | 4🐢 Weak")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 New Match", "📊 Rules Engine", "📈 League Stats", "📋 Recent Matches"])
    
    with tab1:
        st.subheader("Enter New Match Data")
        
        if 'pending_match' not in st.session_state:
            st.session_state.pending_match = None
        
        with st.form("match_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏠 HOME**")
                home_team = st.text_input("Team")
                home_da = st.number_input("DA", 0, 100, 50)
                home_btts = st.number_input("BTTS %", 0, 100, 50)
                home_over = st.number_input("Over %", 0, 100, 50)
            
            with col2:
                st.markdown("**✈️ AWAY**")
                away_team = st.text_input("Team", key="away_team")
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
            
            league = st.selectbox("League", ["EPL", "BUNDESLIGA", "SERIE A", "LA LIGA", "LIGUE 1", "CHAMPIONSHIP"])
            notes = st.text_input("Notes")
            
            submitted = st.form_submit_button("🔍 ANALYZE", use_container_width=True)
        
        if submitted:
            st.session_state.pending_match = {
                'home_team': home_team, 'away_team': away_team, 'league': league,
                'home_da': home_da, 'away_da': away_da,
                'home_btts': home_btts, 'away_btts': away_btts,
                'home_over': home_over, 'away_over': away_over,
                'elite': elite, 'derby': derby, 'relegation': relegation,
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
                    home_goals = st.number_input(f"{data['home_team']} Goals", 0, 20, 0)
                with col_r2:
                    away_goals = st.number_input(f"{data['away_team']} Goals", 0, 20, 0)
                
                total = home_goals + away_goals
                st.info(f"Preview: {home_goals}-{away_goals} | Total: {total} | BTTS: {'✅' if home_goals>0 and away_goals>0 else '❌'} | Over: {'✅' if total>=3 else '❌'}")
                
                saved = st.form_submit_button("💾 SAVE", type="primary", use_container_width=True)
                if saved:
                    match_id = save_match(data, home_goals, away_goals)
                    if match_id:
                        st.success(f"✅ Match #{match_id} saved!")
                        st.balloons()
                        st.session_state.pending_match = None
                        st.rerun()
    
    with tab2:
        st.header("📊 Rules Engine")
        st.markdown("### 22 Active Rules - Sorted by Confidence")
        
        rules = get_rule_performance()
        
        if rules:
            # Gold Rules (100%)
            gold = [r for r in rules if r['accuracy'] == 100 and r['total_apps'] >= 3]
            if gold:
                st.success("🏆 **GOLD RULES (100%)**")
                df_gold = pd.DataFrame(gold)
                st.dataframe(df_gold[['rule_name', 'total_apps', 'hits', 'accuracy']], 
                           hide_index=True, use_container_width=True)
            
            # Silver Rules (90-99%)
            silver = [r for r in rules if 90 <= r['accuracy'] < 100]
            if silver:
                st.info("🥈 **SILVER RULES (90-99%)**")
                df_silver = pd.DataFrame(silver)
                st.dataframe(df_silver[['rule_name', 'total_apps', 'hits', 'accuracy']], 
                           hide_index=True, use_container_width=True)
            
            # Bronze Rules (80-89%)
            bronze = [r for r in rules if 80 <= r['accuracy'] < 90]
            if bronze:
                st.info("🥉 **BRONZE RULES (80-89%)**")
                df_bronze = pd.DataFrame(bronze)
                st.dataframe(df_bronze[['rule_name', 'total_apps', 'hits', 'accuracy']], 
                           hide_index=True, use_container_width=True)
            
            # Developing Rules (70-79%)
            developing = [r for r in rules if 70 <= r['accuracy'] < 80]
            if developing:
                st.info("📈 **DEVELOPING (70-79%)**")
                df_dev = pd.DataFrame(developing)
                st.dataframe(df_dev[['rule_name', 'total_apps', 'hits', 'accuracy']], 
                           hide_index=True, use_container_width=True)
            
            # Monitor Rules (<70%)
            monitor = [r for r in rules if r['accuracy'] < 70 and r['rule_name'] != 'Gray Zone (4+ tiers = 3) - No Edge']
            if monitor:
                st.warning("⚠️ **MONITOR (<70%)**")
                df_mon = pd.DataFrame(monitor)
                st.dataframe(df_mon[['rule_name', 'total_apps', 'hits', 'accuracy']], 
                           hide_index=True, use_container_width=True)
            
            # Gray Zone
            gray = [r for r in rules if 'Gray Zone' in r['rule_name']]
            if gray:
                st.info("⚪ **GRAY ZONE (No Edge)**")
                df_gray = pd.DataFrame(gray)
                st.dataframe(df_gray[['rule_name', 'total_apps']], 
                           hide_index=True, use_container_width=True)
            
            # Visualization
            st.markdown("---")
            st.subheader("📈 Rule Accuracy Chart")
            
            chart_data = pd.DataFrame([r for r in rules if r['total_apps'] >= 3])
            if not chart_data.empty:
                fig = px.bar(chart_data, 
                            x='rule_name', 
                            y='accuracy',
                            color='accuracy',
                            color_continuous_scale='RdYlGn',
                            range_color=[0, 100],
                            title='Rule Accuracy (%)',
                            labels={'rule_name': 'Rule', 'accuracy': 'Accuracy %'})
                fig.update_layout(xaxis_tickangle=-45, height=600)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("📈 League Statistics")
        
        stats = get_league_stats()
        if stats:
            df = pd.DataFrame(stats).T.reset_index()
            df.columns = ['League', 'Matches', 'Avg Goals', 'BTTS %', 'Over %']
            st.dataframe(df, hide_index=True, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df, x='League', y='Avg Goals', title='Average Goals by League')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(df, x='League', y=['BTTS %', 'Over %'], 
                            title='BTTS & Over Rates', barmode='group')
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("📋 Recent Matches")
        
        matches = get_recent_matches(20)
        if matches:
            data = []
            for m in matches:
                rules = m.get('rule_hits', {})
                if isinstance(rules, str):
                    rules = json.loads(rules)
                
                rule_count = len(rules) if rules else 0
                gold_rules = sum(1 for r in rules.values() if r.get('hit') and 'LOCK' in r.get('name', ''))
                
                data.append({
                    'Date': m.get('match_date', '')[-5:],
                    'Home': m.get('home_team', ''),
                    'Score': f"{m.get('home_goals', 0)}-{m.get('away_goals', 0)}",
                    'Away': m.get('away_team', ''),
                    'League': m.get('league', ''),
                    'Rules': rule_count,
                    'Gold': '🏆' * gold_rules if gold_rules else ''
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, hide_index=True, use_container_width=True)

if __name__ == "__main__":
    main()
