#!/usr/bin/env python3
"""
YouTube Media Bulk Downloader
Downloads audio or video from YouTube videos listed in a .txt file
Features: Resume capability, skip duplicates, organized output folders, audio/video mode selection
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
import yt_dlp
import argparse


class YouTubeMediaDownloader:
    def __init__(self, links_file, output_dir="downloads", resume=True, ffmpeg_path=None, single_link=None, download_video=False):
        """
        Initialize downloader
        
        Args:
            links_file: Path to .txt file with YouTube links (one per line)
            output_dir: Directory to save downloaded audio files
            resume: Whether to skip already downloaded files
            ffmpeg_path: Custom path to FFmpeg binary
            single_link: Download single link instead of file
            download_video: Download video instead of audio (default: False)
        """
        self.links_file = links_file
        self.single_link = single_link
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.resume = resume
        self.ffmpeg_path = ffmpeg_path
        self.download_video = download_video
        
        # Set FFmpeg location if provided
        if ffmpeg_path:
            os.environ['PATH'] = f"{ffmpeg_path};{os.environ.get('PATH', '')}"
        
        self.log_file = self.output_dir / "download_log.json"
        self.downloaded = self._load_log()
        
    def _load_log(self):
        """Load previously downloaded URLs from log file"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading log file: {e}")
                return {}
        return {}
    
    def _save_log(self):
        """Save download log to file"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.downloaded, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving log file: {e}")
    
    def _read_links(self):
        """Read YouTube links from .txt file or return single link"""
        # If single link mode, return it directly
        if self.single_link:
            return [self.single_link]
        
        # Otherwise read from file
        try:
            with open(self.links_file, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]
            return links
        except FileNotFoundError:
            print(f"File not found: {self.links_file}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    
    def _get_safe_filename(self, title, url):
        """Create safe filename from video title"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe_title = "".join(c for c in title if c not in invalid_chars)
        safe_title = safe_title.strip()[:100]  # Limit length
        return safe_title if safe_title else url.split('v=')[-1][:11]
    
    def download(self):
        """Download all videos from links file"""
        links = self._read_links()
        
        if not links:
            print("WARNING: No links found in file")
            return
        
        print(f"Found {len(links)} link(s) to process")
        print(f"Output directory: {self.output_dir.resolve()}")
        print(f"Resume mode: {'ON' if self.resume else 'OFF'}")
        print(f"Download mode: {'VIDEO' if self.download_video else 'AUDIO'}")
        print("-" * 60)
        
        successful = 0
        skipped = 0
        failed = 0
        
        for idx, url in enumerate(links, 1):
            print(f"\n[{idx}/{len(links)}] Processing: {url}")
            
            # Check if already downloaded
            if self.resume and url in self.downloaded:
                print(f"Already downloaded: {self.downloaded[url]}")
                skipped += 1
                continue
            
            try:
                title = self._download_media(url)
                if title:
                    self.downloaded[url] = {
                        "title": title,
                        "downloaded_at": datetime.now().isoformat()
                    }
                    self._save_log()
                    successful += 1
                    print(f"Success: {title}")
                else:
                    failed += 1
            except Exception as e:
                print(f"Failed: {str(e)[:100]}")
                failed += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print("DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"Successful: {successful}")
        print(f"Skipped (already exist): {skipped}")
        print(f"Failed: {failed}")
        print(f"Output folder: {self.output_dir.resolve()}")
        print("=" * 60)
    
    def _download_media(self, url):
        """Download audio or video from single YouTube URL"""
        try:
            if self.download_video:
                # Download best video quality
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'socket_timeout': 30,
                    'progress_hooks': [self._progress_hook],
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web'],
                        }
                    },
                    'ignoreerrors': True,
                    'no_color': True,
                    'nocheckcertificate': True,
                }
            else:
                # Download audio (default)
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'socket_timeout': 30,
                    'progress_hooks': [self._progress_hook],
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web'],
                        }
                    },
                    'ignoreerrors': True,
                    'no_color': True,
                    'nocheckcertificate': True,
                }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise Exception("Failed to extract video information (info returned None)")
                return info.get('title', 'Unknown')
        
        except Exception as e:
            import traceback
            error_str = str(e)
            tb_str = traceback.format_exc()
            
            if 'ffmpeg' in error_str.lower() or 'ffprobe' in error_str.lower():
                raise Exception(
                    f"FFmpeg tidak ditemukan. "
                    f"Install FFmpeg atau berikan path.\n"
                    f"Windows: Download dari https://ffmpeg.org/download.html\n"
                    f"macOS: brew install ffmpeg\n"
                    f"Linux: sudo apt-get install ffmpeg"
                )
            
            # Log full traceback for debugging
            print(f"\n[DEBUG] Full error traceback:")
            print(tb_str)
            raise Exception(f"yt-dlp error: {error_str}")
    
    def _progress_hook(self, d):
        """Handle download progress"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                print(f"  {percent:.1f}% downloaded", end='\r')


def main():
    # Get default Music directory for current user (works cross-platform)
    music_dir = os.path.expanduser('~/Music')
    
    parser = argparse.ArgumentParser(
        description='Download audio or video from YouTube videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Download audio from file (to Music folder by default)
  python main.py links.txt
  python main.py links.txt -o custom_folder
  
  # Download video from file
  python main.py links.txt --video
  python main.py links.txt --video -o custom_folder
  
  # Download single audio link
  python main.py --link "https://youtu.be/xxxxx"
  python main.py --link "https://youtu.be/xxxxx" -o custom_folder
  
  # Download single video link
  python main.py --link "https://youtu.be/xxxxx" --video
        '''
    )
    
    parser.add_argument('links_file', nargs='?', default=None, help='File with YouTube links (one per line)')
    parser.add_argument('-o', '--output', default=music_dir, help=f'Output directory (default: Music folder)')
    parser.add_argument('--link', default=None, help='Download single YouTube link')
    parser.add_argument('--no-resume', action='store_true', help='Disable resume mode')
    parser.add_argument('--ffmpeg-path', default=None, help='Custom FFmpeg path')
    parser.add_argument('--video', action='store_true', help='Download video instead of audio (default: audio)')
    
    args = parser.parse_args()
    
    # Validate input
    if args.link:
        # Single link mode - create temporary file
        links_file = None
        single_link = args.link
    elif args.links_file:
        # File mode
        links_file = args.links_file
        single_link = None
    else:
        parser.print_help()
        print("\nError: Provide either links.txt file or use --link for single URL")
        sys.exit(1)
    
    downloader = YouTubeMediaDownloader(
        links_file=links_file,
        output_dir=args.output,
        resume=not args.no_resume,
        ffmpeg_path=args.ffmpeg_path,
        single_link=single_link,
        download_video=args.video
    )
    
    downloader.download()


if __name__ == '__main__':
    main()