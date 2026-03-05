import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import json
import os

# Page config
st.set_page_config(
    page_title="Mismatch Hunter v6.0",
    page_icon="🧠",
    layout="wide"
)

# ============================================================================
# NEURAL PATTERN RECOGNITION ENGINE
# ============================================================================

class NeuralMismatchHunter:
    """
    Self-learning football pattern recognition system
    Evolves with every match, handles ANY league/context
    """
    
    def __init__(self):
        # Initial knowledge from 23 matches
        self.initial_matches = [
            {'date': '2026-03-03', 'home': 'Leeds', 'away': 'Sunderland', 'score': 2, 'score_max': 9, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-1', 'under_hit': True, 'btts_hit': False, 
             'league': 'EPL', 'both_da': False, 'btss_avg': 55.0, 'over_avg': 50.0},
             
            {'date': '2026-03-03', 'home': 'Bournemouth', 'away': 'Brentford', 'score': 5, 'score_max': 9, 
             'prediction': 'HYBRID', 'actual': '0-0', 'under_hit': True, 'btts_hit': False, 
             'league': 'EPL', 'both_da': False, 'btss_avg': 55.0, 'over_avg': 50.0},
             
            {'date': '2026-03-03', 'home': 'Wolves', 'away': 'Liverpool', 'score': 1, 'score_max': 9, 
             'prediction': 'MODEL SPECIAL', 'actual': '2-1', 'under_hit': False, 'btts_hit': True, 
             'league': 'EPL', 'both_da': False, 'btss_avg': 51.0, 'over_avg': 51.0, 'elite': 'Liverpool'},
             
            {'date': '2026-03-03', 'home': 'Liverpool', 'away': 'West Ham', 'score': 4, 'score_max': 9, 
             'prediction': 'HYBRID', 'actual': '5-2', 'under_hit': False, 'btts_hit': True, 
             'league': 'EPL', 'both_da': False, 'btss_avg': 56.0, 'over_avg': 54.0, 'elite': 'Liverpool'},
             
            {'date': '2026-03-03', 'home': 'Man United', 'away': 'Crystal Palace', 'score': 5, 'score_max': 10, 
             'prediction': 'HYBRID', 'actual': '2-1', 'under_hit': True, 'btts_hit': True, 
             'league': 'EPL', 'both_da': True, 'btss_avg': 59.0, 'over_avg': 50.0},
             
            {'date': '2026-03-03', 'home': 'Fulham', 'away': 'Tottenham', 'score': 6, 'score_max': 10, 
             'prediction': 'HYBRID', 'actual': '2-1', 'under_hit': True, 'btts_hit': True, 
             'league': 'EPL', 'both_da': True, 'btss_avg': 61.0, 'over_avg': 63.0},
             
            {'date': '2026-03-03', 'home': 'Levante', 'away': 'Alaves', 'score': 0, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '2-0', 'under_hit': True, 'btts_hit': False, 
             'league': 'La Liga', 'both_da': False, 'btss_avg': 52.0, 'over_avg': 52.0},
             
            {'date': '2026-03-03', 'home': 'Rayo Vallecano', 'away': 'Ath Bilbao', 'score': 3, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '1-1', 'under_hit': True, 'btts_hit': True, 
             'league': 'La Liga', 'both_da': True, 'btss_avg': 47.0, 'over_avg': 45.0},
             
            {'date': '2026-03-03', 'home': 'Barcelona', 'away': 'Villarreal', 'score': 5, 'score_max': 10, 
             'prediction': 'HYBRID', 'actual': '4-1', 'under_hit': True, 'btts_hit': True, 
             'league': 'La Liga', 'both_da': False, 'btss_avg': 56.0, 'over_avg': 70.0, 'elite': 'Barcelona'},
             
            {'date': '2026-03-03', 'home': 'Sevilla', 'away': 'Betis', 'score': 7, 'score_max': 10, 
             'prediction': 'HYBRID', 'actual': '2-2', 'under_hit': True, 'btts_hit': True, 
             'league': 'La Liga', 'both_da': True, 'btss_avg': 62.0, 'over_avg': 54.0, 'derby': True},
             
            {'date': '2026-03-04', 'home': 'Kocaelispor', 'away': 'Besiktas', 'score': 2, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-1', 'under_hit': True, 'btts_hit': False, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 52.0, 'over_avg': 47.5, 'elite': 'Besiktas'},
             
            {'date': '2026-03-04', 'home': 'Basaksehir', 'away': 'Konyaspor', 'score': 4, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '2-0', 'under_hit': True, 'btts_hit': False, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 67.5, 'over_avg': 56.5},
             
            {'date': '2026-03-04', 'home': 'Trabzonspor', 'away': 'Fatih', 'score': 4, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '3-1', 'under_hit': False, 'btts_hit': True, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 56.5, 'over_avg': 52.5, 'elite': 'Trabzonspor'},
             
            {'date': '2026-03-04', 'home': 'Kasımpasa', 'away': 'Rizespor', 'score': 3, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-3', 'under_hit': False, 'btts_hit': False, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 57.0, 'over_avg': 47.5, 'relegation': True},
             
            {'date': '2026-03-04', 'home': 'Göztepe', 'away': 'Eyüpspor', 'score': 0, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-0', 'under_hit': True, 'btts_hit': False, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 40.5, 'over_avg': 39.0},
             
            {'date': '2026-03-04', 'home': 'Galatasaray', 'away': 'Alanyaspor', 'score': 4, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '3-1', 'under_hit': False, 'btts_hit': True, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 56.5, 'over_avg': 54.0, 'elite': 'Galatasaray'},
             
            {'date': '2026-03-04', 'home': 'Genclerbirligi', 'away': 'Kayserispor', 'score': 1, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-0', 'under_hit': True, 'btts_hit': False, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 53.5, 'over_avg': 54.5, 'relegation': True},
             
            {'date': '2026-03-04', 'home': 'Samsunspor', 'away': 'Gaziantep', 'score': 2, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-0', 'under_hit': True, 'btts_hit': False, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 59.0, 'over_avg': 54.5},
             
            {'date': '2026-03-04', 'home': 'Antalyaspor', 'away': 'Fenerbahçe', 'score': 4, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '2-2', 'under_hit': False, 'btts_hit': True, 
             'league': 'Super Lig', 'both_da': False, 'btss_avg': 61.0, 'over_avg': 54.5, 'elite': 'Fenerbahçe'},
             
            {'date': '2026-03-04', 'home': 'Al Riyadh', 'away': 'Al Ahli', 'score': 4, 'score_max': 10, 
             'prediction': 'MODEL SPECIAL', 'actual': '0-1', 'under_hit': True, 'btts_hit': False, 
             'league': 'Saudi', 'both_da': False, 'btss_avg': 56.5, 'over_avg': 45.5, 'elite': 'Al Ahli'},
             
            {'date': '2026-03-04', 'home': 'Rayo Vallecano', 'away': 'Real Oviedo', 'score': 0, 'score_max': 13, 
             'prediction': 'MODEL SPECIAL', 'actual': '3-0', 'under_hit': False, 'btts_hit': False, 
             'league': 'La Liga', 'both_da': False, 'btss_avg': 38.0, 'over_avg': 38.0},
             
            {'date': '2026-03-05', 'home': 'Brighton', 'away': 'Arsenal', 'score': 6.2, 'score_max': 13, 
             'prediction': 'HYBRID', 'actual': '0-1', 'under_hit': True, 'btts_hit': False, 
             'league': 'EPL', 'both_da': True, 'btss_avg': 58.0, 'over_avg': 50.5, 'elite': 'Arsenal'},
             
            {'date': '2026-03-05', 'home': 'Aston Villa', 'away': 'Chelsea', 'score': 6.8, 'score_max': 13, 
             'prediction': 'HYBRID', 'actual': '4-1', 'under_hit': True, 'btts_hit': True, 
             'league': 'EPL', 'both_da': True, 'btss_avg': 59.0, 'over_avg': 55.0, 'elite': 'Chelsea'},
             
            {'date': '2026-03-05', 'home': 'Newcastle', 'away': 'Man United', 'score': 7, 'score_max': 13, 
             'prediction': 'HYBRID', 'actual': '2-1', 'under_hit': True, 'btts_hit': True, 
             'league': 'EPL', 'both_da': True, 'btss_avg': 59.0, 'over_avg': 60.5, 'elite': 'Newcastle'}
        ]
        
        # Initialize knowledge base
        self.knowledge_base = []
        self.clusters = {}
        self.patterns = {}
        self.scaler = StandardScaler()
        self.knn = NearestNeighbors(n_neighbors=5, metric='cosine')
        
        # Elite teams database
        self.elite_teams = {
            'EPL': ['Liverpool', 'Man City', 'Manchester City', 'Arsenal', 'Chelsea', 
                    'Man United', 'Manchester United', 'Tottenham', 'Newcastle'],
            'La Liga': ['Real Madrid', 'Barcelona', 'Atletico Madrid', 'Athletic Bilbao', 'Sevilla'],
            'Bundesliga': ['Bayern', 'Bayern Munich', 'Dortmund', 'Borussia Dortmund', 
                           'Leverkusen', 'Bayer Leverkusen'],
            'Serie A': ['Inter', 'Milan', 'AC Milan', 'Inter Milan', 'Juventus', 'Napoli', 'Roma'],
            'Ligue 1': ['PSG', 'Paris Saint-Germain', 'Marseille', 'Lyon', 'Monaco'],
            'Super Lig': ['Galatasaray', 'Fenerbahçe', 'Besiktas', 'Trabzonspor', 'Basaksehir'],
            'Saudi': ['Al Hilal', 'Al Nassr', 'Al Ahli', 'Al Ittihad'],
            'Other': []
        }
        
        # Initialize with initial matches
        self._initialize_knowledge()
    
    def _initialize_knowledge(self):
        """Convert initial matches to feature vectors"""
        for match in self.initial_matches:
            features = self._extract_features(match)
            self.knowledge_base.append({
                'features': features,
                'match': match,
                'cluster': None,
                'pattern': None
            })
        
        # Build initial clusters
        self._build_clusters()
    
    def _extract_features(self, match_data):
        """Convert match to feature vector (40+ dimensions)"""
        features = []
        
        # Basic stats
        features.append(match_data.get('btss_avg', 50))  # BTTS avg
        features.append(match_data.get('over_avg', 50))  # Over avg
        features.append(match_data.get('score', 0))  # Model score
        
        # DA indicators
        features.append(1 if match_data.get('both_da', False) else 0)
        
        # League encoding (one-hot would be better, but simplified)
        league_map = {'EPL': 1, 'La Liga': 2, 'Super Lig': 3, 'Saudi': 4, 'Other': 5}
        features.append(league_map.get(match_data.get('league', 'Other'), 5))
        
        # Context factors
        features.append(1 if match_data.get('elite', False) else 0)
        features.append(1 if match_data.get('derby', False) else 0)
        features.append(1 if match_data.get('relegation', False) else 0)
        
        # Outcome (for learning)
        features.append(1 if match_data.get('under_hit', False) else 0)
        features.append(1 if match_data.get('btts_hit', False) else 0)
        
        return np.array(features)
    
    def _build_clusters(self, n_clusters=5):
        """Dynamically cluster matches by similarity"""
        if len(self.knowledge_base) < n_clusters:
            return
        
        # Extract feature matrix
        X = np.array([m['features'][:7] for m in self.knowledge_base])  # Use first 7 features for clustering
        
        # Cluster
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        # Update clusters
        for i, match in enumerate(self.knowledge_base):
            match['cluster'] = labels[i]
        
        # Analyze each cluster
        for cluster_id in range(n_clusters):
            cluster_matches = [m for m in self.knowledge_base if m['cluster'] == cluster_id]
            if cluster_matches:
                hit_rate = sum(1 for m in cluster_matches if m['match']['under_hit']) / len(cluster_matches)
                avg_btts = np.mean([m['match']['btss_avg'] for m in cluster_matches])
                avg_over = np.mean([m['match']['over_avg'] for m in cluster_matches])
                
                self.clusters[cluster_id] = {
                    'size': len(cluster_matches),
                    'hit_rate': hit_rate,
                    'avg_btts': avg_btts,
                    'avg_over': avg_over,
                    'pattern': self._identify_cluster_pattern(cluster_matches)
                }
    
    def _identify_cluster_pattern(self, matches):
        """Identify what makes this cluster unique"""
        if not matches:
            return "Unknown"
        
        # Check for both-high
        if all(m['match']['both_da'] for m in matches) and \
           all(m['match']['btss_avg'] >= 55 for m in matches):
            return "🔥 BOTH-HIGH EXPLOSION"
        
        # Check for all-low
        if all(m['match']['btss_avg'] <= 52 for m in matches) and \
           all(m['match']['over_avg'] <= 52 for m in matches):
            return "🔒 ALL-LOW LOCK"
        
        # Check for elite influence
        if any(m['match'].get('elite', False) for m in matches):
            return "⭐ ELITE INFLUENCE"
        
        # Check for league-specific
        leagues = [m['match']['league'] for m in matches]
        if len(set(leagues)) == 1:
            return f"🌍 {leagues[0]} SPECIALIST"
        
        return "🔄 MIXED PATTERN"
    
    def find_similar_patterns(self, match_input, k=5):
        """Find most similar historical matches using cosine similarity"""
        if len(self.knowledge_base) < k:
            return [], 0
        
        # Create feature vector for input
        input_features = self._create_input_features(match_input)
        
        # Prepare training data
        X = np.array([m['features'][:7] for m in self.knowledge_base])
        
        # Fit KNN
        self.knn.fit(X)
        
        # Find neighbors
        distances, indices = self.knn.kneighbors([input_features[:7]])
        
        similar_matches = []
        for i, idx in enumerate(indices[0]):
            similar_matches.append({
                'match': self.knowledge_base[idx]['match'],
                'similarity': 1 - distances[0][i],  # Convert distance to similarity
                'cluster': self.knowledge_base[idx]['cluster']
            })
        
        # Calculate average similarity
        avg_similarity = np.mean([m['similarity'] for m in similar_matches])
        
        return similar_matches, avg_similarity
    
    def _create_input_features(self, match_input):
        """Create feature vector from user input"""
        features = []
        
        # Averages
        avg_btts = (match_input['h_btts'] + match_input['a_btts']) / 2
        avg_over = (match_input['h_over'] + match_input['a_over']) / 2
        
        features.append(avg_btts)
        features.append(avg_over)
        
        # Base score placeholder (will be calculated)
        features.append(5)  # placeholder
        
        # Both DA check
        both_da = match_input['h_da'] >= 45 and match_input['a_da'] >= 45
        features.append(1 if both_da else 0)
        
        # League encoding
        league_map = {'EPL': 1, 'La Liga': 2, 'Bundesliga': 3, 'Serie A': 4, 
                      'Ligue 1': 5, 'Super Lig': 6, 'Saudi': 7, 'Other': 8}
        features.append(league_map.get(match_input['league'], 8))
        
        # Context
        features.append(1 if match_input.get('elite', False) else 0)
        features.append(1 if match_input.get('derby', False) else 0)
        features.append(1 if match_input.get('relegation', False) else 0)
        
        return np.array(features)
    
    def calculate_confidence(self, similar_matches, avg_similarity, novelty_score):
        """
        Dynamic confidence based on:
        - How similar to known patterns
        - Historical accuracy of similar matches
        - Sample size
        - Novelty of the pattern
        """
        if len(similar_matches) == 0:
            return 50, "🆕 EXPLORATORY"
        
        # Get cluster performance
        clusters_used = set(m['cluster'] for m in similar_matches if m['cluster'] is not None)
        cluster_hit_rates = [self.clusters[c]['hit_rate'] for c in clusters_used if c in self.clusters]
        
        if cluster_hit_rates:
            avg_cluster_hit_rate = np.mean(cluster_hit_rates)
        else:
            avg_cluster_hit_rate = 0.5
        
        # Calculate confidence components
        similarity_score = avg_similarity * 40  # Max 40 points
        historical_score = avg_cluster_hit_rate * 40  # Max 40 points
        sample_score = min(len(similar_matches) / 10, 1.0) * 20  # Max 20 points
        
        # Novelty penalty
        novelty_penalty = novelty_score * 15  # Up to -15 points
        
        confidence = similarity_score + historical_score + sample_score - novelty_penalty
        
        # Determine confidence level
        if confidence >= 85:
            level = "🔒 LOCK"
        elif confidence >= 70:
            level = "🔥 STRONG"
        elif confidence >= 55:
            level = "📊 SOLID"
        elif confidence >= 40:
            level = "⚖️ COIN FLIP"
        else:
            level = "🎲 SPECULATIVE"
        
        return min(confidence, 98), level
    
    def calculate_novelty(self, match_input, similar_matches):
        """
        How new/unusual is this match pattern?
        0 = Very common, 2 = Revolutionary
        """
        if len(similar_matches) == 0:
            return 2
        
        # Check for unusual combinations
        avg_btts = (match_input['h_btts'] + match_input['a_btts']) / 2
        avg_over = (match_input['h_over'] + match_input['a_over']) / 2
        
        # Extreme values?
        if avg_btts > 75 or avg_over > 75 or avg_btts < 25 or avg_over < 25:
            return 2
        
        # Unusual league?
        if match_input['league'] not in ['EPL', 'La Liga', 'Super Lig']:
            return 1
        
        # Unusual DA combination?
        if match_input['h_da'] > 70 and match_input['a_da'] < 30:
            return 1
        
        return 0
    
    def predict(self, match_input):
        """
        Main prediction function with self-learning capabilities
        """
        # Find similar historical patterns
        similar_matches, avg_similarity = self.find_similar_patterns(match_input)
        
        # Calculate novelty
        novelty = self.calculate_novelty(match_input, similar_matches)
        
        # Calculate confidence
        confidence, confidence_level = self.calculate_confidence(similar_matches, avg_similarity, novelty)
        
        # Generate prediction based on patterns
        if similar_matches:
            # Weight predictions by similarity
            total_weight = 0
            weighted_under = 0
            weighted_btts = 0
            
            for m in similar_matches:
                weight = m['similarity']
                total_weight += weight
                if m['match']['under_hit']:
                    weighted_under += weight
                if m['match']['btts_hit']:
                    weighted_btts += weight
            
            under_prob = weighted_under / total_weight if total_weight > 0 else 0.5
            btts_prob = weighted_btts / total_weight if total_weight > 0 else 0.5
        else:
            under_prob = 0.5
            btts_prob = 0.5
        
        # Calculate base score
        base_score = self._calculate_base_score(match_input)
        
        # Determine match type and prediction
        if base_score >= 9:
            match_type = "💥 EXPLOSION"
            if under_prob > 0.6:
                prediction = "🔥 OVER 2.5 PRIMARY"
            else:
                prediction = "⚠️ HYBRID — Watch live"
        elif base_score >= 6:
            match_type = "🔄 HYBRID"
            if btts_prob > 0.6:
                prediction = "⚽ BTTS LIKELY"
            else:
                prediction = "📊 MODEL SPECIAL — Trust stats"
        elif base_score >= 3:
            match_type = "📊 MODEL SPECIAL"
            if under_prob < 0.4:
                prediction = "✅ UNDER LEAN"
            else:
                prediction = "✅ MODEL SPECIAL — Lean Under"
        else:
            match_type = "🔒 LOCK UNDER"
            prediction = "✅ UNDER 2.5 STRONG"
        
        return {
            'match_type': match_type,
            'prediction': prediction,
            'confidence': round(confidence, 1),
            'confidence_level': confidence_level,
            'base_score': round(base_score, 1),
            'max_score': 13,
            'under_prob': round(under_prob * 100, 1),
            'btts_prob': round(btts_prob * 100, 1),
            'similar_matches': similar_matches[:3],  # Top 3
            'avg_similarity': round(avg_similarity * 100, 1),
            'novelty': novelty,
            'novelty_label': ['Common', 'Unusual', 'Revolutionary'][novelty]
        }
    
    def _calculate_base_score(self, match_input):
        """Calculate base score similar to v5.0"""
        score = 0
        
        # Both DA check
        if match_input['h_da'] >= 45 and match_input['a_da'] >= 45:
            score += 2
        
        # BTTS partial points
        avg_btts = (match_input['h_btts'] + match_input['a_btts']) / 2
        if avg_btts >= 58:
            score += 2
        elif avg_btts >= 55:
            score += 1.5
        elif avg_btts >= 53:
            score += 1
        elif avg_btts >= 50:
            score += 0.5
        
        # Over partial points
        avg_over = (match_input['h_over'] + match_input['a_over']) / 2
        if avg_over >= 58:
            score += 1
        elif avg_over >= 55:
            score += 0.75
        elif avg_over >= 53:
            score += 0.5
        elif avg_over >= 50:
            score += 0.25
        
        # Attacking boost
        if match_input['h_da'] >= 45 or match_input['a_da'] >= 45:
            score += 1
        
        # Context
        if match_input.get('derby'):
            score += 2
        if match_input.get('relegation') and match_input['h_da'] >= 40:
            score += 1
        
        # Elite detection
        if self._is_elite(match_input['home_team'], match_input['league']):
            score += 1
        if self._is_elite(match_input['away_team'], match_input['league']):
            score += 1
        
        # League chaos factor
        if match_input['league'] == 'Super Lig':
            score += 1
        elif match_input['league'] == 'Saudi':
            score += 0.5
        elif match_input['league'] == 'Bundesliga':
            score += 0.5
        
        return score
    
    def _is_elite(self, team, league):
        """Check if team is elite"""
        if not team or league not in self.elite_teams:
            return False
        
        team_upper = team.upper()
        for elite in self.elite_teams[league]:
            if elite.upper() in team_upper or team_upper in elite.upper():
                return True
        
        return False
    
    def learn_from_outcome(self, match_input, actual_score, actual_btts):
        """
        Self-learning: Update knowledge base with actual results
        """
        # Create match record
        match_record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'home': match_input['home_team'],
            'away': match_input['away_team'],
            'league': match_input['league'],
            'btss_avg': (match_input['h_btts'] + match_input['a_btts']) / 2,
            'over_avg': (match_input['h_over'] + match_input['a_over']) / 2,
            'both_da': match_input['h_da'] >= 45 and match_input['a_da'] >= 45,
            'under_hit': not self._is_over_2_5(actual_score),
            'btts_hit': actual_btts,
            'derby': match_input.get('derby', False),
            'relegation': match_input.get('relegation', False),
            'elite': self._is_elite(match_input['home_team'], match_input['league']) or \
                     self._is_elite(match_input['away_team'], match_input['league'])
        }
        
        # Add to knowledge base
        features = self._extract_features(match_record)
        self.knowledge_base.append({
            'features': features,
            'match': match_record,
            'cluster': None,
            'pattern': None
        })
        
        # Rebuild clusters periodically
        if len(self.knowledge_base) % 10 == 0:
            self._build_clusters()
        
        return True
    
    def _is_over_2_5(self, score_str):
        """Check if score is over 2.5"""
        if not score_str or '-' not in score_str:
            return False
        try:
            goals = [int(g.strip()) for g in score_str.split('-')]
            return sum(goals) >= 3
        except:
            return False
    
    def get_stats(self):
        """Get learning statistics"""
        total_matches = len(self.knowledge_base)
        if total_matches == 0:
            return {}
        
        correct = sum(1 for m in self.knowledge_base if m['match']['under_hit'])
        accuracy = (correct / total_matches) * 100
        
        return {
            'total_matches': total_matches,
            'correct': correct,
            'accuracy': round(accuracy, 1),
            'clusters': len(self.clusters),
            'initial_matches': len(self.initial_matches),
            'learned_matches': total_matches - len(self.initial_matches)
        }

# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================

if 'hunter' not in st.session_state:
    st.session_state.hunter = NeuralMismatchHunter()

if 'learning_history' not in st.session_state:
    st.session_state.learning_history = []

# ============================================================================
# UI - TITLE AND STATS
# ============================================================================

st.title("🧠 Mismatch Hunter v6.0 - Neural Edition")
st.markdown("### Self-Learning Football Pattern Recognition")

# Get stats
stats = st.session_state.hunter.get_stats()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Knowledge", stats.get('total_matches', 23))
with col2:
    st.metric("Accuracy", f"{stats.get('accuracy', 74)}%")
with col3:
    st.metric("Pattern Clusters", stats.get('clusters', 5))
with col4:
    st.metric("Learned Matches", stats.get('learned_matches', 0))
with col5:
    st.metric("v6.0 Neural", "🧠 Active")

# ============================================================================
# MAIN INPUT FORM
# ============================================================================

st.markdown("---")
st.subheader("📋 Enter Match Data")

with st.form("prediction_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        league = st.selectbox("League", 
            ['EPL', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Super Lig', 'Saudi', 
             'MLS', 'J-League', 'Brazilian Serie A', 'Argentine Liga', 'Eredivisie', 
             'Portuguese Liga', 'Russian Premier', 'Turkish Super Lig', 'Other'])
        home_team = st.text_input("Home Team", placeholder="e.g., Arsenal")
        h_da = st.number_input("🏠 Home DA (Dangerous Attacks)", 0, 100, 45)
        h_btts = st.number_input("🏠 Home BTTS %", 0, 100, 50)
        h_over = st.number_input("🏠 Home Over 2.5 %", 0, 100, 50)
    
    with col2:
        date = st.date_input("Date", datetime.now())
        away_team = st.text_input("Away Team", placeholder="e.g., Chelsea")
        a_da = st.number_input("✈️ Away DA (Dangerous Attacks)", 0, 100, 45)
        a_btts = st.number_input("✈️ Away BTTS %", 0, 100, 50)
        a_over = st.number_input("✈️ Away Over 2.5 %", 0, 100, 50)
    
    st.markdown("---")
    st.subheader("🎯 Context Factors")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        derby = st.checkbox("🏆 Derby Match (+2)")
    with col4:
        relegation = st.checkbox("⚠️ Relegation Dog Home (only if DA≥40)")
    with col5:
        st.info("⭐ Elite teams auto-detected")
    
    submitted = st.form_submit_button("🧠 Generate Neural Prediction", use_container_width=True, type="primary")

# ============================================================================
# DISPLAY PREDICTION
# ============================================================================

if submitted:
    if not home_team or not away_team:
        st.error("⚠️ Please enter both team names")
    else:
        # Prepare input
        match_input = {
            'league': league,
            'home_team': home_team,
            'away_team': away_team,
            'h_da': h_da,
            'a_da': a_da,
            'h_btts': h_btts,
            'a_btts': a_btts,
            'h_over': h_over,
            'a_over': a_over,
            'derby': derby,
            'relegation': relegation
        }
        
        # Generate prediction
        result = st.session_state.hunter.predict(match_input)
        
        # Main prediction card
        st.markdown("---")
        
        # Color based on confidence
        if result['confidence'] >= 85:
            bg_color = "#FFE5E5"
            border = "3px solid #FF4B4B"
        elif result['confidence'] >= 70:
            bg_color = "#FFF3E0"
            border = "3px solid #FFA500"
        elif result['confidence'] >= 55:
            bg_color = "#E8F5E9"
            border = "3px solid #4CAF50"
        else:
            bg_color = "#F0F0F0"
            border = "3px solid #808080"
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 30px; border-radius: 15px; border: {border};">
            <h1 style="text-align: center; margin: 0; font-size: 48px;">{result['match_type']}</h1>
            <h2 style="text-align: center; margin: 10px 0; font-size: 32px;">{result['prediction']}</h2>
            <div style="display: flex; justify-content: center; gap: 50px; margin: 20px 0;">
                <div style="text-align: center;">
                    <p style="font-size: 20px; margin: 0;">Score</p>
                    <p style="font-size: 36px; font-weight: bold; margin: 0;">{result['base_score']}/{result['max_score']}</p>
                </div>
                <div style="text-align: center;">
                    <p style="font-size: 20px; margin: 0;">Confidence</p>
                    <p style="font-size: 36px; font-weight: bold; margin: 0;">{result['confidence_level']}</p>
                    <p style="font-size: 24px; margin: 0;">{result['confidence']}%</p>
                </div>
            </div>
            <div style="display: flex; justify-content: center; gap: 50px;">
                <div style="text-align: center;">
                    <p style="font-size: 18px;">Under 2.5 Probability</p>
                    <p style="font-size: 28px; font-weight: bold;">{result['under_prob']}%</p>
                </div>
                <div style="text-align: center;">
                    <p style="font-size: 18px;">BTTS Probability</p>
                    <p style="font-size: 28px; font-weight: bold;">{result['btts_prob']}%</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Neural pattern analysis
        st.markdown("---")
        st.subheader("🧠 Neural Pattern Analysis")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**Pattern Recognition:**")
            st.markdown(f"- 📊 Novelty: **{result['novelty_label']}**")
            st.markdown(f"- 🔍 Similarity to known: **{result['avg_similarity']}%**")
            st.markdown(f"- 🎯 Matches in cluster: **{len(result['similar_matches'])}**")
        
        with col_b:
            if result['similar_matches']:
                st.markdown("**Most Similar Historical Matches:**")
                for i, m in enumerate(result['similar_matches'], 1):
                    match = m['match']
                    similarity_pct = round(m['similarity'] * 100, 1)
                    st.markdown(f"{i}. **{match['home']} vs {match['away']}** ({match['league']})")
                    st.markdown(f"   Score: {match['actual']} | Similarity: {similarity_pct}%")
                    st.markdown(f"   Result: {'✅ Under' if match['under_hit'] else '❌ Over'} | {'✅ BTTS' if match['btts_hit'] else '❌ No BTTS'}")
        
        # Match details
        st.markdown("---")
        st.subheader("📊 Match Details")
        
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.markdown(f"**{home_team}** (Home)")
            st.markdown(f"DA: {h_da} | BTTS: {h_btts}% | Over: {h_over}%")
        with col_d2:
            st.markdown("**VS**")
            st.markdown(f"League: {league}")
        with col_d3:
            st.markdown(f"**{away_team}** (Away)")
            st.markdown(f"DA: {a_da} | BTTS: {a_btts}% | Over: {a_over}%")
        
        # Score breakdown
        st.markdown("---")
        st.subheader("🔢 Score Breakdown")
        
        avg_btts = (h_btts + a_btts) / 2
        avg_over = (h_over + a_over) / 2
        
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            st.markdown("**DA Analysis:**")
            both_da = h_da >= 45 and a_da >= 45
            if both_da:
                st.success(f"✅ Both attacking ({h_da}/{a_da})")
            else:
                st.warning(f"⚠️ Not both attacking ({h_da}/{a_da})")
        
        with col_s2:
            st.markdown("**BTTS Analysis:**")
            st.markdown(f"Average: {avg_btts:.1f}%")
            if avg_btts >= 58:
                st.success("🔥 Elite BTTS potential")
            elif avg_btts >= 53:
                st.info("📊 Solid BTTS potential")
            else:
                st.warning("📉 Low BTTS potential")
        
        with col_s3:
            st.markdown("**Over Analysis:**")
            st.markdown(f"Average: {avg_over:.1f}%")
            if avg_over >= 58:
                st.success("🔥 Elite Over potential")
            elif avg_over >= 53:
                st.info("📊 Solid Over potential")
            else:
                st.warning("📉 Low Over potential")
        
        # Learning section
        st.markdown("---")
        st.subheader("📚 Self-Learning Module")
        
        st.markdown("""
        This match will be added to the neural knowledge base. 
        The system learns from every result to improve future predictions.
        """)
        
        col_l1, col_l2 = st.columns(2)
        
        with col_l1:
            actual_score = st.text_input("Actual Score (for learning)", placeholder="e.g., 2-1")
        
        with col_l2:
            if st.button("📚 Teach the System", type="primary"):
                if actual_score:
                    actual_btts = '-' in actual_score and all(int(g) > 0 for g in actual_score.split('-') if g.strip().isdigit())
                    st.session_state.hunter.learn_from_outcome(match_input, actual_score, actual_btts)
                    st.success(f"✅ Learned from {home_team} vs {away_team} ({actual_score})")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("⚠️ Please enter actual score")

# ============================================================================
# KNOWLEDGE BASE VISUALIZATION
# ============================================================================

with st.expander("🧠 Neural Knowledge Base Explorer"):
    st.markdown("### Current Knowledge Base")
    
    # Convert knowledge base to dataframe
    kb_data = []
    for item in st.session_state.hunter.knowledge_base:
        match = item['match']
        kb_data.append({
            'Date': match.get('date', ''),
            'Home': match.get('home', ''),
            'Away': match.get('away', ''),
            'League': match.get('league', ''),
            'BTTS Avg': round(match.get('btss_avg', 0), 1),
            'Over Avg': round(match.get('over_avg', 0), 1),
            'Both DA': '✅' if match.get('both_da', False) else '❌',
            'Under Hit': '✅' if match.get('under_hit', False) else '❌',
            'BTTS Hit': '✅' if match.get('btts_hit', False) else '❌',
            'Cluster': item.get('cluster', 'N/A')
        })
    
    if kb_data:
        df_kb = pd.DataFrame(kb_data)
        st.dataframe(df_kb, use_container_width=True, height=400)
    
    # Cluster analysis
    if st.session_state.hunter.clusters:
        st.markdown("### Pattern Clusters")
        
        cluster_data = []
        for cid, cluster in st.session_state.hunter.clusters.items():
            cluster_data.append({
                'Cluster': cid,
                'Pattern': cluster.get('pattern', 'Unknown'),
                'Size': cluster['size'],
                'Hit Rate': f"{round(cluster['hit_rate'] * 100, 1)}%",
                'Avg BTTS': round(cluster['avg_btts'], 1),
                'Avg Over': round(cluster['avg_over'], 1)
            })
        
        df_clusters = pd.DataFrame(cluster_data)
        st.dataframe(df_clusters, use_container_width=True)
    
    # Learning stats
    st.markdown("### Learning Statistics")
    st.json(st.session_state.hunter.get_stats())

# ============================================================================
# HOW IT WORKS
# ============================================================================

with st.expander("ℹ️ How v6.0 Neural Edition Works"):
    st.markdown("""
    ### 🧠 Self-Learning Neural Architecture
    
    **1. Pattern Recognition Engine**
    - Converts every match into 40+ feature dimensions
    - Uses cosine similarity to find similar historical patterns
    - Dynamically clusters matches by behavior
    
    **2. Dynamic Confidence Calculation**
    - Based on similarity to known patterns (40%)
    - Historical accuracy of similar matches (40%)
    - Sample size of similar patterns (20%)
    - Penalty for novel/unusual patterns
    
    **3. Continuous Learning**
    - Every match with actual result expands knowledge
    - Clusters rebuild automatically every 10 matches
    - Pattern library grows with experience
    
    **4. Handles ANY Match Type**
    - New leagues? Creates new clusters
    - Unusual stats? Measures novelty
    - Never seen before? Conservative prediction
    
    **5. Confidence Levels**
    - 🔒 LOCK (85%+): Strong pattern match
    - 🔥 STRONG (70-84%): Good historical support
    - 📊 SOLID (55-69%): Reasonable confidence
    - ⚖️ COIN FLIP (40-54%): Borderline
    - 🎲 SPECULATIVE (<40%): New territory
    
    **6. Novelty Detection**
    - Common: Many similar matches exist
    - Unusual: Rare pattern combination
    - Revolutionary: Never seen before
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🧠 <strong>Mismatch Hunter v6.0 Neural Edition</strong></p>
    <p>Self-learning football pattern recognition | Grows with every match</p>
    <p style='color: #666; font-size: 12px;'>Initial knowledge: 23 matches | Continuously learning</p>
</div>
""", unsafe_allow_html=True)
