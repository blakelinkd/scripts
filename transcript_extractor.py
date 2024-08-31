import os
import random
import string
import time
import re
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from punctuators.models import PunctCapSegModelONNX
from translate import Translator
from langdetect import detect
from tqdm import tqdm
import isodate

# Load environment variables
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

# YouTube API configuration
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Instantiate the punctuation correction model
punctuator = PunctCapSegModelONNX.from_pretrained("pcs_en")

# Instantiate the translator
translator = Translator(to_lang="en")

def search_youtube(query, max_results, after_date):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    videos = []
    next_page_token = None

    while len(videos) < max_results:
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=50,
            type='video',
            publishedAfter=after_date.isoformat() + 'Z',
            pageToken=next_page_token
        ).execute()

        for search_result in search_response.get('items', []):
            video_id = search_result['id']['videoId']
            video_title = search_result['snippet']['title']
            videos.append({'id': video_id, 'title': video_title})
            if len(videos) >= max_results:
                break

        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break

    total_results = len(videos)
    return videos, total_results

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcripts = []
        for transcript in transcript_list:
            fetched_transcript = transcript.fetch()
            transcripts.append(fetched_transcript)
            if transcript.language_code == 'en':
                return fetched_transcript
            elif transcript.is_generated:
                return fetched_transcript
        if transcripts:
            return transcripts[0]  # Fallback to the first available transcript
        return None
    except Exception as e:
        print(f"Could not retrieve transcript for video {video_id}: {e}")
        return None

def remove_unk_tokens(text):
    return re.sub(r'<unk>|<Unk>', '', text, flags=re.IGNORECASE)

def correct_punctuation(text):
    # Call the punctuator model
    corrected_texts = punctuator.infer([text])
    if corrected_texts and isinstance(corrected_texts[0], list) and len(corrected_texts[0]) > 0:
        # Join the list of strings and remove <unk> tokens
        return remove_unk_tokens(' '.join(corrected_texts[0])).strip()
    elif corrected_texts and isinstance(corrected_texts[0], str):
        # If it's a single string, just remove <unk> tokens
        return remove_unk_tokens(corrected_texts[0]).strip()
    return remove_unk_tokens(text).strip()

def translate_text(text):
    try:
        return translator.translate(text)
    except Exception as e:
        print(f"Error during translation: {e}")
        return text

def sanitize_directory_name(name):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def get_processed_video_ids(root_dir):
    processed_videos = set()
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".trans.txt"):
                with open(os.path.join(root, file), 'r') as f:
                    link = f.readline().strip()
                    if link.startswith("// link: "):
                        video_id = link.split("=")[-1]
                        processed_videos.add(video_id)
    return processed_videos

def get_video_details(video_id):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    video_response = youtube.videos().list(
        part='contentDetails',
        id=video_id
    ).execute()

    if 'items' in video_response and video_response['items']:
        content_details = video_response['items'][0]['contentDetails']
        duration = isodate.parse_duration(content_details['duration'])
        return duration
    return None

def get_playlist_videos(playlist_id):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    videos = []
    next_page_token = None

    while True:
        playlist_response = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in playlist_response.get('items', []):
            video_id = item['snippet']['resourceId']['videoId']
            video_title = item['snippet']['title']
            videos.append({'id': video_id, 'title': video_title})

        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break

    return videos

def get_video_playlist(video_id):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    video_response = youtube.videos().list(
        part='snippet',
        id=video_id
    ).execute()

    if 'items' in video_response and video_response['items']:
        snippet = video_response['items'][0]['snippet']
        if 'playlistId' in snippet:
            return snippet['playlistId']
    return None

def main():
    query = input("Enter the search query: ")
    max_videos = int(input("Enter the number of videos to process: "))
    after_date_str = input("Enter the date to search videos after (YYYY-MM-DD): ")
    after_date = datetime.strptime(after_date_str, '%Y-%m-%d')
    min_duration = int(input("Enter the minimum video duration in minutes: "))

    # Create directory for the search query
    query_dir = sanitize_directory_name(query)
    transcripts_dir = os.path.join("transcripts", query_dir)

    if not os.path.exists(transcripts_dir):
        os.makedirs(transcripts_dir)

    # Get all processed video IDs from all transcript directories
    all_transcripts_dir = "transcripts"
    processed_videos = get_processed_video_ids(all_transcripts_dir)

    videos, total_results = search_youtube(query, max_videos, after_date)

    print(f"Total results found: {total_results}")

    for index, video in enumerate(tqdm(videos, desc="Processing videos", unit="video"), start=1):
        if video['id'] in processed_videos:
            print(f"Skipping video {index}/{max_videos}: {video['title']} (ID: {video['id']}) - already processed")
            continue

        # Get video duration and check if it's longer than the minimum duration
        duration = get_video_details(video['id'])
        if duration and duration < timedelta(minutes=min_duration):
            print(f"Skipping video {index}/{max_videos}: {video['title']} (ID: {video['id']}) - duration {duration} is shorter than {min_duration} minutes")
            continue

        print(f"\nProcessing video {index}/{max_videos}: {video['title']} (ID: {video['id']})")

        transcript = get_transcript(video['id'])
        if transcript:
            transcript_text = " ".join([entry['text'] for entry in transcript])
            print(f"Raw transcript length: {len(transcript_text)}")
            
            corrected_transcript_text = correct_punctuation(transcript_text)
            print(f"Corrected transcript length: {len(corrected_transcript_text)}")

            # Check if the transcript is significantly truncated
            if len(corrected_transcript_text) < 0.8 * len(transcript_text):
                print(f"Transcript appears truncated. Skipping video {video['id']}.")
                continue

            # Detect the language of the transcript text
            try:
                if detect(corrected_transcript_text) != 'en':
                    corrected_transcript_text = translate_text(corrected_transcript_text)
            except Exception as e:
                print(f"Error during language detection or translation: {e}")

            video_link = f"https://www.youtube.com/watch?v={video['id']}"
            filename = f"{video['title']}.trans.txt"

            filename = sanitize_directory_name(filename)

            if os.path.exists(os.path.join(transcripts_dir, filename)):
                random_sequence = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
                filename = f"{os.path.splitext(filename)[0]}.{random_sequence}.txt"

            with open(os.path.join(transcripts_dir, filename), 'w', encoding='utf-8') as f:
                f.write(f"// link: {video_link}\n{corrected_transcript_text}")

            print(f"Transcript for {video['title']} saved to {os.path.join(transcripts_dir, filename)}.")
        else:
            print(f"No transcript available for {video['title']}.")

        # Check if the video is part of a playlist
        playlist_id = get_video_playlist(video['id'])
        if playlist_id:
            print(f"Video {video['title']} is part of a playlist. Processing playlist...")

            playlist_videos = get_playlist_videos(playlist_id)
            for playlist_video in playlist_videos:
                if playlist_video['id'] in processed_videos:
                    print(f"Skipping playlist video {playlist_video['title']} (ID: {playlist_video['id']}) - already processed")
                    continue

                # Get playlist video duration and check if it's longer than the minimum duration
                playlist_video_duration = get_video_details(playlist_video['id'])
                if playlist_video_duration and playlist_video_duration < timedelta(minutes=min_duration):
                    print(f"Skipping playlist video {playlist_video['title']} (ID: {playlist_video['id']}) - duration {playlist_video_duration} is shorter than {min_duration} minutes")
                    continue

                playlist_transcript = get_transcript(playlist_video['id'])
                if playlist_transcript:
                    playlist_transcript_text = " ".join([entry['text'] for entry in playlist_transcript])
                    print(f"Raw transcript length for playlist video: {len(playlist_transcript_text)}")
                    
                    corrected_playlist_transcript_text = correct_punctuation(playlist_transcript_text)
                    print(f"Corrected transcript length for playlist video: {len(corrected_playlist_transcript_text)}")

                    # Check if the transcript is significantly truncated
                    if len(corrected_playlist_transcript_text) < 0.8 * len(playlist_transcript_text):
                        print(f"Transcript appears truncated. Skipping playlist video {playlist_video['id']}.")
                        continue

                    # Detect the language of the transcript text
                    try:
                        if detect(corrected_playlist_transcript_text) != 'en':
                            corrected_playlist_transcript_text = translate_text(corrected_playlist_transcript_text)
                    except Exception as e:
                        print(f"Error during playlist language detection or translation: {e}")

                    playlist_video_link = f"https://www.youtube.com/watch?v={playlist_video['id']}"
                    playlist_filename = f"{playlist_video['title']}.trans.txt"

                    playlist_filename = sanitize_directory_name(playlist_filename)

                    if os.path.exists(os.path.join(transcripts_dir, playlist_filename)):
                        random_sequence = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
                        playlist_filename = f"{os.path.splitext(playlist_filename)[0]}.{random_sequence}.txt"

                    with open(os.path.join(transcripts_dir, playlist_filename), 'w', encoding='utf-8') as f:
                        f.write(f"// link: {playlist_video_link}\n{corrected_playlist_transcript_text}")

                    print(f"Transcript for playlist video {playlist_video['title']} saved to {os.path.join(transcripts_dir, playlist_filename)}.")
                else:
                    print(f"No transcript available for playlist video {playlist_video['title']}.")

        # Add a delay to avoid rate limiting
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    main()
