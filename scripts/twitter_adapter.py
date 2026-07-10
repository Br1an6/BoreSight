"""
Twitter/X to BoreSight Adapter.
Fetches public activity for a Twitter user using the Twitter v2 API
and converts it into the BoreSight JSON timestamp format.
Requires a Twitter API Bearer Token.
"""
import sys
import json
import httpx
import click

@click.command()
@click.option('--username', required=True, help='Twitter username to scrape.')
@click.option('--output', required=True, help='Output JSON file path.')
@click.option('--bearer-token', required=True, envvar='TWITTER_BEARER_TOKEN', help='Twitter API Bearer Token.')
def scrape_twitter(username: str, output: str, bearer_token: str):
    """Fetches Twitter user activity and extracts timestamps."""
    # First, get the user ID
    user_url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {bearer_token}", "User-Agent": "BoreSight-OSINT"}
    
    click.secho(f"[*] Fetching user ID for @{username}...", fg="cyan")
    try:
        user_resp = httpx.get(user_url, headers=headers)
        user_resp.raise_for_status()
        user_data = user_resp.json()
        if "data" not in user_data:
            click.secho(f"[!] User not found: {user_data}", fg="red")
            sys.exit(1)
        user_id = user_data["data"]["id"]
    except Exception as e:
        click.secho(f"[!] Failed to fetch user ID: {e}", fg="red")
        sys.exit(1)

    # Now get the user's tweets
    tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {"max_results": 100, "tweet.fields": "created_at"}
    
    click.secho(f"[*] Fetching tweets for @{username} (ID: {user_id})...", fg="cyan")
    try:
        tweets_resp = httpx.get(tweets_url, headers=headers, params=params)
        tweets_resp.raise_for_status()
        tweets_data = tweets_resp.json()
    except Exception as e:
        click.secho(f"[!] Failed to fetch tweets: {e}", fg="red")
        sys.exit(1)
        
    boresight_data = []
    tweets = tweets_data.get("data", [])
    for tweet in tweets:
        created_at = tweet.get("created_at")
        if created_at:
            boresight_data.append({
                "timestamp": created_at,
                "source": "Twitter"
            })
            
    if not boresight_data:
        click.secho(f"[-] No public events found for @{username}.", fg="yellow")
        sys.exit(0)
        
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(boresight_data, f, indent=4)
        
    click.secho(f"[+] Successfully saved {len(boresight_data)} timestamps to {output}", fg="green")

if __name__ == "__main__":
    scrape_twitter()
