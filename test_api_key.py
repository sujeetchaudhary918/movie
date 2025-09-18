# test_api_key.py
import requests

# --- CONFIGURATION ---
# Paste the same TMDb API Key here.
TMDB_API_KEY = "3491d28df093be5b5ae5400fb1ac468b"
# ---------------------

def test_key():
    if TMDB_API_KEY == "YOUR_TMDB_API_KEY_HERE":
        print("❌ Error: Please paste your TMDb API key into the script.")
        return

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query=Superman"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Success! Your API key is working correctly.")
            print("   This means the issue is specific to downloading the export files.")
        elif response.status_code == 401:
            print("❌ Failure! Status Code 401: Invalid API Key.")
            print("   Please double-check that you copied the key correctly from the TMDb website.")
        else:
            print(f"❌ Failure! Received Status Code: {response.status_code}")
            print("   There may be an issue with your TMDb account or the API service.")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    test_key()