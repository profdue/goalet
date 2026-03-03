import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v4.0",
    page_icon="⚽",
    layout="wide"
)

# Initialize session state
if 'matches_df' not in st.session_state:
    # Try to load existing data
    if os.path.exists('data/matches.csv'):
        st.session_state.matches_df = pd.read_csv('data/matches.csv')
    else:
        st.session_state.matches_df = pd.DataFrame(columns=[
            'League', 'Date', 'Home', 'Away', 'H_DA', 'A_DA', 
            'H_BTTS', 'A_BTTS', 'H_Over', 'A_Over', 'Derby', 
            'Relegation_dog', 'Actual_score', 'Prediction', 'BTTS_note'
        ])

# Title
st.title("⚽ Mismatch Hunter v4.0 - The Ultra-Lean Version")
st.markdown("---")

# Sidebar for navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Go to:",
        ["➕ Add Matches", "📊 Dashboard", "📈 Results & ROI", "ℹ️ How It Works"]
    )
    
    st.markdown("---")
    st.markdown("**Current Stats**")
    if len(st.session_state.matches_df) > 0:
        total_matches = len(st.session_state.matches_df)
        completed = st.session_state.matches_df['Actual_score'].notna().sum()
        st.metric("Total Matches", total_matches)
        st.metric("Completed", completed)
        if completed > 0:
            hit_rate = (st.session_state.matches_df['Actual_score'].notna() & 
                       st.session_state.matches_df['Actual_score'].apply(
                           lambda x: int(str(x).split('-')[0]) + int(str(x).split('-')[1]) >= 3 if pd.notna(x) and '-' in str(x) else False
                       )).sum() / completed * 100
            st.metric("Over 2.5 Hit Rate", f"{hit_rate:.1f}%")

# Page 1: Add Matches
if page == "➕ Add Matches":
    st.header("Add New Match")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("match_entry"):
            st.subheader("Match Details")
            league = st.text_input("League", placeholder="e.g., Premier League")
            date = st.date_input("Date", datetime.now())
            home = st.text_input("Home Team", placeholder="e.g., Leeds")
            away = st.text_input("Away Team", placeholder="e.g., Sunderland")
            
            st.subheader("Forebet Data")
            h_da = st.number_input("Home Dangerous Attacks", min_value=0, max_value=100, value=45)
            a_da = st.number_input("Away Dangerous Attacks", min_value=0, max_value=100, value=45)
            h_btts = st.number_input("Home BTTS %", min_value=0, max_value=100, value=50)
            a_btts = st.number_input("Away BTTS %", min_value=0, max_value=100, value=50)
            h_over = st.number_input("Home Over 2.5 %", min_value=0, max_value=100, value=50)
            a_over = st.number_input("Away Over 2.5 %", min_value=0, max_value=100, value=50)
    
    with col2:
        st.subheader("Context Factors")
        derby = st.checkbox("🏆 Derby Match? (+2 boost)")
        relegation = st.checkbox("⚠️ Relegation Dog Home? (+1 boost)")
        
        st.subheader("Result (After Match)")
        actual_score = st.text_input("Actual Score (e.g., 2-1)", placeholder="Enter when available")
        
        submitted = st.form_submit_button("Save Match")
        
        if submitted:
            # Calculate scores
            base_score = 0
            # DA condition
            if h_da >= 45 and a_da >= 45:
                base_score += 2
            # BTTS condition
            if (h_btts + a_btts) / 2 >= 55:
                base_score += 2
            # Over condition
            if (h_over + a_over) / 2 >= 55:
                base_score += 1
            
            # Attacking boost
            attacking_boost = 1 if (h_da >= 45 or a_da >= 45) else 0
            
            # Context boosts
            total_score = base_score + attacking_boost + (2 if derby else 0) + (1 if relegation else 0)
            
            # Prediction call
            if total_score >= 7:
                prediction = "🔥 OVER 2.5 PRIMARY"
            elif total_score >= 4:
                prediction = "⚠️ HYBRID — Trust Forebet + BTTS watch"
            else:
                prediction = "✅ MODEL SPECIAL — Under lean"
            
            # BTTS note
            btts_note = "BTTS possible" if (h_btts + a_btts) / 2 >= 55 else "BTTS unlikely"
            
            # Create new row
            new_match = pd.DataFrame([{
                'League': league,
                'Date': date,
                'Home': home,
                'Away': away,
                'H_DA': h_da,
                'A_DA': a_da,
                'H_BTTS': h_btts,
                'A_BTTS': a_btts,
                'H_Over': h_over,
                'A_Over': a_over,
                'Derby': derby,
                'Relegation_dog': relegation,
                'Actual_score': actual_score if actual_score else None,
                'Prediction': prediction,
                'BTTS_note': btts_note
            }])
            
            # Append to dataframe
            st.session_state.matches_df = pd.concat([st.session_state.matches_df, new_match], ignore_index=True)
            
            # Save to CSV
            os.makedirs('data', exist_ok=True)
            st.session_state.matches_df.to_csv('data/matches.csv', index=False)
            
            st.success(f"✅ Match saved! {prediction}")
            
            # Show calculation breakdown
            st.info(f"""
            **Score Calculation:**
            - Base Score: {base_score}/5
            - Attacking Boost: +{attacking_boost}
            - Derby: +{2 if derby else 0}
            - Relegation Dog: +{1 if relegation else 0}
            - **Total: {total_score}/9**
            """)

# Page 2: Dashboard
elif page == "📊 Dashboard":
    st.header("📊 Matches Dashboard")
    
    if len(st.session_state.matches_df) > 0:
        # Display matches table
        st.subheader("Recent Matches")
        display_df = st.session_state.matches_df.copy()
        
        # Format for display
        display_cols = ['Date', 'League', 'Home', 'Away', 'Prediction', 'BTTS_note', 'Actual_score']
        available_cols = [col for col in display_cols if col in display_df.columns]
        
        st.dataframe(
            display_df[available_cols].sort_values('Date', ascending=False),
            use_container_width=True
        )
        
        # Summary stats
        st.subheader("Prediction Distribution")
        col1, col2, col3 = st.columns(3)
        
        pred_counts = display_df['Prediction'].value_counts()
        
        with col1:
            st.metric("🔥 OVER 2.5", pred_counts.get("🔥 OVER 2.5 PRIMARY", 0))
        with col2:
            st.metric("⚠️ HYBRID", pred_counts.get("⚠️ HYBRID — Trust Forebet + BTTS watch", 0))
        with col3:
            st.metric("✅ UNDER", pred_counts.get("✅ MODEL SPECIAL — Under lean", 0))
        
        # Completed matches analysis
        completed = display_df[display_df['Actual_score'].notna()]
        if len(completed) > 0:
            st.subheader("Completed Matches Analysis")
            
            # Calculate over hits
            completed['Over_Hit'] = completed['Actual_score'].apply(
                lambda x: int(str(x).split('-')[0]) + int(str(x).split('-')[1]) >= 3 
                if pd.notna(x) and '-' in str(x) else False
            )
            
            # Calculate BTTS hits
            completed['BTTS_Hit'] = completed['Actual_score'].apply(
                lambda x: int(str(x).split('-')[0]) > 0 and int(str(x).split('-')[1]) > 0
                if pd.notna(x) and '-' in str(x) else False
            )
            
            # Performance by prediction type
            for pred_type in completed['Prediction'].unique():
                subset = completed[completed['Prediction'] == pred_type]
                if len(subset) > 0:
                    hit_rate = subset['Over_Hit'].mean() * 100
                    st.write(f"**{pred_type}**")
                    st.write(f"- Matches: {len(subset)}")
                    st.write(f"- Over 2.5 Hit Rate: {hit_rate:.1f}%")
                    
                    # BTTS accuracy when flagged
                    if "BTTS possible" in subset['BTTS_note'].values:
                        btts_accuracy = subset[subset['BTTS_note'] == 'BTTS possible']['BTTS_Hit'].mean() * 100
                        st.write(f"- BTTS Accuracy (when flagged): {btts_accuracy:.1f}%")
    else:
        st.info("No matches yet. Add some matches to see the dashboard!")

# Page 3: Results & ROI
elif page == "📈 Results & ROI":
    st.header("📈 Performance & ROI Simulation")
    
    if len(st.session_state.matches_df) > 0:
        completed = st.session_state.matches_df[st.session_state.matches_df['Actual_score'].notna()]
        
        if len(completed) > 0:
            # Calculate results
            completed['Over_Hit'] = completed['Actual_score'].apply(
                lambda x: int(str(x).split('-')[0]) + int(str(x).split('-')[1]) >= 3 
                if pd.notna(x) and '-' in str(x) else False
            )
            
            # ROI Simulation (assume +120 odds = 2.2 decimal odds)
            stake = 100  # $100 per bet
            odds = 2.2   # +120 American odds
            
            completed['Profit'] = completed['Over_Hit'].apply(
                lambda x: (stake * odds - stake) if x else -stake
            )
            
            # Metrics
            total_bets = len(completed)
            winning_bets = completed['Over_Hit'].sum()
            win_rate = (winning_bets / total_bets) * 100
            total_profit = completed['Profit'].sum()
            roi = (total_profit / (total_bets * stake)) * 100
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Bets", total_bets)
            with col2:
                st.metric("Winning Bets", winning_bets)
            with col3:
                st.metric("Win Rate", f"{win_rate:.1f}%")
            with col4:
                st.metric("Total Profit", f"${total_profit:.0f}")
            
            st.metric("ROI", f"{roi:.1f}%", delta=f"${total_profit:.0f}")
            
            # Performance chart
            fig = px.bar(
                completed, 
                x=completed.index, 
                y='Profit',
                title="Profit/Loss by Match",
                labels={'x': 'Match #', 'Profit': 'Profit/Loss ($)'}
            )
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed results table
            st.subheader("Detailed Results")
            results_df = completed[['Date', 'League', 'Home', 'Away', 'Actual_score', 'Prediction', 'Over_Hit', 'Profit']]
            st.dataframe(results_df, use_container_width=True)
            
        else:
            st.info("No completed matches yet. Add actual scores to see ROI!")
    else:
        st.info("No matches yet. Add some matches to see results!")

# Page 4: How It Works
else:
    st.header("ℹ️ How The Mismatch Hunter Works")
    
    st.markdown("""
    ### The Scoring System
    
    **Base Score (0-5 points):**
    - **+2 points** if both teams have 45+ Dangerous Attacks
    - **+2 points** if average BTTS % is 55+
    - **+1 point** if average Over 2.5 % is 55+
    
    **Boosts:**
    - **+1 point** if either team has 45+ DA (attacking identity)
    - **+2 points** for Derby matches
    - **+1 point** for Relegation dogs at home
    
    **Maximum possible: 9 points**
    
    ### Predictions
    
    | Score | Call | Action |
    |-------|------|--------|
    | 7-9 | 🔥 OVER 2.5 PRIMARY | Strong over lean |
    | 4-6 | ⚠️ HYBRID | Trust Forebet + watch BTTS |
    | 0-3 | ✅ MODEL SPECIAL | Under lean |
    
    ### How to Use
    
    1. Go to Forebet match page
    2. Find Dangerous Attacks, BTTS %, Over 2.5% in Match Preview
    3. Enter the numbers in the app
    4. Add context factors (Derby/Relegation)
    5. Save match and track results
    
    ### Data Sources
    
    All data from Forebet's match preview pages. The system is designed to be:
    - **Lean**: Only 7 inputs needed
    - **Fast**: 20 seconds per match
    - **Actionable**: Clear calls based on scoring
    """)

# Footer
st.markdown("---")
st.markdown("⚽ **Mismatch Hunter v4.0** - Built for speed, designed for profit")
