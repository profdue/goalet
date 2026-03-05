class TierBasedHunter:
    """
    League-agnostic pattern recognition using TIERS instead of raw numbers
    Each value converted to 1-5 tier based on football meaning
    """
    
    def __init__(self):
        self.knowledge_base = self._initialize_knowledge()
        self.pattern_clusters = defaultdict(list)
        self.league_adjustments = defaultdict(lambda: 0.0)
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
            # PATTERN 1: [1,2,2,2,1,1] - ELITE ATTACK (Bundesliga style)
            {'home_da': 82, 'away_da': 78, 'home_btts': 62, 'away_btts': 62,
             'home_over': 65, 'away_over': 65, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 3.2, 'btts': 1, 'league': 'Bundesliga', 
             'home_team': 'Bayern', 'away_team': 'Dortmund'},
            
            # PATTERN 2: [2,2,2,2,2,3] - STRONG BOTH (EPL top 4)
            {'home_da': 76, 'away_da': 72, 'home_btts': 58, 'away_btts': 56,
             'home_over': 56, 'away_over': 54, 'elite': 1, 'derby': 0, 'relegation': 0,
             'goals': 2.9, 'btts': 1, 'league': 'EPL',
             'home_team': 'Liverpool', 'away_team': 'Arsenal'},
            
            # PATTERN 3: [3,3,3,3,3,3] - MIDTABLE MEDIOCRITY
            {'home_da': 55, 'away_da': 52, 'home_btts': 52, 'away_btts': 50,
             'home_over': 52, 'away_over': 50, 'elite': 0, 'derby': 0, 'relegation': 0,
             'goals': 2.6, 'btts': 0, 'league': 'La Liga',
             'home_team': 'Valencia', 'away_team': 'Real Sociedad'},
            
            # PATTERN 4: [4,4,4,4,4,4] - WEAK BOTH (Relegation battle)
            {'home_da': 42, 'away_da': 40, 'home_btts': 42, 'away_btts': 40,
             'home_over': 40, 'away_over': 38, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 2.2, 'btts': 0, 'league': 'Serie A',
             'home_team': 'Lecce', 'away_team': 'Salernitana'},
            
            # PATTERN 5: [5,5,5,5,5,5] - DEFENSIVE GRIND
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
            
            # PATTERN 8: [4,4,5,1,4,3] - AUSTRIAN SPECIAL (Home weak attack, away always scores)
            {'home_da': 38, 'away_da': 37, 'home_btts': 35, 'away_btts': 65,
             'home_over': 40, 'away_over': 45, 'elite': 0, 'derby': 0, 'relegation': 1,
             'goals': 3.8, 'btts': 1, 'league': 'Austria',
             'home_team': 'Blau Weiss', 'away_team': 'WSG Tirol'},
            
            # PATTERN 9: [2,2,1,3,2,3] - MIXED ATTACK (Common)
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
            # Parse signature back to list
            try:
                sig_tiers = [int(x.strip()) for x in sig.strip('[]').split(',')]
            except:
                continue
            
            # Ensure we have 6 tiers
            if len(sig_tiers) != 6:
                continue
            
            # Calculate tier difference (lower = more similar)
            diff = 0
            for a, b in zip(input_tiers, sig_tiers):
                diff += abs(a - b)
            
            # Convert diff to similarity (0 diff = 1.0, max diff 24 = 0.0)
            similarity = max(0, 1 - (diff / 24))
            
            for match in matches:
                # Add index as tiebreaker to avoid comparing dicts
                similarities.append((similarity, len(similarities), match))
        
        # Sort by similarity first, then by index
        similarities.sort(reverse=True)
        
        # Return without the index
        return [(sim, match) for sim, _, match in similarities[:k]]
    
    def predict(self, match_input):
        """Generate prediction based on tier patterns"""
        
        # Find similar matches
        similar = self.find_similar_matches(match_input)
        
        if not similar:
            return self._fallback_prediction(match_input)
        
        # Calculate weighted averages
        total_weight = 0
        weighted_goals = 0
        weighted_btts = 0
        league_counts = defaultdict(int)
        
        for sim, match in similar:
            weight = sim ** 2
            total_weight += weight
            weighted_goals += weight * match['goals']
            weighted_btts += weight * match['btts']
            league_counts[match.get('league', 'Unknown')] += 1
        
        if total_weight > 0:
            expected_goals = weighted_goals / total_weight
            btts_prob = (weighted_btts / total_weight) * 100
        else:
            expected_goals = 2.5
            btts_prob = 50
        
        # Get most common league in similar matches
        primary_league = max(league_counts, key=league_counts.get) if league_counts else "Unknown"
        
        # Calculate confidence
        avg_similarity = np.mean([s for s, _ in similar])
        sample_size = len(similar)
        
        confidence = (avg_similarity * 0.5 + min(sample_size / 10, 0.3)) * 100
        confidence = min(confidence + 20, 95)  # Base confidence
        
        # Determine match type and action
        match_type, action, prediction = self._classify_match(
            match_input, expected_goals, btts_prob, primary_league
        )
        
        # Calculate explosion score
        score = self._calculate_score(match_input)
        
        # Get tier signature
        tier_signature = self._get_tier_signature(match_input)
        
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
            'sample_size': sample_size,
            'tier_signature': tier_signature,
            'primary_league': primary_league
        }
    
    def _classify_match(self, match_input, expected_goals, btts_prob, primary_league):
        """Classify match type based on tiers and expected outcomes"""
        
        tiers = self._get_tier_signature(match_input)
        
        # Pattern 1: ELITE ATTACK [1,1,1,1,1,1] or similar
        if (tiers[0] <= 2 and tiers[1] <= 2 and 
            tiers[2] <= 2 and tiers[3] <= 2 and 
            tiers[4] <= 2 and tiers[5] <= 2):
            return (
                "💥 EXPLOSION",
                "STRONG Over 2.5 and BTTS",
                f"🔥 OVER 2.5 & BTTS ({expected_goals} goals expected)"
            )
        
        # Pattern 2: DEFENSIVE GRIND [4+,4+,4+,4+,4+,4+]
        if (tiers[0] >= 4 and tiers[1] >= 4 and 
            tiers[2] >= 4 and tiers[3] >= 4 and 
            tiers[4] >= 4 and tiers[5] >= 4):
            return (
                "🔒 LOCK UNDER",
                "STRONG Under 2.5, likely no BTTS",
                f"✅ UNDER 2.5 ({expected_goals} goals expected)"
            )
        
        # Pattern 3: MISMATCH (one team much stronger in DA)
        if abs(tiers[0] - tiers[1]) >= 2:
            dominant = "Home" if tiers[0] < tiers[1] else "Away"
            return (
                "⚖️ MISMATCH",
                f"{dominant} team likely to dominate, watch live",
                f"⚠️ {dominant} advantage, but goals uncertain"
            )
        
        # Pattern 4: AUSTRIAN SPECIAL [4,4,5,1,4,3]
        if (tiers[0] == 4 and tiers[1] == 4 and tiers[2] == 5 and 
            tiers[3] == 1 and tiers[4] == 4 and tiers[5] == 3):
            return (
                "🎢 AUSTRIAN SPECIAL",
                "CHAOS MATCH - Away always scores, home might surprise",
                f"⚽ BTTS likely, goals expected ({expected_goals})"
            )
        
        # Based on expected goals
        if expected_goals >= 3.0:
            return (
                "🔥 HIGH SCORING",
                "Goals likely, consider Over 2.5",
                f"⚽ Over 2.5 lean ({expected_goals} goals)"
            )
        elif expected_goals <= 2.3:
            return (
                "📊 LOW SCORING",
                "Under 2.5 looks good",
                f"✅ Under 2.5 lean ({expected_goals} goals)"
            )
        else:
            return (
                "🔄 HYBRID",
                "Watch live - 50/50 match",
                "⚖️ No strong lean, watch first 30 mins"
            )
    
    def _calculate_score(self, match_input):
        """Calculate explosion score (0-13)"""
        score = 0
        tiers = self._get_tier_signature(match_input)
        
        # Score based on tiers (lower tiers = higher score)
        score += (6 - tiers[0])  # Home DA
        score += (6 - tiers[1])  # Away DA
        score += (6 - tiers[2])  # Home BTTS
        score += (6 - tiers[3])  # Away BTTS
        score += (6 - tiers[4])  # Home Over
        score += (6 - tiers[5])  # Away Over
        
        # Context
        score += match_input.get('elite', 0) * 2
        score += match_input.get('derby', 0) * 1
        score += match_input.get('relegation', 0) * 1
        
        return min(score, 13)
    
    def _fallback_prediction(self, match_input):
        """Fallback when no similar matches found"""
        tiers = self._get_tier_signature(match_input)
        
        # Simple rule-based fallback
        if all(t <= 2 for t in tiers):
            expected_goals = 3.2
            btts_prob = 65
        elif all(t >= 4 for t in tiers):
            expected_goals = 2.0
            btts_prob = 35
        else:
            expected_goals = 2.6
            btts_prob = 50
        
        match_type, action, prediction = self._classify_match(
            match_input, expected_goals, btts_prob, "Unknown"
        )
        
        return {
            'expected_goals': round(expected_goals, 1),
            'btts_probability': round(btts_prob, 1),
            'confidence': 50,
            'match_type': "🆕 " + match_type,
            'action': action,
            'prediction': prediction,
            'score': self._calculate_score(match_input),
            'max_score': 13,
            'similar_matches': [],
            'avg_similarity': 0,
            'sample_size': 0,
            'tier_signature': tiers,
            'primary_league': "New Pattern",
            'note': "🆕 New tier pattern - learning from this match"
        }
    
    def learn(self, match_input, actual_goals, actual_btts, home_team, away_team, league="Unknown"):
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
            'btts': actual_btts,
            'league': league,
            'home_team': home_team,
            'away_team': away_team
        }
        
        self.knowledge_base.append(new_match)
        
        # Update clusters
        signature = str(self._get_tier_signature(new_match))
        self.pattern_clusters[signature].append(new_match)
        
        return len(self.knowledge_base)
