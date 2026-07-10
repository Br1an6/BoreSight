import json
import random
from datetime import datetime, timedelta

def generate_mock_data(filename, source_name, hour_peak, count=100):
    data = []
    base_time = datetime.utcnow()
    for _ in range(count):
        # Generate timestamps primarily clustered around 'hour_peak'
        offset = random.gauss(0, 2) # normal distribution of +/- 2 hours
        hour = int(hour_peak + offset) % 24
        
        # Random day in the past 30 days
        days_ago = random.randint(0, 30)
        
        timestamp = base_time - timedelta(days=days_ago)
        timestamp = timestamp.replace(hour=hour, minute=random.randint(0, 59))
        
        data.append({
            "timestamp": timestamp.isoformat() + "Z",
            "source": source_name
        })
        
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
        
if __name__ == "__main__":
    import os
    os.makedirs("sample_data", exist_ok=True)
    
    # Generate two highly correlated datasets (both peaking around 14:00 UTC)
    # Drastically reduced the record counts to avoid LLM input token limits!
    generate_mock_data("sample_data/mock_a.json", "Reddit", 14, 20)
    generate_mock_data("sample_data/mock_b.json", "GitHub", 14, 15)
    
    # Generate an uncorrelated dataset (peaking at 02:00 UTC)
    generate_mock_data("sample_data/mock_c.json", "HackerNews", 2, 15)
    
    print("[+] Generated mock datasets in sample_data/: mock_a.json, mock_b.json, mock_c.json")
    print("[*] Try testing a high-correlation match:")
    print("    boresight --dataset-a sample_data/mock_a.json --dataset-b sample_data/mock_b.json")
    print("[*] Try testing a low-correlation mismatch:")
    print("    boresight --dataset-a sample_data/mock_a.json --dataset-b sample_data/mock_c.json")
