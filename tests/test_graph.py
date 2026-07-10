import os
from unittest.mock import MagicMock, patch
import pytest
from langgraph.graph import END

from boresight.agents.graph import (
    GraphState,
    node_validation_agent,
    should_continue,
    get_llm
)

def test_get_llm_defaults():
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "LLM_MODEL": "gpt-4"}):
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            get_llm()
            mock_openai.assert_called_once_with(model="gpt-4", temperature=0.2)

def test_get_llm_validator_override():
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-4",
        "VALIDATOR_PROVIDER": "anthropic",
        "VALIDATOR_MODEL": "claude-3"
    }):
        with patch("langchain_anthropic.ChatAnthropic") as mock_anthropic:
            get_llm(role="validator")
            mock_anthropic.assert_called_once_with(model_name="claude-3", temperature=0.2)

def test_should_continue_disabled():
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "false"}):
        state: GraphState = {"is_valid": False, "validation_attempts": 0}
        assert should_continue(state) == END

def test_should_continue_enabled_valid():
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "true"}):
        state: GraphState = {"is_valid": True, "validation_attempts": 1}
        assert should_continue(state) == END

def test_should_continue_enabled_invalid_under_limit():
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "true", "VALIDATION_MAX_RETRIES": "3"}):
        state: GraphState = {"is_valid": False, "validation_attempts": 1}
        assert should_continue(state) == "CorrelationAgent"

def test_should_continue_enabled_invalid_over_limit():
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "true", "VALIDATION_MAX_RETRIES": "3"}):
        state: GraphState = {"is_valid": False, "validation_attempts": 3}
        assert should_continue(state) == END

@patch("boresight.agents.graph.get_llm")
def test_node_validation_agent_disabled(mock_get_llm):
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "false"}):
        state: GraphState = {
            "variance": 0.0,
            "overlap_confidence": 1.0,
            "jaccard_tfidf": 1.0,
            "report": "Brief text",
            "validation_attempts": 0
        }
        res = node_validation_agent(state)
        assert res["is_valid"] is True
        assert res["validation_feedback"] is None
        mock_get_llm.assert_not_called()

@patch("boresight.agents.graph.get_llm")
def test_node_validation_agent_enabled_valid(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = '{"is_valid": true, "feedback": ""}'
    mock_get_llm.return_value = mock_llm
    
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "true"}):
        state: GraphState = {
            "variance": 0.0,
            "overlap_confidence": 1.0,
            "jaccard_tfidf": 1.0,
            "report": "Brief text",
            "validation_attempts": 0
        }
        res = node_validation_agent(state)
        assert res["is_valid"] is True
        assert res["validation_feedback"] is None
        assert res["validation_attempts"] == 1

@patch("boresight.agents.graph.get_llm")
def test_node_validation_agent_enabled_invalid(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = '{"is_valid": false, "feedback": "Needs more detail"}'
    mock_get_llm.return_value = mock_llm
    
    with patch.dict(os.environ, {"VALIDATION_ENABLED": "true"}):
        state: GraphState = {
            "variance": 0.0,
            "overlap_confidence": 1.0,
            "jaccard_tfidf": 1.0,
            "report": "Brief text",
            "validation_attempts": 1
        }
        res = node_validation_agent(state)
        assert res["is_valid"] is False
        assert res["validation_feedback"] == "Needs more detail"
        assert res["validation_attempts"] == 2
