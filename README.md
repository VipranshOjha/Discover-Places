# Discover Places: Smart Location Recommender System

A sophisticated location recommendation system that combines neural networks, collaborative filtering, and contextual information to provide personalized place recommendations based on user preferences, location, weather, and time.

## 🌟 Features

- **Multi-Model Recommendation Engine**
  - Neural Network-based recommendations using TensorFlow
  - Collaborative filtering using SVD (Surprise library)
  - Context-aware recommendations based on weather and time
  - "People also search for" suggestions

- **Smart Context Integration**
  - Weather-aware recommendations
  - Time-based suggestions (day/night)
  - Location-based filtering
  - User preference learning

- **User Management**
  - Secure authentication system with JWT
  - User profile management
  - Interaction tracking
  - Personalized recommendations

- **Admin Dashboard**
  - User management
  - System monitoring
  - Analytics dashboard

<h2>📸 UI Preview – Login, Home, Admin & Recommendations</h2>

<h3>Login & Signup Pages</h3>
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/df7ea2e0-5a4c-4bc4-950b-6e5cb8f0ff25" width="400"/></td>
    <td><img src="https://github.com/user-attachments/assets/8160b7e2-7769-44c0-ab34-8cb9f1344b0e" alt="Signup Page" width="400"/></td>
  </tr>
</table>

<h3>Home & Admin Pages</h3>
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/c8742dce-ab7b-4cb5-a595-fbffd1773aa5" alt="Home Page" width="400"/></td>
    <td><img src="https://github.com/user-attachments/assets/7c882964-0121-4240-b74c-41de994d2f23" alt="Admin Dashboard" width="400"/></td>
  </tr>
</table>

<h3>Recommendations</h3>
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/92b9bee1-7fc8-44b8-994a-793f5ca6c1de" alt="Recommended For You" width="400"/></td>
    <td><img src="https://github.com/user-attachments/assets/8c77681e-4691-4022-9ba8-4f2558a5e1ad" alt="People Also Search For" width="400"/></td>
  </tr>
</table>

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Google Maps API key
- Virtual environment (recommended)

### Dependencies

The project uses several key libraries:
- **Web Framework**: Flask 2.3.2
- **Database**: 
  - Flask-SQLAlchemy 3.1.1
  - psycopg2-binary 2.9.9 (PostgreSQL adapter)
- **Machine Learning**: 
  - TensorFlow 2.15.0
  - scikit-learn 1.3.2
  - Surprise 0.1
  - NumPy 1.24.3
- **Data Processing**: pandas 2.1.1
- **Authentication**: PyJWT 2.8.0
- **Utilities**: 
  - python-dotenv 1.0.1
  - requests 2.31.0
  - joblib 1.3.2
  - Werkzeug 2.3.7
- **Production Server**: gunicorn 21.2.0

### Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Create and activate a virtual environment:
```bash
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On Unix/MacOS
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```
GOMAPS_API_KEY=your_google_maps_api_key
```

5. Set up the database:
```bash
# Make sure PostgreSQL is running
# Update the database URI in app.py with your credentials:
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/dbname'
```

6. Run the application:
```bash
# Development
python app.py

# Production
gunicorn app:app
```

## 🏗️ Project Structure

```
├── app.py                 # Main application file
├── model.py              # Database models
├── People_also_search_for.py  # Collaborative filtering implementation
├── Recommended_for_you_nn.py  # Neural network recommendation system
├── templates/            # HTML templates
├── static/              # Static assets
├── admin/               # Admin dashboard
├── *.pkl               # Encoder files
└── *.keras             # Neural network model
```

## 🔧 Configuration

The system uses several machine learning models and encoders:
- `recommender_model.keras`: Neural network model for personalized recommendations
- `svd_model.pkl`: Collaborative filtering model
- Encoder files:
  - `user_encoder.pkl`: User data encoding
  - `interest_encoder.pkl`: Interest categories encoding
  - `pincode_encoder.pkl`: Location encoding
  - `weather_encoder.pkl`: Weather conditions encoding
  - `lat_scaler.pkl` & `lon_scaler.pkl`: Location scaling

## 📝 API Endpoints

- `/login` - User authentication
- `/signup` - New user registration
- `/recommend` - Get personalized recommendations
- `/recommend/context` - Get context-aware recommendations
- `/recommend/collaborative` - Get collaborative filtering recommendations
- `/search` - Search for places
- `/me` - Get current user information

## 🔒 Security

- JWT-based authentication with 15-minute expiry
- Password hashing using Werkzeug
- Secure cookie handling
- Environment variable protection
- SQL injection prevention through SQLAlchemy

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- Google Maps API for location data
- TensorFlow for neural network implementation
- Surprise library for collaborative filtering
- Flask for the web framework
- PostgreSQL for database management 

