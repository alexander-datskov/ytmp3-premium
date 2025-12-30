#!/usr/bin/env python3

import concurrent.futures
import os
import platform
import shutil
import sys
import time
from getopt import GetoptError, getopt
from pathlib import Path
from typing import List, Tuple

import yt_dlp


# color codes
class color:
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    BOLD = '\033[1m'
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BLINK = '\033[5m'


# clear terminal
def clear():
    if os.name=='nt' : os.system('cls')
    else : os.system('clear')


# Audio quality configurations - BEST TO WORST
AUDIO_FORMATS = {
    '1': {
        'name': 'WAV (UNCOMPRESSED)',
        'ext': 'wav',
        'quality': 'best',
        'description': '⚡ ABSOLUTE MAXIMUM - Raw studio quality, no compression, MASSIVE files',
        'format': 'bestaudio/best',
        'tier': '💎 GODMODE'
    },
    '2': {
        'name': 'FLAC (LOSSLESS)',
        'ext': 'flac',
        'quality': 'best',
        'description': '⚡ AUDIOPHILE ELITE - Perfect lossless, compressed but zero quality loss',
        'format': 'bestaudio/best',
        'tier': '💎 GODMODE'
    },
    '3': {
        'name': 'M4A (AAC HQ)',
        'ext': 'm4a',
        'quality': 'best',
        'description': '🔥 PREMIUM - High-end lossy, excellent quality/size ratio',
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'tier': '🏆 ELITE'
    },
    '4': {
        'name': 'OPUS (MODERN)',
        'ext': 'opus',
        'quality': 'best',
        'description': '🔥 CUTTING EDGE - Superior codec, better than MP3 at same bitrate',
        'format': 'bestaudio[ext=webm][acodec=opus]/bestaudio/best',
        'tier': '🏆 ELITE'
    },
    '5': {
        'name': 'MP3 320kbps',
        'ext': 'mp3',
        'quality': '320',
        'description': '✓ EXCELLENT - Universal compatibility, very high quality',
        'format': 'bestaudio/best',
        'tier': '⭐ SOLID'
    },
    '6': {
        'name': 'MP3 256kbps',
        'ext': 'mp3',
        'quality': '256',
        'description': '✓ VERY GOOD - Most people can\'t tell the difference',
        'format': 'bestaudio/best',
        'tier': '⭐ SOLID'
    },
    '7': {
        'name': 'MP3 192kbps',
        'ext': 'mp3',
        'quality': '192',
        'description': '○ ACCEPTABLE - Balanced, noticeable compression',
        'format': 'bestaudio/best',
        'tier': '📦 DECENT'
    },
    '8': {
        'name': 'MP3 128kbps',
        'ext': 'mp3',
        'quality': '128',
        'description': '⚠ MINIMUM - Small files, audible quality loss',
        'format': 'bestaudio/best',
        'tier': '💀 PEASANT'
    }
}


def hacker_banner():
    """Display sick hacker-style banner"""
    clear()
    print(f"{color.ERROR}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                       ║")
    print(f"║  {color.BLINK}██{color.ERROR}╗   {color.BLINK}██{color.ERROR}╗████████╗{color.BLINK}███{color.ERROR}╗   {color.BLINK}███{color.ERROR}╗{color.BLINK}██████{color.ERROR}╗ {color.BLINK}██████{color.ERROR}╗       {color.BLINK}██████{color.ERROR}╗ ██{color.BLINK}╗     ║")
    print(f"║  {color.WARNING}╚██╗ ██╔╝╚══██╔══╝████╗ ████║██╔══██╗╚════██╗      ██╔══██╗██║     ║")
    print(f"║   {color.OKGREEN}╚████╔╝    ██║   ██╔████╔██║██████╔╝ █████╔╝█████╗██║  ██║██║     ║")
    print(f"║   {color.OKCYAN}╚██╔╝     ██║   ██║╚██╔╝██║██╔═══╝  ╚═══██╗╚════╝██║  ██║██║     ║")
    print(f"║    {color.PURPLE}██║      ██║   ██║ ╚═╝ ██║██║     ██████╔╝      ██████╔╝███████╗║")
    print(f"║    {color.BLUE}╚═╝      ╚═╝   ╚═╝     ╚═╝╚═╝     ╚═════╝       ╚═════╝ ╚══════╝║")
    print("║                                                                       ║")
    print(f"║              {color.BOLD}{color.OKGREEN}[ AUDIO EXTRACTION SYSTEM v4.0 ]{color.ERROR}                   ║")
    print(f"║              {color.OKCYAN}[ MAXIMUM QUALITY • MAXIMUM SPEED ]{color.ERROR}                 ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{color.ENDC}")


def display_quality_menu():
    """Display hacker-style quality selection menu"""
    hacker_banner()
    
    print(f"{color.BOLD}{color.ERROR}[!]{color.ENDC} {color.BOLD}INITIALIZING QUALITY MATRIX...{color.ENDC}\n")
    time.sleep(0.3)
    
    print(f"{color.BOLD}{color.OKCYAN}┌─────────────────────────────────────────────────────────────────────┐{color.ENDC}")
    print(f"{color.BOLD}{color.OKCYAN}│{color.ENDC} {color.BOLD}RANK{color.ENDC}  {color.BOLD}CODEC{color.ENDC}                  {color.BOLD}TIER{color.ENDC}           {color.BOLD}DESCRIPTION{color.ENDC}              {color.BOLD}{color.OKCYAN}│{color.ENDC}")
    print(f"{color.BOLD}{color.OKCYAN}├─────────────────────────────────────────────────────────────────────┤{color.ENDC}")
    
    for key, fmt in AUDIO_FORMATS.items():
        tier_color = color.PURPLE if "GODMODE" in fmt['tier'] else \
                     color.ERROR if "ELITE" in fmt['tier'] else \
                     color.OKGREEN if "SOLID" in fmt['tier'] else \
                     color.WARNING if "DECENT" in fmt['tier'] else \
                     color.BLUE
        
        print(f"{color.BOLD}{color.OKCYAN}│{color.ENDC} {color.BOLD}{color.WARNING}[{key}]{color.ENDC}  {color.BOLD}{fmt['name']:<20}{color.ENDC} {tier_color}{fmt['tier']:<14}{color.ENDC} {fmt['description']:<30} {color.BOLD}{color.OKCYAN}│{color.ENDC}")
    
    print(f"{color.BOLD}{color.OKCYAN}└─────────────────────────────────────────────────────────────────────┘{color.ENDC}\n")
    
    print(f"{color.BOLD}{color.ERROR}[>]{color.ENDC} {color.BOLD}OPERATOR RECOMMENDATIONS:{color.ENDC}")
    print(f"    {color.PURPLE}├─{color.ENDC} {color.BOLD}[1]{color.ENDC} WAV      : Zero compromise, maximum fidelity")
    print(f"    {color.PURPLE}├─{color.ENDC} {color.BOLD}[2]{color.ENDC} FLAC     : Lossless perfection with compression")
    print(f"    {color.ERROR}├─{color.ENDC} {color.BOLD}[3]{color.ENDC} M4A      : Best balance for everyday use")
    print(f"    {color.ERROR}└─{color.ENDC} {color.BOLD}[5]{color.ENDC} MP3 320k : Universal compatibility\n")
    
    print(f"{color.BOLD}{color.ERROR}[!]{color.ENDC} {color.BOLD}WARNING:{color.ENDC} Options 1-2 will produce LARGE files. Disk space required.\n")


def get_quality_choice():
    """Get user's quality choice with hacker vibes"""
    while True:
        choice = input(f"{color.BOLD}{color.OKGREEN}[?]{color.ENDC} {color.BOLD}SELECT QUALITY TIER [1-8] » {color.ENDC}").strip()
        
        if choice == '':
            choice = '2'  # Default to FLAC
            print(f"{color.BOLD}{color.WARNING}[!]{color.ENDC} Defaulting to {color.BOLD}FLAC (LOSSLESS){color.ENDC}")
        
        if choice in AUDIO_FORMATS:
            selected = AUDIO_FORMATS[choice]
            print(f"\n{color.BOLD}{color.OKGREEN}[✓]{color.ENDC} {color.BOLD}LOCKED IN:{color.ENDC} {color.BOLD}{selected['name']}{color.ENDC} {selected['tier']}")
            print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {selected['description']}")
            time.sleep(0.5)
            return choice
        else:
            print(f"{color.BOLD}{color.ERROR}[X]{color.ENDC} INVALID INPUT. Range: 1-8")


def get_download_path():
    """Set default download directory"""
    default_path = '/home/rasp-alex2/Downloads'
    os.makedirs(default_path, exist_ok=True)
    return default_path


def get_ffmpeg_path(path=''):
    """Set ffmpeg binary location"""
    if path!='':
        if os.path.exists(path) and (path.split('/')[-1] in ['ffmpeg', 'ffmpeg.exe']) : return path
        else : print(f"{color.BOLD}{color.ERROR}[X] ffmpeg NOT FOUND at `{path}`{color.ENDC}"); exit(0)

    elif shutil.which('ffmpeg') != None:
        return shutil.which('ffmpeg')
    
    elif os.path.exists(f'{os.path.abspath(os.getcwd())}/ffmpeg'):
        if platform.system() == 'Windows':
            return f'{os.path.abspath(os.getcwd())}/ffmpeg/windows/ffmpeg.exe'
        elif platform.system() == 'Darwin':
            return f'{os.path.abspath(os.getcwd())}/ffmpeg/darwin/ffmpeg'
        elif platform.system() == 'Linux':
            return f'{os.path.abspath(os.getcwd())}/ffmpeg/linux/ffmpeg'

    else:
        print(f"{color.BOLD}{color.ERROR}[X] CRITICAL ERROR: ffmpeg NOT FOUND{color.ENDC}")
        print(f"    Install: https://ffmpeg.org/download.html")
        exit(0)


def usage():
    """Show help"""
    print(
            f"{color.ERROR}yt{color.WARNING}mp3-dl {color.OKGREEN}v4.0 {color.OKCYAN}~MAXIMUM OVERDRIVE{color.ENDC}"
    '\n'    f"Ultra-high-speed audio extraction with quality tier selection."
    '\n'    f"Downloads the ABSOLUTE HIGHEST quality available. No compromises."
    )

    print(
    '\n'    f"[OPTIONS]                     [USAGE]"
    '\n'    f"-d, --dir [PATH]              set download directory"
    '\n'    f"-f, --ffmpeg [PATH]           set the exact path to ffmpeg binary"
    '\n'    f"-l, --limit [NUMBER]          set concurrent download limit (default: 4)"
    '\n'    f"-q, --quality [1-8]           skip menu and use quality tier directly"

    '\n\n'  f"[FLAGS]                       [USAGE]"
    '\n'    f"-h, --help                    show help"
    '\n\n'  f"[EXAMPLES]"
    '\n'    f"./ytmp3-dl.py URL1 URL2                    # Interactive mode"
    '\n'    f"./ytmp3-dl.py -q 2 URL1 URL2               # Instant FLAC extraction"
    '\n'    f"./ytmp3-dl.py -q 1 -l 8 URL1 URL2          # WAV with 8 parallel threads"
    )
    exit()


def print_status():
    """Print download status with hacker aesthetics"""
    clear()
    hacker_banner()
    
    print(f"{color.BOLD}{color.ERROR}[>]{color.ENDC} {color.BOLD}SYSTEM STATUS{color.ENDC}")
    print(f"{color.OKCYAN}├─{color.ENDC} Target URLs        : {color.BOLD}{len(URLS)}{color.ENDC}")
    print(f"{color.OKCYAN}├─{color.ENDC} Audio Codec        : {color.BOLD}{selected_format['name']}{color.ENDC} {selected_format['tier']}")
    print(f"{color.OKCYAN}├─{color.ENDC} FFmpeg Location    : {ffmpeg_path}")
    print(f"{color.OKCYAN}├─{color.ENDC} Output Directory   : {download_path}")
    print(f"{color.OKCYAN}└─{color.ENDC} Parallel Threads   : {color.BOLD}{limit}{color.ENDC}")
    print()
    print(f"{color.BOLD}{color.ERROR}[>]{color.ENDC} {color.BOLD}EXTRACTION QUEUE{color.ENDC}")
    [print(f"    {item}") for item in status]
    print()


def download(url):
    """Download audio from YouTube URL"""
    with yt_dlp.YoutubeDL(yt_dlp_options) as downloader:
        info = downloader.extract_info(url, download=False)
        title = info.get('title', None)

        status[URLS.index(url)] = f"{color.WARNING}[⚡ EXTRACTING]{color.ENDC}  {title}"
        print_status()

        downloader.download([url])

        status[URLS.index(url)] = f"{color.OKGREEN}[✓ COMPLETE]{color.ENDC}    {title}"
        print_status()


# Driver code
status: List[str] = []
cli_options: List[Tuple[str, str]]
URLS: List[str]
quality_choice = None

try:
    cli_options, URLS = getopt(sys.argv[1:], 'hf:d:l:q:', ['help', 'ffmpeg=', 'dir=', 'limit=', 'quality='])  
except GetoptError as e:
    print(e, '\n')
    usage()

if len(cli_options)==0 and len(URLS)==0:
    usage()

# Set default values - MAXIMUM SPEED
limit = 4  # Increased default for speed
ffmpeg_path = get_ffmpeg_path()
download_path = get_download_path()

# Parse command line options
for option, value in cli_options:
    if option in ['-h', '--help'] : usage()
    if option in ['-d', '--dir'] : download_path = value
    if option in ['-f', '--ffmpeg'] : ffmpeg_path = get_ffmpeg_path(value)
    if option in ['-l', '--limit']:
        try : limit = int(value)
        except ValueError:
            print(f"{color.ERROR}[X] Invalid limit '{value}'{color.ENDC} (using default 4)")
            limit = 4
    if option in ['-q', '--quality']:
        if value in AUDIO_FORMATS:
            quality_choice = value
        else:
            print(f"{color.ERROR}[X] Invalid quality '{value}'. Must be 1-9.{color.ENDC}")
            exit(1)

# Display quality menu if not specified in command line
if quality_choice is None:
    display_quality_menu()
    quality_choice = get_quality_choice()

selected_format = AUDIO_FORMATS[quality_choice]

# Configure yt-dlp options for MAXIMUM SPEED and QUALITY
yt_dlp_options = {
    'quiet': True,
    'no_warnings': True,
    'format': selected_format['format'],
    'ffmpeg_location': ffmpeg_path,
    'keepvideo': False,
    'outtmpl': f'{download_path}/%(title)s.%(ext)s',
    'noplaylist': True,
    'noprogress': True,
    'prefer_ffmpeg': True,
    'extract_audio': True,
    'concurrent_fragment_downloads': 16,  # Maximum speed
    'retries': 10,
    'fragment_retries': 10,
    'http_chunk_size': 10485760,  # 10MB chunks for speed
}

# Add postprocessors based on format
if selected_format['ext'] in ['mp3', 'flac', 'wav']:
    yt_dlp_options['postprocessors'] = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': selected_format['ext'],
        'preferredquality': selected_format['quality']
    }]
elif selected_format['ext'] in ['opus', 'ogg', 'm4a']:
    yt_dlp_options['postprocessors'] = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': selected_format['ext'],
    }]

# Maximum quality settings
yt_dlp_options['audioquality'] = 0  # 0 = best quality
yt_dlp_options['audio_format'] = selected_format['ext']

# Initialize status
for url in URLS : status.append(f"{color.OKCYAN}[⏳ QUEUED]{color.ENDC}     {url}")

# Start downloads
clear()
hacker_banner()
print(f"\n{color.BOLD}{color.OKGREEN}[✓]{color.ENDC} {color.BOLD}INITIATING EXTRACTION PROTOCOL...{color.ENDC}")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Quality:{color.ENDC} {selected_format['name']} {selected_format['tier']}")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Threads:{color.ENDC} {limit} parallel operations")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Targets:{color.ENDC} {len(URLS)} URLs\n")
time.sleep(0.5)

with concurrent.futures.ThreadPoolExecutor(max_workers=limit) as executor:
    executor.map(download, URLS)

# Final status
print(f"\n{color.BOLD}{color.OKGREEN}[✓✓✓]{color.ENDC} {color.BOLD}ALL OPERATIONS COMPLETE{color.ENDC}")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} Files saved to: {download_path}\n")