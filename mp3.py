#!/usr/bin/env python3

import concurrent.futures
import os
import platform
import random
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
        'tier': '💎 GODMODE',
        # Force 32-bit signed PCM — no intermediate lossy step, no bit depth downgrade
        'pp_args': ['-acodec', 'pcm_s32le', '-sample_fmt', 's32'],
    },
    '2': {
        'name': 'FLAC (LOSSLESS)',
        'ext': 'flac',
        'quality': 'best',
        'description': '⚡ AUDIOPHILE ELITE - Perfect lossless, compressed but zero quality loss',
        'format': 'bestaudio/best',
        'tier': '💎 GODMODE',
        # 32-bit sample format + max compression level — lossless by spec, never lossy
        'pp_args': ['-sample_fmt', 's32', '-compression_level', '8'],
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
        'tier': '🏆 ELITE',
        # Stream-copy the native Opus track — zero re-encoding, what YouTube actually has
        'pp_args': ['-vn', '-c:a', 'copy'],
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


# ---------------------------------------------------------------------------
# FINGERPRINT POOLS
# Realistic browser/device fingerprints — rotated per strategy to look human.
# Each UA is paired with matching headers so the whole profile is consistent.
# ---------------------------------------------------------------------------

# Real Chrome on Windows 11 fingerprints (most common browser/OS combo on YT)
CHROME_WIN_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'platform': 'Windows',
    },
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'platform': 'Windows',
    },
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'platform': 'Windows',
    },
]

# Real Chrome on macOS fingerprints
CHROME_MAC_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'platform': 'macOS',
    },
    {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'platform': 'macOS',
    },
]

# Real Firefox on Windows fingerprints
FIREFOX_WIN_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'sec_ch_ua': None,  # Firefox doesn't send sec-ch-ua
        'platform': 'Windows',
    },
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'sec_ch_ua': None,
        'platform': 'Windows',
    },
]

# Real Safari on macOS fingerprints
SAFARI_MAC_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15',
        'sec_ch_ua': None,  # Safari doesn't send sec-ch-ua
        'platform': 'macOS',
    },
]

# Android Chrome (mobile) — treated like a real phone by YouTube
ANDROID_CHROME_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.105 Mobile Safari/537.36',
        'sec_ch_ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'platform': 'Android',
    },
    {
        'user_agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.178 Mobile Safari/537.36',
        'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'platform': 'Android',
    },
    {
        'user_agent': 'Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36',
        'sec_ch_ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'platform': 'Android',
    },
]

# iOS Safari — iPhones are almost never flagged
IOS_SAFARI_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1',
        'sec_ch_ua': None,
        'platform': 'iOS',
    },
    {
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'sec_ch_ua': None,
        'platform': 'iOS',
    },
]


def build_http_headers(profile: dict) -> dict:
    """
    Build a full, realistic HTTP header set from a device profile.
    These match what a real browser sends — missing or inconsistent
    headers are one of the biggest bot signals YouTube checks for.
    """
    is_mobile = profile['platform'] in ('Android', 'iOS')
    is_firefox = 'Firefox' in profile['user_agent']
    is_safari  = 'Safari' in profile['user_agent'] and 'Chrome' not in profile['user_agent']

    headers = {
        'User-Agent': profile['user_agent'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': random.choice([
            'en-US,en;q=0.9',
            'en-US,en;q=0.9,es;q=0.8',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8',
        ]),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': random.choice(['none', 'same-origin']),
        'Sec-Fetch-User': '?1',
        'Cache-Control': random.choice(['max-age=0', 'no-cache']),
        'DNT': random.choice(['1', None, None]),  # most people don't set DNT
    }

    # Remove None values
    headers = {k: v for k, v in headers.items() if v is not None}

    # Chrome-specific client hints — Firefox/Safari don't send these
    if profile.get('sec_ch_ua'):
        mobile_val = '?1' if is_mobile else '?0'
        headers['Sec-Ch-Ua']          = profile['sec_ch_ua']
        headers['Sec-Ch-Ua-Mobile']   = mobile_val
        headers['Sec-Ch-Ua-Platform'] = f'"{profile["platform"]}"'

    # Firefox sends slightly different accept header
    if is_firefox:
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        headers['Accept-Language'] = random.choice(['en-US,en;q=0.5', 'en-GB,en;q=0.5'])

    return headers


# ---------------------------------------------------------------------------
# FALLBACK STRATEGY CHAIN
# Ordered from least invasive to most aggressive.
# Each strategy is a complete, consistent device identity.
# ---------------------------------------------------------------------------

def build_strategies() -> list:
    """Build the strategy chain. Called fresh each run so profiles are randomized."""
    return [
        # 1. Bare default — works 99% of the time on residential IPs
        {
            'name': 'Default',
            'overrides': {}
        },

        # 2. Randomized real Chrome/Windows fingerprint
        {
            'name': 'Chrome/Windows fingerprint',
            'overrides': {
                **({'http_headers': build_http_headers(random.choice(CHROME_WIN_PROFILES))}),
            }
        },

        # 3. Android Chrome — real phone UA + matching headers
        {
            'name': 'Android Chrome fingerprint',
            'overrides': {
                'http_headers': build_http_headers(random.choice(ANDROID_CHROME_PROFILES)),
                'extractor_args': {'youtube': {'player_client': ['android']}},
            }
        },

        # 4. iOS Safari — Apple devices almost never get bot-checked
        {
            'name': 'iOS Safari fingerprint',
            'overrides': {
                'http_headers': build_http_headers(random.choice(IOS_SAFARI_PROFILES)),
                'extractor_args': {'youtube': {'player_client': ['ios']}},
            }
        },

        # 5. Chrome on macOS
        {
            'name': 'Chrome/macOS fingerprint',
            'overrides': {
                'http_headers': build_http_headers(random.choice(CHROME_MAC_PROFILES)),
            }
        },

        # 6. Firefox on Windows — different header profile entirely
        {
            'name': 'Firefox/Windows fingerprint',
            'overrides': {
                'http_headers': build_http_headers(random.choice(FIREFOX_WIN_PROFILES)),
            }
        },

        # 7. TV Embedded client — YouTube barely checks smart TV traffic
        {
            'name': 'TV Embedded client',
            'overrides': {
                'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
            }
        },

        # 8. Safari on macOS
        {
            'name': 'Safari/macOS fingerprint',
            'overrides': {
                'http_headers': build_http_headers(random.choice(SAFARI_MAC_PROFILES)),
            }
        },

        # 9. Android + randomized Windows headers as extra noise
        {
            'name': 'Android client + Chrome headers',
            'overrides': {
                'http_headers': build_http_headers(random.choice(CHROME_WIN_PROFILES)),
                'extractor_args': {'youtube': {'player_client': ['android']}},
            }
        },

        # 10. Multi-client chain — last resort, tries android→ios→tv in sequence
        {
            'name': 'Multi-client chain + Android headers',
            'overrides': {
                'http_headers': build_http_headers(random.choice(ANDROID_CHROME_PROFILES)),
                'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'tv_embedded']}},
            }
        },
    ]


def hacker_banner():
    """Display sick hacker-style banner"""
    clear()
    
    banner_lines = [
        "╔═══════════════════════════════════════════════════════════════════════╗",
        "║                                                                       ║",
        "║  ██╗   ██╗████████╗███╗   ███╗██████╗ ██████╗       ██████╗ ██╗       ║",
        "║  ╚██╗ ██╔╝╚══██╔══╝████╗ ████║██╔══██╗╚════██╗      ██╔══██╗██║       ║",
        "║   ╚████╔╝    ██║   ██╔████╔██║██████╔╝ █████╔╝█████╗██║  ██║██║       ║",
        "║    ╚██╔╝     ██║   ██║╚██╔╝██║██╔═══╝  ╚═══██╗╚════╝██║  ██║██║       ║",
        "║     ██║      ██║   ██║ ╚═╝ ██║██║     ██████╔╝      ██████╔╝███████╗  ║",
        "║     ╚═╝      ╚═╝   ╚═╝     ╚═╝╚═╝     ╚═════╝       ╚═════╝ ╚══════╝  ║",
        "║                                                                       ║",
        "║              [ AUDIO EXTRACTION SYSTEM v4.0 ]                         ║",
        "║              [ MAXIMUM QUALITY • MAXIMUM SPEED ]                      ║",
        "╚═══════════════════════════════════════════════════════════════════════╝"
    ]
    
    colors_map = {
        0: color.ERROR,
        1: color.ERROR,
        2: color.BLINK + color.ERROR,
        3: color.BLINK + color.WARNING,
        4: color.BLINK + color.OKGREEN,
        5: color.BLINK + color.OKCYAN,
        6: color.BLINK + color.PURPLE,
        7: color.BLINK + color.BLUE,
        8: color.ERROR,
        9: color.BOLD + color.OKGREEN,
        10: color.OKCYAN,
        11: color.ERROR
    }
    
    for i, line in enumerate(banner_lines):
        print(f"{colors_map.get(i, color.ERROR)}{line}{color.ENDC}")


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
    default_path = '~/ytmp3-premium/music-output'
    expanded_path = os.path.expanduser(default_path)
    os.makedirs(expanded_path, exist_ok=True)
    return expanded_path


def get_ffmpeg_path(path=''):
    """Set ffmpeg binary location"""
    if path != '':
        if os.path.exists(path) and (path.split('/')[-1] in ['ffmpeg', 'ffmpeg.exe']): return path
        else: print(f"{color.BOLD}{color.ERROR}[X] ffmpeg NOT FOUND at `{path}`{color.ENDC}"); exit(0)

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


def build_options(overrides: dict) -> dict:
    """Merge base yt_dlp_options with a fallback strategy's overrides"""
    opts = dict(yt_dlp_options)
    opts.update(overrides)
    return opts


def download(url):
    """
    Download audio from YouTube URL.
    Cycles through the full fingerprint strategy chain on any failure.
    Each strategy presents a different, fully consistent device identity.
    """
    fallback_strategies = build_strategies()  # fresh randomized profiles per download
    last_error = None

    for i, strategy in enumerate(fallback_strategies):
        opts = build_options(strategy['overrides'])
        strategy_label = f"[{i+1}/{len(fallback_strategies)}] {strategy['name']}"

        try:
            with yt_dlp.YoutubeDL(opts) as downloader:
                info = downloader.extract_info(url, download=False)
                title = info.get('title', 'Unknown')

                status[URLS.index(url)] = f"{color.WARNING}[⚡ EXTRACTING]{color.ENDC}  {title}  {color.BLUE}({strategy['name']}){color.ENDC}"
                print_status()

                downloader.download([url])

                status[URLS.index(url)] = f"{color.OKGREEN}[✓ COMPLETE]{color.ENDC}    {title}"
                print_status()
                return  # success — stop trying

        except Exception as e:
            last_error = e
            status[URLS.index(url)] = f"{color.ERROR}[✗ FAILED]{color.ENDC}      {url}  {color.WARNING}→ trying: {strategy_label}{color.ENDC}"
            print_status()
            # Small human-like delay between attempts — rapid retries look robotic
            time.sleep(random.uniform(1.5, 3.5))

    # All strategies exhausted
    status[URLS.index(url)] = f"{color.ERROR}[✗✗ GAVE UP]{color.ENDC}    {url}  {color.ERROR}(all {len(fallback_strategies)} strategies failed){color.ENDC}"
    print_status()
    print(f"{color.BOLD}{color.ERROR}[FATAL]{color.ENDC} Could not download: {url}")
    print(f"        Last error: {last_error}")


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

# Set default values
limit = 4
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
            print(f"{color.ERROR}[X] Invalid quality '{value}'. Must be 1-8.{color.ENDC}")
            exit(1)

# Display quality menu if not specified in command line
if quality_choice is None:
    display_quality_menu()
    quality_choice = get_quality_choice()

selected_format = AUDIO_FORMATS[quality_choice]

# Base yt-dlp options — clean, no fingerprint overrides (strategies handle those)
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
    'concurrent_fragment_downloads': 16,
    'retries': 10,
    'fragment_retries': 10,
    'http_chunk_size': 10485760,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': selected_format['ext'],
        'preferredquality': selected_format['quality'] if selected_format['quality'] != 'best' else '0',
    }],
}

# Wire in per-format ffmpeg args so lossless formats get proper encoding:
#   WAV  → pcm_s32le (32-bit PCM, no bit-depth downgrade)
#   FLAC → s32 sample fmt + compression_level 8 (lossless by spec, max compression)
#   Opus → stream-copy the native track, no re-encode
if selected_format.get('pp_args'):
    yt_dlp_options['postprocessor_args'] = {
        'FFmpegExtractAudio': selected_format['pp_args']
    }

# Initialize status
for url in URLS: status.append(f"{color.OKCYAN}[⏳ QUEUED]{color.ENDC}     {url}")

# Start downloads
clear()
hacker_banner()
print(f"\n{color.BOLD}{color.OKGREEN}[✓]{color.ENDC} {color.BOLD}INITIATING EXTRACTION PROTOCOL...{color.ENDC}")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Quality:{color.ENDC} {selected_format['name']} {selected_format['tier']}")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Threads:{color.ENDC} {limit} parallel operations")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Targets:{color.ENDC} {len(URLS)} URLs")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} {color.BOLD}Fallbacks:{color.ENDC} 10 device fingerprint strategies loaded\n")
time.sleep(0.5)

with concurrent.futures.ThreadPoolExecutor(max_workers=limit) as executor:
    executor.map(download, URLS)

# Final status
print(f"\n{color.BOLD}{color.OKGREEN}[✓✓✓]{color.ENDC} {color.BOLD}ALL OPERATIONS COMPLETE{color.ENDC}")
print(f"{color.BOLD}{color.OKCYAN}[>]{color.ENDC} Files saved to: {download_path}\n")
