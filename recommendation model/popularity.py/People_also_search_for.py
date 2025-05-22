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
from math import log
import random
import pandas as pd
from surprise import Dataset, Reader, SVD
import pickle

class CollaborativeRecommender:
    def __init__(self):
        self.user_interactions: List[UserInteraction] = []
        self.user_interest_matrix: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.user_similarity_matrix: Dict[str, Dict[str, float]] = {}
        self.svd_model = None  # Initialize svd_model
        self.load_model()  # Load model on initialization
    
    def add_interaction(self, interaction: UserInteraction):
        """Add a new user interaction to the system with time decay"""
        self.user_interactions.append(interaction)
        
        # Compute how old the interaction is
        days_ago = (datetime.now() - interaction.timestamp).days
        decay_weight = max(0.1, 1 / (1 + days_ago))  # Prevent zero weight

        # Update user-interest matrix with time-decayed score
        self.user_interest_matrix[interaction.user_id][interaction.interest] += decay_weight
    
    def _calculate_user_similarity(self):
        """Calculate similarity between users based on their interest patterns"""
        users = list(self.user_interest_matrix.keys())
        interests = set()
        for user_interests in self.user_interest_matrix.values():
            interests.update(user_interests.keys())

        # Check if there are enough users and interests
        if not users or not interests:
            print("[INFO] Not enough data to compute user similarity.")
            return  # Exit safely

        # Create user-interest matrix
        matrix = np.zeros((len(users), len(interests)))
        interest_to_idx = {interest: idx for idx, interest in enumerate(interests)}

        for i, user in enumerate(users):
            for interest, count in self.user_interest_matrix[user].items():
                matrix[i, interest_to_idx[interest]] = count

        # Check if the matrix is empty
        if matrix.shape[0] == 0 or matrix.shape[1] == 0:
            print("[INFO] Skipping similarity computation due to empty matrix.")
            return

        # Calculate cosine similarity between users
        similarity_matrix = cosine_similarity(matrix)

        # Store similarities in a more accessible format
        for i, user1 in enumerate(users):
            self.user_similarity_matrix[user1] = {}
            for j, user2 in enumerate(users):
                if i != j:  # Don't include self-similarity
                    self.user_similarity_matrix[user1][user2] = similarity_matrix[i, j]
    
    def get_collaborative_recommendations(self, user_id: str, n_recommendations: int = 3):
        """Get collaborative recommendations for a user based on similar users' interests."""
        if not self.user_interest_matrix:
            print("[WARN] No user interactions yet.")
            return []

        if not self.user_similarity_matrix:
            self._calculate_user_similarity()

        if user_id not in self.user_similarity_matrix:
            print(f"[WARN] No similar users found for user {user_id}")
            return []

        # Get similar users and their interests
        similar_users = sorted(
            self.user_similarity_matrix[user_id].items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_recommendations]

        recommendations = defaultdict(float)

        for similar_user, similarity in similar_users:
            for interest, count in self.user_interest_matrix[similar_user].items():
                recommendations[interest] += similarity * count

        # Sort recommendations by score
        sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

        return sorted_recommendations[:n_recommendations]  # Return top N recommendations

    def save_model(self, path="svd_model.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self.svd_model, f)
            print("[INFO] SVD model saved to disk.")

    def load_model(self, path="svd_model.pkl"):
        try:
            with open(path, "rb") as f:
                self.svd_model = pickle.load(f)
                print("[INFO] SVD model loaded from disk.")
        except FileNotFoundError:
            print("[INFO] No saved model found.")

    def train_svd_model(self):
        data = []

        # Collect interaction data into (user, item, rating) format
        for user_id, interests in self.user_interest_matrix.items():
            for interest, score in interests.items():
                data.append((user_id, interest, score))

        if not data:
            print("[INFO] Not enough data to train SVD.")
            return

        df = pd.DataFrame(data, columns=["user", "item", "rating"])  # <-- Renaming only here
        reader = Reader(rating_scale=(0.1, 5))  # Adjust if needed

        dataset = Dataset.load_from_df(df, reader)
        trainset = dataset.build_full_trainset()

        self.svd_model = SVD()
        self.svd_model.fit(trainset)
        print("[INFO] SVD model trained successfully.")

        self.save_model()  # Save model after training

    def recommend_with_svd(self, user_id: str, top_n: int = 3) -> List[Tuple[str, float]]:
        if not self.svd_model:
            self.train_svd_model()
        if not self.svd_model:
            return []

        known_interests = set(self.user_interest_matrix[user_id].keys())
        all_interests = set()
        for user_data in self.user_interest_matrix.values():
            all_interests.update(user_data.keys())

        candidates = all_interests - known_interests
        predictions = [
            (interest, self.svd_model.predict(user_id, interest).est)
            for interest in candidates
        ]

        return sorted(predictions, key=lambda x: x[1], reverse=True)[:top_n]

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

    # ---- Tunable weights ----
    RECENT_INTEREST_WEIGHT = 3
    CONTEXT_INTEREST_WEIGHT = 1
    COLLAB_INTEREST_WEIGHT = 2 

    # Weighted scoring
    interest_scores = defaultdict(float)

    # 1. Recent interests (e.g., based on pincode match)
    for i in interests:
        interest_scores[i] += RECENT_INTEREST_WEIGHT

    # 2. Contextual signals
    for i in [time_based_interest, day_based_interest, seasonal_interest, weather_based_interest]:
        if i:
            interest_scores[i] += CONTEXT_INTEREST_WEIGHT

    # 3. Collaborative filtering results (with similarity score)
    if user_id and collaborative_recommender:
        collab = collaborative_recommender.recommend_with_svd(user_id, top_n=3)
        
        total_sim = sum(sim for _, sim in collab)
        for interest, sim_score in collab:
            if total_sim > 0:
                interest_scores[interest] += (
                    COLLAB_INTEREST_WEIGHT * (sim_score / total_sim)
                )

        print(collab)

    # --- Compute global interest frequency from collaborative matrix ---
    global_interest_counts = Counter()
    if collaborative_recommender:
        for user_data in collaborative_recommender.user_interest_matrix.values():
            global_interest_counts.update(user_data)

    # --- Apply diversity penalty: divide score by (1 + log(global count)) ---
    for interest in interest_scores:
        global_count = global_interest_counts.get(interest, 1)
        penalty = 1 + log(global_count + 1)
        interest_scores[interest] /= penalty

    # --- Print final interest scores before sorting ---
    print("\nFinal Interest Scores:")
    for i, s in sorted(interest_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"{i}: {s:.2f}")

    # Sort by weighted score, breaking ties randomly
    sorted_interests = sorted(
        interest_scores.items(),
        key=lambda x: (x[1], random.random()),  # break ties randomly
        reverse=True
    )

    # Safely pick best interest and pincode
    top_interest = sorted_interests[0][0] if sorted_interests else None
    top_pincode = Counter(pincodes).most_common(1)[0][0] if pincodes else None

    # Guard against empty recommendations
    if not top_interest or not top_pincode:
        return None  # Nothing confident to return

    return top_interest, top_pincode

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
