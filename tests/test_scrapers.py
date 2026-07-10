import json
import os
import sys
import pytest
from unittest.mock import patch
from click.testing import CliRunner

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.github_adapter import scrape_github
from scripts.reddit_adapter import scrape_reddit
from scripts.hackernews_adapter import scrape_hn
from scripts.devto_adapter import scrape_devto

@pytest.fixture
def runner():
    return CliRunner()

@patch("httpx.get")
def test_github_adapter(mock_get, runner, tmp_path):
    mock_get.return_value.json.return_value = [
        {"created_at": "2023-01-01T12:00:00Z"},
        {"created_at": "2023-01-02T15:30:00Z"}
    ]
    
    out_file = tmp_path / "out.json"
    result = runner.invoke(scrape_github, ["--username", "testuser", "--output", str(out_file)])
    
    assert result.exit_code == 0
    with open(out_file, "r") as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["source"] == "GitHub"
    assert data[0]["timestamp"] == "2023-01-01T12:00:00Z"

@patch("httpx.get")
def test_reddit_adapter(mock_get, runner, tmp_path):
    mock_get.return_value.json.return_value = {
        "data": {
            "children": [
                {"data": {"created_utc": 1672574400}}, # 2023-01-01 12:00:00 UTC
            ]
        }
    }
    
    out_file = tmp_path / "out.json"
    result = runner.invoke(scrape_reddit, ["--username", "testuser", "--output", str(out_file)])
    
    assert result.exit_code == 0
    with open(out_file, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["source"] == "Reddit"
    assert "2023-01-01" in data[0]["timestamp"]

@patch("httpx.get")
def test_hackernews_adapter(mock_get, runner, tmp_path):
    mock_get.return_value.json.return_value = {
        "hits": [
            {"created_at": "2023-01-01T12:00:00Z"}
        ]
    }
    
    out_file = tmp_path / "out.json"
    result = runner.invoke(scrape_hn, ["--username", "testuser", "--output", str(out_file)])
    
    assert result.exit_code == 0
    with open(out_file, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["source"] == "HackerNews"

@patch("httpx.get")
def test_devto_adapter(mock_get, runner, tmp_path):
    mock_get.return_value.json.return_value = [
        {"published_timestamp": "2023-01-01T12:00:00Z"}
    ]
    
    out_file = tmp_path / "out.json"
    result = runner.invoke(scrape_devto, ["--username", "testuser", "--output", str(out_file)])
    
    assert result.exit_code == 0
    with open(out_file, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["source"] == "DEV.to"
