# 🌍 Discover Places

> A smart, lightweight web app to help users explore new places and get personalized recommendations — powered by machine learning and Flask.

---

## 🔎 What is Discover Places?

**Discover Places** is a full-stack Python web application that allows users to:
- Explore interesting locations
- Like and save their favorite spots
- Receive personalized place recommendations

The platform uses **JWT-based authentication**, a **PostgreSQL database**, and two ML-based engines: **content-based filtering** and **popularity-based ranking** — all served via a clean Flask backend and HTML frontend.

---

## ✨ Features

- 🔐 JWT-based Login and Signup
- 🏙️ Browse curated places
- ❤️ Like places you enjoy
- 🧠 Personalized Recommendations:
  - Content-Based Filtering
  - Popularity-Based Ranking
- 🗺️ One-click Google Maps Redirection
- 🗃️ PostgreSQL-powered backend for data persistence
- 📄 Modular ML code for easy extensibility

---

## 🖼️ UI Preview

# 📝 Signup & Login
<p align="center"> <img src="static/img/Signup.png" alt="Signup Page" width="45%" /> <img src="static/img/Login.png" alt="Login Page" width="45%" /> </p>

# 🔐 Admin & 🏠 Home 
<p align="center"> <img src="static/img/Admin%20Dashboard.png" alt="Home Page" width="50%" /> <img src="static/img/Search%20Places.png" alt="Home Page" width="50%" /> </p>

# 🔥 Content-Based & Popularity-Based Recommendation
<p align="center">  <img src="static/img/Recommended%20For%20You.png" alt="Content-Based Recommendation" width="45%" /> <img src="static/img/People%20Also%20Search%20For.png" alt="Popularity-Based Recommendation" width="45%" /> </p>

---

## 🧰 Tech Stack

| Layer        | Technology               |
|--------------|---------------------------|
| Backend      | Python, Flask             |
| Frontend     | HTML, CSS, Bootstrap      |
| Database     | PostgreSQL                |
| Auth         | JWT (JSON Web Tokens)     |
| ML Models    | Scikit-learn, Pandas      |
| Maps         | GoMapsPro (fetching), Google Maps (navigation) |

---

## 🧠 Recommendation System

The app features two types of recommendation models:

1. **Content-Based Filtering**
   - Recommends places similar to the ones a user has liked
   - Based on metadata like category, tags, etc.

2. **Popularity-Based Ranking**
   - Ranks places by likes/views across all users

The code is located inside the `recommendation/` folder and is cleanly modularized for reusability.

---

## 📁 Project Structure

```
Discover-Places/
├── recommendation/ # ML models (content-based, popularity)
│ ├── content_based.py
│ ├── popularity.py
│ └── init.py
├── static/
│ └── img/ # Place images
├── templates/ # HTML templates
│ ├── index.html
│ ├── about.html
│ └── contact.html
├── database/ # DB scripts or migrations (if any)
├── app.py # Main Flask app
├── requirements.txt
├── README.md
└── ...
```

---

## 🚀 Getting Started

### 1. Clone the Repo
```
git clone https://github.com/VipranshOjha/Discover-Places.git
cd Discover-Places
```

### 2. Create Virtual Environment
```
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL
Ensure PostgreSQL is installed and running

Create a database (e.g., discover_places)

Add your DB config in app.py or a .env file

### 5. Run the App
```
python app.py
Open http://127.0.0.1:5000 in your browser.
```
---

## 📍 Mapping Logic
GoMapsPro API is used to fetch and display nearby locations

On click, the app redirects users to Google Maps for directions to that place

---

## 🛠️ Future Enhancements
✅ API-based version of the recommendation system

🌐 Deployment on Render/Railway

👤 User dashboards and profiles

💬 Add reviews or comments for places

---

## 🙌 Contributing
Pull requests are welcome! Please open an issue first for major changes.

---

## 📬 Connect with Me
LinkedIn

GitHub

---

Built with ❤️, PostgreSQL, Flask, and a curiosity for exploration.
