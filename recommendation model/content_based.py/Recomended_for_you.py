from collections import Counter
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from model import (
    WeatherData, UserInteraction,
    get_time_category, get_day_category, get_seasonal_category,
    get_weather_from_api, get_weather_based_interest,
    get_time_based_interest, get_day_based_interest, get_seasonal_interest
)

def recommend_interest_and_pincode(searches: List[Dict], latitude: float = 28.6139, longitude: float = 77.2090) -> Optional[Tuple[str, str]]:
    """
    Given a list of recent searches and location coordinates,
    return the most likely (interest, pincode) tuple.
    Returns None if not enough data.
    
    Example usage:
    searches = [
        {'interest': 'food', 'pincode': '110001'},
        {'interest': 'shopping', 'pincode': '110001'},
        {'interest': 'entertainment', 'pincode': '110002'}
    ]
    result = recommend_interest_and_pincode(searches)
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

    # Combine all interests with weights
    all_interests = interests * 2 + [time_based_interest, day_based_interest, 
                                   seasonal_interest, weather_based_interest]
    
    # Most common interest and pincode
    interest = Counter(all_interests).most_common(1)[0][0]
    pincode = Counter(pincodes).most_common(1)[0][0]
    
    return interest, pincode

# Example usage
if __name__ == "__main__":
    # Example search history
    example_searches = [
        {'interest': 'food', 'pincode': '110001'},
        {'interest': 'shopping', 'pincode': '110001'},
        {'interest': 'entertainment', 'pincode': '110002'}
    ]
    
    print("Testing weather API integration...")
    # Get recommendation
    result = recommend_interest_and_pincode(example_searches)
    if result:
        interest, pincode = result
        print(f"\nFinal Recommendation:")
        print(f"Recommended interest: {interest}")
        print(f"Recommended pincode: {pincode}")
    else:
        print("Not enough data to make a recommendation")
