import pytest
import pandas as pd
from boresight.core.analytics import DatasetProfile, TimestampLog, TemporalProcessor, calculate_correlation

def test_aggregate_to_daily_profile():
    logs = [
        {"timestamp": "2023-01-01T12:00:00Z", "source": "A"},
        {"timestamp": "2023-01-02T12:30:00Z", "source": "A"},
        {"timestamp": "2023-01-03T14:00:00Z", "source": "A"}
    ]
    profile = DatasetProfile(logs=[TimestampLog(**log) for log in logs])
    series = TemporalProcessor.aggregate_to_daily_profile(profile)
    
    assert len(series) == 24
    assert series[12] == pytest.approx(2/3)
    assert series[14] == pytest.approx(1/3)
    assert series[0] == 0.0

def test_calculate_correlation():
    # Perfect match
    series_a = pd.Series([0.5, 0.5] + [0]*22)
    series_b = pd.Series([0.5, 0.5] + [0]*22)
    var, conf, jaccard, wasserstein = calculate_correlation(series_a, series_b)
    assert var == 0.0
    assert conf == pytest.approx(1.0)
    assert jaccard == pytest.approx(1.0)
    assert wasserstein == 0.0
    
    # Complete mismatch
    series_c = pd.Series([0]*22 + [0.5, 0.5])
    var, conf, jaccard, wasserstein = calculate_correlation(series_a, series_c)
    assert var > 0.0
    assert conf == 0.0
    assert jaccard == 0.0
    assert wasserstein > 0.0

def test_zach_anomaly(capsys):
    from boresight.core.analytics import ZachAnomaly
    # Generate 24 logs, one for each hour
    logs = [{"timestamp": f"2023-01-01T{h:02d}:00:00Z", "source": "A"} for h in range(24)]
    profile = DatasetProfile(logs=[TimestampLog(**log) for log in logs])
    
    # This should trigger the warning printout to stderr
    series = TemporalProcessor.aggregate_to_daily_profile(profile)
    assert len(series) == 24
    
    captured = capsys.readouterr()
    assert "😴 ZachAnomaly: We found a Zach! Subject treats a sleep schedule as an optional suggestion." in captured.err

