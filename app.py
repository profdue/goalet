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
            'Relegation_dog', 'Actual_score', 'Prediction', 'BTTS_note',
            'Explosion_Score', 'Match_Type', 'Notes'
        ])

# Helper functions
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

def calculate_match_score(h_da, a_da, h_btts, a_btts, h_over, a_over, derby=False, relegation=False):
    """Calculate explosion score and match type"""
    # Base score
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
    
    # Match type
    if total_score >= 7:
        match_type = "💥 EXPLOSION"
        prediction = "🔥 OVER 2.5 PRIMARY"
    elif total_score >= 4:
        match_type = "🔄 HYBRID"
        prediction = "⚠️ HYBRID — Trust Forebet + BTTS watch"
    else:
        match_type = "📊 MODEL SPECIAL"
        prediction = "✅ MODEL SPECIAL — Under lean"
    
    # BTTS note
    btts_note = "BTTS possible" if (h_btts + a_btts) / 2 >= 55 else "BTTS unlikely"
    
    return {
        'total_score': total_score,
        'match_type': match_type,
        'prediction': prediction,
        'btts_note': btts_note,
        'base_score': base_score,
        'attacking_boost': attacking_boost
    }

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
        
        # Explosion count
        explosion_count = len(st.session_state.matches_df[
            st.session_state.matches_df['Match_Type'] == "💥 EXPLOSION"
        ])
        st.metric("Explosion Matches", explosion_count)
        
        if completed > 0:
            completed_matches = st.session_state.matches_df.dropna(subset=['Actual_score'])
            over_hits = completed_matches['Actual_score'].apply(is_over_2_5).sum()
            hit_rate = (over_hits / completed) * 100
            st.metric("Over 2.5 Hit Rate", f"{hit_rate:.1f}%")
    
    # Export button
    if len(st.session_state.matches_df) > 0:
        st.markdown("---")
        csv = st.session_state.matches_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"mismatch_hunter_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# Page 1: Add Matches
if page == "➕ Add Matches":
    st.header("Add New Match")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("match_entry"):
            st.subheader("Match Details")
            
            # League dropdown instead of free text
            league = st.selectbox(
                "League", 
                ["", "Premier League", "La Liga", "Bundesliga", "Serie A", 
                 "Ligue 1", "Eredivisie", "Primeira Liga", "Championship", 
                 "Other"]
            )
            if league == "Other":
                league = st.text_input("Specify League", placeholder="e.g., Belgian Pro League")
            elif league == "":
                league = None
            
            date = st.date_input("Date", datetime.now())
            home = st.text_input("Home Team", placeholder="e.g., Leeds")
            away = st.text_input("Away Team", placeholder="e.g., Sunderland")
            
            st.subheader("Forebet Data")
            col_da1, col_da2 = st.columns(2)
            with col_da1:
                h_da = st.number_input("🏠 Home DA", min_value=0, max_value=100, value=45, help="Home Dangerous Attacks")
            with col_da2:
                a_da = st.number_input("✈️ Away DA", min_value=0, max_value=100, value=45, help="Away Dangerous Attacks")
            
            col_btts1, col_btts2 = st.columns(2)
            with col_btts1:
                h_btts = st.number_input("🏠 Home BTTS %", min_value=0, max_value=100, value=50)
            with col_btts2:
                a_btts = st.number_input("✈️ Away BTTS %", min_value=0, max_value=100, value=50)
            
            col_over1, col_over2 = st.columns(2)
            with col_over1:
                h_over = st.number_input("🏠 Home Over 2.5 %", min_value=0, max_value=100, value=50)
            with col_over2:
                a_over = st.number_input("✈️ Away Over 2.5 %", min_value=0, max_value=100, value=50)
    
    with col2:
        st.subheader("Context Factors")
        derby = st.checkbox("🏆 Derby Match? (+2 boost)", help="Local rivalry, high intensity")
        relegation = st.checkbox("⚠️ Relegation Dog Home? (+1 boost)", help="Home team fighting to stay up")
        
        st.subheader("Additional Info")
        notes = st.text_area("📝 Notes", placeholder="e.g., Red card at 60', Key player injured, etc.")
        
        st.subheader("Result (After Match)")
        actual_score = st.text_input("Actual Score (e.g., 2-1)", placeholder="Enter after match")
        
        submitted = st.form_submit_button("💾 Save Match")
        
        if submitted and league and home and away:
            # Calculate scores
            score_data = calculate_match_score(
                h_da, a_da, h_btts, a_btts, h_over, a_over, 
                derby, relegation
            )
            
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
                'Prediction': score_data['prediction'],
                'BTTS_note': score_data['btts_note'],
                'Explosion_Score': score_data['total_score'],
                'Match_Type': score_data['match_type'],
                'Notes': notes
            }])
            
            # Append to dataframe
            st.session_state.matches_df = pd.concat([st.session_state.matches_df, new_match], ignore_index=True)
            
            # Save to CSV
            os.makedirs('data', exist_ok=True)
            st.session_state.matches_df.to_csv('data/matches.csv', index=False)
            
            st.success(f"✅ Match saved! {score_data['prediction']}")
            
            # Show calculation breakdown in an expander
            with st.expander("🔢 View Score Calculation"):
                st.markdown(f"""
                **Score Breakdown:**
                - Base Score: {score_data['base_score']}/5
                - Attacking Boost: +{score_data['attacking_boost']}
                - Derby: +{2 if derby else 0}
                - Relegation Dog: +{1 if relegation else 0}
                - **Total Explosion Score: {score_data['total_score']}/9**
                - **Match Type: {score_data['match_type']}**
                """)
        elif submitted:
            st.warning("Please fill in League, Home Team, and Away Team")

# Page 2: Dashboard
elif page == "📊 Dashboard":
    st.header("📊 Matches Dashboard")
    
    if len(st.session_state.matches_df) > 0:
        # Date filter
        st.subheader("Filter Matches")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", 
                min_value=pd.to_datetime(st.session_state.matches_df['Date']).min().date() if len(st.session_state.matches_df) > 0 else datetime.now().date(),
                value=pd.to_datetime(st.session_state.matches_df['Date']).min().date() if len(st.session_state.matches_df) > 0 else datetime.now().date()
            )
        with col2:
            end_date = st.date_input("To Date", datetime.now().date())
        
        # Filter dataframe
        mask = (pd.to_datetime(st.session_state.matches_df['Date']).dt.date >= start_date) & \
               (pd.to_datetime(st.session_state.matches_df['Date']).dt.date <= end_date)
        filtered_df = st.session_state.matches_df[mask]
        
        # Display matches table
        st.subheader("Recent Matches")
        display_df = filtered_df.copy()
        
        # Format for display
        display_cols = ['Date', 'League', 'Home', 'Away', 'Match_Type', 'Prediction', 
                       'BTTS_note', 'Explosion_Score', 'Actual_score', 'Notes']
        available_cols = [col for col in display_cols if col in display_df.columns]
        
        st.dataframe(
            display_df[available_cols].sort_values('Date', ascending=False),
            use_container_width=True,
            height=400
        )
        
        # Summary stats
        st.subheader("Prediction Distribution")
        col1, col2, col3, col4 = st.columns(4)
        
        pred_counts = filtered_df['Match_Type'].value_counts()
        
        with col1:
            st.metric("💥 EXPLOSION", pred_counts.get("💥 EXPLOSION", 0))
        with col2:
            st.metric("🔄 HYBRID", pred_counts.get("🔄 HYBRID", 0))
        with col3:
            st.metric("📊 MODEL SPECIAL", pred_counts.get("📊 MODEL SPECIAL", 0))
        
        # Average explosion score
        with col4:
            st.metric("Avg Explosion Score", f"{filtered_df['Explosion_Score'].mean():.1f}")
        
        # Completed matches analysis
        completed = filtered_df.dropna(subset=['Actual_score'])
        if len(completed) > 0:
            st.subheader("Completed Matches Analysis")
            
            # Calculate hits
            completed = completed.copy()
            completed['Over_Hit'] = completed['Actual_score'].apply(is_over_2_5)
            completed['BTTS_Hit'] = completed['Actual_score'].apply(is_btts)
            
            # Performance by match type
            for match_type in completed['Match_Type'].unique():
                subset = completed[completed['Match_Type'] == match_type]
                if len(subset) > 0:
                    with st.expander(f"{match_type} Analysis ({len(subset)} matches)"):
                        over_rate = subset['Over_Hit'].mean() * 100
                        btts_rate = subset['BTTS_Hit'].mean() * 100
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Over 2.5 Hit Rate", f"{over_rate:.1f}%")
                        with col2:
                            st.metric("BTTS Hit Rate", f"{btts_rate:.1f}%")
                        
                        # Show when BTTS was flagged
                        btts_flagged = subset[subset['BTTS_note'] == 'BTTS possible']
                        if len(btts_flagged) > 0:
                            btts_accuracy = btts_flagged['BTTS_Hit'].mean() * 100
                            st.info(f"When BTTS was flagged: {btts_accuracy:.1f}% hit rate")
    else:
        st.info("No matches yet. Add some matches to see the dashboard!")

# Page 3: Results & ROI
elif page == "📈 Results & ROI":
    st.header("📈 Performance & ROI Simulation")
    st.caption("Assumes flat £100 stake at +120 odds (2.2 decimal) on all OVER 2.5 PRIMARY calls")
    
    if len(st.session_state.matches_df) > 0:
        # Only use completed matches
        completed = st.session_state.matches_df.dropna(subset=['Actual_score']).copy()
        
        if len(completed) > 0:
            # Calculate results
            completed['Over_Hit'] = completed['Actual_score'].apply(is_over_2_5)
            completed['BTTS_Hit'] = completed['Actual_score'].apply(is_btts)
            
            # Only track OVER 2.5 PRIMARY bets
            over_bets = completed[completed['Match_Type'] == "💥 EXPLOSION"].copy()
            
            if len(over_bets) > 0:
                # ROI Simulation (assume +120 odds = 2.2 decimal odds)
                stake = 100  # $100 per bet
                odds = 2.2   # +120 American odds
                
                over_bets['Profit'] = over_bets['Over_Hit'].apply(
                    lambda x: (stake * odds - stake) if x else -stake
                )
                
                # Metrics
                total_bets = len(over_bets)
                winning_bets = over_bets['Over_Hit'].sum()
                win_rate = (winning_bets / total_bets) * 100
                total_profit = over_bets['Profit'].sum()
                roi = (total_profit / (total_bets * stake)) * 100
                
                # Display metrics
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Explosion Bets", total_bets)
                with col2:
                    st.metric("Winning Bets", winning_bets)
                with col3:
                    st.metric("Win Rate", f"{win_rate:.1f}%")
                with col4:
                    st.metric("Total P&L", f"£{total_profit:.0f}")
                with col5:
                    st.metric("ROI", f"{roi:.1f}%", delta=f"£{total_profit:.0f}")
                
                # Performance chart
                fig = px.bar(
                    over_bets.sort_values('Date'), 
                    x=over_bets.index, 
                    y='Profit',
                    title="Profit/Loss by Explosion Match",
                    labels={'x': 'Match #', 'Profit': 'Profit/Loss (£)'},
                    color='Profit',
                    color_continuous_scale=['red', 'green']
                )
                fig.add_hline(y=0, line_dash="dash", line_color="blue")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed results table
                st.subheader("Explosion Match Details")
                results_df = over_bets[['Date', 'League', 'Home', 'Away', 'Actual_score', 
                                        'Over_Hit', 'Profit', 'Notes']]
                st.dataframe(results_df, use_container_width=True)
            else:
                st.info("No EXPLOSION matches with results yet. Keep tracking!")
            
            # Show all matches performance summary
            with st.expander("📊 All Matches Performance"):
                all_completed = completed.copy()
                all_completed['Profit'] = all_completed['Over_Hit'].apply(
                    lambda x: (stake * odds - stake) if x else -stake
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Matches", len(all_completed))
                    st.metric("Overall Win Rate", f"{all_completed['Over_Hit'].mean()*100:.1f}%")
                with col2:
                    st.metric("Overall P&L", f"£{all_completed['Profit'].sum():.0f}")
                    st.metric("Overall ROI", f"{(all_completed['Profit'].sum()/(len(all_completed)*stake))*100:.1f}%")
        else:
            st.info("No completed matches yet. Add actual scores to see results!")
    else:
        st.info("No matches yet. Add some matches to see results!")

# Page 4: How It Works
else:
    st.header("ℹ️ How The Mismatch Hunter Works")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
        """)
        
        st.markdown("""
        ### Match Types
        
        | Score | Type | Call |
        |-------|------|------|
        | 7-9 | 💥 EXPLOSION | 🔥 OVER 2.5 PRIMARY |
        | 4-6 | 🔄 HYBRID | ⚠️ Trust Forebet + BTTS watch |
        | 0-3 | 📊 MODEL SPECIAL | ✅ Under lean |
        """)
    
    with col2:
        st.markdown("""
        ### How to Use
        
        1. Go to **Forebet** match page
        2. Find in Match Preview:
           - Dangerous Attacks (both teams)
           - BTTS % (both teams)
           - Over 2.5% (both teams)
        3. Enter the 7 numbers in the app
        4. Add context (Derby/Relegation)
        5. Save and track results
        
        ### Data Sources
        
        All data from Forebet's match preview pages. 
        The system is designed to be:
        - **Lean**: Only 7 inputs needed
        - **Fast**: 20 seconds per match
        - **Actionable**: Clear calls based on scoring
        """)
    
    st.markdown("---")
    st.markdown("""
    ### The Philosophy
    
    > "The lean version isn't a compromise. It's the MVP of a system that can make money."
    
    We're not waiting for perfect data. We're starting with what works and iterating fast.
    """)

# Footer
st.markdown("---")
st.markdown("⚽ **Mismatch Hunter v4.0** - Built for speed, designed for profit | Data persists in CSV | [Report Issue](https://github.com/profdue/goalet/issues)")
