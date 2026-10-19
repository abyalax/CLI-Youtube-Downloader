#!/usr/bin/env python3
"""
YouTube Media Bulk Downloader
Downloads audio or video from YouTube videos listed in a .txt file
Features: Resume capability, skip duplicates, organized output folders, audio/video/video-only mode selection
"""

import os
import json
import sys
import queue
import threading
import time
from pathlib import Path
from datetime import datetime
import yt_dlp
import argparse
from urllib.parse import urlparse


class YouTubeMediaDownloader:
    def __init__(
        self,
        links_file,
        output_dir="downloads",
        resume=True,
        ffmpeg_path=None,
        single_link=None,
        download_video=False,
        video_only=False,
        show_debug=True,
        show_progress=True,
        quiet=False,
        log_callback=None,
    ):
        """
        Initialize downloader
        
        Args:
            links_file: Path to .txt file with YouTube links (one per line)
            output_dir: Directory to save downloaded audio files
            resume: Whether to skip already downloaded files
            ffmpeg_path: Custom path to FFmpeg binary
            single_link: Download single link instead of file
            download_video: Download video instead of audio (default: False)
            video_only: Download video only without audio (default: False)
        """
        self.links_file = links_file
        self.single_link = single_link
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.resume = resume
        self.ffmpeg_path = ffmpeg_path
        self.download_video = download_video
        self.video_only = video_only
        self.show_debug = show_debug
        self.show_progress = show_progress
        self.quiet = quiet
        self.log_callback = log_callback
        self._last_progress = -1
        self.js_runtimes = {"node": {}}
        self.remote_components = ["ejs:github"]
        self.youtube_player_clients = ["web_embedded"]
        
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
        if self.video_only:
            print(f"Download mode: VIDEO ONLY")
        elif self.download_video:
            print(f"Download mode: VIDEO")
        else:
            print(f"Download mode: AUDIO")
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

    def download_one(self):
        """Download one URL and return a result for interactive mode."""
        url = self.single_link
        if not url:
            raise ValueError("A single link is required")

        if self.resume and url in self.downloaded:
            item = self.downloaded[url]
            title = item.get("title", "already downloaded") if isinstance(item, dict) else str(item)
            return {"status": "skipped", "title": title}

        try:
            title = self._download_media(url)
            if not title:
                return {"status": "failed", "error": "No title was returned by yt-dlp"}

            self.downloaded[url] = {
                "title": title,
                "downloaded_at": datetime.now().isoformat(),
            }
            self._save_log()
            return {"status": "success", "title": title}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
    
    def _download_media(self, url):
        """Download audio or video from single YouTube URL"""
        try:
            # YouTube now requires an external JS runtime plus EJS challenge solver
            # scripts for reliable extraction. We force the working Node-based path
            # and prefer the web_embedded client, which avoids the failing android_vr route.
            extractor_args = {
                'youtube': {
                    'player_client': self.youtube_player_clients,
                }
            }

            common_opts = {
                'js_runtimes': self.js_runtimes,
                'remote_components': self.remote_components,
                'extractor_args': extractor_args,
            }

            if self.video_only:
                # Download video only (no audio)
                ydl_opts = {
                    **common_opts,
                    'format': 'bestvideo',
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'socket_timeout': 30,
                    'progress_hooks': [self._progress_hook],
                    'no_color': True,
                    'nocheckcertificate': True,
                }
            elif self.download_video:
                # Download best video quality with audio
                ydl_opts = {
                    **common_opts,
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'socket_timeout': 30,
                    'progress_hooks': [self._progress_hook],
                    'no_color': True,
                    'nocheckcertificate': True,
                    'no_warnings': True,
                    'merge_output_format': 'mp4',
                }
            else:
                # Download audio (default)
                ydl_opts = {
                    **common_opts,
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': True,
                    'socket_timeout': 30,
                    'progress_hooks': [self._progress_hook],
                    'no_color': True,
                    'nocheckcertificate': True,
                }
            
            # Interactive mode routes task results through the prompt renderer;
            # suppress yt-dlp's direct console output so it cannot overwrite input.
            ydl_opts['quiet'] = self.quiet
            if self.log_callback:
                ydl_opts['no_warnings'] = False
                ydl_opts['logger'] = YTDLPLogger(self.log_callback)
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
            
            # Log full traceback for debugging in the original command-line mode.
            # Interactive mode reports a concise error beside its task number.
            if self.show_debug:
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
                if self.log_callback and int(percent) != self._last_progress:
                    self._last_progress = int(percent)
                    self.log_callback(f"{percent:.1f}% downloaded", "process")
                elif self.show_progress:
                    print(f"  {percent:.1f}% downloaded", end='\r')


class YTDLPLogger:
    """Route yt-dlp's native logger messages into the process layer."""

    def __init__(self, callback):
        self.callback = callback

    def debug(self, message):
        if message:
            self.callback(message, "process")

    def info(self, message):
        if message:
            self.callback(message, "process")

    def warning(self, message):
        if message:
            self.callback(f"WARNING: {message}", "process")

    def error(self, message):
        if message:
            self.callback(f"ERROR: {message}", "process")


class InteractiveDownloadManager:
    """Queue downloads while keeping the terminal prompt responsive."""

    def __init__(self, output_dir, resume=True, ffmpeg_path=None):
        self.output_dir = output_dir
        self.resume = resume
        self.ffmpeg_path = ffmpeg_path
        self.jobs = queue.Queue()
        self.lock = threading.Lock()
        self.next_id = 1
        self.active = None
        self.completed = 0
        self.succeeded = 0
        self.skipped = 0
        self.failed = 0
        self.notifications = queue.Queue()
        self.worker = threading.Thread(target=self._work, name="youtube-downloader", daemon=False)

    def start(self):
        self.worker.start()

    def add(self, url, mode):
        with self.lock:
            task_id = self.next_id
            self.next_id += 1
        self.jobs.put((task_id, url, mode))
        self.notify(f"Queued task #{task_id}: {url} [{mode}]")

    def set_output_dir(self, output_dir):
        path = Path(output_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        with self.lock:
            self.output_dir = path
        self.notify(f"Output directory changed to: {path.resolve()}")

    def notify(self, message, layer="report"):
        """Send worker messages to the prompt renderer instead of printing directly."""
        self.notifications.put((layer, message))

    def _work(self):
        while True:
            task = self.jobs.get()
            if task is None:
                self.jobs.task_done()
                return

            task_id, url, mode = task
            with self.lock:
                self.active = task_id
                task_output_dir = self.output_dir
            self.notify(f"[Task #{task_id}] Started: {url} ({mode})")

            try:
                downloader = YouTubeMediaDownloader(
                    links_file=None,
                    output_dir=task_output_dir,
                    resume=self.resume,
                    ffmpeg_path=self.ffmpeg_path,
                    single_link=url,
                    download_video=mode in ("video", "video-only"),
                video_only=mode == "video-only",
                show_debug=False,
                show_progress=False,
                quiet=False,
                log_callback=self.notify,
            )
                result = downloader.download_one()
            except Exception as exc:
                result = {"status": "failed", "error": str(exc)}

            with self.lock:
                self.active = None
                self.completed += 1
                if result["status"] == "success":
                    self.succeeded += 1
                elif result["status"] == "skipped":
                    self.skipped += 1
                else:
                    self.failed += 1

            if result["status"] == "success":
                self.notify(f"[Task #{task_id}] SUCCESS: {result['title']}")
            elif result["status"] == "skipped":
                self.notify(f"[Task #{task_id}] SKIPPED (already downloaded): {result['title']}")
            else:
                self.notify(f"[Task #{task_id}] FAILED: {result['error']}")
            self.jobs.task_done()

    def status_text(self):
        with self.lock:
            active = self.active
            completed = self.completed
            succeeded = self.succeeded
            skipped = self.skipped
            failed = self.failed
        return (
            f"Status: {self.jobs.qsize()} queued, "
            f"{('task #' + str(active) + ' downloading') if active else 'idle'}; "
            f"completed={completed}, success={succeeded}, skipped={skipped}"
        )

    def status(self):
        print(self.status_text())

    def close(self):
        self.jobs.join()
        self.jobs.put(None)
        self.jobs.join()
        self.worker.join()


class LayeredTerminal:
    """Fixed terminal layers: index at top, dim logs in the middle, prompt at bottom."""

    DIM = "\x1b[2m"
    RESET = "\x1b[0m"

    def __init__(self, manager):
        self.manager = manager
        self.reports = []
        self.process_logs = []
        self.active = False
        self._last_render_key = None

    def start(self):
        self.active = True
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()

    def stop(self):
        if self.active:
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
            self.active = False

    def _collect_notifications(self):
        while True:
            try:
                layer, message = self.manager.notifications.get_nowait()
                if layer == "process":
                    self.process_logs.append(message)
                else:
                    self.reports.append(message)
            except queue.Empty:
                return

    def render(self, prompt="", typed=""):
        self._collect_notifications()
        try:
            size = os.get_terminal_size()
            width, height = size.columns, size.lines
        except OSError:
            width, height = 100, 25

        key = (
            width,
            height,
            prompt,
            typed,
            int(time.monotonic() * 2) % 2 == 0,
            self.manager.status_text(),
            len(self.reports),
            len(self.process_logs),
        )
        if key == self._last_render_key:
            return
        self._last_render_key = key

        cursor_on = key[4]
        input_line = f"URL > {typed}{'|' if cursor_on else ' '}"[:width]
        suggestions = _command_suggestions(typed)
        suggestion_line = f"Suggestions: {'  '.join(suggestions)}  [Tab to complete]" if suggestions else ""
        report_height = max(3, (height - 5) // 2)
        process_height = max(1, height - report_height - 5)
        reports = self.reports[-report_height:]
        processes = self.process_logs[-process_height:]

        body = [
            input_line.ljust(width),
            f"{self.DIM}{suggestion_line[:width]}{self.RESET}" if suggestion_line else "",
            "Download Report",
        ]
        body.extend(f"{self.DIM}{line[:width]}{self.RESET}" for line in reports)
        body.extend(["" for _ in range(max(0, report_height - len(reports)))])
        body.append("YT-DLP Process")
        body.extend(f"{self.DIM}{line[:width]}{self.RESET}" for line in processes)
        body.extend(["" for _ in range(max(0, process_height - len(processes)))])
        body.append(f"Status: {key[5]}")

        sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(body[:height]))
        cursor_column = min(width, len("URL > ") + len(typed) + 1)
        sys.stdout.write(f"\x1b[1;{cursor_column}H")
        sys.stdout.flush()

    def add(self, message):
        self.reports.append(message)


def interactive_mode(output_dir, resume=True, ffmpeg_path=None, default_mode="audio"):
    """Run the terminal-agent-style queue without adding a chatbot."""
    manager = InteractiveDownloadManager(output_dir, resume, ffmpeg_path)
    manager.start()
    terminal = LayeredTerminal(manager)
    terminal.start()

    terminal.add("YouTube background downloader")
    terminal.add(f"Output directory: {Path(output_dir).resolve()}")
    terminal.add("Paste a URL and press Enter. Commands use / and Tab provides autocomplete.")
    terminal.add(f"Default type: {default_mode}. Change it with :type audio, :type video, or :type video-only.")

    try:
        while True:
            try:
                url = _read_prompt("URL (or command): ", manager, terminal).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except Exception as exc:
                terminal.add(f"Input error: {exc}")
                continue

            if not url:
                continue
            try:
                command, argument = _normalise_command(url)
                if command:
                    if command in {"/quit", "/exit"}:
                        if argument:
                            terminal.add(f"Invalid value for {command}. Usage: {command}")
                        else:
                            break
                    elif command == "/status":
                        terminal.add(manager.status_text() if not argument else "Usage: /status")
                    elif command in {"/type", "/mode"}:
                        requested = argument.lower().replace("video only", "video-only")
                        if not requested:
                            terminal.add(f"Current default type: {default_mode}")
                        elif requested in {"audio", "video", "video-only"}:
                            default_mode = requested
                            terminal.add(f"Default type changed to: {default_mode}")
                        else:
                            terminal.add("Invalid type. Use: /type audio | /type video | /type video-only")
                    elif command == "/directory":
                        if argument:
                            manager.set_output_dir(argument.strip('"'))
                        else:
                            terminal.add(f"Current directory: {Path(manager.output_dir).resolve()}")
                    elif command == "/help":
                        terminal.add("Commands: /type [audio|video|video-only], /directory [path], /status, /help, /quit")
                    else:
                        terminal.add(f"Unknown command: {command}. Use /help or press Tab for autocomplete.")
                    continue

                if not _is_valid_url(url):
                    terminal.add("Invalid URL. Paste a complete http:// or https:// video URL.")
                    continue
                manager.add(url, default_mode)
            except Exception as exc:
                terminal.add(f"Operation error: {exc}")
    finally:
        manager.close()
        terminal._collect_notifications()
        summary = manager.status_text()
        terminal.stop()
        print(f"Interactive downloader closed. {summary}")


def _flush_notifications(manager):
    """Print completed background events only from the foreground prompt thread."""
    while True:
        try:
            _, message = manager.notifications.get_nowait()
            print(f"\n{message}")
        except queue.Empty:
            return


def _read_prompt(prompt, manager, terminal=None):
    """Read input without allowing worker messages to overwrite it on Windows."""
    if os.name != "nt" or terminal is None:
        value = input(prompt)
        _flush_notifications(manager)
        return value

    import msvcrt

    typed = []
    while True:
        terminal.render(prompt, "".join(typed))
        if not msvcrt.kbhit():
            time.sleep(0.05)
            continue

        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            return "".join(typed)
        if char == "\003":
            raise KeyboardInterrupt
        if char == "\b":
            if typed:
                typed.pop()
            continue
        if char == "\t":
            typed = list(_autocomplete_command("".join(typed)))
            continue
        if char in ("\x00", "\xe0"):
            msvcrt.getwch()  # Consume the second byte of a special key.
            continue
        typed.append(char)


COMMANDS = ["/type", "/directory", "/status", "/help", "/quit", "/exit", "/mode"]


def _normalise_command(value):
    """Return (command, argument) while accepting old colon aliases."""
    value = value.strip()
    if value.lower() in {"quit", "exit"}:
        return "/quit", ""
    if value.startswith(":"):
        value = "/" + value[1:]
    if not value.startswith("/"):
        return "", ""
    parts = value.split(None, 1)
    command = parts[0].lower()
    argument = parts[1].strip() if len(parts) == 2 else ""
    return command, argument


def _is_valid_url(value):
    """Reject empty/non-URL input before it reaches yt-dlp."""
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _autocomplete_command(value):
    """Complete slash commands when Tab is pressed in the URL prompt."""
    if not value.startswith("/"):
        return value

    command, separator, argument = value.partition(" ")
    if separator:
        command = command.lower()
        if command in {"/type", "/mode"}:
            values = ["audio", "video", "video-only"]
            matches = [f"{command} {item}" for item in values if item.startswith(argument.lower())]
            if len(matches) == 1:
                return matches[0] + " "
            return _common_prefix(matches) if matches else value
        if command == "/directory" and not argument:
            return "/directory ."
        return value

    matches = [command for command in COMMANDS if command.startswith(value.lower())]
    if not matches:
        return value
    if len(matches) == 1:
        return matches[0] + " "

    return _common_prefix(matches)


def _common_prefix(values):
    """Find the longest shared prefix for autocomplete candidates."""
    if not values:
        return ""
    common = values[0]
    for candidate in values[1:]:
        while not candidate.startswith(common):
            common = common[:-1]
    return common


def _command_suggestions(value):
    """Return visible slash-command suggestions for the current input."""
    if not value.startswith("/"):
        return []
    command, separator, argument = value.partition(" ")
    if separator:
        command = command.lower()
        if command in {"/type", "/mode"}:
            return [
                f"{command} {item}"
                for item in ("audio", "video", "video-only")
                if item.startswith(argument.lower())
            ]
        if command == "/directory":
            return [f"{command} .", f"{command} <path>"] if not argument else []
        return []
    return [command for command in COMMANDS if command.startswith(value.lower())]


def _flush_prompt_notifications(prompt, typed, manager):
    messages = []
    while True:
        try:
            _, message = manager.notifications.get_nowait()
            messages.append(message)
        except queue.Empty:
            break
    if not messages:
        return

    # Clear the current line, print events, then redraw the prompt and typed text.
    line_width = len(prompt) + len(typed) + 2
    sys.stdout.write("\r" + (" " * line_width) + "\r")
    for message in messages:
        sys.stdout.write(f"{message}\n")
    sys.stdout.write(prompt + "".join(typed))
    sys.stdout.flush()


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
  
  # Download video only (no audio) from file
  python main.py links.txt --video-only
  python main.py links.txt --video-only -o custom_folder
  
  # Download single audio link
  python main.py --link "https://youtu.be/xxxxx"
  python main.py --link "https://youtu.be/xxxxx" -o custom_folder
  
  # Download single video link
  python main.py --link "https://youtu.be/xxxxx" --video
  
  # Download single video only link (no audio)
  python main.py --link "https://youtu.be/xxxxx" --video-only
  # Interactive background queue (paste URLs continuously)
  python main.py --interactive
        '''
    )
    
    parser.add_argument('links_file', nargs='?', default=None, help='File with YouTube links (one per line)')
    parser.add_argument('-o', '--output', default=music_dir, help=f'Output directory (default: Music folder)')
    parser.add_argument('--link', default=None, help='Download single YouTube link')
    parser.add_argument('--no-resume', action='store_true', help='Disable resume mode')
    parser.add_argument('--ffmpeg-path', default=None, help='Custom FFmpeg path')
    parser.add_argument('--video', action='store_true', help='Download video instead of audio (default: audio)')
    parser.add_argument('--video-only', action='store_true', help='Download video only without audio (default: disabled)')
    parser.add_argument('--interactive', '--agent', action='store_true',
                        help='Interactive background queue for URLs and per-link download types')
    
    args = parser.parse_args()

    if args.interactive:
        interactive_mode(
            output_dir=args.output,
            resume=not args.no_resume,
            ffmpeg_path=args.ffmpeg_path,
            default_mode="video-only" if args.video_only else ("video" if args.video else "audio"),
        )
        return
    
    # Validate mutually exclusive options
    if args.video_only and not args.video:
        # If --video-only is used, automatically enable --video
        args.video = True
    
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
        # No input arguments: start the interactive queue by default.
        interactive_mode(
            output_dir=args.output,
            resume=not args.no_resume,
            ffmpeg_path=args.ffmpeg_path,
            default_mode="video-only" if args.video_only else ("video" if args.video else "audio"),
        )
        return
    
    downloader = YouTubeMediaDownloader(
        links_file=links_file,
        output_dir=args.output,
        resume=not args.no_resume,
        ffmpeg_path=args.ffmpeg_path,
        single_link=single_link,
        download_video=args.video,
        video_only=args.video_only
    )
    
    downloader.download()


if __name__ == '__main__':
    main()
