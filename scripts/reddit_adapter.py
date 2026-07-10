"""
Reddit to BoreSight Adapter.
Fetches public activity for a Reddit user and converts it into the 
BoreSight JSON timestamp format for temporal correlation.
"""
import sys
import json
import httpx
import click
from datetime import datetime, timezone

@click.command()
@click.option('--username', required=True, help='Reddit username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
def scrape_reddit(username: str, output: str):
    """Fetches Reddit user activity and extracts timestamps."""
    url = f"https://www.reddit.com/user/{username}.json?limit=100"
    
    click.secho(f"[*] Fetching public events for u/{username}...", fg="cyan")
    try:
        # Reddit requires a custom User-Agent to avoid 429 Too Many Requests
        response = httpx.get(url, headers={"User-Agent": "BoreSight-OSINT-Bot/1.0"})
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch data: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    children = data.get("data", {}).get("children", [])
    for child in children:
        # Reddit timestamps are UNIX epochs
        created_utc = child.get("data", {}).get("created_utc")
        if created_utc:
            # Convert to ISO 8601 format
            dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
            timestamp_iso = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            boresight_data.append({
                "timestamp": timestamp_iso,
                "source": "Reddit"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public events found for u/{username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_reddit()
