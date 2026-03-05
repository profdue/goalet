import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="Mismatch Hunter v11.0",
    page_icon="🎯",
    layout="wide"
)

# ============================================================================
# HISTORY-BASED PATTERN LEARNING ENGINE
# ============================================================================

class PatternLearningHunter:
    """
    v11.0 - Learns from historical patterns and overrides tier logic when history contradicts
    """
    
    def __init__(self):
        self.knowledge_base = self._initialize_knowledge()
        self.pattern_clusters = defaultdict(list)
        self.pattern_history = {}  # Stores historical outcomes for each pattern
        self.counter_threats = {}
        self._build_initial_clusters()
        self._analyze_pattern_history()
    
    def _da_tier(self, da):
        """Convert DA to tier (1-5)"""
        if da >= 80: return 1
        if da >= 65: return 2
        if da >= 50: return 3
        if da >= 35: return 4
        return 5
    
    def _btts_tier(self, btts):
        """Convert BTTS% to tier (1-5)"""
        if btts >= 65: return 1
        if btts >= 55: return 2
        if btts >= 45: return 3
        if btts >= 35: return 4
        return 5
    
    def _over_tier(self, over):
        """Convert Over% to tier (1-5)"""
        if over >= 65: return 1
        if over >= 55: return 2
        if over >= 45: return 3
        if over >= 35: return 4
        return 5
    
    def _get_tier_signature(self, match):
        """Get 6-number tier signature for a match"""
        return [
            self._da_tier(match['home_da']),
            self._da_tier(match['away_da']),
            self._btts_tier(match['home_btts']),
            self._btts_tier(match['away_btts']),
            self._over_tier(match['home_over']),
            self._over_tier(match['away_over'])
        ]
    
    def _initialize_knowledge(self):
        """Initialize with tier-based knowledge including Sunderland examples"""
        return [
            # PATTERN 1: [1,2,2,2,1,1] - ELITE ATTACK
            {'home_da': 82, 'away_da': 78, 'home_btts': 62, 'away_btts': 62,
             'home_over': 65, 'away_over': 65, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.2, 'btts': 1, 'league': 'Bundesliga', 
             'home_team': 'Bayern', 'away_team': 'Dortmund'},
            
            # PATTERN 2: [2,2,2,2,2,3] - STRONG BOTH
            {'home_da': 76, 'away_da': 72, 'home_btts': 58, 'away_btts': 56,
             'home_over': 56, 'away_over': 54, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 2.9, 'btts': 1, 'league': 'EPL',
             'home_team': 'Liverpool', 'away_team': 'Arsenal'},
            
            # PATTERN 3: [3,3,3,3,3,3] - MIDTABLE
            {'home_da': 55, 'away_da': 52, 'home_btts': 52, 'away_btts': 50,
             'home_over': 52, 'away_over': 50, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.6, 'btts': 0, 'league': 'La Liga',
             'home_team': 'Valencia', 'away_team': 'Real Sociedad'},
            
            # PATTERN 4: [4,4,4,4,4,4] - WEAK BOTH
            {'home_da': 42, 'away_da': 40, 'home_btts': 42, 'away_btts': 40,
             'home_over': 40, 'away_over': 38, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 2.2, 'btts': 0, 'league': 'Serie A',
             'home_team': 'Lecce', 'away_team': 'Salernitana'},
            
            # PATTERN 5: [5,5,5,5,5,5] - DEFENSIVE
            {'home_da': 32, 'away_da': 30, 'home_btts': 32, 'away_btts': 30,
             'home_over': 30, 'away_over': 28, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 1.8, 'btts': 0, 'league': 'Serie A',
             'home_team': 'Cagliari', 'away_team': 'Empoli'},
            
            # PATTERN 6: [1,4,1,4,1,4] - ELITE HOME vs WEAK AWAY
            {'home_da': 85, 'away_da': 40, 'home_btts': 70, 'away_btts': 38,
             'home_over': 72, 'away_over': 36, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.5, 'btts': 0, 'league': 'Bundesliga',
             'home_team': 'Bayern', 'away_team': 'Paderborn'},
            
            # PATTERN 7: [4,1,4,1,4,1] - WEAK HOME vs ELITE AWAY
            {'home_da': 38, 'away_da': 82, 'home_btts': 35, 'away_btts': 68,
             'home_over': 36, 'away_over': 70, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.1, 'btts': 1, 'league': 'Bundesliga',
             'home_team': 'Paderborn', 'away_team': 'Bayern'},
            
            # PATTERN 8: [4,4,5,1,4,3] - AUSTRIAN SPECIAL
            {'home_da': 38, 'away_da': 37, 'home_btts': 35, 'away_btts': 65,
             'home_over': 40, 'away_over': 45, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 3.8, 'btts': 1, 'league': 'Austria',
             'home_team': 'Blau Weiss', 'away_team': 'WSG Tirol'},
            
            # PATTERN 9: [2,2,1,3,2,3] - MIXED ATTACK
            {'home_da': 68, 'away_da': 65, 'home_btts': 68, 'away_btts': 48,
             'home_over': 62, 'away_over': 48, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.8, 'btts': 1, 'league': 'EPL',
             'home_team': 'Aston Villa', 'away_team': 'Brighton'},
            
            # PATTERN 10: [3,3,2,4,3,4] - LEANING DEFENSIVE
            {'home_da': 54, 'away_da': 52, 'home_btts': 58, 'away_btts': 42,
             'home_over': 52, 'away_over': 40, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.4, 'btts': 0, 'league': 'La Liga',
             'home_team': 'Getafe', 'away_team': 'Cadiz'},
            
            # CRITICAL PATTERN: [4,4,2,4,2,4] - Leeds vs Sunderland pattern
            {'home_da': 42, 'away_da': 41, 'home_btts': 64, 'away_btts': 36,
             'home_over': 64, 'away_over': 36, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 1.0, 'btts': 0, 'league': 'EPL',
             'home_team': 'Leeds', 'away_team': 'Sunderland'},
            
            # Another example of same pattern
            {'home_da': 44, 'away_da': 43, 'home_btts': 62, 'away_btts': 38,
             'home_over': 60, 'away_over': 40, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 0.0, 'btts': 0, 'league': 'Championship',
             'home_team': 'Middlesbrough', 'away_team': 'Stoke'},
        ]
    
    def _build_initial_clusters(self):
        """Group matches by tier signature"""
        for match in self.knowledge_base:
            signature = str(self._get_tier_signature(match))
            self.pattern_clusters[signature].append(match)
    
    def _analyze_pattern_history(self):
        """Analyze historical outcomes for each pattern"""
        for signature, matches in self.pattern_clusters.items():
            if len(matches) >= 2:  # Only analyze patterns with enough data
                home_scored = 0
                away_scored = 0
                over_hit = 0
                btts_hit = 0
                total_goals = 0
                
                for match in matches:
                    # Parse score to determine if home/away scored
                    # For now using btts and goals as proxy
                    if match['btts'] == 1:
                        btts_hit += 1
                        home_scored += 1
                        away_scored += 1
                    if match['goals'] >= 3:
                        over_hit += 1
                    total_goals += match['goals']
                
                self.pattern_history[signature] = {
                    'count': len(matches),
                    'home_scored_pct': (home_scored / len(matches)) * 100,
                    'away_scored_pct': (away_scored / len(matches)) * 100,
                    'btts_pct': (btts_hit / len(matches)) * 100,
                    'over_pct': (over_hit / len(matches)) * 100,
                    'avg_goals': total_goals / len(matches)
                }
    
    def find_similar_matches(self, match_input, k=5):
        """Find matches with EXACT same tier signature first, then similar"""
        input_tiers = match_input['tiers']
        input_sig = str(input_tiers)
        
        # FIRST PRIORITY: Exact signature matches
        if input_sig in self.pattern_clusters:
            matches = [(1.0, i, m) for i, m in enumerate(self.pattern_clusters[input_sig])]
            matches.sort(reverse=True)
            return [(sim, match) for sim, _, match in matches[:k]]
        
        # SECOND PRIORITY: Similar but not exact (with penalty)
        similarities = []
        for sig, matches in self.pattern_clusters.items():
            try:
                sig_tiers = [int(x.strip()) for x in sig.strip('[]').split(',')]
            except:
                continue
            
            if len(sig_tiers) != 6:
                continue
            
            # Calculate tier difference with penalty for different signatures
            diff = 0
            tier_matches = 0
            for a, b in zip(input_tiers, sig_tiers):
                diff += abs(a - b)
                if a == b:
                    tier_matches += 1
            
            # Similarity based on diff, but with penalty for not being exact
            similarity = max(0, 1 - (diff / 24))
            
            # Only include if at least 4 tiers match
            if tier_matches >= 4:
                for match in matches:
                    similarities.append((similarity, len(similarities), match))
        
        similarities.sort(reverse=True)
        return [(sim, match) for sim, _, match in similarities[:k]]
    
    def get_pattern_insights(self, tiers):
        """Get historical insights for this pattern"""
        signature = str(tiers)
        if signature in self.pattern_history:
            return self.pattern_history[signature]
        return None
    
    def predict(self, match_input, home_team="", away_team="", league=""):
        """Generate prediction based on history first, tiers second"""
        
        # Get tier signature
        tiers = self._get_tier_signature(match_input)
        match_for_search = {'tiers': tiers}
        
        # Find similar matches (exact signature first)
        similar = self.find_similar_matches(match_for_search)
        
        # Get historical insights for this pattern
        pattern_history = self.get_pattern_insights(tiers)
        
        # Calculate weighted averages from similar matches
        if similar:
            total_weight = 0
            weighted_goals = 0
            weighted_btts = 0
            
            for sim, match in similar:
                weight = sim ** 2
                total_weight += weight
                weighted_goals += weight * match['goals']
                weighted_btts += weight * match['btts']
            
            if total_weight > 0:
                expected_goals = weighted_goals / total_weight
                btts_prob = (weighted_btts / total_weight) * 100
            else:
                expected_goals = 2.5
                btts_prob = 50
        else:
            expected_goals = 2.5
            btts_prob = 50
        
        # ====================================================================
        # HISTORY-BASED DECISION LOGIC
        # ====================================================================
        
        # If we have historical pattern data, USE IT (it's more reliable)
        if pattern_history and pattern_history['count'] >= 2:
            return self._history_based_prediction(
                tiers, pattern_history, expected_goals, btts_prob, similar
            )
        
        # Otherwise fall back to tier-based logic
        return self._tier_based_prediction(
            tiers, expected_goals, btts_prob, similar
        )
    
    def _history_based_prediction(self, tiers, history, expected_goals, btts_prob, similar):
        """Make prediction based on historical pattern data"""
        
        # Historical data overrides tier logic
        home_scores = history['home_scored_pct']
        away_scores = history['away_scored_pct']
        btts_pct = history['btts_pct']
        over_pct = history['over_pct']
        avg_goals = history['avg_goals']
        
        match_type = "📊 HISTORY-BASED"
        
        # Determine bet based on historical patterns
        if btts_pct <= 20 and over_pct <= 20:
            bet = "✅ UNDER 2.5 & NO BTTS"
            action = f"HISTORY SAYS: {history['count']} matches - No BTTS, Under 2.5"
        elif home_scores >= 70 and away_scores <= 30:
            bet = "🏠 HOME TO SCORE"
            action = f"HISTORY SAYS: Home scores in {home_scores:.0f}% of matches"
        elif away_scores >= 70 and home_scores <= 30:
            bet = "✈️ AWAY TO SCORE"
            action = f"HISTORY SAYS: Away scores in {away_scores:.0f}% of matches"
        elif btts_pct >= 70:
            bet = "⚽ BTTS"
            action = f"HISTORY SAYS: BTTS in {btts_pct:.0f}% of matches"
        elif over_pct >= 70:
            bet = "🔥 OVER 2.5"
            action = f"HISTORY SAYS: Over 2.5 in {over_pct:.0f}% of matches"
        elif home_scores <= 20 and away_scores <= 20:
            bet = "✅ UNDER 2.5 & NO BTTS"
            action = f"HISTORY SAYS: No goals from either team in most matches"
        else:
            bet = "⚖️ NO CLEAR PATTERN"
            action = f"HISTORY SAYS: Mixed results - {home_scores:.0f}% home score, {away_scores:.0f}% away score"
        
        # Calculate confidence based on sample size
        base_confidence = 70 + (min(history['count'], 10) * 2)
        
        # Penalty if history contradicts tier logic
        tier_home_score = (tiers[2] <= 2)  # Tier 1-2 means should score
        if tier_home_score and home_scores < 40:
            base_confidence -= 15  # History says no, tiers say yes - penalty
        
        confidence = min(base_confidence, 95)
        
        # Calculate honest score
        score = min(int(avg_goals * 4) + int(btts_pct / 20), 13)
        
        return {
            'match_type': match_type,
            'bet': bet,
            'action': action,
            'expected_goals': round(avg_goals, 1),
            'btts_probability': round(btts_pct, 1),
            'confidence': round(confidence, 1),
            'score': score,
            'max_score': 13,
            'tier_signature': tiers,
            'pattern_history': history,
            'similar_matches': similar[:3]
        }
    
    def _tier_based_prediction(self, tiers, expected_goals, btts_prob, similar):
        """Fallback tier-based prediction when no history available"""
        
        # Calculate base confidence
        avg_similarity = np.mean([s for s, _ in similar]) if similar else 0.5
        confidence = 50 + (avg_similarity * 30)
        
        # Simple tier-based logic
        if (tiers[0] <= 2 and tiers[1] <= 2 and 
            tiers[2] <= 2 and tiers[3] <= 2 and 
            tiers[4] <= 2 and tiers[5] <= 2):
            
            match_type = "💥 EXPLOSION (TIER)"
            bet = "🔥 OVER 2.5 & BTTS"
            action = "All tiers 1-2 suggest goals"
        
        elif (tiers[0] >= 4 and tiers[1] >= 4 and 
              tiers[2] >= 4 and tiers[3] >= 4 and 
              tiers[4] >= 4 and tiers[5] >= 4):
            
            match_type = "🔒 DEFENSIVE (TIER)"
            bet = "✅ UNDER 2.5 & NO BTTS"
            action = "All tiers 4-5 suggest low scoring"
        
        elif abs(tiers[0] - tiers[1]) >= 2:
            match_type = "⚖️ MISMATCH (TIER)"
            dominant = "Home" if tiers[0] < tiers[1] else "Away"
            bet = f"{dominant} TO DOMINATE"
            action = f"{dominant} team has attacking advantage"
        
        elif expected_goals >= 2.8:
            match_type = "🔥 HIGH SCORING (TIER)"
            bet = "🔥 OVER 2.5"
            action = "Tiers suggest goals likely"
        
        elif expected_goals <= 2.3:
            match_type = "📊 LOW SCORING (TIER)"
            bet = "✅ UNDER 2.5"
            action = "Tiers suggest low scoring"
        
        else:
            match_type = "🔄 MIXED (TIER)"
            bet = "⚖️ NO CLEAR EDGE"
            action = "Tiers contradictory - watch live"
        
        # Simple score calculation
        score = 0
        for t in tiers:
            score += (6 - t)
        score = min(score, 13)
        
        return {
            'match_type': match_type,
            'bet': bet,
            'action': action,
            'expected_goals': round(expected_goals, 1),
            'btts_probability': round(btts_prob, 1),
            'confidence': round(confidence, 1),
            'score': score,
            'max_score': 13,
            'tier_signature': tiers,
            'pattern_history': None,
            'similar_matches': similar[:3]
        }
    
    def learn(self, match_input, actual_goals, actual_btts, home_team, away_team, league="Unknown"):
        """Add new match to knowledge base and update pattern history"""
        new_match = {
            'home_da': match_input['home_da'],
            'away_da': match_input['away_da'],
            'home_btts': match_input['home_btts'],
            'away_btts': match_input['away_btts'],
            'home_over': match_input['home_over'],
            'away_over': match_input['away_over'],
            'elite': match_input.get('elite', 0),
            'derby': match_input.get('derby', 0),
            'relegation': match_input.get('relegation', 0),
            'goals': actual_goals,
            'btts': actual_btts,
            'league': league,
            'home_team': home_team,
            'away_team': away_team
        }
        
        self.knowledge_base.append(new_match)
        
        # Update clusters
        signature = str(self._get_tier_signature(new_match))
        self.pattern_clusters[signature].append(new_match)
        
        # Re-analyze pattern history
        self._analyze_pattern_history()
        
        return len(self.knowledge_base)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def tier_to_emoji(tier, category):
    """Convert tier to emoji for display"""
    if category == 'da':
        emojis = ["💥", "⚡", "📊", "🐢", "🛡️"]
    elif category == 'btts':
        emojis = ["🎯", "⚽", "🤔", "🧤", "🚫"]
    else:  # over
        emojis = ["🔥", "📈", "⚖️", "📉", "💤"]
    return emojis[tier-1]


# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v11.0")
    st.markdown("### History-Based Pattern Learning - Trusting What Actually Happened")
    
    # Initialize hunter
    if 'hunter' not in st.session_state:
        st.session_state.hunter = PatternLearningHunter()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Knowledge")
        st.metric("Patterns", len(st.session_state.hunter.knowledge_base))
        st.metric("Clusters", len(st.session_state.hunter.pattern_clusters))
        st.metric("Learned Patterns", len(st.session_state.hunter.pattern_history))
        
        if st.session_state.hunter.pattern_history:
            st.subheader("📈 Pattern Insights")
            for sig, data in list(st.session_state.hunter.pattern_history.items())[:3]:
                st.text(f"{sig}: {data['count']} matches")
                st.text(f"  BTTS: {data['btts_pct']:.0f}% | Over: {data['over_pct']:.0f}%")
        
        st.markdown("---")
        st.markdown("**Tiers:** 1💥 2⚡ 3📊 4🐢 5🛡️")
    
    # Main input form
    with st.form("match_input"):
        st.subheader("📋 Match Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏠 HOME**")
            home_team = st.text_input("Home Team", "Leeds")
            home_da = st.number_input("DA", 0, 100, 42)
            home_btts = st.number_input("BTTS %", 0, 100, 64)
            home_over = st.number_input("Over %", 0, 100, 64)
        
        with col2:
            st.markdown("**✈️ AWAY**")
            away_team = st.text_input("Away Team", "Sunderland")
            away_da = st.number_input("DA", 0, 100, 41, key="away_da")
            away_btts = st.number_input("BTTS %", 0, 100, 36, key="away_btts")
            away_over = st.number_input("Over %", 0, 100, 36, key="away_over")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            elite = st.checkbox("⭐ Elite")
        with col4:
            derby = st.checkbox("🏆 Derby")
        with col5:
            relegation = st.checkbox("⚠️ Relegation")
        
        league = st.text_input("League", "EPL")
        
        submitted = st.form_submit_button("🎯 GET HISTORY-BASED PREDICTION", use_container_width=True)
    
    if submitted:
        match_input = {
            'home_da': home_da,
            'away_da': away_da,
            'home_btts': home_btts,
            'away_btts': away_btts,
            'home_over': home_over,
            'away_over': away_over,
            'elite': 1 if elite else 0,
            'derby': 1 if derby else 0,
            'relegation': 1 if relegation else 0
        }
        
        result = st.session_state.hunter.predict(match_input, home_team, away_team, league)
        tiers = result['tier_signature']
        
        st.markdown("---")
        st.subheader(f"🏆 {home_team} vs {away_team}")
        
        # Tier signature row
        cols = st.columns(6)
        tier_labels = ['H-DA', 'A-DA', 'H-BTTS', 'A-BTTS', 'H-OVER', 'A-OVER']
        tier_cats = ['da', 'da', 'btts', 'btts', 'over', 'over']
        for i, (col, label, cat) in enumerate(zip(cols, tier_labels, tier_cats)):
            emoji = tier_to_emoji(tiers[i], cat)
            col.metric(label, f"{emoji} {tiers[i]}")
        
        # Show pattern history if available
        if result['pattern_history']:
            hist = result['pattern_history']
            st.info(f"📊 **Pattern History ({hist['count']} matches):** "
                   f"Home scores {hist['home_scored_pct']:.0f}% | "
                   f"Away scores {hist['away_scored_pct']:.0f}% | "
                   f"BTTS {hist['btts_pct']:.0f}% | "
                   f"Over {hist['over_pct']:.0f}% | "
                   f"Avg {hist['avg_goals']:.1f} goals")
        
        # MAIN BETTING CALL
        confidence_color = "🟢" if result['confidence'] >= 70 else "🟡" if result['confidence'] >= 50 else "🔴"
        
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2 style="text-align: center; color: #1f1f1f;">{result['match_type']}</h2>
            <h1 style="text-align: center; font-size: 48px; margin: 10px 0;">{result['bet']}</h1>
            <p style="text-align: center; font-size: 20px;">{result['action']}</p>
            <div style="display: flex; justify-content: center; gap: 30px; margin-top: 20px;">
                <div><strong>Expected Goals:</strong> {result['expected_goals']}</div>
                <div><strong>BTTS Prob:</strong> {result['btts_probability']}%</div>
                <div><strong>Confidence:</strong> {confidence_color} {result['confidence']}%</div>
                <div><strong>Score:</strong> {result['score']}/{result['max_score']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Similar matches
        if result['similar_matches']:
            st.subheader("📊 Similar Historical Matches")
            for sim, match in result['similar_matches']:
                pct = int(sim * 100)
                btts_text = "✅ BTTS" if match['btts'] else "❌ No BTTS"
                st.text(f"• {match.get('home_team', 'Home')} vs {match.get('away_team', 'Away')} ({match.get('league', 'Unknown')})")
                st.text(f"  {pct}% similar • {match['goals']} goals • {btts_text}")
        
        # Learning section
        st.markdown("---")
        st.subheader("📚 Teach The System")
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            actual = st.number_input("Actual Goals", 0, 10, 1)
        with col_l2:
            actual_btts = st.checkbox("BTTS Happened?", value=False)
        with col_l3:
            if st.button("📥 Learn From This Match", use_container_width=True):
                total = st.session_state.hunter.learn(
                    match_input, 
                    actual, 
                    1 if actual_btts else 0,
                    home_team,
                    away_team,
                    league
                )
                st.success(f"✅ Learned! Total patterns: {total}")
                st.balloons()
                st.rerun()
    
    st.markdown("---")
    st.markdown("🎯 **v11.0** - History-Based Learning | Trusting Patterns | No Fluff")


if __name__ == "__main__":
    main()
