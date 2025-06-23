import pickle
import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv
import os
import random
import time

# Load environment variables
load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")

@st.cache_data(show_spinner=False)
def search_tmdb_by_title(title, year=None):
    """Search TMDB for a movie by title (and optionally year) and return the first movie's ID."""
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={requests.utils.quote(title)}"
        if year:
            url += f"&year={year}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        results = data.get('results', [])
        if results:
            return results[0]['id']
    except Exception as e:
        pass
    return None

@st.cache_data(show_spinner=False)
def fetch_movie_details(movie_id, title, year=None):
    max_retries = 5
    delay = 2
    last_error = ""
    for attempt in range(max_retries):
        try:
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                # Fallback: Try searching by title
                fallback_id = search_tmdb_by_title(title, year)
                if fallback_id:
                    url = f"https://api.themoviedb.org/3/movie/{fallback_id}?api_key={API_KEY}&language=en-US"
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    poster_path = data.get('poster_path')
                    poster_url = "https://image.tmdb.org/t/p/w500/" + poster_path if poster_path else "https://via.placeholder.com/300x450.png?text=No+Poster"
                    overview = data.get('overview', 'No description available.')
                    rating = data.get('vote_average', 'N/A')
                    genres = ', '.join([genre['name'] for genre in data.get('genres', [])])
                    return poster_url, overview, rating, genres
                else:
                    return (
                        "https://via.placeholder.com/300x450.png?text=Not+Found",
                        f"Movie '{title}' not found in TMDB (ID: {movie_id}).",
                        "N/A",
                        "N/A"
                    )
            response.raise_for_status()
            data = response.json()
            poster_path = data.get('poster_path')
            poster_url = "https://image.tmdb.org/t/p/w500/" + poster_path if poster_path else "https://via.placeholder.com/300x450.png?text=No+Poster"
            overview = data.get('overview', 'No description available.')
            rating = data.get('vote_average', 'N/A')
            genres = ', '.join([genre['name'] for genre in data.get('genres', [])])
            return poster_url, overview, rating, genres
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 1
            else:
                # Friendly message for persistent connection errors
                if "Connection reset by peer" in last_error or "Connection aborted" in last_error:
                    user_message = (
                        "TMDB API is temporarily unavailable or rate-limited. "
                        "Please check your internet connection, your TMDB API key, or try again later."
                    )
                else:
                    user_message = f"No description available (API error: {last_error})"
                return (
                    "https://via.placeholder.com/300x450.png?text=Error",
                    user_message,
                    "N/A",
                    "N/A"
                )

def recommend(movie):
    try:
        movie_index = movies[movies['title'] == movie].index[0]
    except IndexError:
        st.error("Selected movie not found in database.")
        return [], []
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies = []
    recommended_movie_details = []

    for i in movies_list:
        movie_id = movies.iloc[i[0]]['movie_id']
        title = movies.iloc[i[0]]['title']
        # If you have a 'year' column, you can use it here for better search accuracy
        year = movies.iloc[i[0]].get('year', None)
        poster, overview, rating, genres = fetch_movie_details(movie_id, title, year)
        recommended_movies.append(title)
        recommended_movie_details.append({
            "poster": poster,
            "overview": overview,
            "rating": rating,
            "genres": genres
        })

    return recommended_movies, recommended_movie_details

def random_recommend():
    random_movie = random.choice(movies['title'].values)
    return recommend(random_movie), random_movie

st.set_page_config(page_title="Movie Recommender", layout="wide")
st.header('🎬 Movie Recommender System')

try:
    data = pickle.load(open('movie_dict.pkl', 'rb'))
    movies = pd.DataFrame(data)
    similarity = pickle.load(open('similarity.pkl', 'rb'))
except Exception as e:
    st.error("Required data files not found or corrupted. Please ensure 'movie_dict.pkl' and 'similarity.pkl' are present.")
    st.stop()

movie_list = movies['title'].values
selected_movie = st.selectbox("Type or select a movie from the dropdown", movie_list)

if st.button('Show Recommendation'):
    recommended_movie_names, recommended_movie_details = recommend(selected_movie)
    if recommended_movie_names:
        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.image(recommended_movie_details[i]["poster"])
                st.markdown(f"**{recommended_movie_names[i]}**")
                st.caption(f"⭐ {recommended_movie_details[i]['rating']} | {recommended_movie_details[i]['genres']}")
                st.write(recommended_movie_details[i]["overview"])
    else:
        st.info("No recommendations available.")

if st.button('Surprise Me! (Random Recommendation)'):
    (recommended_movie_names, recommended_movie_details), random_movie = random_recommend()
    st.subheader(f"Randomly selected: {random_movie}")
    if recommended_movie_names:
        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.image(recommended_movie_details[i]["poster"])
                st.markdown(f"**{recommended_movie_names[i]}**")
                st.caption(f"⭐ {recommended_movie_details[i]['rating']} | {recommended_movie_details[i]['genres']}")
                st.write(recommended_movie_details[i]["overview"])
    else:
        st.info("No recommendations available.")