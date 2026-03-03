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
            'prediction': '🔄 HYBRID',
            'call': 'Watch BTTS',
            'actual': '0-0',
            'under_hit': True,
            'btts_hit': False,
            'notes': 'Correct Under, BTTS miss but acceptable variance'
        }
    ]

# Title
st.title("⚽ Mismatch Hunter v4.0")
st.markdown("### Ultra-Lean Prediction Engine")
st.markdown("---")

# Helper function for calculations
def calculate_prediction(h_da, a_da, h_btts, a_btts, h_over, a_over, derby=False, relegation=False):
    """Calculate explosion score and prediction"""
    
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
    context_score = (2 if derby else 0) + (1 if relegation else 0)
    
    # Total score
    total_score = base_score + attacking_boost + context_score
    
    # Determine match type and prediction
    if total_score >= 7:
        match_type = "💥 EXPLOSION"
        prediction = "🔥 OVER 2.5 PRIMARY"
        confidence = "High"
        emoji = "🚀"
        action = "Strong Over lean - consider betting Over 2.5"
    elif total_score >= 4:
        match_type = "🔄 HYBRID"
        prediction = "⚠️ HYBRID — Watch BTTS"
        confidence = "Medium"
        emoji = "⚖️"
        action = "Watch live - consider BTTS, but don't force Over"
    else:
        match_type = "📊 MODEL SPECIAL"
        prediction = "✅ MODEL SPECIAL — Under lean"
        confidence = "Low"
        emoji = "🐢"
        action = "Trust the model - Under likely"
    
    return {
        'total_score': total_score,
        'base_score': base_score,
        'match_type': match_type,
        'prediction': prediction,
        'confidence': confidence,
        'emoji': emoji,
        'action': action,
        'da_note': da_note,
        'btts_note': btts_note,
        'over_note': over_note,
        'boost_note': boost_note,
        'avg_btts': avg_btts,
        'avg_over': avg_over,
        'attacking_boost': attacking_boost,
        'context_score': context_score
    }

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
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Matches", total_matches)
    with col2:
        st.metric("Under Hits", f"{under_hits}/{total_matches}")
    with col3:
        st.metric("Under Rate", f"{under_rate:.0f}%")
    with col4:
        st.metric("BTTS Hits", f"{btts_hits}/{total_matches}")
    
    # Display table
    st.dataframe(
        df[['date', 'home', 'away', 'score', 'prediction', 'actual', 'under_hit', 'btts_hit']],
        use_container_width=True,
        height=150
    )
    
    # Key insights
    st.markdown("**🔍 Key Insights:**")
    st.markdown("""
    - ✅ **100% Under accuracy** when score <4 (1/1)
    - ✅ **100% Under accuracy** when score 4-6 (1/1)
    - ⚠️ **BTTS accuracy**: 0% (0/2) - small sample, but caution is working
    - 🎯 **Overall direction accuracy**: 100% (2/2 on avoiding false Over triggers)
    """)
    
    # Add note about small sample
    st.caption("⚠️ Small sample size - track 10+ matches for meaningful stats")

# Main input form
with st.form("prediction_form"):
    st.subheader("📋 Enter Match Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        league = st.text_input("League", placeholder="e.g., Premier League", value="EPL")
        home_team = st.text_input("Home Team", placeholder="e.g., Leeds")
        h_da = st.number_input("🏠 Home DA", min_value=0, max_value=100, value=45, step=1)
        h_btts = st.number_input("🏠 Home BTTS %", min_value=0, max_value=100, value=50, step=1)
        h_over = st.number_input("🏠 Home Over 2.5 %", min_value=0, max_value=100, value=50, step=1)
    
    with col2:
        date = st.date_input("Date", datetime.now())
        away_team = st.text_input("Away Team", placeholder="e.g., Sunderland")
        a_da = st.number_input("✈️ Away DA", min_value=0, max_value=100, value=45, step=1)
        a_btts = st.number_input("✈️ Away BTTS %", min_value=0, max_value=100, value=50, step=1)
        a_over = st.number_input("✈️ Away Over 2.5 %", min_value=0, max_value=100, value=50, step=1)
    
    st.markdown("---")
    st.subheader("🎯 Context Factors")
    
    col3, col4 = st.columns(2)
    with col3:
        derby = st.checkbox("🏆 Derby Match (+2)", help="Local rivalry, high intensity")
    with col4:
        relegation = st.checkbox("⚠️ Relegation Dog Home (+1)", help="Home team fighting to stay up")
    
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
            derby, relegation
        )
        
        # Display header
        st.markdown("---")
        st.markdown(f"## {result['emoji']} Prediction Result")
        
        # Main prediction card
        with st.container():
            # Color based on confidence
            if result['confidence'] == "High":
                bg_color = "#FFE5E5"
                border = "3px solid #FF4B4B"
            elif result['confidence'] == "Medium":
                bg_color = "#FFF3E0"
                border = "3px solid #FFA500"
            else:
                bg_color = "#E8F5E9"
                border = "3px solid #4CAF50"
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border: {border};">
                <h2 style="text-align: center; margin: 0;">{result['match_type']}</h2>
                <h1 style="text-align: center; margin: 10px 0; font-size: 36px;">{result['prediction']}</h1>
                <p style="text-align: center; font-size: 20px;">Explosion Score: {result['total_score']}/9 | Confidence: {result['confidence']}</p>
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
            if derby or relegation:
                if derby:
                    st.markdown("- ✅ Derby match (+2)")
                if relegation:
                    st.markdown("- ✅ Relegation dog (+1)")
            else:
                st.markdown("- No context boosts applied")
            st.markdown(f"**Context Total: +{result['context_score']}**")
        
        # Summary
        st.markdown("---")
        st.markdown(f"### 🎯 Final Explosion Score: **{result['total_score']}/9**")
        
        # Action recommendation
        if result['total_score'] >= 7:
            st.success(f"🚀 **ACTION: {result['action']}**")
        elif result['total_score'] >= 4:
            st.warning(f"⚖️ **ACTION: {result['action']}**")
        else:
            st.info(f"🐢 **ACTION: {result['action']}**")
        
        # Shareable result
        st.markdown("---")
        st.subheader("📱 Shareable Result")
        share_text = f"""
        {result['emoji']} {home_team} vs {away_team}
        Type: {result['match_type']}
        Prediction: {result['prediction']}
        Score: {result['total_score']}/9
        Action: {result['action']}
        """
        st.code(share_text, language="text")
        
        # Option to log result
        with st.expander("📝 Log This Match Result"):
            st.markdown("**After the match, enter the actual score:**")
            col_log1, col_log2 = st.columns(2)
            with col_log1:
                actual_score = st.text_input("Actual Score (e.g., 2-1)", key="actual_score_input")
            with col_log2:
                if st.button("✅ Log Result"):
                    if actual_score and '-' in actual_score:
                        # Parse score
                        try:
                            goals = [int(g.strip()) for g in actual_score.split('-')]
                            under_hit = sum(goals) < 3
                            btts_hit = goals[0] > 0 and goals[1] > 0
                            
                            # Add to tracked matches
                            new_match = {
                                'date': date.strftime('%Y-%m-%d'),
                                'home': home_team,
                                'away': away_team,
                                'score': result['total_score'],
                                'prediction': result['match_type'],
                                'call': result['prediction'],
                                'actual': actual_score,
                                'under_hit': under_hit,
                                'btts_hit': btts_hit,
                                'notes': ''
                            }
                            st.session_state.tracked_matches.append(new_match)
                            st.success(f"✅ Logged! Under hit: {under_hit}, BTTS hit: {btts_hit}")
                            st.rerun()
                        except:
                            st.error("Invalid score format")
                    else:
                        st.error("Please enter a valid score")

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
    
    ### Match Types
    | Score | Type | Call | Action |
    |-------|------|------|--------|
    | 7-9 | 💥 EXPLOSION | 🔥 OVER 2.5 PRIMARY | Strong Over lean |
    | 4-6 | 🔄 HYBRID | ⚠️ Watch BTTS | Consider BTTS, don't force Over |
    | 0-3 | 📊 MODEL SPECIAL | ✅ Under lean | Trust the model |
    
    ### Recent Validations
    - **Leeds 0-1 Sunderland** (Score 2): ✅ Under hit
    - **Bournemouth 0-0 Brentford** (Score 5): ✅ Under hit, ⚠️ BTTS miss
    """)

# Footer
st.markdown("---")
st.markdown("⚽ **Mismatch Hunter v4.0** - Pure prediction engine | Track record: 2/2 on direction | Build: March 2026")
