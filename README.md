# YouTube Transcript Extractor

This project is a Python script that searches YouTube for videos based on a user-provided query, retrieves their transcripts, processes them (including punctuation correction and translation if necessary), and saves them to text files.

## Features

- Search YouTube videos based on user query and date range
- Extract transcripts from videos
- Correct punctuation in transcripts
- Translate non-English transcripts to English
- Process videos from playlists
- Save transcripts as text files

## Prerequisites

- Python 3.7 or higher
- A Google Cloud project with the YouTube Data API v3 enabled
- A YouTube Data API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/youtube-transcript-extractor.git
   cd youtube-transcript-extractor
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install google-api-python-client youtube-transcript-api python-dotenv punctuators translate langdetect tqdm
   ```

4. Set up the `.env` file:
   - Create a new file named `.env` in the root directory of the project.
   - Open the `.env` file in a text editor.
   - Add the following line, replacing `your_api_key_here` with your actual YouTube Data API key:
     ```
     YOUTUBE_API_KEY=your_api_key_here
     ```
   - Save and close the file.

   Note: The `.env` file is used to securely store your API key. Make sure not to share this file or commit it to version control.

## Usage

1. Run the script:
   ```
   python transcript_extractor.py
   ```

2. When prompted, enter:
   - The search query for YouTube videos
   - The number of videos to process
   - The date to search videos after (in YYYY-MM-DD format)

3. The script will process the videos, extract transcripts, correct punctuation, translate if necessary, and save the results in the `transcripts` directory.

## Output

Transcripts are saved in the `transcripts/<query>` directory. Each file is named after the video title and includes:
- A comment with the video link
- The processed transcript text

## Notes

- The script includes rate limiting to avoid exceeding YouTube API quotas
- Previously processed videos are skipped to avoid duplication
- If a video is part of a playlist, the script will also process other videos in that playlist

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.