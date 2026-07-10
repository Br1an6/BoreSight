import asyncio
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

from boresight.core.network import AsyncNetworkClient
from boresight.core.analytics import DatasetProfile, TemporalProcessor, calculate_correlation
from main import fetch_or_read_dataset

# Initialize FastMCP Server
mcp = FastMCP("BoreSight Analytics")

@mcp.tool()
async def analyze_datasets(dataset_a: str, dataset_b: str) -> str:
    """
    Run BoreSight ML statistical correlation on two datasets.
    Provides mathematical analysis comparing active hours and behaviors.
    """
    network_client = AsyncNetworkClient()
    data_a = await fetch_or_read_dataset(dataset_a, network_client)
    data_b = await fetch_or_read_dataset(dataset_b, network_client)
    
    profile_a = DatasetProfile(logs=data_a)
    profile_b = DatasetProfile(logs=data_b)
    
    series_a = TemporalProcessor.aggregate_to_daily_profile(profile_a)
    series_b = TemporalProcessor.aggregate_to_daily_profile(profile_b)
    
    var, conf, jaccard, wasserstein = calculate_correlation(series_a, series_b)
    
    return f"""BoreSight Analysis Results:
- Dataset A Records: {len(data_a)}
- Dataset B Records: {len(data_b)}
---
- Overlap Confidence Index: {conf:.4f}
- Statistical Variance: {var:.4f}
- Jaccard TF-IDF: {jaccard:.4f}
- Earth Mover's (Wasserstein) Distance: {wasserstein:.4f}
"""

if __name__ == "__main__":
    mcp.run(transport="stdio")
