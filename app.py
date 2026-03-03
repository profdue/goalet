import streamlit as st
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v4.0 - Predictor",
    page_icon="⚽",
    layout="centered"
)

# Initialize session state for tracking matches (temporary, resets on refresh)
if 'tracked_matches' not in st.session_state:
    st.session_state.tracked_matches = [
        {
            'date': '2026-03-03',
            'home': 'Leeds',
            'away': 'Sunderland',
            'score': 2,
            'score_max': 9,
            'prediction': '📊 MODEL SPECIAL',
            'call': 'Under lean',
            'actual': '0-1',
            'under_hit': True,
            'btts_hit': False,
            'notes': 'Perfect Under call, both DA <45'
        },
        {
            'date': '2026-03-03',
            'home': 'Bournemouth',
            'away': 'Brentford',
            'score': 5,
            'score_max': 9,
            'prediction': '🔄 HYBRID',
            'call': 'Watch BTTS',
            'actual': '0-0',
            'under_hit': True,
            'btts_hit': False,
            'notes': 'Correct Under, BTTS miss but acceptable variance'
        },
        {
            'date': '2026-03-03',
            'home': 'Wolves',
            'away': 'Liverpool',
            'score': 1,
            'score_max': 9,
            'prediction': '📊 MODEL SPECIAL',
            'call': 'Under lean',
            'actual': '2-1',
            'under_hit': False,
            'btts_hit': True,
            'notes': 'Miss - Liverpool elite variance, late goals'
        },
        {
            'date': '2026-03-03',
            'home': 'Liverpool',
            'away': 'West Ham',
            'score': 4,
            'score_max': 9,
            'prediction': '🔄 HYBRID',
            'call': 'Watch BTTS',
            'actual': '5-2',
            'under_hit': False,
            'btts_hit': True,
            'notes': 'BTTS hit, Under miss - blowout underestimated'
        }
    ]

# Title
st.title("⚽ Mismatch Hunter v4.0")
st.markdown("### Ultra-Lean Prediction Engine")
st.markdown("---")

# Helper function for calculations
def calculate_prediction(h_da, a_da, h_btts, a_btts, h_over, a_over, 
                        derby=False, relegation=False, elite_team=False):
    """Calculate explosion score and prediction with elite team boost"""
    
    # Base score calculation
    base_score = 0
    
    # DA condition - both teams attacking
    if h_da >= 45 and a_da >= 45:
        base_score += 2
        da_note = "✅ Both teams attacking"
    else:
        da_note = "❌ Not both teams attacking"
    
    # BTTS condition
    avg_btts = (h_btts + a_btts) / 2
    if avg_btts >= 55:
        base_score += 2
        btts_note = f"✅ BTTS {avg_btts:.1f}% ≥ 55%"
    else:
        btts_note = f"❌ BTTS {avg_btts:.1f}% < 55%"
    
    # Over 2.5 condition
    avg_over = (h_over + a_over) / 2
    if avg_over >= 55:
        base_score += 1
        over_note = f"✅ Over 2.5 {avg_over:.1f}% ≥ 55%"
    else:
        over_note = f"❌ Over 2.5 {avg_over:.1f}% < 55%"
    
    # Attacking boost (if either team attacks)
    attacking_boost = 1 if (h_da >= 45 or a_da >= 45) else 0
    if attacking_boost:
        boost_note = "✅ Attacking identity (+1)"
    else:
        boost_note = "❌ No attacking boost"
    
    # Context boosts
    context_score = (2 if derby else 0) + (1 if relegation else 0) + (1 if elite_team else 0)
    
    # Track which boosts applied
    boosts_applied = []
    if derby:
        boosts_applied.append("🏆 Derby (+2)")
    if relegation:
        boosts_applied.append("⚠️ Relegation dog (+1)")
    if elite_team:
        boosts_applied.append("⭐ Elite team (+1)")
    
    # Total score (now out of 10 max)
    total_score = base_score + attacking_boost + context_score
    max_score = 10  # 5 base + 1 attacking + 2 derby + 1 relegation + 1 elite
    
    # Determine match type and prediction (adjusted thresholds for 10-point scale)
    if total_score >= 8:
        match_type = "💥 EXPLOSION"
        prediction = "🔥 OVER 2.5 PRIMARY"
        confidence = "High"
        emoji = "🚀"
        action = "STRONG OVER lean - consider betting Over 2.5"
        bg_color = "#FFE5E5"
        border = "3px solid #FF4B4B"
    elif total_score >= 5:
        match_type = "🔄 HYBRID"
        prediction = "⚠️ HYBRID — Watch BTTS & live"
        confidence = "Medium"
        emoji = "⚖️"
        action = "Watch live - BTTS likely, consider Over if momentum"
        bg_color = "#FFF3E0"
        border = "3px solid #FFA500"
    elif total_score >= 3:
        match_type = "📊 MODEL SPECIAL"
        prediction = "✅ MODEL SPECIAL — Lean Under"
        confidence = "Low-Medium"
        emoji = "🐢"
        action = "Slight Under lean, but watch for elite team impact"
        bg_color = "#E8F5E9"
        border = "3px solid #4CAF50"
    else:
        match_type = "📊 MODEL SPECIAL"
        prediction = "✅ MODEL SPECIAL — Strong Under lean"
        confidence = "Low"
        emoji = "🐢"
        action = "STRONG Under lean - trust the model"
        bg_color = "#E8F5E9"
        border = "3px solid #2E7D32"
    
    return {
        'total_score': total_score,
        'max_score': max_score,
        'base_score': base_score,
        'match_type': match_type,
        'prediction': prediction,
        'confidence': confidence,
        'emoji': emoji,
        'action': action,
        'bg_color': bg_color,
        'border': border,
        'da_note': da_note,
        'btts_note': btts_note,
        'over_note': over_note,
        'boost_note': boost_note,
        'avg_btts': avg_btts,
        'avg_over': avg_over,
        'attacking_boost': attacking_boost,
        'context_score': context_score,
        'boosts_applied': boosts_applied,
        'elite_team': elite_team,
        'derby': derby,
        'relegation': relegation
    }

# Safe score parsing functions
def is_over_2_5(score_str):
    """Safely check if score is Over 2.5"""
    if pd.isna(score_str) or not isinstance(score_str, str) or '-' not in score_str:
        return False
    try:
        goals = [int(g.strip()) for g in score_str.split('-')]
        if len(goals) == 2:
            return sum(goals) >= 3
        return False
    except:
        return False

def is_btts(score_str):
    """Safely check if BTTS happened"""
    if pd.isna(score_str) or not isinstance(score_str, str) or '-' not in score_str:
        return False
    try:
        goals = [int(g.strip()) for g in score_str.split('-')]
        if len(goals) == 2:
            return goals[0] > 0 and goals[1] > 0
        return False
    except:
        return False

# Live Performance Tracker
with st.expander("📊 Live Performance Tracker", expanded=True):
    st.markdown("### 📈 Current Track Record")
    
    # Create DataFrame for display
    df = pd.DataFrame(st.session_state.tracked_matches)
    
    # Calculate stats
    total_matches = len(df)
    under_hits = df['under_hit'].sum()
    under_rate = (under_hits / total_matches) * 100
    btts_hits = df['btts_hit'].sum()
    btts_rate = (btts_hits / total_matches) * 100
    
    # Low score performance (original 9-point scale for historical)
    low_score_matches = df[df['score'] < 4]
    low_score_rate = (low_score_matches['under_hit'].sum() / len(low_score_matches) * 100) if len(low_score_matches) > 0 else 0
    
    # Medium score performance
    medium_score_matches = df[(df['score'] >= 4) & (df['score'] < 7)]
    medium_score_rate = (medium_score_matches['under_hit'].sum() / len(medium_score_matches) * 100) if len(medium_score_matches) > 0 else 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Matches", total_matches)
    with col2:
        st.metric("Under Hits", f"{under_hits}/{total_matches}")
    with col3:
        st.metric("Under Rate", f"{under_rate:.0f}%")
    with col4:
        st.metric("BTTS Rate", f"{btts_rate:.0f}%")
    
    # Display table with color-coded scores
    def color_score(val):
        if val < 4:
            return 'background-color: #E8F5E9'  # Light green
        elif val < 7:
            return 'background-color: #FFF3E0'  # Light orange
        else:
            return 'background-color: #FFE5E5'  # Light red
    
    display_df = df[['date', 'home', 'away', 'score', 'prediction', 'actual', 'under_hit', 'btts_hit']].copy()
    styled_df = display_df.style.applymap(color_score, subset=['score'])
    st.dataframe(styled_df, use_container_width=True, height=200)
    
    # Key insights
    st.markdown("**🔍 Key Insights:**")
    
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        st.markdown(f"""
        - ✅ **Low score (0-3): {low_score_matches['under_hit'].sum()}/{len(low_score_matches)} ({low_score_rate:.0f}%)**
        - ✅ **Medium score (4-6): {medium_score_matches['under_hit'].sum()}/{len(medium_score_matches)} ({medium_score_rate:.0f}%)**
        """)
    with col_i2:
        st.markdown(f"""
        - 🎯 **Overall direction: {under_hits}/{total_matches} ({under_rate:.0f}%)**
        - 🚫 **False Over triggers: {total_matches - under_hits}**
        """)
    
    # Recent validation highlight
    if len(df) > 0:
        last_match = df.iloc[-1]
        if last_match['under_hit']:
            st.success(f"✅ **Latest: {last_match['home']} vs {last_match['away']}** - Under hit ({last_match['actual']})")
        else:
            st.warning(f"⚠️ **Latest: {last_match['home']} vs {last_match['away']}** - Under miss ({last_match['actual']}) - learning opportunity")
    
    st.caption("⚠️ Small sample - track 10+ matches for meaningful stats. New elite team boost active for future predictions.")

# Main input form
with st.form("prediction_form"):
    st.subheader("📋 Enter Match Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        league = st.text_input("League", placeholder="e.g., Premier League", value="EPL")
        home_team = st.text_input("Home Team", placeholder="e.g., Liverpool")
        h_da = st.number_input("🏠 Home DA", min_value=0, max_value=100, value=45, step=1)
        h_btts = st.number_input("🏠 Home BTTS %", min_value=0, max_value=100, value=50, step=1)
        h_over = st.number_input("🏠 Home Over 2.5 %", min_value=0, max_value=100, value=50, step=1)
    
    with col2:
        date = st.date_input("Date", datetime.now())
        away_team = st.text_input("Away Team", placeholder="e.g., West Ham")
        a_da = st.number_input("✈️ Away DA", min_value=0, max_value=100, value=45, step=1)
        a_btts = st.number_input("✈️ Away BTTS %", min_value=0, max_value=100, value=50, step=1)
        a_over = st.number_input("✈️ Away Over 2.5 %", min_value=0, max_value=100, value=50, step=1)
    
    st.markdown("---")
    st.subheader("🎯 Context Factors")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        derby = st.checkbox("🏆 Derby Match (+2)", help="Local rivalry, high intensity")
    with col4:
        relegation = st.checkbox("⚠️ Relegation Dog Home (+1)", help="Home team fighting to stay up")
    with col5:
        elite_team = st.checkbox("⭐ Elite Team (+1)", 
                                help="Top-tier team: Liverpool, Man City, Arsenal, Chelsea, Man Utd, PSG, Bayern, Real Madrid, Barcelona, Inter, Milan, Juventus")
    
    # Submit button
    submitted = st.form_submit_button("🔮 Generate Prediction", use_container_width=True, type="primary")

# Show prediction when form is submitted
if submitted:
    if not home_team or not away_team:
        st.error("⚠️ Please enter both team names")
    else:
        # Calculate prediction
        result = calculate_prediction(
            h_da, a_da, h_btts, a_btts, h_over, a_over,
            derby, relegation, elite_team
        )
        
        # Display header
        st.markdown("---")
        st.markdown(f"## {result['emoji']} Prediction Result")
        
        # Main prediction card
        with st.container():
            st.markdown(f"""
            <div style="background-color: {result['bg_color']}; padding: 20px; border-radius: 10px; border: {result['border']};">
                <h2 style="text-align: center; margin: 0;">{result['match_type']}</h2>
                <h1 style="text-align: center; margin: 10px 0; font-size: 36px;">{result['prediction']}</h1>
                <p style="text-align: center; font-size: 20px;">Explosion Score: {result['total_score']}/{result['max_score']} | Confidence: {result['confidence']}</p>
                <p style="text-align: center; font-size: 18px; font-weight: bold;">{result['action']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Match details
        st.markdown("---")
        st.subheader("📊 Match Details")
        
        col5, col6, col7 = st.columns(3)
        with col5:
            st.markdown(f"**{home_team}** (Home)")
            st.markdown(f"DA: {h_da} | BTTS: {h_btts}% | Over: {h_over}%")
        with col6:
            st.markdown("**VS**")
        with col7:
            st.markdown(f"**{away_team}** (Away)")
            st.markdown(f"DA: {a_da} | BTTS: {a_btts}% | Over: {a_over}%")
        
        # Score breakdown
        st.markdown("---")
        st.subheader("🔢 Score Breakdown")
        
        col8, col9 = st.columns(2)
        
        with col8:
            st.markdown("**Base Score Components:**")
            st.markdown(f"- {result['da_note']} (+2)")
            st.markdown(f"- {result['btts_note']} (+2)")
            st.markdown(f"- {result['over_note']} (+1)")
            st.markdown(f"**Base Total: {result['base_score']}/5**")
        
        with col9:
            st.markdown("**Boosts:**")
            st.markdown(f"- {result['boost_note']}")
            if result['boosts_applied']:
                for boost in result['boosts_applied']:
                    st.markdown(f"- ✅ {boost}")
            else:
                st.markdown("- No context boosts applied")
            st.markdown(f"**Context Total: +{result['context_score']}**")
        
        # Summary
        st.markdown("---")
        st.markdown(f"### 🎯 Final Explosion Score: **{result['total_score']}/{result['max_score']}**")
        
        # Action recommendation
        if result['total_score'] >= 8:
            st.success(f"🚀 **ACTION: {result['action']}**")
        elif result['total_score'] >= 5:
            st.warning(f"⚖️ **ACTION: {result['action']}**")
        elif result['total_score'] >= 3:
            st.info(f"🐢 **ACTION: {result['action']}**")
        else:
            st.info(f"🐢 **ACTION: {result['action']}**")
        
        # Shareable result
        st.markdown("---")
        st.subheader("📱 Shareable Result")
        
        # Create context string for shareable result
        context_flags = []
        if derby:
            context_flags.append("Derby")
        if relegation:
            context_flags.append("Relegation Dog")
        if elite_team:
            context_flags.append("Elite Team")
        context_str = f" [{', '.join(context_flags)}]" if context_flags else ""
        
        share_text = f"""
        {result['emoji']} {home_team} vs {away_team}{context_str}
        Type: {result['match_type']}
        Prediction: {result['prediction']}
        Score: {result['total_score']}/{result['max_score']}
        Action: {result['action']}
        """
        st.code(share_text, language="text")
        
        # Option to log result
        with st.expander("📝 Log This Match Result"):
            st.markdown("**After the match, enter the actual score to update tracker:**")
            col_log1, col_log2 = st.columns(2)
            with col_log1:
                actual_score = st.text_input("Actual Score (e.g., 2-1)", key="actual_score_input")
            with col_log2:
                notes = st.text_input("Notes (optional)", placeholder="e.g., Late goals, red card, etc.")
            
            if st.button("✅ Log Result"):
                if actual_score and '-' in actual_score:
                    try:
                        # Parse score
                        goals = [int(g.strip()) for g in actual_score.split('-')]
                        under_hit = sum(goals) < 3
                        btts_hit = goals[0] > 0 and goals[1] > 0
                        
                        # Add to tracked matches
                        new_match = {
                            'date': date.strftime('%Y-%m-%d'),
                            'home': home_team,
                            'away': away_team,
                            'score': result['total_score'],
                            'score_max': result['max_score'],
                            'prediction': result['match_type'],
                            'call': result['prediction'],
                            'actual': actual_score,
                            'under_hit': under_hit,
                            'btts_hit': btts_hit,
                            'notes': notes if notes else "No notes"
                        }
                        st.session_state.tracked_matches.append(new_match)
                        st.success(f"✅ Logged! Under hit: {under_hit}, BTTS hit: {btts_hit}")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing score: {e}")
                else:
                    st.error("Please enter a valid score (e.g., 2-1)")

# How it works section
with st.expander("ℹ️ How The Scoring Works"):
    st.markdown("""
    ### Base Score (0-5 points)
    - **+2** if both teams have 45+ Dangerous Attacks
    - **+2** if average BTTS % is 55+
    - **+1** if average Over 2.5 % is 55+
    
    ### Boosts
    - **+1** if either team has 45+ DA (attacking identity)
    - **+2** for Derby matches
    - **+1** for Relegation dogs at home
    - **+1** for Elite Team involvement (NEW! 🆕)
    
    ### Match Types (10-point scale)
    | Score | Type | Call | Action |
    |-------|------|------|--------|
    | 8-10 | 💥 EXPLOSION | 🔥 OVER 2.5 PRIMARY | Strong Over lean |
    | 5-7 | 🔄 HYBRID | ⚠️ Watch BTTS & live | BTTS likely, consider Over |
    | 3-4 | 📊 MODEL SPECIAL | ✅ Lean Under | Slight Under, watch elite |
    | 0-2 | 📊 MODEL SPECIAL | ✅ Strong Under lean | Trust the model |
    
    ### Elite Team Examples
    - **Premier League:** Liverpool, Man City, Arsenal, Chelsea, Man Utd
    - **La Liga:** Real Madrid, Barcelona, Atletico Madrid
    - **Bundesliga:** Bayern Munich, Borussia Dortmund
    - **Serie A:** Inter, Milan, Juventus
    - **Ligue 1:** PSG
    - **Other:** Ajax, Porto, Benfica (in big European matches)
    
    ### Recent Validations
    - **Leeds 0-1 Sunderland** (Score 2/9): ✅ Under hit
    - **Bournemouth 0-0 Brentford** (Score 5/9): ✅ Under hit, ⚠️ BTTS miss
    - **Wolves 2-1 Liverpool** (Score 1/9): ❌ Under miss - Elite variance (now +1 elite boost would make 2/10)
    - **Liverpool 5-2 West Ham** (Score 4/9): ⚠️ BTTS hit, Under miss - Elite boost now active
    
    ### The Philosophy
    > "The lean version isn't a compromise. It's the MVP of a system that can make money."
    
    We're not waiting for perfect data. We're starting with what works and iterating fast.
    """)

# Footer
st.markdown("---")
st.markdown("⚽ **Mismatch Hunter v4.0** - Pure prediction engine | Elite Team boost active | Build: March 2026")
