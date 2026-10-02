"""Construcción del grafo LangGraph del orquestador (ver docs/arquitectura/ARQUITECTURA.md)."""
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.agents.identity import identity_agent_node
from app.agents.policy import policy_agent_node
from app.agents.response import response_agent_node
from app.agents.risk import risk_agent_node
from app.config import settings
from app.graph.nodes import (decision_node, finalize_node, provision_user_node, request_customer_info_node,
                             validate_input_node)
from app.graph.state import OnboardingState


def route_after_validation(state: dict) -> str:
    return "identity_agent" if state["cedula_valid"] else "decision"


def route_after_identity(state: dict) -> str:
    return "decision" if state.get("outcome_code") else "risk_agent"


def route_after_risk(state: dict) -> str:
    code = state.get("outcome_code")
    if code == "ONB-RSK-002":
        return "request_customer_info"
    return "decision" if code else "policy_agent"


def route_after_decision(state: dict) -> str:
    return "provision_user" if state["decision"]["status"] == "APPROVED" else "response_agent"


def build_graph(checkpointer=None):
    graph = StateGraph(OnboardingState)
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("identity_agent", identity_agent_node)
    graph.add_node("risk_agent", risk_agent_node)
    graph.add_node("request_customer_info", request_customer_info_node)
    graph.add_node("policy_agent", policy_agent_node)
    graph.add_node("decision", decision_node)
    graph.add_node("provision_user", provision_user_node)
    graph.add_node("response_agent", response_agent_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input", route_after_validation, ["identity_agent", "decision"])
    graph.add_conditional_edges("identity_agent", route_after_identity, ["risk_agent", "decision"])
    graph.add_conditional_edges("risk_agent", route_after_risk, ["request_customer_info", "policy_agent", "decision"])
    graph.add_edge("request_customer_info", "policy_agent")
    graph.add_edge("policy_agent", "decision")
    graph.add_conditional_edges("decision", route_after_decision, ["provision_user", "response_agent"])
    graph.add_edge("provision_user", "response_agent")
    graph.add_edge("response_agent", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)


_graph = None


def get_graph():
    """Grafo compilado con checkpointer PostgreSQL (esquema 'checkpoint')."""
    global _graph
    if _graph is None:
        pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, open=True,
                              check=ConnectionPool.check_connection, kwargs={
            "autocommit": True, "prepare_threshold": 0, "row_factory": dict_row,
            "options": "-c search_path=checkpoint"})
        saver = PostgresSaver(pool)
        saver.setup()
        _graph = build_graph(saver)
    return _graph
