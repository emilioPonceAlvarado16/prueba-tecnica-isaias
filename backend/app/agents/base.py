"""Bucle genérico de agente: LLM con tools acotados por el ToolGate + guardia de tools obligatorios.

Si el LLM no está disponible, el agente degrada a modo determinístico (ejecuta los tools obligatorios):
las reglas de decisión no dependen del LLM.
"""
import json
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.tool_gate import ToolGate
from app.config import settings
from app.db import repository


@dataclass
class AgentRun:
    summary: str | None = None
    llm_error: str | None = None
    tool_calls_by_llm: list[str] = field(default_factory=list)


def chat_model(temperature: float) -> ChatOpenAI:
    return ChatOpenAI(model=settings.chat_model, temperature=temperature, timeout=30, max_retries=1)


def run_agent(agent_code: str, task: str, facts: dict, gate: ToolGate,
              mandatory: dict[str, dict], max_steps: int = 4) -> AgentRun:
    agent = repository.get_agent(agent_code)
    run = AgentRun()
    bound_tools = gate.select_tools(task, required=list(mandatory))

    if settings.openai_api_key:
        try:
            llm = chat_model(float(agent["temperature"])).bind_tools(gate.openai_specs(bound_tools))
            messages = [SystemMessage(agent["system_prompt"]),
                        HumanMessage(f"{task}\n\nContexto (sin datos personales):\n{json.dumps(facts, ensure_ascii=False)}")]
            for _ in range(max_steps):
                ai = llm.invoke(messages)
                messages.append(ai)
                if not ai.tool_calls:
                    run.summary = (ai.content or "").strip() or None
                    break
                for call in ai.tool_calls:
                    run.tool_calls_by_llm.append(call["name"])
                    content = gate.execute_for_llm(call["name"], call.get("args") or {})
                    messages.append(ToolMessage(json.dumps(content, ensure_ascii=False, default=str),
                                                tool_call_id=call["id"]))
        except Exception as exc:  # noqa: BLE001 - cualquier falla del LLM degrada a modo determinístico
            run.llm_error = f"{type(exc).__name__}: {exc}"[:300]

    # Guardia: los tools obligatorios se ejecutan aunque el LLM no los haya llamado
    for code, args in mandatory.items():
        if code not in gate.results and code not in gate.failures:
            gate.forced.append(code)
            gate.execute_for_llm(code, args)
    return run


def agent_output(gate: ToolGate, run: AgentRun) -> dict:
    """Metadatos de orquestación que se guardan en core.onboarding_step.output."""
    return {
        "tool_selection": gate.selection,
        "llm_tool_calls": run.tool_calls_by_llm,
        "forced_tools": gate.forced,
        "denied_tools": gate.denied,
        "tool_failures": gate.failures,
        "llm_summary": run.summary,
        "llm_error": run.llm_error,
    }
