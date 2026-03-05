import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="Mismatch Hunter v10.0",
    page_icon="🎯",
    layout="wide"
)

# ============================================================================
# TIER-BASED PATTERN RECOGNITION WITH COUNTER THREAT DETECTION
# ============================================================================

class TierBasedHunter:
    """
    League-agnostic pattern recognition using TIERS
    v10.0 adds Counter Threat detection and honest scoring
    """
    
    def __init__(self):
        self.knowledge_base = self._initialize_knowledge()
        self.pattern_clusters = defaultdict(list)
        self.counter_threats = {}  # Track teams that overperform
        self._build_initial_clusters()
    
    def _da_tier(self, da):
        """Convert DA to tier (1-5)"""
        if da >= 80: return 1  # Elite attack
        if da >= 65: return 2  # Strong attack
        if da >= 50: return 3  # Average attack
        if da >= 35: return 4  # Weak attack
        return 5                # Defensive shell
    
    def _btts_tier_v2(self, btts, team_name="", league=""):
        """
        Enhanced BTTS tier with Counter Threat detection
        Returns (tier, is_counter_threat)
        """
        base_tier = self._btts_tier_base(btts)
        is_counter = False
        
        # Check if this team is a known counter threat
        if team_name and team_name in self.counter_threats:
            is_counter = True
            # Counter threats get special handling
            if base_tier == 4:  # If stats say Tier 4 but they're counter threat
                return (4, True)  # Keep tier 4 but mark as counter
        else:
            # Auto-detect potential counter threats from knowledge base
            potential = self._detect_counter_threat(team_name, league)
            if potential:
                is_counter = True
                if team_name:
                    self.counter_threats[team_name] = {
                        'league': league,
                        'detected_date': datetime.now().strftime('%Y-%m-%d')
                    }
        
        return (base_tier, is_counter)
    
    def _btts_tier_base(self, btts):
        """Base BTTS tier (1-5)"""
        if btts >= 65: return 1  # Always scores
        if btts >= 55: return 2  # Usually scores
        if btts >= 45: return 3  # 50/50
        if btts >= 35: return 4  # Usually doesn't score
        return 5                  # Never scores
    
    def _detect_counter_threat(self, team_name, league):
        """
        Detect if a team is a counter threat based on historical performance
        """
        if not team_name:
            return False
        
        # Look for this team in knowledge base
        team_matches = [m for m in self.knowledge_base 
                       if m.get('home_team') == team_name or m.get('away_team') == team_name]
        
        if len(team_matches) < 3:
            return False
        
        # Calculate actual BTTS rate
        btts_count = 0
        total = 0
        for match in team_matches:
            if match.get('btts') == 1:
                btts_count += 1
            total += 1
        
        actual_btts_rate = (btts_count / total) * 100
        
        # Get average BTTS stat for this team
        stat_btts = []
        for match in team_matches:
            if match.get('home_team') == team_name:
                stat_btts.append(match.get('home_btts', 0))
            else:
                stat_btts.append(match.get('away_btts', 0))
        
        avg_stat = np.mean(stat_btts) if stat_btts else 50
        
        # If actual performance is significantly better than stats
        if actual_btts_rate > avg_stat + 10 and avg_stat < 50:
            return True
        
        return False
    
    def _over_tier(self, over):
        """Convert Over% to tier (1-5)"""
        if over >= 65: return 1  # Goal fest
        if over >= 55: return 2  # Goals likely
        if over >= 45: return 3  # 50/50
        if over >= 35: return 4  # Goals unlikely
        return 5                  # Dead game
    
    def _get_tier_signature(self, match, home_team="", away_team="", league=""):
        """Get 6-number tier signature with counter threat detection"""
        home_btts_tier, home_counter = self._btts_tier_v2(match['home_btts'], home_team, league)
        away_btts_tier, away_counter = self._btts_tier_v2(match['away_btts'], away_team, league)
        
        return {
            'tiers': [
                self._da_tier(match['home_da']),
                self._da_tier(match['away_da']),
                home_btts_tier,
                away_btts_tier,
                self._over_tier(match['home_over']),
                self._over_tier(match['away_over'])
            ],
            'counter_threats': {
                'home': home_counter,
                'away': away_counter
            }
        }
    
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
            
            # Add Sunderland as a known counter threat
            {'home_da': 41, 'away_da': 42, 'home_btts': 36, 'away_btts': 36,
             'home_over': 36, 'away_over': 44, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 1.8, 'btts': 0, 'league': 'EPL',
             'home_team': 'Sunderland', 'away_team': 'Leeds'},
        ]
    
    def _build_initial_clusters(self):
        """Group matches by tier signature"""
        for match in self.knowledge_base:
            sig_data = self._get_tier_signature(
                match, 
                match.get('home_team', ''), 
                match.get('away_team', ''),
                match.get('league', '')
            )
            signature = str(sig_data['tiers'])
            self.pattern_clusters[signature].append(match)
    
    def calculate_contradiction_penalty(self, tiers, counter_threats):
        """
        Calculate penalty based on contradictions in the data
        Higher penalty = less confidence
        """
        penalty = 0
        
        # Counter threat penalties
        if counter_threats['away']:
            penalty += 5  # Away team is sneaky
        if counter_threats['home']:
            penalty += 5  # Home team is sneaky
        
        # BTTS contradictions
        if tiers[2] <= 2 and tiers[3] >= 4:
            # Home scores, away doesn't - normal
            pass
        elif tiers[2] >= 4 and tiers[3] <= 2:
            # Away scores, home doesn't - unusual
            penalty += 10
        elif tiers[2] == 4 and tiers[3] == 4:
            # Both supposedly don't score
            if counter_threats['home'] or counter_threats['away']:
                penalty += 15  # But one might!
        
        # Over contradictions
        if abs(tiers[4] - tiers[5]) >= 2:
            # One team's games high scoring, other low
            penalty += 8
        
        # DA vs Over contradictions
        if tiers[0] <= 2 and tiers[4] >= 3:
            # Strong attack but games not high scoring?
            penalty += 5
        
        return min(penalty, 30)  # Max penalty 30%
    
    def calculate_honest_score(self, tiers, counter_threats):
        """
        Calculate honest score (0-13) with contradictions factored in
        """
        base_score = 0
        
        # Base points from tiers
        for t in tiers:
            base_score += (6 - t)
        
        # Subtract penalty
        penalty = self.calculate_contradiction_penalty(tiers, counter_threats)
        penalty_points = int(penalty / 3)  # Convert % to points
        
        final_score = base_score - penalty_points
        return max(final_score, 0)  # Can't go below 0
    
    def find_similar_matches(self, match_input, k=5):
        """Find matches with same or similar tier signature"""
        input_tiers = match_input['tiers']
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
    
    def predict(self, match_input, home_team="", away_team="", league=""):
        """Generate prediction with honest scoring"""
        
        # Get tier signature with counter threat detection
        sig_data = self._get_tier_signature(match_input, home_team, away_team, league)
        tiers = sig_data['tiers']
        counter_threats = sig_data['counter_threats']
        
        # Find similar matches
        match_for_search = {'tiers': tiers}
        similar = self.find_similar_matches(match_for_search)
        
        if not similar:
            return self._fallback_prediction(tiers, counter_threats)
        
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
        
        # Calculate base confidence
        avg_similarity = np.mean([s for s, _ in similar])
        base_confidence = avg_similarity * 100
        
        # Apply contradiction penalty
        penalty = self.calculate_contradiction_penalty(tiers, counter_threats)
        confidence = max(base_confidence - penalty, 30)  # Can't go below 30%
        
        # Calculate honest score
        honest_score = self.calculate_honest_score(tiers, counter_threats)
        
        # ====================================================================
        # ENHANCED BETTING LOGIC WITH COUNTER THREAT AWARENESS
        # ====================================================================
        
        match_type = ""
        bet = ""
        action = ""
        
        # Check for counter threat warnings first
        if counter_threats['away'] and tiers[0] <= 2:
            match_type = "⚠️ COUNTER THREAT WARNING"
            bet = "🏠 HOME WIN + AWAY GOAL?"
            action = "Home should dominate, but away team steals goals - consider BTTS"
            
        elif counter_threats['home'] and tiers[1] <= 2:
            match_type = "⚠️ COUNTER THREAT WARNING"
            bet = "✈️ AWAY WIN + HOME GOAL?"
            action = "Away should dominate, but home team steals goals - consider BTTS"
        
        # PATTERN 1: EXPLOSION - All tiers 1-2
        elif (tiers[0] <= 2 and tiers[1] <= 2 and 
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
            if not counter_threats['home'] and not counter_threats['away']:
                if expected_goals <= 2.2:
                    bet = "✅ UNDER 2.5 & NO BTTS"
                    action = "STRONG BET: Under 2.5 and No BTTS"
                else:
                    bet = "✅ UNDER 2.5"
                    action = "BET: Under 2.5"
            else:
                match_type = "⚠️ DEFENSIVE BUT WATCH"
                bet = "✅ UNDER 2.5"
                action = "BET: Under 2.5 - but counter threat could score"
        
        # PATTERN 3: MISMATCH - One team much stronger
        elif abs(tiers[0] - tiers[1]) >= 2:
            match_type = "⚖️ MISMATCH"
            dominant = "Home" if tiers[0] < tiers[1] else "Away"
            
            # Check if underdog is counter threat
            underdog = "away" if dominant == "Home" else "home"
            if counter_threats[underdog]:
                match_type = "⚖️ MISMATCH + COUNTER THREAT"
                bet = f"🔥 {dominant} TO WIN - BUT {underdog.upper()} MAY SCORE"
                action = f"BET: {dominant} win, consider BTTS"
            elif tiers[4] <= 2 or tiers[5] <= 2:
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
            if btts_prob <= 45 and not (counter_threats['home'] or counter_threats['away']):
                bet = "✅ UNDER 2.5 & NO BTTS"
                action = "STRONG BET: Under 2.5 and No BTTS"
            elif counter_threats['home'] or counter_threats['away']:
                match_type = "📊 LOW SCORING + COUNTER THREAT"
                bet = "✅ UNDER 2.5"
                action = "BET: Under 2.5 - but counter threat could spoil clean sheet"
            else:
                bet = "✅ UNDER 2.5"
                action = "BET: Under 2.5"
        
        # PATTERN 6: CONTRADICTION
        else:
            match_type = "🔄 CONTRADICTION"
            
            # Check for specific patterns
            if tiers[2] <= 2 and tiers[3] >= 4:
                bet = "🏠 HOME TO SCORE"
                action = "BET: Home team to score"
            elif tiers[2] >= 4 and tiers[3] <= 2:
                bet = "✈️ AWAY TO SCORE"
                action = "BET: Away team to score"
            elif abs(tiers[4] - tiers[5]) >= 2:
                high_over_team = "Home" if tiers[4] < tiers[5] else "Away"
                bet = f"{high_over_team} OVER 0.5 TEAM GOALS"
                action = f"BET: {high_over_team} team to score"
            else:
                bet = "⚖️ NO CLEAR EDGE"
                action = "AVOID: Stats too contradictory for confident bet"
        
        return {
            'match_type': match_type,
            'bet': bet,
            'action': action,
            'expected_goals': round(expected_goals, 1),
            'btts_probability': round(btts_prob, 1),
            'confidence': round(confidence, 1),
            'score': honest_score,
            'max_score': 13,
            'tier_signature': tiers,
            'counter_threats': counter_threats,
            'penalty_applied': round(penalty, 1),
            'similar_matches': similar[:3]
        }
    
    def _fallback_prediction(self, tiers, counter_threats):
        """Fallback when no similar matches found"""
        
        honest_score = self.calculate_honest_score(tiers, counter_threats)
        penalty = self.calculate_contradiction_penalty(tiers, counter_threats)
        confidence = 50 - penalty
        
        if all(t <= 2 for t in tiers):
            return {
                'match_type': "🆕 NEW PATTERN - EXPLOSIVE",
                'bet': "🔥 OVER 2.5",
                'action': "SPECULATIVE BET: Pattern suggests goals",
                'expected_goals': 3.0,
                'btts_probability': 60,
                'confidence': max(confidence, 30),
                'score': honest_score,
                'max_score': 13,
                'tier_signature': tiers,
                'counter_threats': counter_threats,
                'penalty_applied': penalty,
                'similar_matches': []
            }
        elif all(t >= 4 for t in tiers):
            if counter_threats['home'] or counter_threats['away']:
                return {
                    'match_type': "🆕 DEFENSIVE + COUNTER THREAT",
                    'bet': "✅ UNDER 2.5",
                    'action': "BET: Under 2.5 - but counter threat may score",
                    'expected_goals': 2.2,
                    'btts_probability': 35,
                    'confidence': max(confidence, 30),
                    'score': honest_score,
                    'max_score': 13,
                    'tier_signature': tiers,
                    'counter_threats': counter_threats,
                    'penalty_applied': penalty,
                    'similar_matches': []
                }
            else:
                return {
                    'match_type': "🆕 NEW PATTERN - DEFENSIVE",
                    'bet': "✅ UNDER 2.5",
                    'action': "SPECULATIVE BET: Pattern suggests low scoring",
                    'expected_goals': 2.2,
                    'btts_probability': 35,
                    'confidence': max(confidence, 30),
                    'score': honest_score,
                    'max_score': 13,
                    'tier_signature': tiers,
                    'counter_threats': counter_threats,
                    'penalty_applied': penalty,
                    'similar_matches': []
                }
        else:
            return {
                'match_type': "🆕 NEW PATTERN",
                'bet': "⚖️ NO CLEAR EDGE",
                'action': "LEARNING MODE: No historical data for this pattern",
                'expected_goals': 2.6,
                'btts_probability': 50,
                'confidence': max(confidence, 30),
                'score': honest_score,
                'max_score': 13,
                'tier_signature': tiers,
                'counter_threats': counter_threats,
                'penalty_applied': penalty,
                'similar_matches': []
            }
    
    def learn(self, match_input, actual_goals, actual_btts, home_team, away_team, league="Unknown"):
        """Add new match to knowledge base and update counter threats"""
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
        sig_data = self._get_tier_signature(match_input, home_team, away_team, league)
        signature = str(sig_data['tiers'])
        self.pattern_clusters[signature].append(new_match)
        
        # Check for counter threats
        self._detect_counter_threat(home_team, league)
        self._detect_counter_threat(away_team, league)
        
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
# MAIN UI - CLEAN AND SIMPLE
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v10.0")
    st.markdown("### Counter Threat Detection & Honest Scoring")
    
    # Initialize hunter
    if 'hunter' not in st.session_state:
        st.session_state.hunter = TierBasedHunter()
    
    # Sidebar - Simple stats
    with st.sidebar:
        st.header("📊 Knowledge")
        st.metric("Patterns", len(st.session_state.hunter.knowledge_base))
        st.metric("Clusters", len(st.session_state.hunter.pattern_clusters))
        st.metric("Counter Threats", len(st.session_state.hunter.counter_threats))
        
        if st.session_state.hunter.counter_threats:
            st.subheader("⚠️ Counter Threats")
            for team in list(st.session_state.hunter.counter_threats.keys())[:5]:
                st.text(f"• {team}")
        
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
        
        submitted = st.form_submit_button("🎯 GET HONEST BET", use_container_width=True)
    
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
        counter = result['counter_threats']
        
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
            
            # Add counter threat indicator
            if (i == 2 and counter['home']) or (i == 3 and counter['away']):
                col.metric(label, f"{emoji} {tiers[i]}", delta="⚠️")
            else:
                col.metric(label, f"{emoji} {tiers[i]}")
        
        # Counter threat warnings
        if counter['home'] or counter['away']:
            warning = ""
            if counter['home']:
                warning += f"⚠️ {home_team} is a COUNTER THREAT - they score when stats say they shouldn't. "
            if counter['away']:
                warning += f"⚠️ {away_team} is a COUNTER THREAT - they score when stats say they shouldn't. "
            st.warning(warning)
        
        # MAIN BETTING CALL - BIG AND CLEAR
        confidence_color = "🟢" if result['confidence'] >= 70 else "🟡" if result['confidence'] >= 50 else "🔴"
        
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2 style="text-align: center; color: #1f1f1f;">{result['match_type']}</h2>
            <h1 style="text-align: center; font-size: 48px; margin: 10px 0;">{result['bet']}</h1>
            <p style="text-align: center; font-size: 20px;">{result['action']}</p>
            <div style="display: flex; justify-content: center; gap: 30px; margin-top: 20px;">
                <div><strong>Goals:</strong> {result['expected_goals']}</div>
                <div><strong>BTTS:</strong> {result['btts_probability']}%</div>
                <div><strong>Confidence:</strong> {confidence_color} {result['confidence']}%</div>
                <div><strong>Score:</strong> {result['score']}/{result['max_score']}</div>
                <div><strong>Penalty:</strong> -{result['penalty_applied']}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Similar matches (optional - can be hidden)
        with st.expander("📊 Similar Historical Matches"):
            if result['similar_matches']:
                for sim, match in result['similar_matches']:
                    pct = int(sim * 100)
                    btts_text = "✅ BTTS" if match['btts'] else "❌ No BTTS"
                    st.text(f"{match.get('home_team', 'Home')} vs {match.get('away_team', 'Away')} ({match.get('league', 'Unknown')})")
                    st.text(f"  {pct}% similar • {match['goals']} goals • {btts_text}")
            else:
                st.text("No similar matches in database")
        
        # Learning section
        st.markdown("---")
        st.subheader("📚 Learning")
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            actual = st.number_input("Actual Goals", 0, 10, 1)
        with col_l2:
            actual_btts = st.checkbox("BTTS Happened?")
        with col_l3:
            if st.button("📥 Teach System"):
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
    
    # Footer
    st.markdown("---")
    st.markdown("🎯 **v10.0** - Counter Threat Detection | Honest Scoring | No Fluff")


if __name__ == "__main__":
    main()
