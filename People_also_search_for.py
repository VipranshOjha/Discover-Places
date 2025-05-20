from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from model import (
    WeatherData, UserInteraction,
    get_time_category, get_day_category, get_seasonal_category,
    get_weather_from_api, get_weather_based_interest,
    get_time_based_interest, get_day_based_interest, get_seasonal_interest
)

class CollaborativeRecommender:
    def __init__(self):
        self.user_interactions: List[UserInteraction] = []
        self.user_interest_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.user_similarity_matrix: Dict[str, Dict[str, float]] = {}
    
    def add_interaction(self, interaction: UserInteraction):
        """Add a new user interaction to the system"""
        self.user_interactions.append(interaction)
        # Update user-interest matrix (count occurrences)
        self.user_interest_matrix[interaction.user_id][interaction.interest] += 1
    
    def _calculate_user_similarity(self):
        """Calculate similarity between users based on their interest patterns"""
        # Convert user-interest matrix to a format suitable for cosine similarity
        users = list(self.user_interest_matrix.keys())
        interests = set()
        for user_interests in self.user_interest_matrix.values():
            interests.update(user_interests.keys())
        
        # Create user-interest matrix
        matrix = np.zeros((len(users), len(interests)))
        interest_to_idx = {interest: idx for idx, interest in enumerate(interests)}
        
        for i, user in enumerate(users):
            for interest, count in self.user_interest_matrix[user].items():
                matrix[i, interest_to_idx[interest]] = count
        
        # Calculate cosine similarity between users
        similarity_matrix = cosine_similarity(matrix)
        
        # Store similarities in a more accessible format
        for i, user1 in enumerate(users):
            self.user_similarity_matrix[user1] = {}
            for j, user2 in enumerate(users):
                if i != j:  # Don't include self-similarity
                    self.user_similarity_matrix[user1][user2] = similarity_matrix[i, j]
    
    def get_collaborative_recommendations(self, user_id: str, n_recommendations: int = 3) -> List[Tuple[str, float]]:
        """Get recommendations based on similar users' preferences"""
        if not self.user_similarity_matrix:
            self._calculate_user_similarity()
        
        if user_id not in self.user_similarity_matrix:
            return []
        
        # Get similar users
        similar_users = sorted(
            self.user_similarity_matrix[user_id].items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_recommendations]
        
        # Get interests from similar users
        recommendations = defaultdict(float)
        for similar_user, similarity in similar_users:
            for interest, count in self.user_interest_matrix[similar_user].items():
                recommendations[interest] += similarity * count
        
        # Sort and return top recommendations
        return sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

def recommend_interest_and_pincode(
    searches: List[Dict],
    user_id: Optional[str] = None,
    collaborative_recommender: Optional[CollaborativeRecommender] = None,
    latitude: float = 28.6139,
    longitude: float = 77.2090
) -> Optional[Tuple[str, str]]:
    """
    Given a list of recent searches and optional user_id for collaborative filtering,
    return the most likely (interest, pincode) tuple.
    Returns None if not enough data.
    """
    if not searches:
        return None

    # Extract basic data
    interests = [s['interest'] for s in searches if 'interest' in s]
    pincodes = [s['pincode'] for s in searches if 'pincode' in s]
    
    if not interests or not pincodes:
        return None

    # Get current time-based factors
    current_time = datetime.now()
    time_category = get_time_category(current_time.hour)
    day_category = get_day_category(current_time.weekday())
    seasonal_category = get_seasonal_category(current_time.month)
    
    # Get real weather data
    weather_data = get_weather_from_api(latitude, longitude)
    weather_based_interest = get_weather_based_interest(weather_data)

    # Get context-based interests
    time_based_interest = get_time_based_interest(time_category)
    day_based_interest = get_day_based_interest(day_category)
    seasonal_interest = get_seasonal_interest(seasonal_category)

    # Combine content-based interests
    content_based_interests = interests * 2 + [
        time_based_interest,
        day_based_interest,
        seasonal_interest,
        weather_based_interest
    ]

    # Add collaborative filtering if available
    if user_id and collaborative_recommender:
        # Get collaborative recommendations
        collab_recommendations = collaborative_recommender.get_collaborative_recommendations(user_id)
        
        # Add collaborative recommendations with high weight
        for interest, score in collab_recommendations:
            content_based_interests.extend([interest] * int(score * 2))
        
        # Add the current search to collaborative recommender
        for search in searches:
            if 'interest' in search and 'pincode' in search:
                interaction = UserInteraction(
                    user_id=user_id,
                    interest=search['interest'],
                    pincode=search['pincode'],
                    timestamp=current_time
                )
                collaborative_recommender.add_interaction(interaction)
    
    # Most common interest and pincode
    interest = Counter(content_based_interests).most_common(1)[0][0]
    pincode = Counter(pincodes).most_common(1)[0][0]
    
    return interest, pincode

# Example usage
if __name__ == "__main__":
    # Create collaborative recommender
    collab_recommender = CollaborativeRecommender()
    
    # Add some example user interactions
    example_interactions = [
        UserInteraction("user1", "food", "110001", datetime.now(), 1.0),
        UserInteraction("user1", "shopping", "110001", datetime.now(), 1.0),
        UserInteraction("user2", "food", "110002", datetime.now(), 1.0),
        UserInteraction("user2", "entertainment", "110002", datetime.now(), 1.0),
        UserInteraction("user3", "shopping", "110001", datetime.now(), 1.0),
        UserInteraction("user3", "entertainment", "110001", datetime.now(), 1.0),
    ]
    
    for interaction in example_interactions:
        collab_recommender.add_interaction(interaction)
    
    # Example search history
    example_searches = [
        {'interest': 'food', 'pincode': '110001'},
        {'interest': 'shopping', 'pincode': '110001'},
        {'interest': 'entertainment', 'pincode': '110002'}
    ]
    
    print("Testing recommendation system with both content-based and collaborative filtering...")
    
    # Get recommendation with collaborative filtering
    result = recommend_interest_and_pincode(
        example_searches,
        user_id="user1",
        collaborative_recommender=collab_recommender
    )
    
    if result:
        interest, pincode = result
        print(f"\nFinal Recommendation:")
        print(f"Recommended interest: {interest}")
        print(f"Recommended pincode: {pincode}")
        
        # Show collaborative recommendations
        print("\nCollaborative Recommendations for user1:")
        collab_recs = collab_recommender.get_collaborative_recommendations("user1")
        for interest, score in collab_recs:
            print(f"{interest}: {score:.2f}")
    else:
        print("Not enough data to make a recommendation")
