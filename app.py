import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import json

# Try to import supabase with error handling
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Supabase module not installed. Database features disabled. Run: pip install supabase")

# Page config
st.set_page_config(
    page_title="Discovery Hunter v16.0",
    page_icon="🔍",
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
# TIER FUNCTIONS
# ============================================================================

def tier_to_emoji(tier, category):
    """Convert tier number to emoji with category context"""
    emojis = {
        'da': ["💥", "⚡", "📊", "🐢"],
        'btts': ["🎯", "⚽", "🤔", "🧤"],
        'over': ["🔥", "📈", "⚖️", "📉"]
    }
    return emojis[category][tier-1]

def get_tier_description(tier, category):
    """Get text description of tier"""
    if category == 'da':
        descriptions = ["Elite Defense", "Strong Defense", "Average Defense", "Weak Defense"]
    elif category == 'btts':
        descriptions = ["Always Scores", "Usually Scores", "50/50", "Rarely Scores"]
    else:
        descriptions = ["Goal Fest", "Goals Likely", "50/50", "Goals Unlikely"]
    return descriptions[tier-1]

def format_tier_display(tiers):
    """Format tiers for display with emojis"""
    categories = ['da', 'da', 'btts', 'btts', 'over', 'over']
    labels = ['HOME DA', 'AWAY DA', 'HOME BTTS', 'AWAY BTTS', 'HOME OVER', 'AWAY OVER']
    
    display = []
    for i, (tier, cat, label) in enumerate(zip(tiers, categories, labels)):
        emoji = tier_to_emoji(tier, cat)
        desc = get_tier_description(tier, cat)
        display.append(f"{label}: {emoji} Tier {tier} ({desc})")
    
    return display

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def save_match(data, home_goals=None, away_goals=None):
    """Save match to Supabase with optional result"""
    if supabase is None:
        st.error("Supabase not connected")
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
        st.error(f"Error saving to database: {e}")
        return None

def get_rule_performance():
    """Get current rule performance stats"""
    if supabase is None:
        return {}
    
    try:
        # Use the view we created
        result = supabase.table('rule_performance').select('*').execute()
        return result.data
    except Exception as e:
        # Fallback to direct query if view doesn't exist
        try:
            result = supabase.table('matches')\
                .select('rule_hits')\
                .eq('result_entered', True)\
                .not_.is_('rule_hits', 'null')\
                .execute()
            
            matches = result.data
            rule_stats = {}
            
            for match in matches:
                rules = match.get('rule_hits')
                if not rules:
                    continue
                
                if isinstance(rules, str):
                    rules = json.loads(rules)
                
                for key, rule in rules.items():
                    if key not in rule_stats:
                        rule_stats[key] = {
                            'rule_name': rule['name'],
                            'total': 0,
                            'hits': 0
                        }
                    rule_stats[key]['total'] += 1
                    if rule['hit']:
                        rule_stats[key]['hits'] += 1
            
            # Format for display
            result_data = []
            for key, stats in rule_stats.items():
                accuracy = (stats['hits'] / stats['total'] * 100) if stats['total'] > 0 else 0
                result_data.append({
                    'rule_name': stats['rule_name'],
                    'total_applications': stats['total'],
                    'hits': stats['hits'],
                    'accuracy': round(accuracy, 1)
                })
            
            return sorted(result_data, key=lambda x: x['accuracy'], reverse=True)
        except Exception as e2:
            st.error(f"Error getting rule performance: {e2}")
            return []

def get_league_stats():
    """Get league statistics"""
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
                'over_rate': round((over_count / total_matches) * 100, 1) if total_matches > 0 else 0,
                'total_goals': int(total_goals)
            }
        return stats
    except Exception as e:
        st.error(f"Error getting league stats: {e}")
        return {}

def get_recent_matches(limit=10):
    """Get recent matches with results"""
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

def get_database_stats():
    """Get overall database statistics"""
    if supabase is None:
        return {}
    
    try:
        total = supabase.table('matches').select('*', count='exact').execute()
        completed = supabase.table('matches').select('*', count='exact').eq('result_entered', True).execute()
        
        return {
            'total': total.count if hasattr(total, 'count') else 0,
            'completed': completed.count if hasattr(completed, 'count') else 0
        }
    except Exception as e:
        st.error(f"Error getting database stats: {e}")
        return {}

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🔍 Discovery Hunter v16.0")
    st.markdown("### Data-Driven Football Pattern Discovery Engine")
    
    # Check Supabase connection
    if not SUPABASE_AVAILABLE:
        st.warning("⚠️ Supabase not installed. Run: `pip install supabase`")
        return
    elif supabase is None:
        st.error("❌ Supabase connection failed. Check your secrets.")
        return
    else:
        st.success("✅ Supabase connected")
    
    # Sidebar - Database Stats
    with st.sidebar:
        st.header("📊 Database Stats")
        stats = get_database_stats()
        st.metric("Total Matches", stats.get('total', 0))
        st.metric("Completed", stats.get('completed', 0))
        
        # Quick rule summary
        st.markdown("---")
        st.subheader("🎯 Top Rules")
        rules = get_rule_performance()
        if rules:
            for rule in rules[:3]:  # Show top 3
                st.metric(
                    rule['rule_name'][:30] + "...",
                    f"{rule['accuracy']}%",
                    f"{rule['hits']}/{rule['total_applications']}"
                )
        
        st.markdown("---")
        st.markdown("**TIER KEY**")
        st.markdown("1💥 Elite | 2⚡ Strong | 3📊 Average | 4🐢 Weak")
        st.markdown("**Tiers 1-4 only**")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 New Match", 
        "📊 Rules Engine", 
        "📈 League Stats", 
        "🔬 Discovery Lab",
        "📋 Recent Matches"
    ])
    
    with tab1:
        st.subheader("Enter New Match Data")
        
        # Initialize session state for pending match
        if 'pending_match' not in st.session_state:
            st.session_state.pending_match = None
        
        with st.form("match_input_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏠 HOME TEAM**")
                home_team = st.text_input("Home Team", placeholder="e.g., Arsenal")
                home_da = st.number_input("DA (Defensive Strength)", 0, 100, 50, 
                                         help="Higher = Better Defense")
                home_btts = st.number_input("BTTS %", 0, 100, 50,
                                           help="Likelihood of Both Teams Scoring")
                home_over = st.number_input("Over %", 0, 100, 50,
                                           help="Likelihood of Over 2.5 Goals")
            
            with col2:
                st.markdown("**✈️ AWAY TEAM**")
                away_team = st.text_input("Away Team", placeholder="e.g., Chelsea")
                away_da = st.number_input("DA", 0, 100, 50, key="away_da")
                away_btts = st.number_input("BTTS %", 0, 100, 50, key="away_btts")
                away_over = st.number_input("Over %", 0, 100, 50, key="away_over")
            
            col3, col4, col5 = st.columns(3)
            with col3:
                elite = st.checkbox("⭐ Elite Match", help="Top teams, title race")
            with col4:
                derby = st.checkbox("🏆 Derby", help="Local rivals")
            with col5:
                relegation = st.checkbox("⚠️ Relegation Battle", help="Both teams fighting to stay up")
            
            league = st.selectbox("League", 
                                 ["EPL", "BUNDESLIGA", "SERIE A", "LA LIGA", "LIGUE 1", 
                                  "CHAMPIONSHIP", "SUPER LIG", "AUSTRIAN", "TEST LEAGUE"])
            notes = st.text_input("Notes (optional)", placeholder="Injuries, weather, etc.")
            
            submitted = st.form_submit_button("🔍 ANALYZE & PREVIEW", use_container_width=True, type="primary")
        
        if submitted:
            # Validate required fields
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
                st.success("Match data captured! Scroll down to enter result.")
                st.rerun()
        
        # Show pending match and result entry
        if st.session_state.pending_match:
            data = st.session_state.pending_match
            
            st.markdown("---")
            st.subheader("📋 Match Preview")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.markdown(f"**🏠 {data['home_team']}**")
                st.text(f"DA: {data['home_da']}")
                st.text(f"BTTS: {data['home_btts']}%")
                st.text(f"Over: {data['home_over']}%")
            with col2:
                st.markdown(f"**✈️ {data['away_team']}**")
                st.text(f"DA: {data['away_da']}")
                st.text(f"BTTS: {data['away_btts']}%")
                st.text(f"Over: {data['away_over']}%")
            with col3:
                context = []
                if data['elite']: context.append("⭐ Elite")
                if data['derby']: context.append("🏆 Derby")
                if data['relegation']: context.append("⚠️ Relegation")
                st.markdown(f"**League:** {data['league']}")
                st.markdown(f"**Context:** {' | '.join(context) if context else 'None'}")
                if data['notes']:
                    st.markdown(f"**Notes:** {data['notes']}")
            
            st.markdown("---")
            st.subheader("📥 Enter Actual Result")
            
            with st.form("result_entry_form"):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    home_goals = st.number_input(f"{data['home_team']} Goals", 0, 20, 0)
                with col_r2:
                    away_goals = st.number_input(f"{data['away_team']} Goals", 0, 20, 0)
                
                # Preview
                total_goals = home_goals + away_goals
                btts = (home_goals > 0 and away_goals > 0)
                over = total_goals >= 3
                
                st.info(
                    f"**Preview:** {home_goals}-{away_goals} | "
                    f"Total: {total_goals} | "
                    f"BTTS: {'✅' if btts else '❌'} | "
                    f"Over 2.5: {'✅' if over else '❌'}"
                )
                
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                with col_b2:
                    saved = st.form_submit_button("💾 SAVE TO DATABASE", type="primary", use_container_width=True)
                
                if saved:
                    match_id = save_match(data, home_goals, away_goals)
                    if match_id:
                        st.success(f"✅ Match #{match_id} saved successfully!")
                        st.balloons()
                        st.session_state.pending_match = None
                        st.rerun()
    
    with tab2:
        st.header("📊 Rules Engine")
        st.markdown("### Live Rule Performance Tracking")
        
        rules = get_rule_performance()
        
        if rules:
            # Separate perfect rules (100%) from others
            perfect_rules = [r for r in rules if r['accuracy'] == 100]
            active_rules = [r for r in rules if r['accuracy'] < 100 and r['accuracy'] >= 70]
            weak_rules = [r for r in rules if r['accuracy'] < 70]
            
            if perfect_rules:
                st.success("🎯 **PERFECT RULES (100%)**")
                df_perfect = pd.DataFrame(perfect_rules)
                df_perfect = df_perfect.rename(columns={
                    'rule_name': 'Rule',
                    'total_applications': 'Apps',
                    'hits': 'Hits',
                    'accuracy': 'Accuracy %'
                })
                st.dataframe(df_perfect, hide_index=True, use_container_width=True)
            
            if active_rules:
                st.info("📊 **ACTIVE RULES (70-99%)**")
                df_active = pd.DataFrame(active_rules)
                df_active = df_active.rename(columns={
                    'rule_name': 'Rule',
                    'total_applications': 'Apps',
                    'hits': 'Hits',
                    'accuracy': 'Accuracy %'
                })
                st.dataframe(df_active, hide_index=True, use_container_width=True)
            
            if weak_rules:
                st.warning("⚠️ **WEAK RULES (<70%)**")
                df_weak = pd.DataFrame(weak_rules)
                df_weak = df_weak.rename(columns={
                    'rule_name': 'Rule',
                    'total_applications': 'Apps',
                    'hits': 'Hits',
                    'accuracy': 'Accuracy %'
                })
                st.dataframe(df_weak, hide_index=True, use_container_width=True)
            
            # Visualization
            st.markdown("---")
            st.subheader("📈 Rule Accuracy Chart")
            
            chart_data = pd.DataFrame(rules)
            fig = px.bar(chart_data, 
                        x='rule_name', 
                        y='accuracy',
                        color='accuracy',
                        color_continuous_scale='RdYlGn',
                        range_color=[0, 100],
                        title='Rule Accuracy (%)',
                        labels={'rule_name': 'Rule', 'accuracy': 'Accuracy %'})
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No rule data available yet. Add matches to discover patterns.")
    
    with tab3:
        st.header("📈 League Statistics")
        st.markdown("### Performance by League")
        
        league_stats = get_league_stats()
        
        if league_stats:
            # Convert to DataFrame
            data = []
            for league, stats in league_stats.items():
                data.append({
                    'League': league,
                    'Matches': stats['matches'],
                    'Avg Goals': stats['avg_goals'],
                    'BTTS %': stats['btts_rate'],
                    'Over %': stats['over_rate'],
                    'Total Goals': stats['total_goals']
                })
            
            df = pd.DataFrame(data)
            df = df.sort_values('Matches', ascending=False)
            
            # Display table
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
                            barmode='group',
                            color_discrete_map={'BTTS %': 'blue', 'Over %': 'red'})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No league data available yet. Add completed matches to see statistics.")
    
    with tab4:
        st.header("🔬 Discovery Lab")
        st.markdown("### Track Your 100% Rules in Real-Time")
        
        # Show current perfect rules
        rules = get_rule_performance()
        perfect_rules = [r for r in rules if r['accuracy'] == 100] if rules else []
        
        if perfect_rules:
            st.success(f"🎯 **{len(perfect_rules)} Perfect Rules Currently Active**")
            for rule in perfect_rules:
                st.metric(
                    rule['rule_name'],
                    f"{rule['accuracy']}%",
                    f"{rule['hits']}/{rule['total_applications']}"
                )
        else:
            st.info("No perfect rules yet. Keep collecting data!")
        
        # Rule maintenance tips
        st.markdown("---")
        st.subheader("🔧 Rule Maintenance")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **When to KEEP a rule:**
            - >90% accuracy after 20+ applications
            - Consistent across multiple leagues
            - Makes football sense
            
            **When to REFINE a rule:**
            - 70-90% accuracy
            - Has clear exceptions
            - Needs context (elite/derby)
            """)
        
        with col2:
            st.markdown("""
            **When to DROP a rule:**
            - <70% accuracy after 20+ apps
            - Worse than coin flip
            - No logical explanation
            
            **When to ADD a rule:**
            - New pattern emerges
            - Rule-breakers share common trait
            - Statistically significant
            """)
    
    with tab5:
        st.header("📋 Recent Matches")
        st.markdown("### Latest Completed Matches")
        
        recent = get_recent_matches(20)
        
        if recent:
            # Format for display
            display_data = []
            for match in recent:
                # Get rule summary
                rules = match.get('rule_hits')
                rule_count = 0
                rule_hits = 0
                
                if rules:
                    if isinstance(rules, str):
                        rules = json.loads(rules)
                    if isinstance(rules, dict):
                        rule_count = len(rules)
                        rule_hits = sum(1 for r in rules.values() if r.get('hit', False))
                
                display_data.append({
                    'Date': match.get('match_date', '')[-5:],
                    'Home': match.get('home_team', ''),
                    'Score': f"{match.get('home_goals', 0)}-{match.get('away_goals', 0)}",
                    'Away': match.get('away_team', ''),
                    'League': match.get('league', ''),
                    'Rules': f"{rule_hits}/{rule_count}" if rule_count > 0 else "None",
                    'Importance': match.get('importance_score', 0)
                })
            
            df = pd.DataFrame(display_data)
            st.dataframe(df, hide_index=True, use_container_width=True)
            
            # Show rule-breakers
            st.markdown("---")
            st.subheader("⚠️ Recent Rule-Breakers")
            
            breakers = []
            for match in recent[:10]:
                rules = match.get('rule_hits')
                if not rules:
                    continue
                
                if isinstance(rules, str):
                    rules = json.loads(rules)
                
                if isinstance(rules, dict):
                    failed = [r['name'] for r in rules.values() if not r.get('hit', False)]
                    if failed:
                        breakers.append({
                            'Match': f"{match['home_team']} {match['home_goals']}-{match['away_goals']} {match['away_team']}",
                            'Broken Rules': ', '.join(failed[:2])  # Show first 2
                        })
            
            if breakers:
                for breaker in breakers:
                    st.warning(f"**{breaker['Match']}** broke: {breaker['Broken Rules']}")
            else:
                st.info("No recent rule-breakers found!")
        else:
            st.info("No completed matches yet. Add matches to see them here.")

if __name__ == "__main__":
    main()
