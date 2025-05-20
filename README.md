# 🌍 Discover Places

An intelligent, lightweight platform to discover, recommend, and explore places — built with Flask, HTML, and machine learning magic.

---

## 🧠 What is *Discover Places*?

**Discover Places** is a web-based application that helps users find interesting places, get smart recommendations, and navigate to them using Google Maps. Unlike traditional search engines, this platform learns from **user preferences** and **place data** to offer relevant suggestions using **machine learning models**.

✅ Think TripAdvisor meets a personal recommender, but simpler and smarter.

---

## ✨ Features

- 🔐 User login & registration (JWT Auth)
- 🏞️ Browse & discover new places
- ❤️ Like places you enjoy
- 📍 Redirect to Google Maps for navigation
- 📈 Smart recommendations using ML
- 🧠 Two recommendation systems:
  - Content-Based Filtering
  - Popularity-Based Ranking
  - 
---

## 🖼️ UI Preview

# Signup Page
![Signup Page](static/img/Signup.png)
# Login Page 
![Login Page](static/img/Login.png) 
# Home Page 
![Home Page](static/img/Search%20Places.png)
# Recommendation 
Content-Based Filtering
![Recommend](static/img/Recommended%20For%20You.png)

Popularity-Based Ranking
![Recommend](static/img/People%20Also%20Search%20For.png)

---

## 🧰 Tech Stack

| Layer       | Technology             |
|-------------|------------------------|
| 🌐 Frontend | HTML, CSS, JavaScript   |
| 🧠 Backend  | Python, Flask          |
| 🧪 ML Models | Scikit-learn, Pandas   |
| 📍 Maps     | GoMapsPro API (fetching), Google Maps (redirection) |

---

## 📦 Folder Structure

```

Discover-Places/
├── templates/           # HTML pages
├── static/
│   └── img/             # Uploaded images
├── recommendation/
│   ├── content\_based.py
│   ├── popularity.py
│   └── **init**.py
├── app.py               # Flask app
├── requirements.txt     # Dependencies
├── README.md            # You’re here!
└── ...

````

---

## 🚀 Getting Started

### 1. Clone the Repo

```bash
git clone https://github.com/VipranshOjha/Discover-Places.git
cd Discover-Places
````

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Run the Flask App

```bash
python app.py
```

> App runs locally at: `http://127.0.0.1:5000`

---

## 🧠 Recommendation Engines

Inside the `recommendation/` folder:

* `content_based.py`: Uses metadata similarity (e.g., category, tags) to find similar places.
* `popularity.py`: Ranks based on user interactions (likes, views, etc.).

Each can be imported and run independently or integrated directly into Flask routes.

---

## 📍 How Mapping Works

* **GoMapsPro API** is used to fetch detailed place data.
* When a user clicks the address, they are redirected to **Google Maps** for directions.

---

## 🙌 Contributing

Got a feature idea or found a bug?
Feel free to [open an issue](https://github.com/VipranshOjha/Discover-Places/issues) or submit a pull request!

---

## 📬 Connect with Me

* [LinkedIn](https://www.linkedin.com/in/vipransh-ojha)
* [GitHub](https://github.com/VipranshOjha)

---

> Built with Flask, and a curious mind 🧠💡

```
