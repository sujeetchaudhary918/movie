# process_titles.py
import json
import gzip
import os

# Find the downloaded file in the current directory
source_file = next((f for f in os.listdir('.') if f.startswith('movie_ids_') and f.endswith('.json.gz')), None)

if not source_file:
    print("Error: No 'movie_ids_...json.gz' file found in this directory.")
    print("Please download it from https://developers.themoviedb.org/docs/data-exports and place it here.")
else:
    print(f"Processing file: {source_file}...")
    movie_data = {}
    with gzip.open(source_file, 'rt', encoding='utf-8') as f:
        for line in f:
            movie = json.loads(line)
            # We only need the title and ID for our search
            if not movie.get('adult'): # Exclude adult titles
                movie_data[movie['original_title']] = movie['id']

    with open('movie_titles.json', 'w', encoding='utf-8') as f:
        json.dump(movie_data, f)

    print(f"Successfully created 'movie_titles.json' with {len(movie_data)} movies.")