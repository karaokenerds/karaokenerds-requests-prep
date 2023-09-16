import requests
import os
from bs4 import BeautifulSoup
import yt_dlp as ydl_module
import logging
from fetch_lyrics_from_genius.fetch_lyrics import clean_lyrics, write_lyrics_file
import lyricsgenius

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

URL = "https://karaokenerds.com/Request/?sort=votes"
CACHE_FILE = "karaokenerds_cache.html"


def fetch_top_requests(url):
    logger.info("Fetching top requests from %s", url)
    html_content = fetch_content_from_url(url)
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", id="requests")
    rows = table.find("tbody").find_all("tr")
    top_requests = [
        (row.find_all("td")[1].a.text, row.find_all("td")[2].a.text) for row in rows
    ][:30]
    return top_requests


def fetch_content_from_url(url):
    """Fetch content from URL and cache it in a file."""
    if os.path.exists(CACHE_FILE):
        logger.info(f"Reading content from cache: {CACHE_FILE}")
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return file.read()
    else:
        logger.info(f"Fetching content from {url}")
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        with open(CACHE_FILE, "w", encoding="utf-8") as file:
            file.write(content)
        return content

        
def get_youtube_id(query):
    ydl_opts = {'format': 'bestaudio', 'noplaylist': 'True', 'extract_flat': True}
    with ydl_module.YoutubeDL(ydl_opts) as ydl:
        try:
            # Try to directly get the video assuming the query might be a URL or video ID
            video = ydl.extract_info(query, download=False)
        except:
            # If direct retrieval fails, then search for it
            video = ydl.extract_info(f"ytsearch1:{query}", download=False)['entries'][0]
        if video:
            youtube_id = video.get('id')
            return youtube_id
        else:
            logger.warning(f"No YouTube results found for query: {query}")
            logger.debug(f"info_dict: {info_dict}")
            return None



def download_audio(youtube_id, filename):
    ydl_opts = {
        "format": "ba",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "outtmpl": f"{filename}.%(ext)s",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
    }

    with ydl_module.YoutubeDL(ydl_opts) as youtube_dl_instance:
        youtube_dl_instance.download([f"https://www.youtube.com/watch?v={youtube_id}"])


def fetch_lyrics_from_genius(artist, title):
    genius = lyricsgenius.Genius(os.environ["GENIUS_API_TOKEN"])
    song = genius.search_song(title, artist)
    if song:
        lyrics = clean_lyrics(song.lyrics)
        write_lyrics_file(song.title, song.artist, lyrics)
        logger.info("Lyrics for %s by %s fetched successfully", title, artist)
    else:
        logger.warning("Could not find lyrics for %s by %s", title, artist)


def main():
    top_requests = fetch_top_requests(URL)
    logger.info("Fetched top 30 song requests")
    for artist, title in top_requests:
        query = f"{artist} {title}"
        
        logger.info(f"\nProcessing song: {title} by {artist}")
        
        logger.info("Step 2 & 3: Searching YouTube for video ID...")
        youtube_id = get_youtube_id(query)
        if youtube_id:
            logger.info("Step 4: Downloading audio from YouTube...")
            filename = f"{artist} - {title} ({youtube_id})"
            download_audio(youtube_id, filename)
            
            logger.info("Step 5: Fetching lyrics from Genius...")
            fetch_lyrics_from_genius(artist, title)
        else:
            logger.warning(f"Skipping {title} by {artist} due to missing YouTube ID.")
    logger.info("\nAll songs downloaded and lyrics fetched!")



if __name__ == "__main__":
    main()
