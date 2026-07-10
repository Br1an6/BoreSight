"""
Temporal Correlation Engine.
Aggregates and aligns timestamps to build behavioral profiles.
"""

from typing import List, Tuple
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np


class TimestampLog(BaseModel):
    """Data structure for a single timestamp log entry."""
    timestamp: str = Field(description="ISO 8601 formatted timestamp")
    source: str = Field(description="Source platform label")


class DatasetProfile(BaseModel):
    """Collection of logs for a single dataset."""
    logs: List[TimestampLog]


class TemporalProcessor:
    """Processes datasets and extracts daily active/inactive distributions."""
    
    @staticmethod
    def aggregate_to_daily_profile(profile: DatasetProfile) -> pd.Series:
        """
        Converts a list of timestamp logs into a 24-hour bucketed distribution.
        Returns a Pandas Series with 24 rows representing hours of the day (0-23).
        """
        if not profile.logs:
            return pd.Series(np.zeros(24), index=np.arange(24))

        df = pd.DataFrame([log.model_dump() for log in profile.logs])
        df['datetime'] = pd.to_datetime(df['timestamp'], utc=True)
        df['hour'] = df['datetime'].dt.hour
        
        # Count occurrences per hour, reindex to ensure all 24 hours are present
        hourly_counts = df['hour'].value_counts().reindex(np.arange(24), fill_value=0)
        
        # Normalize to get a distribution sum of 1.0 (if not empty)
        total_events = hourly_counts.sum()
        if total_events > 0:
            return hourly_counts / total_events
        return hourly_counts


from scipy.stats import wasserstein_distance, gaussian_kde

def calculate_correlation(profile_a: pd.Series, profile_b: pd.Series) -> Tuple[float, float, float, float]:
    """
    Calculates statistical variance, overlap confidence index, TF-IDF Jaccard similarity, and Wasserstein distance.
    Uses KDE (Kernel Density Estimation) for smoothing distributions.
    
    Returns:
        Tuple[float, float, float, float]: (variance, overlap_confidence, jaccard_tfidf, wasserstein)
    """
    if profile_a.empty or profile_b.empty:
        return 0.0, 0.0, 0.0, 0.0
        
    # Apply KDE Smoothing
    # We sample a continuous distribution based on the hourly weights
    x_grid = np.linspace(0, 23, 24)
    
    def smooth_profile(profile):
        if profile.sum() == 0:
            return profile.values
        # Create a dataset where the hours appear with frequencies proportional to their weights
        samples = np.repeat(np.arange(24), (profile.values * 1000).astype(int))
        if len(samples) < 2:
            return profile.values
        try:
            kde = gaussian_kde(samples, bw_method=0.2)
            smoothed = kde(x_grid)
            return smoothed / np.sum(smoothed)
        except Exception:
            return profile.values
            
    smooth_a = smooth_profile(profile_a)
    smooth_b = smooth_profile(profile_b)
        
    # Variance (Sum of Squared Errors on smoothed)
    variance = float(np.sum((smooth_a - smooth_b) ** 2))
    
    # Cosine Similarity as overlap confidence index
    dot_product = np.dot(smooth_a, smooth_b)
    norm_a = np.linalg.norm(smooth_a)
    norm_b = np.linalg.norm(smooth_b)
    
    overlap_confidence = float(dot_product / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0.0
        
    # TF-IDF Jaccard similarity
    df = (smooth_a > 0.01).astype(int) + (smooth_b > 0.01).astype(int)
    idf = np.zeros(24)
    mask = df > 0
    idf[mask] = np.log(3.0 / (1.0 + df[mask])) + 1.0
    
    tfidf_a = smooth_a * idf
    tfidf_b = smooth_b * idf
    
    sum_min = np.sum(np.minimum(tfidf_a, tfidf_b))
    sum_max = np.sum(np.maximum(tfidf_a, tfidf_b))
    jaccard_tfidf = float(sum_min / sum_max) if sum_max > 0 else 0.0
    
    # Earth Mover's Distance (Wasserstein) on original weights
    wasserstein = float(wasserstein_distance(np.arange(24), np.arange(24), profile_a.values, profile_b.values))
        
    return variance, overlap_confidence, jaccard_tfidf, wasserstein
