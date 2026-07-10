"""
LangGraph Orchestration Engine.
Runs the multi-step forensic analysis pipeline.
"""

from typing import TypedDict, Dict, List, Optional
import os
import json
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd

from boresight.core.analytics import DatasetProfile, TemporalProcessor, calculate_correlation
from boresight.agents.prompts import (
    CORRELATION_AGENT_SYSTEM_PROMPT,
    build_correlation_user_prompt,
    VALIDATION_AGENT_SYSTEM_PROMPT,
    build_validation_user_prompt
)

def get_llm(role: str = "analyzer"):
    if role == "validator":
        provider = os.getenv("VALIDATOR_PROVIDER", os.getenv("LLM_PROVIDER", "openai")).lower()
        model = os.getenv("VALIDATOR_MODEL", os.getenv("LLM_MODEL"))
    else:
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model = os.getenv("LLM_MODEL")
        
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model or "gpt-4o", temperature=0.2)
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model or "llama3", temperature=0.2)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model or "gemini-1.5-flash", temperature=0.2)
    elif provider in ["anthropic", "claude"]:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model_name=model or "claude-3-5-sonnet-20240620", temperature=0.2)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


class GraphState(TypedDict):
    """State tracked through the LangGraph execution."""
    raw_dataset_a: List[Dict[str, str]]
    raw_dataset_b: List[Dict[str, str]]
    normalized_profile_a: Optional[pd.Series]
    normalized_profile_b: Optional[pd.Series]
    variance: float
    overlap_confidence: float
    jaccard_tfidf: float
    wasserstein: float
    report: str
    validation_attempts: int
    validation_feedback: Optional[str]
    is_valid: bool


def node_data_ingest(state: GraphState) -> GraphState:
    """Node 1: Normalizes raw datasets into Pydantic models and parses them."""
    try:
        # We validate by pushing them through Pydantic (exceptions bubble up if invalid)
        _ = DatasetProfile(logs=state["raw_dataset_a"])
        _ = DatasetProfile(logs=state["raw_dataset_b"])
    except Exception as e:
        raise ValueError(f"Failed to parse raw dataset into Pydantic models: {e}")
        
    return state


def node_pattern_analyzer(state: GraphState) -> GraphState:
    """Node 2: Evaluates daily active/inactive distributions and calculates correlation."""
    profile_a = DatasetProfile(logs=state["raw_dataset_a"])
    profile_b = DatasetProfile(logs=state["raw_dataset_b"])
    
    series_a = TemporalProcessor.aggregate_to_daily_profile(profile_a)
    series_b = TemporalProcessor.aggregate_to_daily_profile(profile_b)
    
    variance, overlap, jaccard_tfidf, wasserstein = calculate_correlation(series_a, series_b)
    
    return {
        **state,
        "normalized_profile_a": series_a,
        "normalized_profile_b": series_b,
        "variance": variance,
        "overlap_confidence": overlap,
        "jaccard_tfidf": jaccard_tfidf,
        "wasserstein": wasserstein
    }


def node_correlation_agent(state: GraphState) -> GraphState:
    """Node 3: Generates a forensic intelligence brief using an LLM."""
    llm = get_llm(role="analyzer")
    
    profile_a_dict = state['normalized_profile_a'].to_dict() if state['normalized_profile_a'] is not None else {}
    profile_b_dict = state['normalized_profile_b'].to_dict() if state['normalized_profile_b'] is not None else {}
    
    user_prompt = build_correlation_user_prompt(
        variance=state['variance'],
        overlap=state['overlap_confidence'],
        jaccard_tfidf=state.get('jaccard_tfidf', 0.0),
        wasserstein=state.get('wasserstein', 0.0),
        profile_a=profile_a_dict,
        profile_b=profile_b_dict,
        feedback=state.get('validation_feedback')
    )
    
    messages = [
        SystemMessage(content=CORRELATION_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    
    return {
        **state,
        "report": str(response.content)
    }


def node_validation_agent(state: GraphState) -> GraphState:
    """Node 4: Validates the generated brief against statistics using a validator LLM."""
    validation_enabled = os.getenv("VALIDATION_ENABLED", "false").lower() == "true"
    if not validation_enabled:
        return {
            **state,
            "is_valid": True,
            "validation_feedback": None
        }
        
    llm = get_llm(role="validator")
    user_prompt = build_validation_user_prompt(
        variance=state['variance'],
        overlap=state['overlap_confidence'],
        jaccard_tfidf=state.get('jaccard_tfidf', 0.0),
        wasserstein=state.get('wasserstein', 0.0),
        report=state['report']
    )
    
    messages = [
        SystemMessage(content=VALIDATION_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    content = str(response.content).strip()
    
    # Strip markdown block wraps if present
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 2 and (lines[0].startswith("```json") or lines[0].startswith("```")):
            content = "\n".join(lines[1:-1]).strip()
            
    is_valid = True
    feedback = None
    try:
        res_json = json.loads(content)
        is_valid = bool(res_json.get("is_valid", True))
        feedback = res_json.get("feedback")
    except Exception as e:
        feedback = f"Failed to parse validator JSON: {e}. Output was: {content}"
        is_valid = True
        
    attempts = state.get("validation_attempts", 0) + 1
    
    return {
        **state,
        "is_valid": is_valid,
        "validation_feedback": feedback if not is_valid else None,
        "validation_attempts": attempts
    }


def should_continue(state: GraphState):
    """Router to decide whether to exit or retry the correlation analysis."""
    validation_enabled = os.getenv("VALIDATION_ENABLED", "false").lower() == "true"
    if not validation_enabled:
        return END
        
    max_retries = int(os.getenv("VALIDATION_MAX_RETRIES", "3"))
    
    if state.get("is_valid", True):
        return END
        
    if state.get("validation_attempts", 0) < max_retries:
        return "CorrelationAgent"
        
    return END


def build_forensic_graph() -> StateGraph:
    """Compiles and returns the LangGraph workflow."""
    workflow = StateGraph(GraphState)
    
    workflow.add_node("DataIngest", node_data_ingest)
    workflow.add_node("PatternAnalyzer", node_pattern_analyzer)
    workflow.add_node("CorrelationAgent", node_correlation_agent)
    workflow.add_node("ValidationAgent", node_validation_agent)
    
    workflow.add_edge(START, "DataIngest")
    workflow.add_edge("DataIngest", "PatternAnalyzer")
    workflow.add_edge("PatternAnalyzer", "CorrelationAgent")
    workflow.add_edge("CorrelationAgent", "ValidationAgent")
    
    workflow.add_conditional_edges(
        "ValidationAgent",
        should_continue,
        {
            "CorrelationAgent": "CorrelationAgent",
            END: END
        }
    )
    
    return workflow.compile()
