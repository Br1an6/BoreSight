"""
DEV.to to BoreSight Adapter.
Fetches public articles for a DEV.to user and converts them into the 
BoreSight JSON timestamp format.
"""
import sys
import json
import httpx
import click

@click.command()
@click.option('--username', required=True, help='DEV.to username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
def scrape_devto(username: str, output: str):
    """Fetches DEV.to user articles and extracts timestamps."""
    url = f"https://dev.to/api/articles?username={username}"
    
    click.secho(f"[*] Fetching articles for DEV.to user {username}...", fg="cyan")
    try:
        response = httpx.get(url, headers={"User-Agent": "BoreSight-OSINT"})
        response.raise_for_status()
        articles = response.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch data: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    for article in articles:
        # DEV.to provides published_timestamp in ISO 8601 format
        created_at = article.get("published_timestamp") or article.get("created_at")
        if created_at:
            boresight_data.append({
                "timestamp": created_at,
                "source": "DEV.to"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public articles found for {username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_devto()
