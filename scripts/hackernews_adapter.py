"""
HackerNews to BoreSight Adapter.
Fetches public activity for a HackerNews user using the HN Algolia API
and converts it into the BoreSight JSON timestamp format.
"""
import sys
import json
import httpx
import click

@click.command()
@click.option('--username', required=True, help='HackerNews username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
def scrape_hn(username: str, output: str):
    """Fetches HackerNews user activity and extracts timestamps."""
    url = f"https://hn.algolia.com/api/v1/search_by_date?tags=author_{username}&hitsPerPage=100"
    
    click.secho(f"[*] Fetching public events for HN user {username}...", fg="cyan")
    try:
        response = httpx.get(url, headers={"User-Agent": "BoreSight-OSINT"})
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch data: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    hits = data.get("hits", [])
    for hit in hits:
        created_at = hit.get("created_at")
        if created_at:
            boresight_data.append({
                "timestamp": created_at,
                "source": "HackerNews"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public events found for {username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_hn()
