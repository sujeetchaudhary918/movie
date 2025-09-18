import streamlit as st
import requests
import urllib.parse
import json
from thefuzz import process, fuzz

# ✅ SET PAGE CONFIG AS THE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="🎬 Movie Recommender", layout="wide")

# --- AUTH0 CONFIGURATION (from secrets.toml) ---
try:
    AUTH0_DOMAIN = st.secrets.auth0.domain
    CLIENT_ID = st.secrets.auth0.client_id
    CLIENT_SECRET = st.secrets.auth0.client_secret
    REDIRECT_URI = "http://localhost:8501"
    AUDIENCE = st.secrets.auth0.audience
except (AttributeError, KeyError):
    st.error("Auth0 secrets are not configured. Please add them to your .streamlit/secrets.toml file.")
    st.stop()

# --- TMDB API CONFIGURATION ---
API_KEY = "3491d28df093be5b5ae5400fb1ac468b"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# --- INITIALIZE SESSION STATE ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'grid'
if 'selected_movie_id' not in st.session_state: st.session_state.selected_movie_id = None
if 'current_pages' not in st.session_state: st.session_state.current_pages = {}
if 'family_mode' not in st.session_state: st.session_state.family_mode = True
if 'user_info' not in st.session_state: st.session_state.user_info = None
if 'search_query' not in st.session_state: st.session_state.search_query = ""

# --- NAVIGATION HELPER FUNCTION ---
def go_home():
    st.session_state.view_mode = 'grid'
    st.session_state.selected_movie_id = None
    st.session_state.search_query = ""
    st.session_state.current_pages = {}

# --- AUTHENTICATION & USER PREFERENCES HELPER FUNCTIONS ---
def get_auth_url():
    params = {"response_type": "code", "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "scope": "openid profile email", "audience": AUDIENCE}
    return f"https://{AUTH0_DOMAIN}/authorize?{urllib.parse.urlencode(params)}"
def exchange_code_for_token(code):
    token_payload = {"grant_type": "authorization_code", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code, "redirect_uri": REDIRECT_URI}
    token_response = requests.post(f"https://{AUTH0_DOMAIN}/oauth/token", json=token_payload)
    if token_response.status_code == 200:
        token_data = token_response.json()
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        user_info_response = requests.get(f"https://{AUTH0_DOMAIN}/userinfo", headers=headers)
        if user_info_response.status_code == 200: return user_info_response.json()
    return None
def get_logout_url():
    params = {"client_id": CLIENT_ID, "returnTo": REDIRECT_URI}
    return f"https://{AUTH0_DOMAIN}/v2/logout?{urllib.parse.urlencode(params)}"
def load_user_preferences():
    try:
        with open('user_preferences.json', 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}
def save_user_preferences(prefs):
    with open('user_preferences.json', 'w') as f: json.dump(prefs, f, indent=4)

# --- TMDb API HELPER FUNCTIONS ---
@st.cache_data
def get_genres(*args, **kwargs):
    url = f"{BASE_URL}/genre/movie/list?api_key={API_KEY}"
    response = requests.get(url)
    return {genre['name']: genre['id'] for genre in response.json()['genres']} if response.status_code == 200 else {}
@st.cache_data
def get_movies_by_category(category, page=1, region_filters=None, family_mode=False):
    params = {'api_key': API_KEY, 'page': page, 'include_adult': not family_mode}
    if region_filters:
        url = f"{BASE_URL}/discover/movie"
        params.update(region_filters)
        if family_mode:
            params['certification_country'] = 'US'
            params['certification.lte'] = 'PG-13'
            params['without_genres'] = '27,53'
    else:
        url = f"{BASE_URL}/movie/{category}"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 1)
    return [], 1
@st.cache_data
def get_movies_by_genres(genre_ids, page=1, family_mode=False):
    if not genre_ids: return [], 1
    url = f"{BASE_URL}/discover/movie"
    params = {'api_key': API_KEY, 'with_genres': ",".join(map(str, genre_ids)), 'page': page, 'include_adult': not family_mode}
    if family_mode:
        params['certification_country'] = 'US'
        params['certification.lte'] = 'PG-13'
        params['without_genres'] = '27,53'
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 1)
    return [], 1
@st.cache_data
def search_movie(query, family_mode=False):
    url = f"{BASE_URL}/search/movie?api_key={API_KEY}&query={urllib.parse.quote(query)}&include_adult={not family_mode}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else {}
@st.cache_data
def get_similar_movies(movie_id, family_mode=False):
    url = f"{BASE_URL}/movie/{movie_id}/similar?api_key={API_KEY}&include_adult={not family_mode}"
    return requests.get(url).json()
@st.cache_data
def get_movie_details(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&append_to_response=release_dates,videos"
    return requests.get(url).json()
@st.cache_data
def load_movie_titles(family_mode=False):
    try:
        with open('movie_titles.json', 'r', encoding='utf-8') as f:
            titles_map = json.load(f)
        if family_mode:
            EXPLICIT_KEYWORDS = ["fifty shades", "sex", "porn", "adult"]
            clean_titles = {title: movie_id for title, movie_id in titles_map.items() if not any(keyword in title.lower() for keyword in EXPLICIT_KEYWORDS)}
            return clean_titles
        return titles_map
    except FileNotFoundError:
        return None
def find_closest_match(query, titles_map):
    if not query: return None, None
    best_match = process.extractOne(query.lower(), titles_map.keys(), scorer=fuzz.WRatio, score_cutoff=85)
    if best_match:
        title = best_match[0]
        return title, titles_map[title]
    return None, None

# --- UI DISPLAY FUNCTIONS ---
def display_movies_grid(movies, key_prefix):
    display_count = (len(movies) // 5) * 5
    movies_to_display = movies[:display_count]
    if not movies_to_display:
        st.info("No movies to display in this category.")
        return
    cols = st.columns(5)
    for i, movie in enumerate(movies_to_display):
        with cols[i % 5]:
            if movie.get("poster_path"):
                st.image(f"{IMAGE_BASE}{movie['poster_path']}", use_container_width=True)
                st.caption(f"**{movie['title']}**")
                if st.button("View Details", key=f"{key_prefix}_{movie['id']}"):
                    st.session_state.view_mode = 'detail'
                    st.session_state.selected_movie_id = movie['id']
                    st.rerun()

def display_movie_details(movie_id):
    details = get_movie_details(movie_id)
    st.subheader(details.get('title', ''))
    col1, col2 = st.columns([1, 2])
    with col1:
        if details.get("poster_path"): st.image(f"{IMAGE_BASE}{details['poster_path']}", use_container_width=True)
    with col2:
        st.write(f"**⭐ Rating:** {details.get('vote_average', 0):.1f}/10")
        st.write(f"**📅 Release Date:** {details.get('release_date', 'N/A')}")
        genres = [g['name'] for g in details.get('genres', [])]
        st.write(f"**🎭 Genres:** {', '.join(genres)}")
        st.write(f"**Overview:** {details.get('overview', 'No description available.')}")
        videos = details.get("videos", {}).get("results", [])
        trailer = next((v for v in videos if v['type'] == 'Trailer' and v['site'] == 'YouTube'), None)
        if trailer: st.video(f"https://www.youtube.com/watch?v={trailer['key']}")

def show_detail_view():
    if st.button("← Back to movie list"):
        go_home()
        st.rerun()
    display_movie_details(st.session_state.selected_movie_id)

def display_pagination_controls(category_key, total_pages):
    current_page = st.session_state.current_pages.get(category_key, 1)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Previous", key=f"prev_{category_key}", disabled=(current_page == 1)):
            st.session_state.current_pages[category_key] -= 1
            st.rerun()
    with col2:
        st.markdown(f"<div style='text-align: center; margin-top: 5px;'>Page {current_page} of {min(total_pages, 500)}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("Next ➡️", key=f"next_{category_key}", disabled=(current_page >= total_pages or current_page >= 500)):
            st.session_state.current_pages[category_key] += 1
            st.rerun()

# UPDATED: --- REUSABLE SEARCH COMPONENT with corrected indentation ---
def display_search_feature():
    st.header("Find Movies Similar to One You Like")
    query = st.text_input("Search for a movie:", value=st.session_state.search_query, key="search_input")
    st.session_state.search_query = query
    
    if query:
        family_mode = st.session_state.family_mode
        results_data = search_movie(query.strip(), family_mode=family_mode)
        
        # Check if the search was successful and has results
        if results_data and "results" in results_data and len(results_data["results"]) > 0:
            options = {f"{m['title']} ({m.get('release_date','N/A')[:4]})": m["id"] for m in results_data["results"]}
            choice = st.selectbox("Select a movie from the search results:", list(options.keys()), key="search_choice")
            movie_id = options[choice]
            
            st.markdown("---")
            display_movie_details(movie_id)
            st.markdown("---")
            
            st.subheader("🍿 Recommended Movies")
            similar_movies = get_similar_movies(movie_id, family_mode=family_mode).get("results", [])
            if similar_movies:
                display_movies_grid(similar_movies, key_prefix="similar")
            else:
                st.warning("No similar movies found.")
        
        # This 'else' block runs if the search returned no results
        else:
            movie_titles = load_movie_titles(family_mode=family_mode)
            if movie_titles:
                corrected_title, movie_id = find_closest_match(query, movie_titles)
                if corrected_title:
                    st.info(f"Did you mean **{corrected_title}**?")
                    if st.button(f"Search for '{corrected_title}'"):
                        st.session_state.search_query = corrected_title
                        st.rerun()

# --- HEADER AND LOGIN/LOGOUT BUTTONS ---
def display_header():
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("🎬 Movie Recommender", use_container_width=True):
            go_home()
            st.rerun()
    with col2:
        st.session_state.family_mode = st.toggle("👪 Family Mode", value=st.session_state.family_mode)
    with col3:
        with st.container():
            if st.session_state.user_info is None:
                st.link_button("Login / Sign Up", get_auth_url())
            else:
                st.sidebar.button("Logout", on_click=lambda: st.markdown(f'<meta http-equiv="refresh" content="0; url={get_logout_url()}">', unsafe_allow_html=True))

# --- LOGGED-OUT HOMEPAGE ---
def logged_out_homepage():
    st.write("Browse popular categories or log in for a personalized experience.")
    display_search_feature()
    st.markdown("---")
    categories = {"🔥 Popular": ("popular", {}), "🆕 Now Playing": ("now_playing", {}), "⭐ Top Rated": ("top_rated", {}), "🇮🇳 Bollywood": ("discover", {'with_origin_country': 'IN', 'with_original_language': 'hi'}), "🇺🇸 Hollywood": ("discover", {'with_origin_country': 'US'})}
    tabs = st.tabs(list(categories.keys()))
    for i, tab in enumerate(tabs):
        with tab:
            category_key = list(categories.keys())[i]
            category_type, filters = categories[category_key]
            if category_key not in st.session_state.current_pages:
                st.session_state.current_pages[category_key] = 1
            page = st.session_state.current_pages[category_key]
            movies, total_pages = get_movies_by_category(category_type, page=page, region_filters=filters, family_mode=st.session_state.family_mode)
            if movies:
                display_movies_grid(movies, key_prefix=category_key.replace(" ", "_"))
                st.markdown("---")
                display_pagination_controls(category_key, total_pages)
            else:
                st.info("No movies to display in this category right now.")

# --- LOGGED-IN MAIN APP ---
def main_app():
    user = st.session_state.user_info
    username = user.get('nickname', user.get('email'))
    st.sidebar.header(f"Welcome, {user.get('name', '')}!")
    st.sidebar.image(user.get('picture'), width=100)
    st.sidebar.header("Your Favorite Genres")
    all_genres = get_genres()
    all_preferences = load_user_preferences()
    user_saved_genres = all_preferences.get(username, [])
    selected_genres = st.sidebar.multiselect("Select your genres:", options=list(all_genres.keys()), default=user_saved_genres)
    if selected_genres != user_saved_genres:
        all_preferences[username] = selected_genres
        save_user_preferences(all_preferences)
        st.session_state.current_pages['genre_prefs'] = 1
        st.sidebar.success("Preferences saved!")
        st.rerun()
    display_search_feature()
    st.markdown("---")
    if selected_genres:
        st.header("Movies Based on Your Favorite Genres")
        category_key = "genre_prefs"
        page = st.session_state.current_pages.get(category_key, 1)
        genre_ids = [all_genres[name] for name in selected_genres]
        movies, total_pages = get_movies_by_genres(genre_ids, page=page, family_mode=st.session_state.family_mode)
        if movies:
            display_movies_grid(movies, key_prefix="genre")
            st.markdown("---")
            display_pagination_controls(category_key, total_pages)

# --- LOGIN/LOGOUT AND APP ROUTING ---
query_params = st.query_params
if "code" in query_params and st.session_state.user_info is None:
    user_info = exchange_code_for_token(query_params["code"])
    if user_info:
        st.session_state.user_info = user_info
        st.query_params.clear()
        st.rerun()

# --- MAIN ROUTER ---
display_header()
if st.session_state.view_mode == 'detail':
    show_detail_view()
else:
    if st.session_state.user_info is None:
        logged_out_homepage()
    else:
        main_app()