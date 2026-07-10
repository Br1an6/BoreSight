"""
Wikipedia to BoreSight Adapter.
Fetches public edit contributions for a Wikipedia user using the MediaWiki API
and converts them into the BoreSight JSON timestamp format.
"""
import sys
import json
import httpx
import click

@click.command()
@click.option('--username', required=True, help='Wikipedia username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
def scrape_wikipedia(username: str, output: str):
    """Fetches Wikipedia user edit contributions and extracts timestamps."""
    # MediaWiki API to get user contributions
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": username,
        "format": "json",
        "uclimit": 100
    }
    
    click.secho(f"[*] Fetching edit contributions for Wikipedia user {username}...", fg="cyan")
    try:
        response = httpx.get(url, params=params, headers={"User-Agent": "BoreSight-OSINT"})
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch data: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    contribs = data.get("query", {}).get("usercontribs", [])
    
    for contrib in contribs:
        timestamp = contrib.get("timestamp")
        if timestamp:
            boresight_data.append({
                "timestamp": timestamp,
                "source": "Wikipedia"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public contributions found for {username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_wikipedia()
