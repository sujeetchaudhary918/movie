import streamlit as st
import requests
import urllib.parse
import json

# ✅ SET PAGE CONFIG
st.set_page_config(page_title="🎬 Media Recommender", layout="wide")

# --- CONFIGURATION ---
try:
    AUTH0_DOMAIN = st.secrets.auth0.domain
    CLIENT_ID = st.secrets.auth0.client_id
    CLIENT_SECRET = st.secrets.auth0.client_secret
    REDIRECT_URI = "http://localhost:8501"
    AUDIENCE = st.secrets.auth0.audience
    API_KEY = "3491d28df093be5b5ae5400fb1ac468b"
except (AttributeError, KeyError):
    st.error("Auth0 or TMDb secrets are not configured correctly in .streamlit/secrets.toml")
    st.stop()

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# --- INITIALIZE SESSION STATE ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'grid'
if 'selected_media_id' not in st.session_state: st.session_state.selected_media_id = None
if 'selected_media_type' not in st.session_state: st.session_state.selected_media_type = None
if 'current_pages' not in st.session_state: st.session_state.current_pages = {}
if 'family_mode' not in st.session_state: st.session_state.family_mode = True
if 'user_info' not in st.session_state: st.session_state.user_info = None
if 'search_results' not in st.session_state: st.session_state.search_results = []
if 'search_query' not in st.session_state: st.session_state.search_query = ""

# --- NAVIGATION & AUTHENTICATION HELPERS ---
def go_home():
    st.session_state.view_mode = 'grid'
    st.session_state.selected_media_id = None
    st.session_state.search_results = []
    st.session_state.search_query = ""
    st.session_state.current_pages = {}

def get_auth_url():
    params = {"response_type": "code", "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "scope": "openid profile email", "audience": AUDIENCE}
    return f"https://{AUTH0_DOMAIN}/authorize?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    payload = {"grant_type": "authorization_code", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code, "redirect_uri": REDIRECT_URI}
    response = requests.post(f"https://{AUTH0_DOMAIN}/oauth/token", json=payload)
    if response.status_code == 200:
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        user_info = requests.get(f"https://{AUTH0_DOMAIN}/userinfo", headers=headers)
        if user_info.status_code == 200: return user_info.json()
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

# --- TMDb API HELPERS ---
@st.cache_data
def get_genres(media_type):
    url = f"{BASE_URL}/genre/{media_type}/list?api_key={API_KEY}"
    response = requests.get(url)
    return {genre['name']: genre['id'] for genre in response.json()['genres']} if response.status_code == 200 else {}

@st.cache_data
def get_media_by_category(media_type, category, page=1):
    params = {'api_key': API_KEY, 'page': page, 'include_adult': not st.session_state.family_mode}
    url = f"{BASE_URL}/{media_type}/{category}"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 1)
    return [], 1

@st.cache_data
def discover_media_by_filter(media_type, page=1, **kwargs):
    params = {'api_key': API_KEY, 'page': page, 'include_adult': not st.session_state.family_mode, 'sort_by': 'popularity.desc'}
    params.update(kwargs)
    if st.session_state.family_mode and 'with_origin_country' not in kwargs:
        params['certification_country'] = 'US'
        params['certification.lte'] = 'PG-13' if media_type == 'movie' else 'TV-14'
    url = f"{BASE_URL}/discover/{media_type}"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 1)
    return [], 1

@st.cache_data
def get_media_by_genres(media_type, genre_ids, page=1):
    if not genre_ids: return [], 1
    url = f"{BASE_URL}/discover/{media_type}"
    params = {'api_key': API_KEY, 'with_genres': ",".join(map(str, genre_ids)), 'page': page, 'include_adult': not st.session_state.family_mode}
    if st.session_state.family_mode:
        params['certification_country'] = 'US'
        params['certification.lte'] = 'PG-13' if media_type == 'movie' else 'TV-14'
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 1)
    return [], 1

@st.cache_data
def multi_search(query, family_mode=False):
    url = f"{BASE_URL}/search/multi?api_key={API_KEY}&query={urllib.parse.quote(query)}&include_adult={not family_mode}"
    response = requests.get(url)
    return response.json().get('results', []) if response.status_code == 200 else []

@st.cache_data
def get_media_details(media_type, media_id):
    url = f"{BASE_URL}/{media_type}/{media_id}?api_key={API_KEY}&append_to_response=videos"
    return requests.get(url).json()

# --- UI DISPLAY FUNCTIONS ---
def display_media_grid(media_list, key_prefix):
    if not media_list: return
    cols = st.columns(5)
    for i, media in enumerate(media_list):
        with cols[i % 5]:
            title = media.get("title") or media.get("name")
            if media.get("poster_path"):
                st.image(f"{IMAGE_BASE}{media['poster_path']}", use_container_width=True)
                st.caption(f"**{title}**")
                if st.button("View Details", key=f"{key_prefix}_{media['id']}"):
                    st.session_state.view_mode = 'detail'
                    st.session_state.selected_media_id = media['id']
                    st.session_state.selected_media_type = media.get('media_type') or st.session_state.media_type
                    st.rerun()

def display_media_details(media_type, media_id):
    details = get_media_details(media_type, media_id)
    title = details.get('title') or details.get('name')
    overview = details.get('overview')
    release_date = details.get('release_date') or details.get('first_air_date')
    rating = details.get('vote_average', 0)
    st.subheader(title)
    col1, col2 = st.columns([1, 2])
    with col1:
        if details.get("poster_path"): st.image(f"{IMAGE_BASE}{details['poster_path']}", use_container_width=True)
    with col2:
        st.write(f"**⭐ Rating:** {rating:.1f}/10")
        st.write(f"**📅 First Aired:** {release_date}" if media_type == 'tv' else f"**📅 Release Date:** {release_date}")
        genres = [g['name'] for g in details.get('genres', [])]
        st.write(f"**🎭 Genres:** {', '.join(genres)}")
        st.write(f"**Overview:** {overview}")
        trailer = next((v for v in details.get("videos", {}, {}).get("results", []) if v['type'] == 'Trailer' and v['site'] == 'YouTube'), None)
        if trailer: st.video(f"https://www.youtube.com/watch?v={trailer['key']}")
    if media_type == 'tv' and details.get('seasons'):
        st.markdown("---")
        st.subheader("Seasons")
        for season in details['seasons']:
            if season.get('season_number', 0) == 0: continue
            with st.expander(f"Season {season.get('season_number')} ({season.get('episode_count')} episodes)"):
                scol1, scol2 = st.columns([1, 3])
                with scol1:
                    if season.get('poster_path'): st.image(f"{IMAGE_BASE}{season['poster_path']}")
                with scol2:
                    st.write(f"**Aired:** {season.get('air_date', 'N/A')}")
                    st.write(season.get('overview', 'No overview available.'))

def show_detail_view():
    if st.button("← Back to Browsing"):
        go_home(); st.rerun()
    trailer = next((v for v in details.get("videos", {}).get("results", []) if v['type'] == 'Trailer' and v['site'] == 'YouTube'), None)

def display_pagination_controls(category_key, total_pages):
    current_page = st.session_state.current_pages.get(category_key, 1)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Previous", key=f"prev_{category_key}", disabled=(current_page == 1)):
            st.session_state.current_pages[category_key] -= 1; st.rerun()
    with col2:
        st.markdown(f"<div style='text-align: center; margin-top: 5px;'>Page {current_page} of {min(total_pages, 500)}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("Next ➡️", key=f"next_{category_key}", disabled=(current_page >= min(total_pages, 500))):
            st.session_state.current_pages[category_key] += 1; st.rerun()

def display_search_feature(search_type='title'):
    if search_type == 'title':
        with st.form(key='title_search_form'):
            search_query = st.text_input("Search for a title", value=st.session_state.search_query)
            submit_button = st.form_submit_button(label='Search')
        if submit_button and search_query:
            st.session_state.search_query = search_query
            results = multi_search(search_query.strip(), family_mode=st.session_state.family_mode)
            media_results = [res for res in results if res.get('media_type') in ['movie', 'tv']]
            st.session_state.search_results = media_results
            st.rerun()
    
    # Keyword search logic can be added here if needed in the future

# --- HEADER AND MAIN UI COMPONENTS ---
def display_header():
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("🎬 Media Recommender", use_container_width=True):
            go_home(); st.rerun()
    with col2:
        st.session_state.family_mode = st.toggle("👪 Family Mode", value=st.session_state.family_mode)
    with col3:
        if st.session_state.user_info is None:
            st.link_button("Login / Sign Up", get_auth_url())
    st.radio("Select Media Type", ['movie', 'tv'], key='media_type', format_func=lambda x: "Movies" if x == 'movie' else "TV Shows", horizontal=True)

# UPDATED: --- LOGGED-OUT HOMEPAGE with corrected category structure ---
def logged_out_homepage():
    st.write("Browse popular categories or log in for a personalized experience.")
    
    # Display search results if they exist, otherwise show browse view
    if st.session_state.search_results or st.session_state.search_query:
        st.subheader("Search Results")
        if st.session_state.search_results:
            display_media_grid(st.session_state.search_results, key_prefix="search")
        else:
            st.warning(f"No results found for '{st.session_state.search_query}'.")
    else:
        display_search_feature('title')
        st.markdown("---")
        media_type = st.session_state.media_type
        # This dictionary structure is now consistent
        categories = {
            'movie': {
                "🔥 Popular Movies": ("popular", {}),
                "⭐ Top Rated Movies": ("top_rated", {}),
                "🇮🇳 Bollywood": ("discover", {'with_origin_country': 'IN', 'with_original_language': 'hi'}),
            },
            'tv': {
                "🔥 Popular TV": ("popular", {}),
                "⭐ Top Rated TV": ("top_rated", {}),
                "🇮🇳 Indian TV": ("discover", {'with_origin_country': 'IN'})
            }
        }
        active_categories = categories.get(media_type, {})
        tab_names = list(active_categories.keys())
        if tab_names:
            tabs = st.tabs(tab_names)
            for i, tab in enumerate(tabs):
                with tab:
                    category_key = tab_names[i]
                    category_type, filters = active_categories[category_key]
                    page = st.session_state.current_pages.get(category_key, 1)
                    if category_type == "discover":
                        media, total_pages = discover_media_by_filter(media_type, page=page, **filters)
                    else:
                        media, total_pages = get_media_by_category(media_type, category_type, page=page)
                    if media:
                        display_media_grid(media, key_prefix=category_key.replace(" ", "_"))
                        st.markdown("---")
                        display_pagination_controls(category_key, total_pages)
                    else:
                        st.info("No results found for this category.")

# --- MAIN APP (for logged-in users) ---
def main_app():
    user = st.session_state.user_info
    username = user.get('nickname', user.get('email'))
    st.sidebar.header(f"Welcome, {user.get('name', '')}!")
    st.sidebar.image(user.get('picture'), width=100)
    st.sidebar.link_button("Logout", get_logout_url())
    media_type = st.session_state.media_type
    st.sidebar.header(f"Your Favorite {media_type.replace('_', ' ').capitalize()} Genres")
    all_genres = get_genres(media_type)
    all_preferences = load_user_preferences()
    user_prefs = all_preferences.get(username, {})
    user_saved_genres = user_prefs.get(f"{media_type}_genres", [])
    selected_genres = st.sidebar.multiselect("Select genres:", options=list(all_genres.keys()), default=user_saved_genres)
    if selected_genres != user_saved_genres:
        if "genres" not in user_prefs: user_prefs["genres"] = {}
        user_prefs[f"{media_type}_genres"] = selected_genres
        all_preferences[username] = user_prefs
        save_user_preferences(all_preferences)
        st.sidebar.success("Preferences saved!")
        st.rerun()

    # Main Page Content
    if st.session_state.search_results or st.session_state.search_query:
        st.subheader("Search Results")
        if st.session_state.search_results:
            display_media_grid(st.session_state.search_results, key_prefix="search")
        else:
            st.warning(f"No results found for '{st.session_state.search_query}'.")
    else:
        display_search_feature('title')
        st.markdown("---")
        if selected_genres:
            st.header(f"{media_type.capitalize()}s Based on Your Genres")
            category_key = f"{media_type}_genre_prefs"
            page = st.session_state.current_pages.get(category_key, 1)
            genre_ids = [all_genres[name] for name in selected_genres if name in all_genres]
            media, total_pages = get_media_by_genres(media_type, genre_ids, page=page)
            if media:
                display_media_grid(media, key_prefix="genre_results")
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
col_left, col_main, col_right = st.columns([1, 6, 1])
with col_main:
    display_header()
    if st.session_state.view_mode == 'detail':
        show_detail_view()
    else:
        if st.session_state.user_info is None:
            logged_out_homepage()
        else:
            main_app()