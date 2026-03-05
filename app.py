import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import json
import os
from collections import defaultdict

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v7.0",
    page_icon="🎯",
    layout="wide"
)

# ============================================================================
# PURE NUMBER PATTERN RECOGNITION ENGINE
# ============================================================================

class PureNumberHunter:
    """
    League-agnostic pattern recognition using only 11 core numbers
    No league names, no country bias, just pure statistics
    """
    
    def __init__(self):
        # Initialize with synthetic data based on league averages
        # This gives us baseline patterns without league bias
        self.knowledge_base = self._initialize_knowledge()
        self.pattern_clusters = {}
        self._build_initial_clusters()
    
    def _initialize_knowledge(self):
        """Create initial knowledge base from league averages (no league names)"""
        return [
            # EXPLOSION PATTERN (Bundesliga style)
            {'home_da': 82, 'away_da': 78, 'home_btts': 62, 'away_btts': 62,
             'home_over': 65, 'away_over': 65, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.2, 'btts': 1},
            {'home_da': 84, 'away_da': 76, 'home_btts': 64, 'away_btts': 60,
             'home_over': 67, 'away_over': 63, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.3, 'btts': 1},
            {'home_da': 80, 'away_da': 80, 'home_btts': 60, 'away_btts': 64,
             'home_over': 63, 'away_over': 66, 'elite': 0, 'derby': 1, 'relegation': 0,
             'goals': 3.1, 'btts': 1},
            
            # DEFENSIVE PATTERN (Serie A style)
            {'home_da': 72, 'away_da': 68, 'home_btts': 48, 'away_btts': 48,
             'home_over': 46, 'away_over': 46, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.5, 'btts': 0},
            {'home_da': 70, 'away_da': 66, 'home_btts': 46, 'away_btts': 44,
             'home_over': 44, 'away_over': 42, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 2.3, 'btts': 0},
            {'home_da': 74, 'away_da': 70, 'home_btts': 50, 'away_btts': 46,
             'home_over': 48, 'away_over': 44, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.6, 'btts': 0},
            
            # HYBRID PATTERN (EPL/La Liga style)
            {'home_da': 76, 'away_da': 72, 'home_btts': 56, 'away_btts': 56,
             'home_over': 54, 'away_over': 54, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.8, 'btts': 1},
            {'home_da': 78, 'away_da': 70, 'home_btts': 58, 'away_btts': 52,
             'home_over': 56, 'away_over': 50, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 2.9, 'btts': 1},
            {'home_da': 75, 'away_da': 73, 'home_btts': 55, 'away_btts': 55,
             'home_over': 57, 'away_over': 57, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 2.9, 'btts': 1},
            
            # MISMATCH PATTERN (One dominant team)
            {'home_da': 85, 'away_da': 55, 'home_btts': 70, 'away_btts': 40,
             'home_over': 72, 'away_over': 38, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.5, 'btts': 0},
            {'home_da': 60, 'away_da': 82, 'home_btts': 45, 'away_btts': 68,
             'home_over': 42, 'away_over': 70, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.1, 'btts': 1},
        ]
    
    def _build_initial_clusters(self):
        """Group similar patterns together"""
        # Simple clustering by goal ranges
        self.pattern_clusters = {
            'explosion': {'min_goals': 3.0, 'max_goals': 4.0, 'matches': []},
            'hybrid': {'min_goals': 2.6, 'max_goals': 3.0, 'matches': []},
            'defensive': {'min_goals': 2.0, 'max_goals': 2.6, 'matches': []},
            'mismatch': {'min_goals': 2.8, 'max_goals': 3.8, 'matches': []}
        }
        
        for match in self.knowledge_base:
            if match['goals'] >= 3.0:
                if abs(match['home_da'] - match['away_da']) > 20:
                    self.pattern_clusters['mismatch']['matches'].append(match)
                else:
                    self.pattern_clusters['explosion']['matches'].append(match)
            elif match['goals'] >= 2.6:
                self.pattern_clusters['hybrid']['matches'].append(match)
            else:
                self.pattern_clusters['defensive']['matches'].append(match)
    
    def calculate_similarity(self, match1, match2):
        """Calculate cosine similarity between two matches using core numbers"""
        # Core features: DA, BTTS, Over (6 numbers)
        v1 = np.array([
            match1['home_da'], match1['away_da'],
            match1['home_btts'], match1['away_btts'],
            match1['home_over'], match1['away_over']
        ])
        v2 = np.array([
            match2['home_da'], match2['away_da'],
            match2['home_btts'], match2['away_btts'],
            match2['home_over'], match2['away_over']
        ])
        
        # Normalize
        v1_norm = v1 / np.linalg.norm(v1)
        v2_norm = v2 / np.linalg.norm(v2)
        
        # Cosine similarity
        similarity = np.dot(v1_norm, v2_norm)
        return similarity
    
    def find_similar_matches(self, match_input, k=5):
        """Find most similar matches in knowledge base"""
        similarities = []
        for i, known_match in enumerate(self.knowledge_base):
            sim = self.calculate_similarity(match_input, known_match)
            similarities.append((sim, i, known_match))
        
        # Sort by similarity
        similarities.sort(reverse=True)
        
        # Return top k
        return [(sim, match) for sim, _, match in similarities[:k]]
    
    def predict(self, match_input):
        """Generate prediction based on similar historical patterns"""
        
        # Find similar matches
        similar = self.find_similar_matches(match_input)
        
        if not similar:
            return self._fallback_prediction(match_input)
        
        # Calculate weighted averages
        total_weight = 0
        weighted_goals = 0
        weighted_btts = 0
        
        for sim, match in similar:
            weight = sim ** 2  # Square to emphasize very similar matches
            total_weight += weight
            weighted_goals += weight * match['goals']
            weighted_btts += weight * match['btts']
        
        if total_weight > 0:
            expected_goals = weighted_goals / total_weight
            btts_prob = (weighted_btts / total_weight) * 100
        else:
            expected_goals = 2.7  # League average
            btts_prob = 52
        
        # Calculate confidence based on similarity and sample size
        avg_similarity = np.mean([s for s, _ in similar])
        sample_size = len(similar)
        
        confidence = (avg_similarity * 0.6 + min(sample_size / 10, 0.4)) * 100
        confidence = min(confidence, 95)
        
        # Determine match type and action
        match_type, action, prediction = self._classify_match(
            match_input, expected_goals, btts_prob
        )
        
        # Calculate explosion score
        score = self._calculate_score(match_input)
        
        return {
            'expected_goals': round(expected_goals, 1),
            'btts_probability': round(btts_prob, 1),
            'confidence': round(confidence, 1),
            'match_type': match_type,
            'action': action,
            'prediction': prediction,
            'score': score,
            'max_score': 13,
            'similar_matches': similar[:3],
            'avg_similarity': round(avg_similarity * 100, 1),
            'sample_size': sample_size
        }
    
    def _classify_match(self, match_input, expected_goals, btts_prob):
        """Classify match type based on numbers"""
        
        avg_da = (match_input['home_da'] + match_input['away_da']) / 2
        avg_btts = (match_input['home_btts'] + match_input['away_btts']) / 2
        avg_over = (match_input['home_over'] + match_input['away_over']) / 2
        da_diff = abs(match_input['home_da'] - match_input['away_da'])
        
        # EXPLOSION: Both teams attack, both high percentages
        if (match_input['home_da'] >= 75 and match_input['away_da'] >= 75 and
            avg_btts >= 58 and avg_over >= 58):
            return (
                "💥 EXPLOSION",
                "STRONG Over 2.5 & BTTS",
                f"🔥 OVER 2.5 & BTTS (expected {expected_goals} goals)"
            )
        
        # DEFENSIVE LOCK: Both teams defensive
        elif (match_input['home_da'] <= 70 and match_input['away_da'] <= 70 and
              avg_btts <= 50 and avg_over <= 48):
            return (
                "🔒 LOCK UNDER",
                "STRONG Under 2.5, likely no BTTS",
                f"✅ UNDER 2.5 (expected {expected_goals} goals)"
            )
        
        # MISMATCH: One team dominant
        elif da_diff >= 20 and (avg_btts >= 55 or avg_over >= 55):
            dominant_team = "Home" if match_input['home_da'] > match_input['away_da'] else "Away"
            return (
                "⚖️ MISMATCH",
                f"{dominant_team} team likely to dominate",
                f"⚠️ Watch {dominant_team} to score 2+"
            )
        
        # HIGH SCORING POTENTIAL
        elif expected_goals >= 2.9:
            return (
                "🔥 HIGH SCORING",
                "Goals likely, consider Over 2.5",
                f"⚽ Over 2.5 lean ({expected_goals} goals expected)"
            )
        
        # LOW SCORING POTENTIAL
        elif expected_goals <= 2.5:
            return (
                "📊 LOW SCORING",
                "Under 2.5 looks good",
                f"✅ Under 2.5 lean ({expected_goals} goals expected)"
            )
        
        # BORDERLINE
        else:
            return (
                "🔄 HYBRID",
                "Watch live - 50/50 match",
                "⚖️ No strong lean, watch first 30 mins"
            )
    
    def _calculate_score(self, match_input):
        """Calculate explosion score (0-13)"""
        score = 0
        
        # DA points
        if match_input['home_da'] >= 75 and match_input['away_da'] >= 75:
            score += 3
        elif match_input['home_da'] >= 75 or match_input['away_da'] >= 75:
            score += 2
        
        # BTTS points
        avg_btts = (match_input['home_btts'] + match_input['away_btts']) / 2
        if avg_btts >= 60:
            score += 3
        elif avg_btts >= 55:
            score += 2
        elif avg_btts >= 50:
            score += 1
        
        # Over points
        avg_over = (match_input['home_over'] + match_input['away_over']) / 2
        if avg_over >= 60:
            score += 3
        elif avg_over >= 55:
            score += 2
        elif avg_over >= 50:
            score += 1
        
        # Context
        score += match_input.get('elite', 0) * 1
        score += match_input.get('derby', 0) * 1
        score += match_input.get('relegation', 0) * 1
        
        return min(score, 13)
    
    def _fallback_prediction(self, match_input):
        """Fallback when no similar matches found"""
        avg_da = (match_input['home_da'] + match_input['away_da']) / 2
        avg_btts = (match_input['home_btts'] + match_input['away_btts']) / 2
        avg_over = (match_input['home_over'] + match_input['away_over']) / 2
        
        # Simple rule-based fallback
        if avg_da >= 75 and avg_btts >= 55 and avg_over >= 55:
            expected_goals = 3.1
            btts_prob = 60
        elif avg_da <= 65 and avg_btts <= 48 and avg_over <= 48:
            expected_goals = 2.4
            btts_prob = 45
        else:
            expected_goals = 2.7
            btts_prob = 52
        
        match_type, action, prediction = self._classify_match(
            match_input, expected_goals, btts_prob
        )
        
        return {
            'expected_goals': round(expected_goals, 1),
            'btts_probability': round(btts_prob, 1),
            'confidence': 50,
            'match_type': match_type,
            'action': action,
            'prediction': prediction,
            'score': self._calculate_score(match_input),
            'max_score': 13,
            'similar_matches': [],
            'avg_similarity': 0,
            'sample_size': 0,
            'note': "🆕 New pattern - learning from this match"
        }
    
    def learn(self, match_input, actual_goals, actual_btts):
        """Add new match to knowledge base"""
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
            'btts': actual_btts
        }
        
        self.knowledge_base.append(new_match)
        self._build_initial_clusters()  # Reclustering would be more sophisticated in production
        
        return len(self.knowledge_base)

# ============================================================================
# UI COMPONENTS
# ============================================================================

def main():
    st.title("🎯 Mismatch Hunter v7.0")
    st.markdown("### Pure Number Logic - No League Bias")
    
    # Initialize hunter
    if 'hunter' not in st.session_state:
        st.session_state.hunter = PureNumberHunter()
    
    # Sidebar stats
    with st.sidebar:
        st.header("📊 Knowledge Base")
        st.metric("Total Patterns", len(st.session_state.hunter.knowledge_base))
        
        # Pattern distribution
        st.subheader("Pattern Clusters")
        for cluster, data in st.session_state.hunter.pattern_clusters.items():
            st.metric(
                cluster.title(),
                len(data['matches']),
                f"{data['min_goals']}-{data['max_goals']} goals"
            )
        
        st.markdown("---")
        st.markdown(""**
        **The 11 Numbers:**
        - Home/Away DA (0-100)
        - Home/Away BTTS% (0-100)
        - Home/Away Over% (0-100)
        - Elite (0/1)
        - Derby (0/1)
        - Relegation (0/1)
        - Goals (actual)
        - BTTS (actual)
        """)
    
    # Main input form
    with st.form("match_input"):
        st.subheader("📋 Enter Match Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🏠 HOME TEAM**")
            home_da = st.number_input("DA (Dangerous Attacks)", 0, 100, 50)
            home_btts = st.number_input("BTTS %", 0, 100, 50)
            home_over = st.number_input("Over 2.5 %", 0, 100, 50)
        
        with col2:
            st.markdown("**✈️ AWAY TEAM**")
            away_da = st.number_input("DA (Dangerous Attacks)", 0, 100, 50, key="away_da")
            away_btts = st.number_input("BTTS %", 0, 100, 50, key="away_btts")
            away_over = st.number_input("Over 2.5 %", 0, 100, 50, key="away_over")
        
        with col3:
            st.markdown("**🎯 CONTEXT**")
            elite = st.checkbox("⭐ Elite Team Present")
            derby = st.checkbox("🏆 Derby Match")
            relegation = st.checkbox("⚠️ Relegation Battle")
        
        submitted = st.form_submit_button("🎯 GENERATE PREDICTION", use_container_width=True)
    
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
        
        # Get prediction
        result = st.session_state.hunter.predict(match_input)
        
        # Display results
        st.markdown("---")
        
        # Main prediction card
        color_map = {
            '💥 EXPLOSION': '#FF4B4B',
            '🔒 LOCK UNDER': '#2E7D32',
            '⚖️ MISMATCH': '#FFA500',
            '🔥 HIGH SCORING': '#FF6B6B',
            '📊 LOW SCORING': '#4CAF50',
            '🔄 HYBRID': '#808080'
        }
        
        bg_color = color_map.get(result['match_type'].split()[0], '#F0F0F0')
        
        st.markdown(f"""
        <div style="background-color: {bg_color}20; padding: 30px; border-radius: 15px; border: 3px solid {bg_color};">
            <h1 style="text-align: center; margin: 0; font-size: 48px;">{result['match_type']}</h1>
            <h2 style="text-align: center; margin: 10px 0; font-size: 32px;">{result['prediction']}</h2>
            
            <div style="display: flex; justify-content: center; gap: 50px; margin: 30px 0;">
                <div style="text-align: center;">
                    <p style="font-size: 18px; margin: 0;">Expected Goals</p>
                    <p style="font-size: 42px; font-weight: bold; margin: 0;">{result['expected_goals']}</p>
                </div>
                <div style="text-align: center;">
                    <p style="font-size: 18px; margin: 0;">BTTS Probability</p>
                    <p style="font-size: 42px; font-weight: bold; margin: 0;">{result['btts_probability']}%</p>
                </div>
                <div style="text-align: center;">
                    <p style="font-size: 18px; margin: 0;">Confidence</p>
                    <p style="font-size: 42px; font-weight: bold; margin: 0;">{result['confidence']}%</p>
                </div>
            </div>
            
            <div style="display: flex; justify-content: center; margin: 20px 0;">
                <div style="background-color: white; padding: 15px 30px; border-radius: 10px;">
                    <p style="font-size: 24px; font-weight: bold; margin: 0;">{result['action']}</p>
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                <div><strong>Explosion Score:</strong> {result['score']}/{result['max_score']}</div>
                <div><strong>Pattern Similarity:</strong> {result['avg_similarity']}%</div>
                <div><strong>Similar Matches:</strong> {result['sample_size']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Similar matches
        if result['similar_matches']:
            st.subheader("📊 Similar Historical Patterns")
            
            cols = st.columns(3)
            for i, (sim, match) in enumerate(result['similar_matches']):
                with cols[i]:
                    similarity_pct = int(sim * 100)
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 10px; padding: 15px;">
                        <h4 style="margin: 0 0 10px 0;">{similarity_pct}% Similar</h4>
                        <p>DA: {match['home_da']}/{match['away_da']}</p>
                        <p>BTTS: {match['home_btts']}%/{match['away_btts']}%</p>
                        <p>Over: {match['home_over']}%/{match['away_over']}%</p>
                        <p style="font-size: 20px; font-weight: bold; margin: 10px 0 0 0;">
                            {match['goals']} goals • {'✅ BTTS' if match['btts'] else '❌ No BTTS'}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Learning section
        st.markdown("---")
        st.subheader("📚 Teach The System")
        
        col_l1, col_l2, col_l3 = st.columns([2, 1, 2])
        
        with col_l1:
            actual_goals = st.number_input("Actual Goals", 0, 10, 2)
        
        with col_l2:
            actual_btts = st.checkbox("BTTS Happened?")
        
        with col_l3:
            if st.button("📥 Learn From This Match", use_container_width=True):
                total = st.session_state.hunter.learn(
                    match_input, 
                    actual_goals, 
                    1 if actual_btts else 0
                )
                st.success(f"✅ Match added to knowledge base! Total patterns: {total}")
                st.balloons()
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>🎯 <strong>Mismatch Hunter v7.0</strong> - Pure Number Logic</p>
        <p>No league names • No country bias • Just 11 numbers predicting football</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
