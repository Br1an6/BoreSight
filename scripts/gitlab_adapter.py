"""
GitLab to BoreSight Adapter.
Fetches public activity for a GitLab user using their public API
and converts it into the BoreSight JSON timestamp format.
"""
import sys
import json
import httpx
import click

@click.command()
@click.option('--username', required=True, help='GitLab username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
def scrape_gitlab(username: str, output: str):
    """Fetches GitLab user activity and extracts timestamps."""
    
    # 1. Resolve username to GitLab User ID
    user_url = f"https://gitlab.com/api/v4/users?username={username}"
    click.secho(f"[*] Resolving GitLab user ID for {username}...", fg="cyan")
    try:
        user_resp = httpx.get(user_url, headers={"User-Agent": "BoreSight-OSINT"})
        user_resp.raise_for_status()
        users = user_resp.json()
        if not users:
            click.secho(f"[!] User not found.", fg="red")
            sys.exit(1)
        user_id = users[0]["id"]
    except Exception as e:
        click.secho(f"[!] Failed to fetch user ID: {e}", fg="red")
        sys.exit(1)

    # 2. Fetch User Events
    events_url = f"https://gitlab.com/api/v4/users/{user_id}/events"
    click.secho(f"[*] Fetching events for GitLab user {username} (ID: {user_id})...", fg="cyan")
    try:
        events_resp = httpx.get(events_url, headers={"User-Agent": "BoreSight-OSINT"})
        events_resp.raise_for_status()
        events = events_resp.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch events: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    for event in events:
        created_at = event.get("created_at")
        if created_at:
            boresight_data.append({
                "timestamp": created_at,
                "source": "GitLab"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public events found for {username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_gitlab()
