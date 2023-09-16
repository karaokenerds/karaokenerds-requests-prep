import requests
from bs4 import BeautifulSoup
import yt_dlp as ydl

# Importing necessary functions from your package
from fetch_lyrics_from_genius.fetch_lyrics import clean_lyrics, write_lyrics_file
import lyricsgenius

# Step 1: Scrape the HTML table to get the top 30 requests.

# URL from which the HTML content will be fetched
url = "https://karaokenerds.com/Request/?sort=votes"

# Step 1: Fetch the HTML content and then scrape the table to get the top 30 requests.
response = requests.get(url)
response.raise_for_status()  # This will raise an error if the HTTP request returned an error status
html_content = response.text

soup = BeautifulSoup(html_content, 'html.parser')
table = soup.find('table', id='requests')
rows = table.find('tbody').find_all('tr')

top_requests = []
for row in rows:
    artist = row.find_all('td')[1].a.text
    title = row.find_all('td')[2].a.text
    top_requests.append((artist, title))
    if len(top_requests) == 30:
        break

# Step 2 and 3: For each request, search YouTube and get the top result's ID.
def get_youtube_id(query):
    ydl_opts = {'quiet': True, 'default_search': 'ytsearch', 'extract_flat': True}
    with ydl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(query, download=False)
        return info_dict['entries'][0]['id']

# Step 4: Download audio using yt-dlp
def download_audio(youtube_id, filename):
    ydl_opts = {
        'format': 'ba',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': f'{filename}.%(ext)s'
    }
    with ydl.YoutubeDL(ydl_opts) as youtube_dl_instance:
        youtube_dl_instance.download([f'https://www.youtube.com/watch?v={youtube_id}'])


# Step 5: Fetch lyrics from Genius
def fetch_lyrics_from_genius(artist, title):
    # Using the Genius API token from an environment variable
    genius = lyricsgenius.Genius(os.environ['GENIUS_API_TOKEN'])
    song = genius.search_song(title, artist)
    if song:
        lyrics = clean_lyrics(song.lyrics)
        write_lyrics_file(song.title, song.artist, lyrics)
        print(f"Lyrics for {title} by {artist} fetched successfully.")
    else:
        print(f"Could not find lyrics for {title} by {artist}.")

for artist, title in top_requests:
    query = f"{artist} {title}"
    youtube_id = get_youtube_id(query)
    filename = f"{artist} - {title} ({youtube_id})"
    download_audio(youtube_id, filename)
    fetch_lyrics_from_genius(artist, title)

print("All songs downloaded and lyrics fetched!")