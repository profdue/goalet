import streamlit as st
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v4.0 - Predictor",
    page_icon="⚽",
    layout="centered"
)

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
    elif total_score >= 4:
        match_type = "🔄 HYBRID"
        prediction = "⚠️ HYBRID — Watch BTTS"
        confidence = "Medium"
        emoji = "⚖️"
    else:
        match_type = "📊 MODEL SPECIAL"
        prediction = "✅ MODEL SPECIAL — Under lean"
        confidence = "Low"
        emoji = "🐢"
    
    return {
        'total_score': total_score,
        'base_score': base_score,
        'match_type': match_type,
        'prediction': prediction,
        'confidence': confidence,
        'emoji': emoji,
        'da_note': da_note,
        'btts_note': btts_note,
        'over_note': over_note,
        'boost_note': boost_note,
        'avg_btts': avg_btts,
        'avg_over': avg_over,
        'attacking_boost': attacking_boost,
        'context_score': context_score
    }

# Main input form
with st.form("prediction_form"):
    st.subheader("📋 Enter Match Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        league = st.text_input("League", placeholder="e.g., Premier League")
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
                <h1 style="text-align: center; margin: 10px 0; font-size: 48px;">{result['prediction']}</h1>
                <p style="text-align: center; font-size: 20px;">Explosion Score: {result['total_score']}/9 | Confidence: {result['confidence']}</p>
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
            st.success("🚀 **ACTION: Strong Over 2.5 lean - Consider betting Over 2.5**")
        elif result['total_score'] >= 4:
            st.warning("⚖️ **ACTION: Hybrid match - Watch live, consider BTTS**")
        else:
            st.info("🐢 **ACTION: Model special - Under lean likely**")
        
        # Shareable result
        st.markdown("---")
        st.subheader("📱 Shareable Result")
        share_text = f"""
        {result['emoji']} {home_team} vs {away_team}
        Type: {result['match_type']}
        Prediction: {result['prediction']}
        Score: {result['total_score']}/9
        """
        st.code(share_text, language="text")

# How it works section (always visible)
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
    | Score | Type | Call |
    |-------|------|------|
    | 7-9 | 💥 EXPLOSION | 🔥 OVER 2.5 PRIMARY |
    | 4-6 | 🔄 HYBRID | ⚠️ Watch BTTS |
    | 0-3 | 📊 MODEL SPECIAL | ✅ Under lean |
    """)

# Footer
st.markdown("---")
st.markdown("⚽ **Mismatch Hunter v4.0** - Pure prediction engine, no data storage")
