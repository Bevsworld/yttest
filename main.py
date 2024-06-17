import requests
from bs4 import BeautifulSoup
from moviepy.editor import VideoFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Constants for YouTube API
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    credentials = flow.run_console()
    return build('youtube', 'v3', credentials=credentials)

def initialize_upload(youtube, file, title, description, category='22', privacy_status='public'):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': category
        },
        'status': {
            'privacyStatus': privacy_status
        }
    }
    media_body = MediaFileUpload(file, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media_body)
    response = request.execute()
    print(f'Upload successful! Video ID: {response["id"]}')

def download_video(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

# URL to scrape
url = "https://www.riksdagen.se/sv/webb-tv/video/debatt-om-forslag/preventiva-tvangsmedel-for-att-forebygga-och_hb01juu24/"
response = requests.get(url)
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    download_link = soup.select_one("#below-player > ul > li:nth-child(2) > a")
    if download_link and download_link.has_attr('href'):
        video_url = download_link['href']
        print("Download Video URL:", video_url)

        # Download and process the video
        video_file = download_video(video_url)
        video_clip = VideoFileClip(video_file)

        # Setup YouTube service
        youtube = get_authenticated_service()

        # Process speakers and times
        speakers_list = soup.find('div', id='speakers-list')
        if speakers_list:
            ol_items = speakers_list.find_all('ol')
            for ol in ol_items:
                li_items = ol.find_all('li')
                for li in li_items:
                    time_tag = li.find('time')
                    span_tags = li.find_all('span')

                    if time_tag and len(span_tags) >= 3:
                        start_time = time_tag.text.strip()
                        speaker_name = span_tags[2].text.strip()
                        start_seconds = sum(int(x) * 60 ** i for i, x in enumerate(reversed(start_time.split(":"))))
                        end_seconds = start_seconds + 30  # Adjust duration as needed

                        clip = video_clip.subclip(start_seconds, end_seconds)
                        filename = f"{speaker_name}_{start_time}.mp4"
                        clip.write_videofile(filename, codec='libx264')

                        # Upload each clip to YouTube
                        title = f"Segment: {speaker_name} at {start_time}"
                        description = f"Video segment featuring {speaker_name} speaking at {start_time}."
                        initialize_upload(youtube, filename, title, description)

                        print(f"Saved and uploaded clip: {filename}")
        else:
            print("Speakers list div not found.")
    else:
        print("No direct video link found. Check the page for the correct video element.")
else:
    print("Failed to retrieve webpage. Status code:", response.status_code)
