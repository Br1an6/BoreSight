import os
from unittest.mock import patch
from click.testing import CliRunner
from main import cli

def test_cli_validation_flags():
    runner = CliRunner()
    # Mock async_main so we don't actually run the full app
    with patch("main.async_main") as mock_async_main:
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, [
                "--dataset-a", "sample_data/mock_a.json",
                "--dataset-b", "sample_data/mock_b.json",
                "-o", "report.txt",
                "--validate",
                "--validation-retries", "5",
                "--validator-provider", "openai",
                "--validator-model", "gpt-4"
            ])
            
            assert result.exit_code == 0
            assert os.environ.get("VALIDATION_ENABLED") == "true"
            assert os.environ.get("VALIDATION_MAX_RETRIES") == "5"
            assert os.environ.get("VALIDATOR_PROVIDER") == "openai"
            assert os.environ.get("VALIDATOR_MODEL") == "gpt-4"
            mock_async_main.assert_called_once_with(
                "sample_data/mock_a.json",
                "sample_data/mock_b.json",
                None,
                None,
                "report.txt",
                False
            )

def test_cli_no_validation_flag():
    runner = CliRunner()
    with patch("main.async_main") as mock_async_main:
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, [
                "--dataset-a", "sample_data/mock_a.json",
                "--dataset-b", "sample_data/mock_b.json",
                "--no-validate"
            ])
            
            assert result.exit_code == 0
            assert os.environ.get("VALIDATION_ENABLED") == "false"

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["-v"])
    assert result.exit_code == 0
    assert "BoreSight v0.0.2" in result.output

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["-h"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output

def test_extract_timezone():
    from main import extract_timezone
    assert extract_timezone("The user is likely in UTC-5 timezone.") == "UTC-5"
    assert extract_timezone("Based on activity, the user resides in GMT+8 (China).") == "UTC+8"
    assert extract_timezone("Likely timezone abbreviation: JST (Tokyo).") == "UTC+9"
    assert extract_timezone("No timezone here") is None

def test_get_world_map_lines():
    from main import get_world_map_lines
    lines = get_world_map_lines("UTC-5")
    assert len(lines) == 23
    assert any("\033[1;31m●\033[0m" in line for line in lines)
