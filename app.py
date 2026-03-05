import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="Mismatch Hunter v9.0",
    page_icon="🎯",
    layout="wide"
)

# ============================================================================
# TIER-BASED PATTERN RECOGNITION ENGINE
# ============================================================================

class TierBasedHunter:
    """
    League-agnostic pattern recognition using TIERS instead of raw numbers
    Each value converted to 1-5 tier based on football meaning
    """
    
    def __init__(self):
        self.knowledge_base = self._initialize_knowledge()
        self.pattern_clusters = defaultdict(list)
        self._build_initial_clusters()
    
    def _da_tier(self, da):
        """Convert DA to tier (1-5)"""
        if da >= 80: return 1  # Elite attack
        if da >= 65: return 2  # Strong attack
        if da >= 50: return 3  # Average attack
        if da >= 35: return 4  # Weak attack
        return 5                # Defensive shell
    
    def _btts_tier(self, btts):
        """Convert BTTS% to tier (1-5)"""
        if btts >= 65: return 1  # Always scores
        if btts >= 55: return 2  # Usually scores
        if btts >= 45: return 3  # 50/50
        if btts >= 35: return 4  # Usually doesn't score
        return 5                  # Never scores
    
    def _over_tier(self, over):
        """Convert Over% to tier (1-5)"""
        if over >= 65: return 1  # Goal fest
        if over >= 55: return 2  # Goals likely
        if over >= 45: return 3  # 50/50
        if over >= 35: return 4  # Goals unlikely
        return 5                  # Dead game
    
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
        """Initialize with tier-based knowledge"""
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
        ]
    
    def _build_initial_clusters(self):
        """Group matches by tier signature"""
        for match in self.knowledge_base:
            signature = str(self._get_tier_signature(match))
            self.pattern_clusters[signature].append(match)
    
    def find_similar_matches(self, match_input, k=5):
        """Find matches with same or similar tier signature"""
        input_tiers = self._get_tier_signature(match_input)
        input_sig = str(input_tiers)
        
        # First try exact signature match
        if input_sig in self.pattern_clusters:
            matches = [(1.0, i, m) for i, m in enumerate(self.pattern_clusters[input_sig])]
            matches.sort(reverse=True)
            return [(sim, match) for sim, _, match in matches[:k]]
        
        # If no exact match, find closest by tier difference
        similarities = []
        for sig, matches in self.pattern_clusters.items():
            try:
                sig_tiers = [int(x.strip()) for x in sig.strip('[]').split(',')]
            except:
                continue
            
            if len(sig_tiers) != 6:
                continue
            
            diff = 0
            for a, b in zip(input_tiers, sig_tiers):
                diff += abs(a - b)
            
            similarity = max(0, 1 - (diff / 24))
            
            for match in matches:
                similarities.append((similarity, len(similarities), match))
        
        similarities.sort(reverse=True)
        return [(sim, match) for sim, _, match in similarities[:k]]
    
    def predict(self, match_input):
        """Generate prediction based on tier patterns"""
        
        similar = self.find_similar_matches(match_input)
        
        if not similar:
            return self._fallback_prediction(match_input)
        
        # Calculate weighted averages
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
        
        # Calculate confidence
        avg_similarity = np.mean([s for s, _ in similar])
        confidence = min(avg_similarity * 100, 95)
        
        # Get tier signature
        tiers = self._get_tier_signature(match_input)
        
        # ====================================================================
        # CLEAN BETTING LOGIC - NO "WATCH FIRST 30 MINS"
        # ====================================================================
        
        # PATTERN 1: EXPLOSION - All tiers 1-2
        if (tiers[0] <= 2 and tiers[1] <= 2 and 
            tiers[2] <= 2 and tiers[3] <= 2 and 
            tiers[4] <= 2 and tiers[5] <= 2):
            
            match_type = "💥 EXPLOSION"
            if expected_goals >= 3.0:
                bet = "🔥 OVER 2.5 & BTTS"
                action = "STRONG BET: Over 2.5 and Both Teams to Score"
            else:
                bet = "⚽ BTTS"
                action = "BET: Both Teams to Score"
        
        # PATTERN 2: DEFENSIVE LOCK - All tiers 4-5
        elif (tiers[0] >= 4 and tiers[1] >= 4 and 
              tiers[2] >= 4 and tiers[3] >= 4 and 
              tiers[4] >= 4 and tiers[5] >= 4):
            
            match_type = "🔒 DEFENSIVE LOCK"
            if expected_goals <= 2.2:
                bet = "✅ UNDER 2.5 & NO BTTS"
                action = "STRONG BET: Under 2.5 and No BTTS"
            else:
                bet = "✅ UNDER 2.5"
                action = "BET: Under 2.5"
        
        # PATTERN 3: MISMATCH - One team much stronger
        elif abs(tiers[0] - tiers[1]) >= 2:
            match_type = "⚖️ MISMATCH"
            dominant = "Home" if tiers[0] < tiers[1] else "Away"
            
            if tiers[4] <= 2 or tiers[5] <= 2:  # One team has high Over
                bet = f"🔥 {dominant} TO SCORE 2+"
                action = f"BET: {dominant} team Over 1.5 Team Goals"
            else:
                bet = f"⚠️ {dominant} ADVANTAGE"
                action = f"WATCH: {dominant} team likely to control game"
        
        # PATTERN 4: HIGH SCORING
        elif expected_goals >= 3.0:
            match_type = "🔥 HIGH SCORING"
            if btts_prob >= 60:
                bet = "🔥 OVER 2.5 & BTTS"
                action = "STRONG BET: Over 2.5 and Both Teams to Score"
            else:
                bet = "🔥 OVER 2.5"
                action = "BET: Over 2.5"
        
        # PATTERN 5: LOW SCORING
        elif expected_goals <= 2.3:
            match_type = "📊 LOW SCORING"
            if btts_prob <= 45:
                bet = "✅ UNDER 2.5 & NO BTTS"
                action = "STRONG BET: Under 2.5 and No BTTS"
            else:
                bet = "✅ UNDER 2.5"
                action = "BET: Under 2.5"
        
        # PATTERN 6: CONTRADICTION - Stats don't align
        elif (tiers[4] <= 2 and tiers[5] >= 3) or (tiers[4] >= 3 and tiers[5] <= 2):
            match_type = "⚠️ CONTRADICTION"
            
            # One team high Over, other low Over
            if tiers[4] <= 2:  # Home high Over
                bet = "🏠 HOME TEAM TO SCORE"
                action = "BET: Home team Over 0.5 Team Goals"
            elif tiers[5] <= 2:  # Away high Over
                bet = "✈️ AWAY TEAM TO SCORE"
                action = "BET: Away team Over 0.5 Team Goals"
            else:
                bet = "⚽ BTTS POSSIBLE"
                action = "CONTRADICTION: Stats conflict - consider BTTS"
        
        # PATTERN 7: AUSTRIAN SPECIAL
        elif (tiers[0] == 4 and tiers[1] == 4 and tiers[2] == 5 and 
              tiers[3] == 1 and tiers[4] == 4 and tiers[5] == 3):
            
            match_type = "🎢 AUSTRIAN SPECIAL"
            bet = "⚽ AWAY TEAM TO SCORE"
            action = "BET: Away team to score (85% historical)"
        
        # PATTERN 8: DEFAULT - Balanced
        else:
            match_type = "🔄 BALANCED"
            if btts_prob >= 55:
                bet = "⚽ BTTS"
                action = "BET: Both Teams to Score"
            elif btts_prob <= 45:
                bet = "🚫 NO BTTS"
                action = "BET: No Both Teams to Score"
            else:
                bet = "⚖️ NO CLEAR EDGE"
                action = "AVOID: Stats too balanced for confident bet"
        
        # Calculate score (simplified - not 13/13 for everything!)
        score = 0
        score += (6 - tiers[0]) + (6 - tiers[1])  # DA
        score += (6 - tiers[2]) + (6 - tiers[3])  # BTTS
        score += (6 - tiers[4]) + (6 - tiers[5])  # Over
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
            'similar_matches': similar[:3]
        }
    
    def _fallback_prediction(self, match_input):
        """Fallback when no similar matches found"""
        tiers = self._get_tier_signature(match_input)
        
        if all(t <= 2 for t in tiers):
            return {
                'match_type': "🆕 NEW PATTERN - EXPLOSIVE",
                'bet': "🔥 OVER 2.5",
                'action': "SPECULATIVE BET: Pattern suggests goals",
                'expected_goals': 3.0,
                'btts_probability': 60,
                'confidence': 50,
                'score': self._calculate_simple_score(tiers),
                'max_score': 13,
                'tier_signature': tiers,
                'similar_matches': []
            }
        elif all(t >= 4 for t in tiers):
            return {
                'match_type': "🆕 NEW PATTERN - DEFENSIVE",
                'bet': "✅ UNDER 2.5",
                'action': "SPECULATIVE BET: Pattern suggests low scoring",
                'expected_goals': 2.2,
                'btts_probability': 35,
                'confidence': 50,
                'score': self._calculate_simple_score(tiers),
                'max_score': 13,
                'tier_signature': tiers,
                'similar_matches': []
            }
        else:
            return {
                'match_type': "🆕 NEW PATTERN",
                'bet': "⚖️ NO CLEAR EDGE",
                'action': "LEARNING MODE: No historical data for this pattern",
                'expected_goals': 2.6,
                'btts_probability': 50,
                'confidence': 40,
                'score': self._calculate_simple_score(tiers),
                'max_score': 13,
                'tier_signature': tiers,
                'similar_matches': []
            }
    
    def _calculate_simple_score(self, tiers):
        """Simple score calculation for fallback"""
        score = 0
        for t in tiers:
            score += (6 - t)
        return min(score, 13)


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
# MAIN UI - CLEAN AND SIMPLE
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v9.0")
    st.markdown("### Pure Betting Logic - No Fluff")
    
    # Initialize hunter
    if 'hunter' not in st.session_state:
        st.session_state.hunter = TierBasedHunter()
    
    # Sidebar - Simple stats
    with st.sidebar:
        st.header("📊 Knowledge")
        st.metric("Patterns", len(st.session_state.hunter.knowledge_base))
        st.metric("Clusters", len(st.session_state.hunter.pattern_clusters))
        
        st.markdown("---")
        st.markdown("**Tiers:** 1💥 2⚡ 3📊 4🐢 5🛡️")
    
    # Main input form
    with st.form("match_input"):
        st.subheader("📋 Match Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏠 HOME**")
            home_team = st.text_input("Home Team", "Brighton")
            home_da = st.number_input("DA", 0, 100, 52)
            home_btts = st.number_input("BTTS %", 0, 100, 64)
            home_over = st.number_input("Over %", 0, 100, 46)
        
        with col2:
            st.markdown("**✈️ AWAY**")
            away_team = st.text_input("Away Team", "Arsenal")
            away_da = st.number_input("DA", 0, 100, 62, key="away_da")
            away_btts = st.number_input("BTTS %", 0, 100, 52, key="away_btts")
            away_over = st.number_input("Over %", 0, 100, 55, key="away_over")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            elite = st.checkbox("⭐ Elite")
        with col4:
            derby = st.checkbox("🏆 Derby")
        with col5:
            relegation = st.checkbox("⚠️ Relegation")
        
        submitted = st.form_submit_button("🎯 GET BET", use_container_width=True)
    
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
        
        result = st.session_state.hunter.predict(match_input)
        tiers = result['tier_signature']
        
        # ====================================================================
        # CLEAN UI - NO HTML CLUTTER
        # ====================================================================
        
        st.markdown("---")
        st.subheader(f"🏆 {home_team} vs {away_team}")
        
        # Tier signature row
        cols = st.columns(6)
        tier_labels = ['H-DA', 'A-DA', 'H-BTTS', 'A-BTTS', 'H-OVER', 'A-OVER']
        tier_cats = ['da', 'da', 'btts', 'btts', 'over', 'over']
        for i, (col, label, cat) in enumerate(zip(cols, tier_labels, tier_cats)):
            emoji = tier_to_emoji(tiers[i], cat)
            col.metric(label, f"{emoji} {tiers[i]}")
        
        # MAIN BETTING CALL - BIG AND CLEAR
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2 style="text-align: center; color: #1f1f1f;">{result['match_type']}</h2>
            <h1 style="text-align: center; font-size: 48px; margin: 10px 0;">{result['bet']}</h1>
            <p style="text-align: center; font-size: 20px;">{result['action']}</p>
            <div style="display: flex; justify-content: center; gap: 30px; margin-top: 20px;">
                <div><strong>Goals:</strong> {result['expected_goals']}</div>
                <div><strong>BTTS:</strong> {result['btts_probability']}%</div>
                <div><strong>Confidence:</strong> {result['confidence']}%</div>
                <div><strong>Score:</strong> {result['score']}/{result['max_score']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Similar matches (optional - can be hidden)
        with st.expander("📊 Similar Historical Matches"):
            if result['similar_matches']:
                for sim, match in result['similar_matches']:
                    pct = int(sim * 100)
                    btts_text = "✅ BTTS" if match['btts'] else "❌ No BTTS"
                    st.text(f"{match['home_team']} vs {match['away_team']} ({match['league']})")
                    st.text(f"  {pct}% similar • {match['goals']} goals • {btts_text}")
            else:
                st.text("No similar matches in database")
        
        # Learning section (minimal)
        st.markdown("---")
        st.subheader("📚 Learning")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            actual = st.number_input("Actual Goals", 0, 10, 2)
        with col_l2:
            if st.button("📥 Teach System"):
                st.info("Learning feature coming in v10")
    
    # Footer
    st.markdown("---")
    st.markdown("🎯 **v9.0** - Pure betting logic | No fluff | Just bets")


if __name__ == "__main__":
    main()
