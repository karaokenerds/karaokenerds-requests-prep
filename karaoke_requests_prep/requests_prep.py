import requests
import os
import glob
from bs4 import BeautifulSoup
import yt_dlp
import logging
from fetch_lyrics_from_genius.fetch_lyrics import clean_lyrics, write_lyrics_file
import lyricsgenius
from audio_separator import Separator

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

URL = "https://karaokenerds.com/Request/?sort=votes"
CACHE_FILE = "karaokenerds_cache.html"


class KaraokeNerdsRequestsPrep:
    def __init__(
        self,
        limit=5,
        log_level=logging.DEBUG,
        log_formatter=None,
        model_name="UVR_MDXNET_KARA_2",
        model_file_dir="/tmp/audio-separator-models/",
        output_dir=None,
        use_cuda=False,
        use_coreml=False,
        normalization_enabled=True,
        denoise_enabled=True,
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.log_level = log_level
        self.log_formatter = log_formatter

        self.log_handler = logging.StreamHandler()

        if self.log_formatter is None:
            self.log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")

        self.log_handler.setFormatter(self.log_formatter)
        self.logger.addHandler(self.log_handler)

        self.logger.debug(f"RequestsPrep instantiating with limit: {limit}")

        self.limit = limit
        self.model_name = model_name
        self.model_file_dir = model_file_dir
        self.output_dir = output_dir
        self.use_cuda = use_cuda
        self.use_coreml = use_coreml
        self.normalization_enabled = normalization_enabled
        self.denoise_enabled = denoise_enabled

    def fetch_top_requests(self, url):
        logger.info("Fetching top requests from %s", url)
        html_content = self.fetch_content_from_url(url)
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", id="requests")
        rows = table.find("tbody").find_all("tr")
        top_requests = [(row.find_all("td")[1].a.text, row.find_all("td")[2].a.text) for row in rows][: self.limit]
        return top_requests

    def fetch_content_from_url(self, url):
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

    def get_youtube_id_for_top_search_result(self, query):
        ydl_opts = {"format": "bestaudio", "noplaylist": "True", "extract_flat": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video = ydl.extract_info(f"ytsearch1:{query}", download=False)["entries"][0]

            if video:
                youtube_id = video.get("id")
                return youtube_id
            else:
                logger.warning(f"No YouTube results found for query: {query}")
                return None

    def download_audio(self, youtube_id, filename):
        ydl_opts = {
            "format": "ba",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": f"{filename}",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as youtube_dl_instance:
            youtube_dl_instance.download([f"https://www.youtube.com/watch?v={youtube_id}"])

    def fetch_lyrics_from_genius(self, artist, title):
        genius = lyricsgenius.Genius(os.environ["GENIUS_API_TOKEN"])
        song = genius.search_song(title, artist)
        if song:
            lyrics = clean_lyrics(song.lyrics)
            write_lyrics_file(song.title, song.artist, lyrics)
            logger.info("Lyrics for %s by %s fetched successfully", title, artist)
        else:
            logger.warning("Could not find lyrics for %s by %s", title, artist)

    def sanitize_filename(self, filename):
        """Replace or remove characters that are unsafe for filenames."""
        # Replace problematic characters with underscores
        for char in ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]:
            filename = filename.replace(char, "_")
        # Remove any trailing periods or spaces
        filename = filename.rstrip(". ")
        return filename

    def separate_audio(self, audio_file, output_filename_prefix):
        if audio_file is None or not os.path.isfile(audio_file):
            raise Exception("Error: Invalid audio source provided.")

        self.logger.debug(f"audio_file is valid file: {audio_file}")

        primary_stem_path = os.path.join(self.output_dir, f"{output_filename_prefix} (Instrumental)_{self.model_name}.wav")
        secondary_stem_path = os.path.join(self.output_dir, f"{output_filename_prefix} (Vocals)_{self.model_name}.wav")

        if os.path.isfile(primary_stem_path) and os.path.isfile(secondary_stem_path):
            self.logger.debug(f"Separated audio files already exist in output paths, skipping separation: {primary_stem_path}")
        else:
            self.logger.debug(f"instantiating Separator with model_name: {self.model_name} and output_dir: {self.output_dir}")
            separator = Separator(
                audio_file,
                model_name=self.model_name,
                model_file_dir=self.model_file_dir,
                output_dir=self.output_dir,
                log_formatter=self.log_formatter,
                log_level=self.log_level,
            )
            primary_stem_path, secondary_stem_path = separator.separate()

            self.logger.debug(f"Separation complete! Output files: {primary_stem_path} {secondary_stem_path}")

        return primary_stem_path, secondary_stem_path

    def prep(self):
        top_requests = self.fetch_top_requests(URL)
        logger.info("Fetched top 30 song requests")
        for artist, title in top_requests:
            query = f"{artist} {title}"

            logger.info(f"Processing song: {title} by {artist}")

            sanitized_artist = self.sanitize_filename(artist)
            sanitized_title = self.sanitize_filename(title)

            filename_pattern = f"audio/{sanitized_artist} - {sanitized_title}*.wav"
            existing_files = glob.glob(filename_pattern)
            if existing_files:
                logger.info(f"File matching pattern {filename_pattern} already exists. Skipping download.")

            else:
                logger.info(f"No existing audio found with pattern: {filename_pattern}")

                logger.info("Searching YouTube for video ID...")
                youtube_id = self.get_youtube_id_for_top_search_result(query)
                if youtube_id:
                    filename = f"audio/{sanitized_artist} - {sanitized_title} ({youtube_id}).wav"

                    logger.info("Downloading audio from YouTube to filename {filename}")
                    self.download_audio(youtube_id, filename)

                    logger.info("Fetching lyrics from Genius...")
                    self.fetch_lyrics_from_genius(artist, title)
                else:
                    logger.warning(f"Skipping {title} by {artist} due to missing YouTube ID.")

            separation_filename_prefix = f"audio/{sanitized_artist} - {sanitized_title}"
            self.separate_audio(existing_files[0], separation_filename_prefix)

        logger.info("Script finished, all songs downloaded, lyrics fetched and audio separated!")
