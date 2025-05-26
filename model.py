from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter
import requests
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, func

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    preferred_pincode = db.Column(db.String(6))
    field_of_interest = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    interest = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    weather_condition = db.Column(db.String(50))
    is_day = db.Column(db.Boolean)
    temperature = db.Column(db.Float)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    @classmethod
    def most_active_time_of_day(cls, user_id):
        """
        Returns the most active time category for a user based on their interaction timestamps.
        """
        from model import get_time_category
        interactions = cls.query.filter_by(user_id=user_id).all()
        if not interactions:
            return None
        time_categories = [get_time_category(i.timestamp.hour) for i in interactions]
        if not time_categories:
            return None
        from collections import Counter
        most_common = Counter(time_categories).most_common(1)
        return most_common[0][0] if most_common else None

    @classmethod
    def most_active_hour(cls, user_id=None):
        """
        Returns the hour(s) of day with the most interactions. If user_id is provided, filters by user.
        Returns a list of (hour, count) tuples sorted by hour.
        """
        query = db.session.query(
            extract('hour', cls.timestamp).label('hour'),
            func.count().label('count')
        )
        if user_id:
            query = query.filter(cls.user_id == user_id)
        query = query.group_by('hour').order_by('hour')
        return query.all()

    @classmethod
    def interest_by_hour(cls, user_id=None):
        """
        Returns a list of (hour, interest, count) tuples, showing how many times each interest was searched per hour.
        If user_id is provided, filters by user.
        """
        query = db.session.query(
            extract('hour', cls.timestamp).label('hour'),
            cls.interest,
            func.count().label('count')
        )
        if user_id:
            query = query.filter(cls.user_id == user_id)
        query = query.group_by('hour', cls.interest).order_by('hour')
        return query.all()

@dataclass
class WeatherData:
    temperature: float
    condition: str
    is_day: bool

def get_time_category(hour: int) -> str:
    """Convert hour to time category with more specific slots"""
    if 5 <= hour < 7:
        return "early_morning"
    elif 7 <= hour < 11:
        return "breakfast"
    elif 11 <= hour < 15:
        return "lunch"
    elif 15 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 19:
        return "evening"
    elif 19 <= hour < 22:
        return "dinner"
    else:
        return "late_night"

def get_day_category(day: int) -> str:
    """Convert day number to more specific category"""
    if day == 0:  # Monday
        return "start_of_week"
    elif day == 4:  # Friday
        return "end_of_week"
    elif day >= 5:  # Weekend
        return "weekend"
    else:
        return "mid_week"

def get_seasonal_category(month: int) -> str:
    """Determine seasonal category with more specific patterns"""
    # Festive seasons (approximate months)
    festive_months = {
        
        1: "new_year",      
        3: "holi",          
        4: "easter",        
        8: "rakhi",         
        10: "dussehra",     
        11: "diwali",       
        12: "christmas"     
    }
    
    # Vacation periods
    vacation_months = {
        6: "summer_vacation",
        7: "summer_vacation",
        12: "winter_vacation"
    }
    
    # Weather-based seasons
    weather_seasons = {
        3: "spring",
        4: "spring",
        5: "summer",
        6: "summer",
        7: "monsoon",
        8: "monsoon",
        9: "autumn",
        10: "autumn",
        11: "winter",
        12: "winter",
        1: "winter",
        2: "winter"
    }
    
    if month in festive_months:
        return festive_months[month]
    elif month in vacation_months:
        return vacation_months[month]
    else:
        return weather_seasons[month]

def get_weather_from_api(latitude: float, longitude: float) -> WeatherData:
    """
    Get weather data from Open-Meteo API
    Returns temperature in Celsius and weather condition
    """
    try:
        # Open-Meteo API endpoint
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,is_day,weather_code"
        
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Extract current weather data
        current = data['current']
        temp = current['temperature_2m']
        is_day = current['is_day'] == 1
        weather_code = current['weather_code']
        
        # Convert WMO weather codes to conditions
        weather_conditions = {
            0: "clear",
            1: "partly_cloudy",
            2: "cloudy",
            3: "overcast",
            45: "foggy",
            48: "foggy",
            51: "drizzle",
            53: "drizzle",
            55: "drizzle",
            61: "rainy",
            63: "rainy",
            65: "rainy",
            71: "snowy",
            73: "snowy",
            75: "snowy",
            77: "snowy",
            80: "rainy",
            81: "rainy",
            82: "rainy",
            85: "snowy",
            86: "snowy",
            95: "thunderstorm",
            96: "thunderstorm",
            99: "thunderstorm"
        }
        
        condition = weather_conditions.get(weather_code, "unknown")
        weather_data = WeatherData(temperature=temp, condition=condition, is_day=is_day)
        
        # Print weather data
        print("\nCurrent Weather Data from Open-Meteo API:")
        print(f"Temperature: {weather_data.temperature}°C")
        print(f"Condition: {weather_data.condition}")
        print(f"Time of Day: {'Day' if weather_data.is_day else 'Night'}")
        print(f"Raw Weather Code: {weather_code}")
        print(f"API Response URL: {url}\n")
        
        return weather_data
        
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        # Fallback to a default condition
        return WeatherData(temperature=20.0, condition="clear", is_day=True)

def get_weather_based_interest(weather: WeatherData) -> str:
    """Get likely interest based on weather conditions"""
    weather_interests = {
        "clear": "outdoor_activities" if weather.is_day else "entertainment",
        "partly_cloudy": "outdoor_activities" if weather.is_day else "entertainment",
        "cloudy": "shopping",
        "overcast": "shopping",
        "foggy": "indoor_entertainment",
        "drizzle": "indoor_entertainment",
        "rainy": "indoor_entertainment",
        "snowy": "indoor_entertainment",
        "thunderstorm": "indoor_entertainment",
        "unknown": "general"
    }
    
    # Temperature-based adjustments
    if weather.temperature > 30:  # Hot weather
        return "water_parks" if weather.is_day else "entertainment"
    elif weather.temperature < 10:  # Cold weather
        return "indoor_entertainment"
    
    return weather_interests.get(weather.condition, "general")

def get_time_based_interest(time_category: str) -> str:
    """Get likely interest based on time of day with more specific categories"""
    time_interests = {
        "early_morning": "fitness",
        "breakfast": "food",
        "lunch": "food",
        "afternoon": "shopping",
        "evening": "parks",
        "dinner": "food",
        "late_night": "entertainment"
    }
    return time_interests.get(time_category, "general")

def get_day_based_interest(day_category: str) -> str:
    """Get likely interest based on day of week with more specific patterns"""
    day_interests = {
        "start_of_week": "services",
        "mid_week": "shopping",
        "end_of_week": "entertainment",
        "weekend": "entertainment"
    }
    return day_interests.get(day_category, "general")

def get_seasonal_interest(seasonal_category: str) -> str:
    """Get likely interest based on seasonal category with more specific patterns"""
    seasonal_interests = {
        # Festive seasons
        "new_year": "entertainment",
        "holi": "entertainment",
        "easter": "shopping",
        "rakhi": "shopping",
        "dussehra": "entertainment",
        "diwali": "shopping",
        "christmas": "shopping",
        
        # Vacations
        "summer_vacation": "travel",
        "winter_vacation": "travel",
        
        # Weather seasons
        "spring": "parks",
        "summer": "water_parks",
        "monsoon": "indoor_entertainment",
        "autumn": "parks",
        "winter": "indoor_entertainment"
    }
    return seasonal_interests.get(seasonal_category, "general") 
