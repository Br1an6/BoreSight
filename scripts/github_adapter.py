"""
GitHub to BoreSight Adapter.
Fetches public commit activity for a GitHub user and converts it into the 
BoreSight JSON timestamp format for temporal correlation.
"""
import sys
import json
import httpx
import click

@click.command()
@click.option('--username', required=True, help='GitHub username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
def scrape_github(username: str, output: str):
    """Fetches GitHub events and extracts timestamps."""
    url = f"https://api.github.com/users/{username}/events/public"
    
    click.secho(f"[*] Fetching public events for {username}...", fg="cyan")
    try:
        response = httpx.get(url, headers={"User-Agent": "BoreSight-OSINT"})
        response.raise_for_status()
        events = response.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch data: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    for event in events:
        created_at = event.get("created_at")
        if created_at:
            boresight_data.append({
                "timestamp": created_at,
                "source": "GitHub"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public events found for {username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_github()
