from info import BIN_CHANNEL, URL
from utils import temp
import urllib.parse
import html # aiofiles was imported but not used, so removed it.


# styles from deepseek.com
watch_tmplt = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta property="og:image" content="https://i.ibb.co/M8S0Zzj/live-streaming.png" itemprop="thumbnailUrl">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading}</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
    <style>
        :root {
            --primary: #818cf8;
            --primary-hover: #6366f1;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --bg-color: #0f172a;
            --player-bg: #1e293b;
            --footer-bg: #1e293b;
            --border-color: #334155;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            align-items: center;
            justify-content: center;
        }
        
        header {
            width: 90%;
            max-width: 800px;
            padding: 20px 0;
            text-align: center;
        }
        
        h1 {
            color: var(--primary);
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .player-container {
            width: 90%;
            max-width: 800px;
            background-color: var(--player-bg);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            margin-bottom: 30px;
        }
        
        .plyr {
            border-radius: 8px;
        }
        
        footer {
            width: 90%;
            max-width: 800px;
            text-align: center;
            padding: 20px 0;
            color: var(--text-secondary);
            font-size: 0.9em;
            border-top: 1px solid var(--border-color);
            margin-top: auto;
        }
        
        footer a {
            color: var(--primary);
            text-decoration: none;
        }
        
        footer a:hover {
            text-decoration: underline;
        }
        
        .plyr--full-screen {
            background-color: #000;
        }
    </style>
</head>
<body>
    <header>
        <h1>{heading}</h1>
    </header>

    <main class="player-container">
        <video controls crossorigin playsinline class="player">
            <source src="{src}" type="video/mp4">
            <p>Your browser does not support HTML5 video. Here is a <a href="{src}">link to the video</a> instead.</p>
        </video>
    </main>

    <footer>
        <p>You are watching: <strong>{file_name}</strong></p>
        <p>Video not playing? Your browser might not support the codec. Please try downloading the file or playing in VLC.</p>
    </footer>

    <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize Plyr player
            const player = new Plyr('.player', {
                controls: [
                    'play-large',
                    'play',
                    'progress',
                    'current-time',
                    'duration',
                    'mute',
                    'volume',
                    'captions',
                    'settings',
                    'pip',
                    'airplay',
                    'fullscreen'
                ],
                settings: ['captions', 'quality', 'speed'],
                hideControls: false
            });
        });
    </script>
</body>
</html>
"""

async def media_watch(message_id):
    try:
        media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        media = getattr(media_msg, media_msg.media.value, None)

        if not media or not media.file_name or not media.mime_type:
            return "<h1>Error: Media information not found or incomplete.</h1>"

        src = urllib.parse.urljoin(URL, f'download/{message_id}')
        tag = media.mime_type.split('/')[0].strip()

        if tag == 'video':
            heading = html.escape(f'Watch - {media.file_name}')
            file_name = html.escape(media.file_name) # Ensure file_name is also escaped
            html_ = watch_tmplt.replace('{heading}', heading).replace('{file_name}', file_name).replace('{src}', src)
        elif tag == 'audio': # Optional: Handle audio files if you want to stream them with an audio player
            heading = html.escape(f'Listen - {media.file_name}')
            file_name = html.escape(media.file_name)
            # You would need a different template for audio or adapt the current one
            html_ = f"<h1>Audio Streaming Not Implemented Yet for: {file_name}</h1><audio controls><source src='{src}' type='{media.mime_type}'></audio>"
        else:
            html_ = f'<h1>This file type ({media.mime_type}) is not streamable.</h1>'
        return html_
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Error in media_watch: {e}")
        return "<h1>An error occurred while preparing the media. Please try again later.</h1>"
