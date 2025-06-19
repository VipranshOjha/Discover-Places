from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
import requests
import os
from dotenv import load_dotenv
import re
import jwt
from datetime import datetime, timedelta
from model import db, User, UserInteraction
import tensorflow as tf
import joblib
import numpy as np
from People_also_search_for import (
    recommend_interest_and_pincode as collab_recommender_fn,
    CollaborativeRecommender
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from admin import admin_bp
from sqlalchemy.sql import func, desc

# Initialize model and encoders as None
model = None
user_encoder = None
interest_encoder = None
pincode_encoder = None
weather_encoder = None
lat_scaler = None
lon_scaler = None

def load_model_and_encoders():
    global model, user_encoder, interest_encoder, pincode_encoder, weather_encoder, lat_scaler, lon_scaler
    try:
        # Check if files exist
        required_files = [
            "recommender_model.keras",
            "user_encoder.pkl",
            "interest_encoder.pkl",
            "pincode_encoder.pkl",
            "weather_encoder.pkl",
            "lat_scaler.pkl",
            "lon_scaler.pkl"
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            print("Missing required files:", missing_files)
            return False
            
        # Load model and encoders
        model = tf.keras.models.load_model("recommender_model.keras")
        user_encoder = joblib.load('user_encoder.pkl')
        interest_encoder = joblib.load('interest_encoder.pkl')
        pincode_encoder = joblib.load('pincode_encoder.pkl')
        weather_encoder = joblib.load('weather_encoder.pkl')
        lat_scaler = joblib.load('lat_scaler.pkl')
        lon_scaler = joblib.load('lon_scaler.pkl')
        
        print("Successfully loaded model and encoders")
        return True
        
    except Exception as e:
        print("Error loading model and encoders:", str(e))
        import traceback
        print("Full traceback:", traceback.format_exc())
        return False

# Try to load model and encoders at startup
model_loaded = load_model_and_encoders()

load_dotenv()

JWT_SECRET = 'super_secret_jwt_key'
JWT_EXPIRY_MINUTES = 15 #Expires in 15 minutes

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:boathead@localhost/test'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize collaborative recommender inside app context
collab_recommender = None

def init_collab_recommender():
    global collab_recommender
    collab_recommender = CollaborativeRecommender()

with app.app_context():
    db.create_all()
    init_collab_recommender()

def generate_jwt(user_id, username):
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def get_current_user():
    token = request.cookies.get('jwt_token')
    if not token:
        return None
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return User.query.get(decoded['user_id'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']

        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

        if user and check_password_hash(user.password, password):
            token = generate_jwt(user.id, user.username)
            response = redirect(url_for('index'))
            response.set_cookie('jwt_token', token, httponly=True)
            return response
        else:
            message = 'Invalid username/email or password.'

    return render_template('login.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        if User.query.filter((User.username == username) | (User.email == email)).first():
            message = 'Username or email already exists.'
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login', signed_up='1'))
    return render_template('signup.html', message=message)

API_KEY = os.environ.get("GOMAPS_API_KEY")

INTEREST_KEYWORDS = {
    "education": "school OR college OR university OR coaching center",
    "healthcare": "hospital OR clinic OR pharmacy",
    "shopping": "mall OR market OR store",
    "food": "restaurant OR cafe OR dhaba",
    "travel": "monument OR tourist spot OR temple OR park",
    "entertainment": "cinema OR amusement park OR game zone",
    "sports": "gym OR stadium OR playground",
    "services": "bank OR post office OR police station"
}

def get_map_link(place_name, address):
    query = f"{place_name}, {address}".replace(" ", "+")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', username=user.username if user else None)

@app.route('/logout')
def logout():
    response = redirect(url_for('login', logged_out=1))
    response.delete_cookie('jwt_token')
    return response

def get_nn_recommendation(user_id, latitude, longitude, weather_condition, is_day):
    if not model_loaded:
        raise ValueError("Model and encoders not properly loaded")
        
    try:
        # Get current time features
        current_time = datetime.now()
        hour = current_time.hour
        day_of_week = current_time.weekday()
        month = current_time.month
        season = (month % 12 + 3) // 3  # 1: Spring, 2: Summer, 3: Fall, 4: Winter
        
        print("Time features:", {
            "hour": hour,
            "day_of_week": day_of_week,
            "month": month,
            "season": season
        })
        
        # Encode inputs
        try:
            user_enc = user_encoder.transform([user_id])[0]
            print("User encoded:", user_enc)
        except Exception as e:
            print("Error encoding user:", str(e))
            raise ValueError(f"Invalid user_id: {user_id}")
            
        try:
            weather_enc = weather_encoder.transform([weather_condition])[0]
            print("Weather encoded:", weather_enc)
        except Exception as e:
            print("Error encoding weather:", str(e))
            raise ValueError(f"Invalid weather_condition: {weather_condition}")
        
        # Scale coordinates
        try:
            lat_scaled = lat_scaler.transform([[latitude]])[0][0]
            lon_scaled = lon_scaler.transform([[longitude]])[0][0]
            print("Scaled coordinates:", {"lat": lat_scaled, "lon": lon_scaled})
        except Exception as e:
            print("Error scaling coordinates:", str(e))
            raise ValueError(f"Invalid coordinates: lat={latitude}, lon={longitude}")
        
        # Prepare input arrays
        inputs = [
            np.array([user_enc]),
            np.array([hour]),
            np.array([day_of_week]),
            np.array([season]),
            np.array([weather_enc]),
            np.array([is_day]),
            np.array([lat_scaled]),
            np.array([lon_scaled]),
            np.array([0])  # Default last interest
        ]
        
        print("Model inputs prepared")
        
        # Get predictions
        try:
            interest_pred, pincode_pred = model.predict(inputs)
            print("Model predictions received")
        except Exception as e:
            print("Error in model prediction:", str(e))
            raise ValueError("Failed to get model predictions")
        
        # Get most likely interest and pincode
        interest_idx = np.argmax(interest_pred[0])
        pincode_idx = np.argmax(pincode_pred[0])
        
        try:
            interest = interest_encoder.inverse_transform([interest_idx])[0]
            pincode = pincode_encoder.inverse_transform([pincode_idx])[0]
            print("Decoded predictions:", {"interest": interest, "pincode": pincode})
        except Exception as e:
            print("Error decoding predictions:", str(e))
            raise ValueError("Failed to decode model predictions")
        
        return interest, pincode
        
    except Exception as e:
        print("Error in get_nn_recommendation:", str(e))
        import traceback
        print("Full traceback:", traceback.format_exc())
        raise

@app.route('/recommend/context', methods=['POST'])
def recommend_contextual():
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        if not user.preferred_pincode or not user.field_of_interest:
            return jsonify({"results": []})

        # Get user's last interaction for location and weather data
        last_interaction = (
            UserInteraction.query
            .filter_by(user_id=str(user.id))
            .order_by(UserInteraction.timestamp.desc())
            .first()
        )

        if not last_interaction:
            print("No interaction history found for user:", user.id)
            return jsonify({"results": []})

        # Check if we have valid location data
        if last_interaction.latitude is None or last_interaction.longitude is None:
            print("Missing location data in last interaction")
            return jsonify({"results": []})

        print("Last interaction found:", {
            "user_id": last_interaction.user_id,
            "latitude": last_interaction.latitude,
            "longitude": last_interaction.longitude,
            "weather": last_interaction.weather_condition,
            "is_day": last_interaction.is_day
        })

        try:
            # Get recommendation using neural network
            if model_loaded:
                interest, pincode = get_nn_recommendation(
                    user_id=str(user.id),
                    latitude=last_interaction.latitude,
                    longitude=last_interaction.longitude,
                    weather_condition=last_interaction.weather_condition or "clear",
                    is_day=last_interaction.is_day or True
                )
            else:
                return jsonify({"error": "Neural network model not loaded"}), 503

            print("NN recommendation:", {"interest": interest, "pincode": pincode})

            # Get search results
            search_data = search_places_core_raw(pincode, interest)
            print("Search data:", search_data)
            
            # Ensure we return proper JSON response
            if "error" in search_data:
                return jsonify({"error": search_data["error"]}), 400
                
            return jsonify({"results": search_data.get("results", [])})

        except Exception as e:
            print("Error in recommendation process:", str(e))
            import traceback
            print("Full traceback:", traceback.format_exc())
            return jsonify({"error": f"Failed to generate recommendations: {str(e)}"}), 500

    except Exception as e:
        print("Error in context recommendation route:", str(e))
        import traceback
        print("Full traceback:", traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recommend/collaborative', methods=['POST'])
def recommend_collaborative():
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        if not user.preferred_pincode or not user.field_of_interest:
            return jsonify({"results": []})

        # Get user's recent interactions
        recent_interactions = (
            UserInteraction.query
            .filter_by(user_id=str(user.id))
            .order_by(UserInteraction.timestamp.desc())
            .limit(5)
            .all()
        )

        if not recent_interactions:
            return jsonify({"results": []})

        # Convert interactions to search format
        searches = [
            {
                'interest': i.interest,
                'pincode': i.pincode,
                'latitude': i.latitude,
                'longitude': i.longitude
            }
            for i in recent_interactions
        ]

        # Get recommendation using collaborative filtering
        recommendation = collab_recommender_fn(
            searches,
            user_id=str(user.id),
            collaborative_recommender=collab_recommender
        )

        if not recommendation:
            return jsonify({"results": []})

        interest, pincode = recommendation
        search_data = search_places_core_raw(pincode, interest)
        
        if "error" in search_data:
            return jsonify({"error": search_data["error"]}), 400
            
        return jsonify({"results": search_data.get("results", [])})

    except Exception as e:
        print("Error in collaborative recommendation:", str(e))
        import traceback
        print("Full traceback:", traceback.format_exc())
        return jsonify({"error": "Failed to generate recommendations"}), 500

@app.route('/recommend', methods=['POST'])
def recommend_places():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if not user.preferred_pincode or not user.field_of_interest:
        return jsonify({"results": []})

    pincode = user.preferred_pincode
    interest = user.field_of_interest
    return search_places_core(pincode, interest)

def search_places_core(pincode, interest):
    if not pincode or not interest:
        return jsonify({"error": "PIN code and interest are required"}), 400

    if not API_KEY:
        return jsonify({"error": "GOMAPS API key is not configured"}), 500

    try:
        # Get district/state from pincode
        pin_url = f"https://api.postalpincode.in/pincode/{pincode}"
        pin_response = requests.get(pin_url).json()
        if pin_response[0]['Status'] != 'Success':
            return jsonify({"error": "Invalid PIN code"}), 404

        district = pin_response[0]['PostOffice'][0]['District']
        state = pin_response[0]['PostOffice'][0]['State']

        # Step 1: Geocode the pincode to get lat/lng
        geocode_url = f"https://maps.gomaps.pro/maps/api/geocode/json"
        geocode_params = {
            'address': pincode,
            'key': API_KEY
        }
        geo_resp = requests.get(geocode_url, params=geocode_params).json()
        print("Geocode API response:", geo_resp)

        if 'status' not in geo_resp:
            return jsonify({"error": "Geocode API response missing 'status'. Full response: {}".format(geo_resp)}), 500

        if geo_resp.get('status') == 'OK':
            location = geo_resp['results'][0]['geometry']['location']
            lat, lng = location['lat'], location['lng']
        else:
            return jsonify({"error": f"Failed to geocode pincode: {geo_resp.get('status')}"}), 500

        # Format query based on interest
        query_term = INTEREST_KEYWORDS.get(interest.lower(), interest)
        search_query = f"{query_term} in {district}, {state}, India"

        print("GOMAPS Query:", search_query)

        # Step 2: Use lat/lng and radius in textsearch
        search_url = f"https://maps.gomaps.pro/maps/api/place/textsearch/json"
        params = {
            'query': search_query,
            'location': f"{lat},{lng}",
            'radius': 2000,
            'key': API_KEY,
            'language': 'en',
            'region': 'in'
        }
        
        search_response = requests.get(search_url, params=params)
        if not search_response.ok:
            return jsonify({"error": "Failed to contact GOMAPS API"}), 500

        search_data = search_response.json()
        print("GOMAPS API Response:", search_data.get("status"))

        if search_data.get("status") != "OK":
            return jsonify({"error": f"GOMAPS API error: {search_data.get('status')}"}), 500

        places = search_data.get("results", [])
        if not places:
            return jsonify({"message": "No places found for your search criteria."})

        # Step 3: Filter results by pincode in address
        filtered_places = []
        for place in places:
            address = place.get("formatted_address", "")
            # Strict pincode match
            if re.search(r'\b{}\b'.format(re.escape(str(pincode))), address):
                filtered_places.append(place)

        all_results = []
        # Only use strictly filtered places
        for place in filtered_places:
            place_id = place.get("place_id")
            name = place.get("name", "Unknown Place")
            address = place.get("formatted_address", "No address available")
            types = place.get("types", [])
            place_type = ", ".join(types).replace("_", " ").title()

            # Use photo_reference from textsearch result
            photo_url = "/static/images/default_place.jpg"
            photos = place.get("photos")
            if photos and len(photos) > 0:
                ref = photos[0].get("photo_reference")
                if ref:
                    photo_url = f"https://maps.gomaps.pro/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={API_KEY}"

            # Map link
            map_link = get_map_link(name, address)

            all_results.append({
                "name": name,
                "address": address,
                "place_type": place_type,
                "photo_reference": photo_url,
                "description": f"A {interest.lower()} place in {district}, {state}.",
                "map_link": map_link
            })

        return {
            "results": all_results,
            "lat": lat,
            "lng": lng
        }

    except Exception as e:
        print("Exception:", e)
        return {"error": str(e)}

@app.route('/search_api', methods=['POST'])
def search_places_api():
    data = request.json
    pincode = data.get('pincode')
    interest = data.get('interest')

    if not pincode or not interest:
        return jsonify({"error": "PIN code and interest are required"}), 400

    # Call the search_places_core function to get search data
    result = search_places_core_raw(pincode, interest)
    return jsonify(result)

def search_places_core_raw(pincode, interest):
    if not pincode or not interest:
        return {"error": "PIN code and interest are required"}

    if not API_KEY:
        return {"error": "GOMAPS API key is not configured"}

    try:
        # Get district/state from pincode
        pin_url = f"https://api.postalpincode.in/pincode/{pincode}"
        pin_response = requests.get(pin_url).json()
        if pin_response[0]['Status'] != 'Success':
            return {"error": "Invalid PIN code"}

        district = pin_response[0]['PostOffice'][0]['District']
        state = pin_response[0]['PostOffice'][0]['State']

        # Step 1: Geocode the pincode to get lat/lng
        geocode_url = f"https://maps.gomaps.pro/maps/api/geocode/json"
        geocode_params = {
            'address': pincode,
            'key': API_KEY
        }
        geo_resp = requests.get(geocode_url, params=geocode_params).json()

        if 'status' not in geo_resp:
            return {"error": "Geocode API response missing 'status'."}

        if geo_resp.get('status') == 'OK':
            location = geo_resp['results'][0]['geometry']['location']
            lat, lng = location['lat'], location['lng']
        else:
            return {"error": f"Failed to geocode pincode: {geo_resp.get('status')}"}

        # Format query based on interest
        query_term = INTEREST_KEYWORDS.get(interest.lower(), interest)
        search_query = f"{query_term} in {district}, {state}, India"

        # Step 2: Use lat/lng and radius in textsearch
        search_url = f"https://maps.gomaps.pro/maps/api/place/textsearch/json"
        params = {
            'query': search_query,
            'location': f"{lat},{lng}",
            'radius': 2000,
            'key': API_KEY,
            'language': 'en',
            'region': 'in'
        }
        
        search_response = requests.get(search_url, params=params)
        if not search_response.ok:
            return {"error": "Failed to contact GOMAPS API"}

        search_data = search_response.json()

        if search_data.get("status") != "OK":
            return {"error": f"GOMAPS API error: {search_data.get('status')}"}

        places = search_data.get("results", [])
        if not places:
            return {"message": "No places found for your search criteria."}

        # Step 3: Filter results by pincode in address
        filtered_places = []
        for place in places:
            address = place.get("formatted_address", "")
            # Strict pincode match
            if re.search(r'\b{}\b'.format(re.escape(str(pincode))), address):
                filtered_places.append(place)

        all_results = []
        # Only use strictly filtered places
        for place in filtered_places:
            place_id = place.get("place_id")
            name = place.get("name", "Unknown Place")
            address = place.get("formatted_address", "No address available")
            types = place.get("types", [])
            place_type = ", ".join(types).replace("_", " ").title()

            # Use photo_reference from textsearch result
            photo_url = "/static/images/default_place.jpg"
            photos = place.get("photos")
            if photos and len(photos) > 0:
                ref = photos[0].get("photo_reference")
                if ref:
                    photo_url = f"https://maps.gomaps.pro/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={API_KEY}"

            # Map link
            map_link = get_map_link(name, address)

            all_results.append({
                "name": name,
                "address": address,
                "place_type": place_type,
                "photo_reference": photo_url,
                "description": f"A {interest.lower()} place in {district}, {state}.",
                "map_link": map_link
            })

        return {
            "results": all_results,
            "lat": lat,
            "lng": lng
        }

    except Exception as e:
        return {"error": str(e)}

@app.route('/search', methods=['POST'])
def search_places():
    try:
        user = get_current_user()  # Might be None

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        pincode = data.get('pincode')
        interest = data.get('interest')

        if not pincode or not interest:
            return jsonify({"error": "PIN code and interest are required"}), 400

        try:
            # Call the search_places_core function to get search data
            search_data = search_places_core_raw(pincode, interest)

            # Save user interaction with lat/lng and weather data if the user is authenticated
            if user:
                try:
                    interaction = UserInteraction(
                        user_id=str(user.id),
                        interest=interest,
                        pincode=pincode,
                        timestamp=datetime.now(),
                        latitude=search_data.get("lat"),
                        longitude=search_data.get("lng"),
                        weather_condition=search_data.get("weather_condition"),
                        is_day=search_data.get("is_day"),
                        temperature=search_data.get("temperature")
                    )
                    db.session.add(interaction)
                    db.session.commit()
                except Exception as e:
                    print("Error saving user interaction:", str(e))
                    # Continue even if saving interaction fails

            # Return results to frontend
            if "error" in search_data:
                return jsonify({"error": search_data["error"]}), 400
            return jsonify({"results": search_data.get("results", [])})

        except Exception as e:
            print("Error in search process:", str(e))
            import traceback
            print("Full traceback:", traceback.format_exc())
            return jsonify({"error": "Failed to process search request"}), 500

    except Exception as e:
        print("Error in /search route:", str(e))
        import traceback
        print("Full traceback:", traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@app.route('/me')
def check_login():
    user = get_current_user()
    return jsonify({
        "logged_in": bool(user),
        "username": user.username if user else None
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # print("Registered routes:")
        # print(app.url_map)
    app.run(debug=True)
