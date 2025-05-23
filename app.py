from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
import requests
import os
from dotenv import load_dotenv
import re
import jwt
from datetime import datetime, timedelta
from model import db, User, UserInteraction
from Recommended_for_you import recommend_interest_and_pincode as context_recommender
from People_also_search_for import (
    recommend_interest_and_pincode as collab_recommender_fn,
    CollaborativeRecommender
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from admin import admin_bp
from sqlalchemy.sql import func, desc

collab_recommender = CollaborativeRecommender()

load_dotenv()

JWT_SECRET = 'super_secret_jwt_key'
JWT_EXPIRY_MINUTES = 15 #Expires in 15 minutes

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:boathead@localhost/test'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

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

@app.route('/search', methods=['POST'])
def search_places():
    user = get_current_user()  # Might be None

    data = request.json
    pincode = data.get('pincode')
    interest = data.get('interest')

    if not pincode or not interest:
        return jsonify({"error": "PIN code and interest are required"}), 400

    # Save for logged in user only
    if user:
        user.preferred_pincode = pincode
        user.field_of_interest = interest
        db.session.commit()

        interaction = UserInteraction(
            user_id=str(user.id),
            interest=interest,
            pincode=pincode,
            timestamp=datetime.now()
        )
        db.session.add(interaction)
        db.session.commit()
        collab_recommender.add_interaction(interaction)

    return search_places_core(pincode, interest)

    data = request.json
    pincode = data.get('pincode')
    interest = data.get('interest')

    if not pincode or not interest:
        return jsonify({"error": "PIN code and interest are required"}), 400

    user.preferred_pincode = pincode
    user.field_of_interest = interest
    db.session.commit() 

    interaction = UserInteraction(
        user_id=str(user.id),
        interest=interest,
        pincode=pincode,
        timestamp=datetime.now()
    )
    db.session.add(interaction)
    db.session.commit()
    collab_recommender.add_interaction(interaction)

    return search_places_core(pincode, interest)

@app.route('/me')
def check_login():
    user = get_current_user()
    return jsonify({
        "logged_in": bool(user),
        "username": user.username if user else None
    })

@app.route('/recommend/context', methods=['POST'])
def recommend_contextual():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if not user.preferred_pincode or not user.field_of_interest:
        return jsonify({"results": []})

    recent_interactions = (
        UserInteraction.query
        .filter_by(user_id=str(user.id))
        .order_by(UserInteraction.timestamp.desc())
        .limit(5)
        .all()
    )

    searches = [
        {'interest': i.interest, 'pincode': i.pincode}
        for i in recent_interactions
    ]

    recommendation = context_recommender(searches)
    if not recommendation:
        return jsonify({"results": []})

    interest, pincode = recommendation
    return search_places_core(pincode, interest)

@app.route('/recommend/collaborative', methods=['POST'])
def recommend_collaborative():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if not user.preferred_pincode or not user.field_of_interest:
        return jsonify({"results": []})

    searches = [{'interest': user.field_of_interest, 'pincode': user.preferred_pincode}]
    recommendation = collab_recommender_fn(
        searches,
        user_id=str(user.id),
        collaborative_recommender=collab_recommender
    )
    if not recommendation:
        return jsonify({"results": []})

    interest, pincode = recommendation
    return search_places_core(pincode, interest)

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

        return jsonify({"results": all_results})

    except Exception as e:
        print("Exception:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # print("Registered routes:")
        # print(app.url_map)
    app.run(debug=True)
