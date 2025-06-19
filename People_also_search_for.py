<<<<<<< HEAD
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
from sqlalchemy import func, desc
from sqlalchemy.sql import func, desc
from model import db, UserInteraction

class CollaborativeRecommender:
    def __init__(self):
        self.user_interaction_matrix = None
        self.user_similarity_matrix = None
        self.interest_pincode_matrix = None
        self.interest_pincode_similarity = None
        self.interest_pincode_counts = {}
        self.unique_interests = []
        self.unique_pincodes = []
        self.update_matrices()

    def update_matrices(self):
        # Get all interactions
        interactions = UserInteraction.query.all()
        
        if not interactions:
            return
            
        # Create user-interaction matrix
        user_interactions = {}
        for interaction in interactions:
            user_id = interaction.user_id
            if user_id not in user_interactions:
                user_interactions[user_id] = []
            user_interactions[user_id].append({
                'interest': interaction.interest,
                'pincode': interaction.pincode
            })
            
        # Create interest-pincode matrix
        self.interest_pincode_counts = {}
        for user_id, interactions in user_interactions.items():
            for interaction in interactions:
                key = (interaction['interest'], interaction['pincode'])
                if key not in self.interest_pincode_counts:
                    self.interest_pincode_counts[key] = 0
                self.interest_pincode_counts[key] += 1
                
        # Convert to matrix format
        self.unique_interests = sorted(set(k[0] for k in self.interest_pincode_counts.keys()))
        self.unique_pincodes = sorted(set(k[1] for k in self.interest_pincode_counts.keys()))
        
        self.interest_pincode_matrix = np.zeros((len(self.unique_interests), len(self.unique_pincodes)))
        for (interest, pincode), count in self.interest_pincode_counts.items():
            i = self.unique_interests.index(interest)
            j = self.unique_pincodes.index(pincode)
            self.interest_pincode_matrix[i, j] = count
            
        # Calculate similarity matrices
        if len(self.unique_interests) > 1 and len(self.unique_pincodes) > 1:
            self.interest_pincode_similarity = cosine_similarity(self.interest_pincode_matrix)
        else:
            self.interest_pincode_similarity = np.eye(len(self.unique_interests))

    def get_similar_interests(self, interest, n=3):
        if self.interest_pincode_similarity is None or not self.interest_pincode_counts:
            return []
            
        if interest not in self.unique_interests:
            return []
            
        interest_idx = self.unique_interests.index(interest)
        similarities = self.interest_pincode_similarity[interest_idx]
        
        # Get top N similar interests
        similar_indices = np.argsort(similarities)[::-1][1:n+1]
        return [self.unique_interests[i] for i in similar_indices]

    def get_similar_pincodes(self, pincode, n=3):
        if self.interest_pincode_similarity is None or not self.interest_pincode_counts:
            return []
            
        if pincode not in self.unique_pincodes:
            return []
            
        pincode_idx = self.unique_pincodes.index(pincode)
        similarities = self.interest_pincode_similarity.T[pincode_idx]
        
        # Get top N similar pincodes
        similar_indices = np.argsort(similarities)[::-1][1:n+1]
        return [self.unique_pincodes[i] for i in similar_indices]

def get_context_based_recommendation(searches, latitude, longitude):
    """Get recommendation based on context (time, weather, etc.)"""
    if not searches:
        return None
        
    # Get current time and weather
    current_time = datetime.now()
    hour = current_time.hour
    day = current_time.weekday()
    month = current_time.month
    
    # Get weather data
    weather_data = get_weather_from_api(latitude, longitude)
    if not weather_data:
        return None
        
    # Get time-based interest
    time_interest = get_time_based_interest(hour)
    
    # Get day-based interest
    day_interest = get_day_based_interest(day)
    
    # Get seasonal interest
    seasonal_interest = get_seasonal_interest(month)
    
    # Get weather-based interest
    weather_interest = get_weather_based_interest(weather_data.condition)
    
    # Combine all interests
    all_interests = []
    if time_interest:
        all_interests.append(time_interest)
    if day_interest:
        all_interests.append(day_interest)
    if seasonal_interest:
        all_interests.append(seasonal_interest)
    if weather_interest:
        all_interests.append(weather_interest)
        
    # Get most common interest
    if all_interests:
        interest_counter = Counter(all_interests)
        recommended_interest = interest_counter.most_common(1)[0][0]
    else:
        recommended_interest = searches[0]['interest']
        
    # Get pincode from recent searches
    recommended_pincode = searches[0]['pincode']
    
    return recommended_interest, recommended_pincode

def recommend_interest_and_pincode(searches, user_id=None, collaborative_recommender=None):
    """
    Get recommendation using both collaborative filtering and context-based rules.
    Returns (interest, pincode) tuple or None if no recommendation can be made.
    """
    if not searches:
        return None
        
    # Get latitude and longitude from the first search
    first_search = searches[0]
    latitude = first_search.get('latitude')
    longitude = first_search.get('longitude')
    
    if not latitude or not longitude:
        return None
        
    # Try collaborative filtering first
    if collaborative_recommender and user_id:
        # Get similar interests and pincodes
        similar_interests = collaborative_recommender.get_similar_interests(first_search['interest'])
        similar_pincodes = collaborative_recommender.get_similar_pincodes(first_search['pincode'])
        
        if similar_interests and similar_pincodes:
            return similar_interests[0], similar_pincodes[0]
    
    # Fallback to context-based recommendation
    return get_context_based_recommendation(searches, latitude, longitude)

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
=======
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
from sqlalchemy import func, desc
from sqlalchemy.sql import func, desc
from model import db, UserInteraction

class CollaborativeRecommender:
    def __init__(self):
        self.user_interaction_matrix = None
        self.user_similarity_matrix = None
        self.interest_pincode_matrix = None
        self.interest_pincode_similarity = None
        self.interest_pincode_counts = {}
        self.unique_interests = []
        self.unique_pincodes = []
        self.update_matrices()

    def update_matrices(self):
        # Get all interactions
        interactions = UserInteraction.query.all()
        
        if not interactions:
            return
            
        # Create user-interaction matrix
        user_interactions = {}
        for interaction in interactions:
            user_id = interaction.user_id
            if user_id not in user_interactions:
                user_interactions[user_id] = []
            user_interactions[user_id].append({
                'interest': interaction.interest,
                'pincode': interaction.pincode
            })
            
        # Create interest-pincode matrix
        self.interest_pincode_counts = {}
        for user_id, interactions in user_interactions.items():
            for interaction in interactions:
                key = (interaction['interest'], interaction['pincode'])
                if key not in self.interest_pincode_counts:
                    self.interest_pincode_counts[key] = 0
                self.interest_pincode_counts[key] += 1
                
        # Convert to matrix format
        self.unique_interests = sorted(set(k[0] for k in self.interest_pincode_counts.keys()))
        self.unique_pincodes = sorted(set(k[1] for k in self.interest_pincode_counts.keys()))
        
        self.interest_pincode_matrix = np.zeros((len(self.unique_interests), len(self.unique_pincodes)))
        for (interest, pincode), count in self.interest_pincode_counts.items():
            i = self.unique_interests.index(interest)
            j = self.unique_pincodes.index(pincode)
            self.interest_pincode_matrix[i, j] = count
            
        # Calculate similarity matrices
        if len(self.unique_interests) > 1 and len(self.unique_pincodes) > 1:
            self.interest_pincode_similarity = cosine_similarity(self.interest_pincode_matrix)
        else:
            self.interest_pincode_similarity = np.eye(len(self.unique_interests))

    def get_similar_interests(self, interest, n=3):
        if self.interest_pincode_similarity is None or not self.interest_pincode_counts:
            return []
            
        if interest not in self.unique_interests:
            return []
            
        interest_idx = self.unique_interests.index(interest)
        similarities = self.interest_pincode_similarity[interest_idx]
        
        # Get top N similar interests
        similar_indices = np.argsort(similarities)[::-1][1:n+1]
        return [self.unique_interests[i] for i in similar_indices]

    def get_similar_pincodes(self, pincode, n=3):
        if self.interest_pincode_similarity is None or not self.interest_pincode_counts:
            return []
            
        if pincode not in self.unique_pincodes:
            return []
            
        pincode_idx = self.unique_pincodes.index(pincode)
        similarities = self.interest_pincode_similarity.T[pincode_idx]
        
        # Get top N similar pincodes
        similar_indices = np.argsort(similarities)[::-1][1:n+1]
        return [self.unique_pincodes[i] for i in similar_indices]

def get_context_based_recommendation(searches, latitude, longitude):
    """Get recommendation based on context (time, weather, etc.)"""
    if not searches:
        return None
        
    # Get current time and weather
    current_time = datetime.now()
    hour = current_time.hour
    day = current_time.weekday()
    month = current_time.month
    
    # Get weather data
    weather_data = get_weather_from_api(latitude, longitude)
    if not weather_data:
        return None
        
    # Get time-based interest
    time_interest = get_time_based_interest(hour)
    
    # Get day-based interest
    day_interest = get_day_based_interest(day)
    
    # Get seasonal interest
    seasonal_interest = get_seasonal_interest(month)
    
    # Get weather-based interest
    weather_interest = get_weather_based_interest(weather_data.condition)
    
    # Combine all interests
    all_interests = []
    if time_interest:
        all_interests.append(time_interest)
    if day_interest:
        all_interests.append(day_interest)
    if seasonal_interest:
        all_interests.append(seasonal_interest)
    if weather_interest:
        all_interests.append(weather_interest)
        
    # Get most common interest
    if all_interests:
        interest_counter = Counter(all_interests)
        recommended_interest = interest_counter.most_common(1)[0][0]
    else:
        recommended_interest = searches[0]['interest']
        
    # Get pincode from recent searches
    recommended_pincode = searches[0]['pincode']
    
    return recommended_interest, recommended_pincode

def recommend_interest_and_pincode(searches, user_id=None, collaborative_recommender=None):
    """
    Get recommendation using both collaborative filtering and context-based rules.
    Returns (interest, pincode) tuple or None if no recommendation can be made.
    """
    if not searches:
        return None
        
    # Get latitude and longitude from the first search
    first_search = searches[0]
    latitude = first_search.get('latitude')
    longitude = first_search.get('longitude')
    
    if not latitude or not longitude:
        return None
        
    # Try collaborative filtering first
    if collaborative_recommender and user_id:
        # Get similar interests and pincodes
        similar_interests = collaborative_recommender.get_similar_interests(first_search['interest'])
        similar_pincodes = collaborative_recommender.get_similar_pincodes(first_search['pincode'])
        
        if similar_interests and similar_pincodes:
            return similar_interests[0], similar_pincodes[0]
    
    # Fallback to context-based recommendation
    return get_context_based_recommendation(searches, latitude, longitude)

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
>>>>>>> cb83b1a40305781fd5f48ffcc08ca9c305d45b06
