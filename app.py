import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Supabase connection
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Run: pip install supabase")

st.set_page_config(
    page_title="⚽ Football Intelligence v25.0", 
    page_icon="🧠", 
    layout="wide"
)

if SUPABASE_AVAILABLE:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
else:
    supabase = None

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300)
def get_pattern_intelligence():
    """Get the rule-pattern intelligence matrix"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table('pattern_rule_intelligence')\
            .select('*')\
            .execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading intelligence: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_pattern_prediction(pattern_code, triggered_rules):
    """Get prediction using the intelligence matrix"""
    if supabase is None:
        return None
    
    try:
        # Get all rules for this pattern
        result = supabase.table('pattern_rule_intelligence')\
            .select('*')\
            .eq('pattern_code', pattern_code)\
            .execute()
        
        if not result.data:
            return None
        
        df = pd.DataFrame(result.data)
        
        # Filter to rules that triggered
        matching_rules = df[df['rule_key'].isin(triggered_rules)]
        
        if len(matching_rules) == 0:
            return None
        
        # Calculate weighted score
        total_weight = matching_rules['weight'].sum()
        weighted_score = 0
        
        for _, rule in matching_rules.iterrows():
            if rule['signal'] in ['OVER/BTTS', 'BALANCED']:
                weighted_score += rule['weight']
            else:  # UNDER signals
                weighted_score -= rule['weight']
        
        normalized_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Determine prediction
        if normalized_score > 0.2:
            prediction = "OVER 2.5 / BTTS"
            confidence = min(abs(normalized_score) * 100, 95)
            color = "#ff4444"
        elif normalized_score < -0.2:
            prediction = "UNDER 2.5 / NO BTTS"
            confidence = min(abs(normalized_score) * 100, 95)
            color = "#4444ff"
        else:
            prediction = "BALANCED - NO EDGE"
            confidence = 50
            color = "#888888"
        
        return {
            'prediction': prediction,
            'confidence': round(confidence, 1),
            'color': color,
            'rules_used': len(matching_rules),
            'top_rules': matching_rules.nlargest(3, 'weight')[['rule_key', 'rule_accuracy', 'signal']].to_dict('records'),
            'pattern_btts_rate': df['pattern_btts_rate'].iloc[0] if len(df) > 0 else 50
        }
        
    except Exception as e:
        st.error(f"Prediction error: {e}")
        return None

@st.cache_data(ttl=300)
def get_gold_patterns():
    """Get promoted gold patterns"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table('gold_patterns')\
            .select('*')\
            .eq('status', 'ACTIVE')\
            .execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_emerging_patterns():
    """Get emerging patterns from tracking"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table('pattern_tracking')\
            .select('*')\
            .eq('is_emerging', True)\
            .order('confidence_score', desc=True)\
            .execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            return df
        return pd.DataFrame()
    except Exception as e:
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
            'match_date': data.get('match_date', datetime.now().date().isoformat()),
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
# TIER CALCULATION
# ============================================================================

def calculate_tier(value, category):
    """Convert percentage to tier (1-4)"""
    if category == 'da':
        if value >= 75: return 1
        elif value >= 60: return 2
        elif value >= 40: return 3
        else: return 4
    else:
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
# MAIN APP
# ============================================================================

def main():
    st.title("🧠 Football Intelligence Platform v25.0")
    st.markdown("### Self-Learning • Rule-Based • Pattern Recognition")
    
    if not SUPABASE_AVAILABLE or supabase is None:
        st.error("Supabase connection failed")
        return
    
    # Load intelligence
    intelligence_df = get_pattern_intelligence()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 System Status")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Patterns", len(intelligence_df['pattern_code'].unique()) if not intelligence_df.empty else 0)
        with col2:
            st.metric("Active Rules", len(intelligence_df['rule_key'].unique()) if not intelligence_df.empty else 0)
        
        st.markdown("---")
        st.markdown("**🎯 PREDICTION KEY**")
        st.markdown("🔥 OVER 2.5 | ❄️ UNDER 2.5")
        st.markdown("⚽ BTTS | 🧤 NO BTTS")
        st.markdown("🏠 HOME | ✈️ AWAY | ⚖️ DRAW")
        
        st.markdown("---")
        st.markdown("**📈 Intelligence Stats**")
        if not intelligence_df.empty:
            top_rules = intelligence_df.groupby('rule_key').agg({
                'rule_accuracy': 'mean',
                'occurrences': 'sum'
            }).nlargest(3, 'rule_accuracy')
            
            for idx, (rule, data) in enumerate(top_rules.iterrows()):
                st.metric(
                    f"#{idx+1} {rule}", 
                    f"{data['rule_accuracy']:.1f}%", 
                    f"{int(data['occurrences'])} matches"
                )
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 NEW MATCH", 
        "🏆 GOLD PATTERNS", 
        "📈 EMERGING",
        "📊 INTELLIGENCE"
    ])
    
    # ===== TAB 1: NEW MATCH =====
    with tab1:
        st.header("🔍 Enter New Match")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("match_form"):
                # Teams
                col_home, col_away = st.columns(2)
                with col_home:
                    st.markdown("**🏠 HOME**")
                    home_team = st.text_input("Team Name", key="home_team")
                with col_away:
                    st.markdown("**✈️ AWAY**")
                    away_team = st.text_input("Team Name", key="away_team")
                
                # Stats
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.markdown("**Defensive Action**")
                    home_da = st.number_input("Home DA", 0, 100, 50, key="home_da")
                    away_da = st.number_input("Away DA", 0, 100, 50, key="away_da")
                
                with col_s2:
                    st.markdown("**BTTS %**")
                    home_btts = st.number_input("Home BTTS", 0, 100, 50, key="home_btts")
                    away_btts = st.number_input("Away BTTS", 0, 100, 50, key="away_btts")
                
                with col_s3:
                    st.markdown("**Over 2.5 %**")
                    home_over = st.number_input("Home Over", 0, 100, 50, key="home_over")
                    away_over = st.number_input("Away Over", 0, 100, 50, key="away_over")
                
                # Context
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    elite = st.checkbox("⭐ Elite")
                with col_c2:
                    derby = st.checkbox("🏆 Derby")
                with col_c3:
                    relegation = st.checkbox("⚠️ Relegation")
                
                league = st.selectbox(
                    "League",
                    ["EPL", "LA LIGA", "BUNDESLIGA", "SERIE A", "LIGUE 1", "OTHER"]
                )
                
                if league == "OTHER":
                    league = st.text_input("League Name")
                
                notes = st.text_input("Notes (optional)")
                
                analyze_btn = st.form_submit_button("🔮 ANALYZE", use_container_width=True)
        
        with col2:
            st.markdown("**📋 Quick Reference**")
            st.info("""
            **Tiers:**
            - **Tier 1:** Elite (75+/70+)
            - **Tier 2:** Strong (60-74/55-69)
            - **Tier 3:** Average (40-59/40-54)
            - **Tier 4:** Weak (<40)
            """)
        
        if analyze_btn and home_team and away_team:
            # Calculate tiers
            home_da_tier = calculate_tier(home_da, 'da')
            away_da_tier = calculate_tier(away_da, 'da')
            home_btts_tier = calculate_tier(home_btts, 'btts')
            away_btts_tier = calculate_tier(away_btts, 'btts')
            home_over_tier = calculate_tier(home_over, 'over')
            away_over_tier = calculate_tier(away_over, 'over')
            
            # Calculate flags
            home_adv_flag = home_da_tier < away_da_tier
            btts_pressure = (home_btts_tier <= 2 and away_da_tier >= 3) or (away_btts_tier <= 2 and home_da_tier >= 3) or elite or derby
            overs_pressure = (home_over_tier <= 2 and away_da_tier >= 3) or (away_over_tier <= 2 and home_da_tier >= 3)
            importance = (1 if elite else 0) + (1 if derby else 0) + (1 if relegation else 0)
            
            # Pattern code
            pattern_code = f"{'T' if home_adv_flag else 'F'},{'T' if overs_pressure else 'F'},{'T' if btts_pressure else 'F'},{importance}"
            
            # Determine which rules would trigger (simplified for demo)
            triggered_rules = []
            if home_da_tier == 4 and away_da_tier == 4:
                triggered_rules.append('rule_1')
            if away_btts_tier == 1 and home_da_tier >= 3:
                triggered_rules.append('rule_2')
            if home_da_tier <= 2 and away_da_tier >= 3:
                triggered_rules.append('rule_10')
            if home_da_tier == 3 and away_da_tier == 3 and home_over_tier == 4 and away_over_tier == 4:
                triggered_rules.append('rule_13')
            if home_btts_tier <= 2 and away_btts_tier <= 2:
                triggered_rules.append('rule_20_home')
            if away_btts_tier <= 2 and home_btts_tier <= 2:
                triggered_rules.append('rule_20_away')
            
            # Get prediction from intelligence
            prediction = get_pattern_prediction(pattern_code, triggered_rules)
            
            # Display results
            st.markdown("---")
            
            col_p1, col_p2 = st.columns([2, 1])
            
            with col_p1:
                if prediction:
                    st.markdown(f"""
                    <div style="background-color: #1e3a5f; padding: 25px; border-radius: 10px; border-left: 5px solid {prediction['color']};">
                        <h2 style="color: white; margin: 0;">{pattern_code}</h2>
                        <p style="color: #ffd700; font-size: 28px; font-weight: bold; margin: 10px 0;">{prediction['prediction']}</p>
                        <p style="color: white; font-size: 20px;">Confidence: {prediction['confidence']}%</p>
                        <p style="color: #aaa;">Based on {prediction['rules_used']} rules with historical data</p>
                        <div style="background-color: #2a4a7a; padding: 15px; border-radius: 5px; margin-top: 15px;">
                            <p style="color: #ddd; margin: 0;">Top contributing rules:</p>
                            {"".join([f'<p style="color: white; margin: 5px 0;">• {r["rule_key"]}: {r["rule_accuracy"]}% accurate → {r["signal"]}</p>' for r in prediction['top_rules']])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("No intelligence data yet for this pattern. Add more matches!")
            
            with col_p2:
                st.markdown("**📋 Match Profile**")
                st.markdown(f"""
                - **Home DA:** Tier {home_da_tier} ({get_tier_description(home_da_tier, 'da')})
                - **Away DA:** Tier {away_da_tier} ({get_tier_description(away_da_tier, 'da')})
                - **Home BTTS:** Tier {home_btts_tier} ({get_tier_description(home_btts_tier, 'btts')})
                - **Away BTTS:** Tier {away_btts_tier} ({get_tier_description(away_btts_tier, 'btts')})
                - **Importance:** {['Low', 'Medium', 'High'][importance]}
                """)
            # Enter result
st.markdown("---")
st.subheader("📥 Enter Result")

# Use session state to preserve values
if 'home_goals_input' not in st.session_state:
    st.session_state.home_goals_input = 0
if 'away_goals_input' not in st.session_state:
    st.session_state.away_goals_input = 0

col_r1, col_r2, col_r3 = st.columns([1, 1, 2])
with col_r1:
    home_goals = st.number_input(
        f"{home_team} Goals", 
        0, 10, 
        value=st.session_state.home_goals_input,
        key="home_goals_field"
    )
with col_r2:
    away_goals = st.number_input(
        f"{away_team} Goals", 
        0, 10, 
        value=st.session_state.away_goals_input,
        key="away_goals_field"
    )
with col_r3:
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 SAVE", type="primary", use_container_width=True):
            # Store in session state
            st.session_state.home_goals_input = home_goals
            st.session_state.away_goals_input = away_goals
            
            match_data = {
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'match_date': datetime.now().date().isoformat(),
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
            
            saved = save_match(match_data, home_goals, away_goals)
            if saved:
                st.success(f"✅ Match saved! Intelligence updated.")
                st.cache_data.clear()
                # Don't rerun immediately - show success message
                st.balloons()
                # Clear session state after successful save
                st.session_state.home_goals_input = 0
                st.session_state.away_goals_input = 0
                # Optional: wait then rerun
                st.rerun()
    
    with col_clear:
        if st.button("🗑️ CLEAR", use_container_width=True):
            st.session_state.home_goals_input = 0
            st.session_state.away_goals_input = 0
            st.rerun()
    
    # ===== TAB 2: GOLD PATTERNS =====
    with tab2:
        st.header("🏆 Gold Patterns")
        
        gold = get_gold_patterns()
        
        if not gold.empty:
            for _, pattern in gold.iterrows():
                tier_color = {
                    'PLATINUM': '#e5e4e2',
                    'HIGH': '#ffd700',
                    'MEDIUM': '#c0c0c0',
                    'LOW': '#cd7f32'
                }.get(pattern.get('confidence_tier'), '#ffffff')
                
                st.markdown(f"""
                <div style="background-color: #1e3a5f; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid {tier_color};">
                    <div style="display: flex; justify-content: space-between;">
                        <h3 style="color: white; margin: 0;">{pattern.get('pattern_name', pattern['pattern_code'])}</h3>
                        <span style="background-color: {tier_color}; color: black; padding: 5px 10px; border-radius: 5px;">{pattern.get('confidence_tier', 'NEW')}</span>
                    </div>
                    <p style="color: #ddd;">{pattern['pattern_code']}</p>
                    <div style="display: flex; gap: 20px; margin-top: 10px;">
                        <div><span style="color: #aaa;">Matches:</span> {pattern.get('discovery_sample_size', 0)}</div>
                        <div><span style="color: #aaa;">Home Win:</span> {pattern.get('discovery_home_win_rate', 0):.1f}%</div>
                        <div><span style="color: #aaa;">Over:</span> {pattern.get('discovery_over_rate', 0):.1f}%</div>
                        <div><span style="color: #aaa;">BTTS:</span> {pattern.get('discovery_btts_rate', 0):.1f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No gold patterns yet")
    
    # ===== TAB 3: EMERGING =====
    with tab3:
        st.header("📈 Emerging Patterns")
        
        emerging = get_emerging_patterns()
        
        if not emerging.empty:
            fig = px.scatter(
                emerging,
                x='total_matches',
                y='confidence_score',
                size='confidence_score',
                color='current_btts_rate',
                hover_data=['pattern_code'],
                title='Emerging Patterns - Confidence vs Sample Size'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            for _, pattern in emerging.iterrows():
                st.markdown(f"""
                <div style="background-color: #2a2a4a; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <h4 style="color: white;">{pattern['pattern_code']}</h4>
                    <div style="display: flex; gap: 20px;">
                        <div>Confidence: {pattern.get('confidence_score', 0):.1f}%</div>
                        <div>Matches: {pattern.get('total_matches', 0)}</div>
                        <div>BTTS: {pattern.get('current_btts_rate', 0):.1f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No emerging patterns")
    
    # ===== TAB 4: INTELLIGENCE =====
    with tab4:
        st.header("📊 Pattern Intelligence Matrix")
        
        if not intelligence_df.empty:
            # Summary stats
            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            col_i1.metric("Total Patterns", intelligence_df['pattern_code'].nunique())
            col_i2.metric("Total Rules", intelligence_df['rule_key'].nunique())
            col_i3.metric("Avg Rule Accuracy", f"{intelligence_df['rule_accuracy'].mean():.1f}%")
            col_i4.metric("Total Data Points", len(intelligence_df))
            
            # Filterable table
            pattern_filter = st.selectbox(
                "Filter by Pattern",
                ['All'] + sorted(intelligence_df['pattern_code'].unique().tolist())
            )
            
            if pattern_filter != 'All':
                display_df = intelligence_df[intelligence_df['pattern_code'] == pattern_filter]
            else:
                display_df = intelligence_df
            
            st.dataframe(
                display_df[['pattern_code', 'rule_key', 'occurrences', 'rule_accuracy', 'pattern_btts_rate', 'weight', 'signal']]
                .sort_values(['pattern_code', 'weight'], ascending=[True, False]),
                hide_index=True,
                use_container_width=True
            )
            
            # Visualization
            st.subheader("Rule Performance Across Patterns")
            top_rules = intelligence_df.groupby('rule_key').agg({
                'rule_accuracy': 'mean',
                'occurrences': 'sum'
            }).nlargest(10, 'rule_accuracy').reset_index()
            
            fig = px.bar(
                top_rules,
                x='rule_key',
                y='rule_accuracy',
                color='occurrences',
                title='Top 10 Most Accurate Rules',
                labels={'rule_accuracy': 'Accuracy (%)', 'occurrences': 'Total Occurrences'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Intelligence data loading...")

if __name__ == "__main__":
    main()
