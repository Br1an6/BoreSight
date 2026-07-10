"""
BoreSight CLI Entrypoint.
"""

import sys
import json
import os
import re
import asyncio
import click
import random
import string
from pathlib import Path
from typing import List, Dict, Optional

from boresight.core.network import ProxyRotator, AsyncNetworkClient
from boresight.agents.graph import build_forensic_graph, GraphState


async def matrix_animation(stop_event: asyncio.Event):
    """Matrix vertical drop down animation using ANSI escape codes."""
    # Replaced Japanese characters with standard ASCII symbols to prevent UnicodeEncodeError in some terminals
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    width = 60
    height = 10
    
    sys.stdout.write("\n" * height)
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    # Initialize with random negative starting positions so they fall gracefully from the top
    drops = [random.randint(-15, 0) for _ in range(width)]
    lengths = [random.randint(5, 10) for _ in range(width)]
    
    try:
        while not stop_event.is_set():
            sys.stdout.write(f"\033[{height}A")
            for y in range(height):
                line = ""
                for x in range(width):
                    if drops[x] == y:
                        # Head of the drop (bright white)
                        line += f"\033[1;37m{random.choice(chars)}\033[0m"
                    elif drops[x] - 2 <= y < drops[x]:
                        # Middle of the drop (bright green)
                        line += f"\033[1;32m{random.choice(chars)}\033[0m"
                    elif drops[x] - lengths[x] < y < drops[x] - 2:
                        # Tail of the drop (dark shaded green)
                        line += f"\033[38;5;28m{random.choice(chars)}\033[0m"
                    else:
                        line += " "
                sys.stdout.write(line + "\033[K\n")
            sys.stdout.flush()
            
            for x in range(width):
                # If the drop has completely fallen off the bottom
                if drops[x] - lengths[x] > height:
                    if random.random() < 0.05:
                        drops[x] = 0
                        lengths[x] = random.randint(5, 10)
                else:
                    drops[x] += 1
            await asyncio.sleep(0.06)
    finally:
        sys.stdout.write(f"\033[{height}A")
        for _ in range(height):
            sys.stdout.write("\033[2K\n")
        sys.stdout.write(f"\033[{height}A")
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()



async def fetch_or_read_dataset(path_or_url: str, network_client: AsyncNetworkClient) -> List[Dict[str, str]]:
    """Helper function to load dataset from local file or remote URL."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        try:
            response = await network_client.fetch(path_or_url)
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Remote dataset must be a JSON array of timestamp objects.")
            return data
        except Exception as e:
            click.secho(f"Error fetching dataset from URL {path_or_url}: {e}", fg="red")
            sys.exit(1)
    else:
        file_path = Path(path_or_url)
        if not file_path.is_file():
            click.secho(f"Local file not found: {path_or_url}", fg="red")
            sys.exit(1)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("Local dataset must be a JSON array of timestamp objects.")
                return data
        except Exception as e:
            click.secho(f"Error reading dataset from file {path_or_url}: {e}", fg="red")
            sys.exit(1)


def extract_timezone(report: str) -> Optional[str]:
    """Helper to extract guessed timezone from the report text."""
    # Match UTC/GMT offsets (e.g. UTC+8, GMT-5)
    match = re.search(r'\b(UTC|GMT)\s*([+-]\d{1,2})(?::\d{2})?\b', report, re.IGNORECASE)
    if match:
        sign = match.group(2)[0]
        val = int(match.group(2)[1:])
        offset = val if sign == '+' else -val
        offset = max(-11, min(12, offset))
        return f"UTC{offset:+d}"
        
    # Match common abbreviations
    tz_mapping = {
        r'\bEST\b': "UTC-5",
        r'\bEDT\b': "UTC-4",
        r'\bPST\b': "UTC-8",
        r'\bPDT\b': "UTC-7",
        r'\bMST\b': "UTC-7",
        r'\bMDT\b': "UTC-6",
        r'\bCST\b': "UTC-6",
        r'\bCDT\b': "UTC-5",
        r'\bCET\b': "UTC+1",
        r'\bCEST\b': "UTC+2",
        r'\bGMT\b': "UTC+0",
        r'\bJST\b': "UTC+9",
        r'\bAEST\b': "UTC+10",
        r'\bAEDT\b': "UTC+11",
    }
    for pattern, tz in tz_mapping.items():
        if re.search(pattern, report, re.IGNORECASE):
            return tz
            
    # Generic UTC offset in text (e.g. "UTC +3")
    match_generic = re.search(r'\bUTC\s*([+-]\d{1,2})\b', report, re.IGNORECASE)
    if match_generic:
        val = int(match_generic.group(1))
        offset = max(-11, min(12, val))
        return f"UTC{offset:+d}"
        
    return None


def get_world_map_lines(timezone_str: str) -> List[str]:
    """Generates colored ASCII world map lines with a pinpoint at the given timezone."""
    tz_coords = {
        "UTC-11": (1, 13), "UTC-10": (4, 11), "UTC-9": (5, 7), "UTC-8": (11, 9),
        "UTC-7": (14, 9), "UTC-6": (17, 9), "UTC-5": (20, 9), "UTC-4": (21, 14),
        "UTC-3": (25, 14), "UTC-2": (27, 16), "UTC-1": (30, 9), "UTC+0": (34, 8),
        "UTC+1": (35, 8), "UTC+2": (41, 10), "UTC+3": (42, 8), "UTC+4": (45, 10),
        "UTC+5": (48, 10), "UTC+6": (52, 10), "UTC+7": (54, 11), "UTC+8": (57, 9),
        "UTC+9": (62, 10), "UTC+10": (64, 14), "UTC+11": (66, 13), "UTC+12": (68, 15),
    }
    
    # Clean timezone_str to match keys
    m = re.match(r'UTC([+-])(\d+)', timezone_str)
    if m:
        sign = m.group(1)
        val = int(m.group(2))
        timezone_key = f"UTC{sign}{val}"
    else:
        timezone_key = timezone_str

    target_coord = tz_coords.get(timezone_key)

    USER_MAP = r"""         . _..::__:  ,-"-"._       |]       ,     _,.__              
  _.___ _ _<_>`!(._`.`-.    /        _._     `_ ,_/  '  '-._.---.-.__ 
.{     " " `-==,',._\{  \  / {)     / _ ">_,-' `                 /-/_ 
 \_.:--.       `._ )`^-. "'      , [_/(                       __,/-'  
'"'     \         "    _L       |-_,--'                )     /. (|    
         |           ,'         _)_.\\._<> {}              _,' /  '   
         `.         /          [_/_'` `"(                <'}  )       
          \\    .-. )          /   `-'"..' `:._          _)  '        
   `        \  (  `(          /         `:\  > \  ,-^.  /' '          
             `._,   ""        |           \`'   \|   ?_)  {\          
                `=.---.       `._._       ,'     "`  |' ,- '.         
                  |    `-._        |     /          `:`<_|=--._       
                  (        >       .     | ,          `=.__.`-'\      
                   `.     /        |     |{|              ,-.,\     . 
                    |   ,'          \   / `'            ,"     \      
                    |  /             |_'                |  __  /      
                    | |                                 '-'  `-'   \. 
                    |/                                        "    /  
                    \.                                            '   
                                                                      
                     ,/           ______._.--._ _..---.---------.     
__,-----"-..?----_/ )\    . ,-'"             "                  (__--/
                      /__/\/                                          """

    MAP_GRID = [row for row in USER_MAP.split("\n")]
    map_width = max(len(row) for row in MAP_GRID)
    MAP_GRID = [row.ljust(map_width) for row in MAP_GRID]

    output_lines = []
    for y, row in enumerate(MAP_GRID):
        colored_row = ""
        for x, char in enumerate(row):
            if target_coord and x == target_coord[0] and y == target_coord[1]:
                colored_row += "\033[1;31m●\033[0m" # Bold Red Dot
            elif char in [" ", "\t"]:
                colored_row += f"\033[34m{char}\033[0m" # Blue Ocean
            else:
                colored_row += f"\033[32m{char}\033[0m" # Green Land
        output_lines.append(colored_row)
    return output_lines


async def async_main(dataset_a: str, dataset_b: Optional[str], dataset_dir: Optional[str], proxies_file: Optional[str], output_file: Optional[str] = None) -> None:
    # 1. Initialize Network Engine
    rotator: Optional[ProxyRotator] = None
    if proxies_file:
        proxy_path = Path(proxies_file)
        if not proxy_path.is_file():
            click.secho(f"Proxies file not found: {proxies_file}", fg="red")
            sys.exit(1)
        with open(proxy_path, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies:
            rotator = ProxyRotator(proxies)
            click.secho(f"[*] Loaded {len(proxies)} proxies.", fg="blue")
            
    network_client = AsyncNetworkClient(proxy_rotator=rotator)
    
    # 2. Fetch Datasets
    click.secho("[*] Loading primary dataset...", fg="cyan")
    data_a = await fetch_or_read_dataset(dataset_a, network_client)
    click.secho(f"[*] Loaded {len(data_a)} records for Dataset A.", fg="cyan")
    
    if dataset_dir:
        click.secho(f"[*] Running 1-to-Many bulk correlation against directory: {dataset_dir}", fg="yellow")
        dir_path = Path(dataset_dir)
        if not dir_path.is_dir():
            click.secho(f"[!] Directory not found: {dataset_dir}", fg="red")
            sys.exit(1)
            
        from boresight.core.analytics import DatasetProfile, TemporalProcessor, calculate_correlation
        
        profile_a = DatasetProfile(logs=data_a)
        series_a = TemporalProcessor.aggregate_to_daily_profile(profile_a)
        
        candidates = []
        for file_path in dir_path.glob("*.json"):
            # skip comparing against itself if it's in the same dir
            if str(file_path) == dataset_a:
                continue
            try:
                candidate_data = await fetch_or_read_dataset(str(file_path), network_client)
                profile_cand = DatasetProfile(logs=candidate_data)
                series_cand = TemporalProcessor.aggregate_to_daily_profile(profile_cand)
                
                variance, overlap, jaccard, wasserstein = calculate_correlation(series_a, series_cand)
                candidates.append({
                    "file": file_path.name,
                    "wasserstein": wasserstein,
                    "jaccard": jaccard,
                    "data": candidate_data
                })
            except Exception as e:
                click.secho(f"[-] Skipped {file_path.name} due to error: {e}", fg="red")
                
        if not candidates:
            click.secho("[!] No valid candidate datasets found in directory.", fg="red")
            sys.exit(1)
            
        # Sort candidates by Wasserstein Distance (lower is better, meaning closer distributions)
        candidates.sort(key=lambda x: x["wasserstein"])
        
        click.secho("\n" + "="*50, fg="cyan", bold=True)
        click.secho("1-TO-MANY CORRELATION LEADERBOARD", fg="cyan", bold=True)
        click.secho("="*50, fg="cyan", bold=True)
        for i, cand in enumerate(candidates[:5]):
            color = "green" if i == 0 else "yellow"
            click.secho(f"{i+1}. {cand['file']} | Wasserstein: {cand['wasserstein']:.4f} | Jaccard TF-IDF: {cand['jaccard']:.4f}", fg=color)
            
        click.secho(f"\n[*] Selecting top candidate ({candidates[0]['file']}) for deep LLM analysis...", fg="green")
        data_b = candidates[0]['data']
        dataset_b = candidates[0]['file'] # purely for logging context
        
    elif dataset_b:
        data_b = await fetch_or_read_dataset(dataset_b, network_client)
        click.secho(f"[*] Loaded {len(data_b)} records for Dataset B.", fg="cyan")
    else:
        click.secho("[!] Must provide either --dataset-b or --dataset-dir", fg="red")
        sys.exit(1)
    
    # 3. Graph Execution
    click.secho("[*] Initializing temporal correlation engine...", fg="yellow")
    graph = build_forensic_graph()
    
    initial_state: GraphState = {
        "raw_dataset_a": data_a,
        "raw_dataset_b": data_b,
        "normalized_profile_a": None,
        "normalized_profile_b": None,
        "variance": 0.0,
        "overlap_confidence": 0.0,
        "jaccard_tfidf": 0.0,
        "report": "",
        "validation_attempts": 0,
        "validation_feedback": None,
        "is_valid": False
    }
    
    # Start matrix animation
    stop_event = asyncio.Event()
    animation_task = asyncio.create_task(matrix_animation(stop_event))
    
    # Ensure animation starts drawing before we lock the thread
    await asyncio.sleep(0.1)
    
    try:
        final_state = await asyncio.to_thread(graph.invoke, initial_state)
    except Exception as e:
        stop_event.set()
        await animation_task
        click.secho(f"[!] Error during correlation analysis: {e}", fg="red")
        sys.exit(1)
    finally:
        stop_event.set()
        await animation_task
        
    # 4. Reporting
    click.secho("\n" + "="*60, fg="green", bold=True)
    click.secho("FORENSIC INTELLIGENCE BRIEF", fg="green", bold=True)
    click.secho("="*60 + "\n", fg="green", bold=True)
    
    click.echo(final_state["report"])
    
    # Try to extract timezone and draw map
    guessed_tz = extract_timezone(final_state["report"])
    map_lines = []
    if guessed_tz:
        map_lines = get_world_map_lines(guessed_tz)
        click.secho(f"\n--- Guessed Location Pinpoint (Timezone: {guessed_tz}) ---", fg="cyan", bold=True)
        for line in map_lines:
            click.echo(line)
        click.echo("")

    click.secho("\n" + "="*60, fg="green", bold=True)
    click.secho(f"Earth Mover's (Wasserstein) Distance: {final_state.get('wasserstein', 0.0):.4f}", fg="magenta")
    click.secho(f"Overlap Confidence Index: {final_state['overlap_confidence']:.4f}", fg="magenta")
    click.secho(f"Statistical Variance:     {final_state['variance']:.4f}", fg="magenta")
    click.secho("="*60 + "\n", fg="green", bold=True)

    if output_file:
        try:
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            is_md = output_file.lower().endswith('.md')
            with open(output_file, "w", encoding="utf-8") as f:
                if is_md:
                    f.write("# FORENSIC INTELLIGENCE BRIEF\n\n")
                    f.write(final_state["report"])
                    f.write("\n\n")
                    
                    if map_lines:
                        f.write(f"### Guessed Location Pinpoint (Timezone: {guessed_tz})\n")
                        f.write("```text\n")
                        for line in map_lines:
                            f.write(ansi_escape.sub('', line) + "\n")
                        f.write("```\n\n")
                        
                    f.write("### Statistical Analysis\n")
                    f.write(f"- **Wasserstein Distance:** `{final_state.get('wasserstein', 0.0):.4f}`\n")
                    f.write(f"- **Overlap Confidence Index:** `{final_state['overlap_confidence']:.4f}`\n")
                    f.write(f"- **Statistical Variance:** `{final_state['variance']:.4f}`\n")
                else:
                    f.write("="*60 + "\n")
                    f.write("FORENSIC INTELLIGENCE BRIEF\n")
                    f.write("="*60 + "\n\n")
                    f.write(final_state["report"])
                    f.write("\n\n")
                    
                    if map_lines:
                        f.write(f"--- Guessed Location Pinpoint (Timezone: {guessed_tz}) ---\n")
                        for line in map_lines:
                            f.write(ansi_escape.sub('', line) + "\n")
                        f.write("\n")
                        
                    f.write("="*60 + "\n")
                    f.write(f"Wasserstein Distance:     {final_state.get('wasserstein', 0.0):.4f}\n")
                    f.write(f"Overlap Confidence Index: {final_state['overlap_confidence']:.4f}\n")
                    f.write(f"Statistical Variance:     {final_state['variance']:.4f}\n")
                    f.write("="*60 + "\n")
            click.secho(f"[+] Saved report to {output_file}", fg="green")
        except Exception as e:
            click.secho(f"[!] Failed to write output file: {e}", fg="red")


def print_banner():
    BLUE = "\033[38;5;33m"
    RESET = "\033[0m"
    STEEL = "\033[38;5;244m"
    SCOPE = "\033[38;5;123m"

    BORESIGHT_LOGO = f"""{BLUE}
████   ███  ████  █████  ████ ███  ███  █   █ █████   {SCOPE}
{BLUE}█░░░█ █ ░░█ █░░░█ █░░░░░█ ░░░░ █░░█ ░░░ █░  █░ ░█░░░  {SCOPE}
{BLUE}████░░█░ ░█░████░░████░░░███░░░█░░█░ ██░█████░░ █░░░░ {SCOPE}
{BLUE}█░░░█ █░░ █░█░░█░ █░░░░   ░░█  █░░█░░ █░█░░░█░░ █░░   {SCOPE}
{BLUE}████░░ ███ ░█░░░█░█████░████░░███░ ███ ░█░░░█░░ █░░   {SCOPE}                             
{BLUE} ░░░░ ░ ░░░ ░░░  ░ ░░░░░ ░░░░ ░░░░  ░░░ ░░░  ░░  ░░   {SCOPE} ____________                             
{BLUE}  ░░░░   ░░░  ░   ░ ░░░░░ ░░░░  ░░░  ░░░  ░   ░   ░   {STEEL}|____________|
                         ______________________________||________||___
                        [___|____________|/____,----------._ [====]o'""-,__....----====={STEEL}
                                         [____(oooooooooooo)___________/__________     |
                                               //\"\"\"\"\"\"\"\"\"\"  |====| [_)           \\    |
                                              // \\\\          |====|                \\   |
                                             //   \\\\         |====|                 \"\"\"\"
                                            (_)   (_)        `----'{RESET}
"""
    click.echo(BORESIGHT_LOGO)


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--dataset-a', required=True, help='Path or URL to primary dataset JSON.')
@click.option('--dataset-b', required=False, help='Path or URL to secondary dataset JSON (1-to-1 analysis).')
@click.option('--dataset-dir', required=False, help='Path to directory of datasets (1-to-Many analysis).')
@click.option('--proxies', required=False, type=str, help='Path to a text file containing proxy endpoints.')
@click.option('-o', '--output', type=click.Path(writable=True), help='Path to output file for saving the forensic brief.')
@click.option('--validate/--no-validate', default=None, help='Enable/disable self-validation of the generated brief (overrides VALIDATION_ENABLED).')
@click.option('--validation-retries', type=int, default=None, help='Maximum number of validation retries (overrides VALIDATION_MAX_RETRIES).')
@click.option('--validator-provider', type=str, default=None, help='LLM provider for validation (overrides VALIDATOR_PROVIDER).')
@click.option('--validator-model', type=str, default=None, help='LLM model for validation (overrides VALIDATOR_MODEL).')
@click.version_option('0.0.1', '-v', '--version', message='BoreSight v%(version)s')
def cli(
    dataset_a: str,
    dataset_b: Optional[str],
    dataset_dir: Optional[str],
    proxies: Optional[str],
    output: Optional[str],
    validate: Optional[bool],
    validation_retries: Optional[int],
    validator_provider: Optional[str],
    validator_model: Optional[str]
) -> None:
    """
    BoreSight: Passive time-series correlation and behavioral alignment tool.
    """
    if validate is not None:
        os.environ["VALIDATION_ENABLED"] = "true" if validate else "false"
    if validation_retries is not None:
        os.environ["VALIDATION_MAX_RETRIES"] = str(validation_retries)
    if validator_provider is not None:
        os.environ["VALIDATOR_PROVIDER"] = validator_provider
    if validator_model is not None:
        os.environ["VALIDATOR_MODEL"] = validator_model

    print_banner()
    click.secho("Starting BoreSight Analysis...", fg="blue", bold=True)
    asyncio.run(async_main(dataset_a, dataset_b, dataset_dir, proxies, output))


if __name__ == '__main__':
    cli()
