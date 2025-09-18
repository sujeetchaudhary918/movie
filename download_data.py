# download_data.py
import requests
from datetime import datetime

# --- CONFIGURATION ---
# Paste your TMDb API Key here. It's the same one from your main app.
TMDB_API_KEY = "3491d28df093be5b5ae5400fb1ac468b"
# ---------------------

def download_movie_ids_file():
    """
    Downloads the daily movie IDs export file from TMDb using an API key.
    """
    if TMDB_API_KEY == "YOUR_TMDB_API_KEY_HERE":
        print("❌ Error: Please paste your TMDb API key into the script.")
        return

    # 1. Construct the filename for today's date
    today = datetime.now().strftime('%m_%d_%Y')
    file_name = f"movie_ids_{today}.json.gz"
    download_url = f"http://files.tmdb.org/p/exports/{file_name}"

    # 2. Make the authenticated request
    print(f"⬇️  Downloading {file_name} from TMDb...")
    params = {'api_key': TMDB_API_KEY}
    
    try:
        response = requests.get(download_url, params=params, stream=True)
        
        # 3. Check if the download was successful
        if response.status_code == 200:
            # 4. Save the file
            with open(file_name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ Download successful! File saved as '{file_name}'.")
            print("\n➡️  Next, run the 'process_titles.py' script to prepare the data for the app.")
        else:
            print(f"❌ Error: Failed to download file. Status Code: {response.status_code}")
            print("   Please check your API key and make sure the file for today exists.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    download_movie_ids_file()