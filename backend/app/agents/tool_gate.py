"""ToolGate: el orquestador controla qué tools puede usar cada agente.

1. RAG de tools: candidatos semánticos para la tarea del agente (rag.tool_embedding).
2. Intersección obligatoria con la allowlist (core.agent_tool_permission).
3. Cualquier intento fuera de la allowlist -> 'denied' en core.tool_call_log, no se ejecuta.
4. Ejecución con contratos marshmallow, timeout y reintentos (core.tool), auditada por intento.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from marshmallow import ValidationError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.db import repository
from app.domain.cedula import mask
from app.rag.tool_retriever import retrieve_tools
from app.tools.errors import ToolError, ToolTimeout
from app.tools.registry import TOOLS

_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="tool")


def _mask_args(args: dict) -> dict:
    masked = dict(args)
    if "document_id" in masked:
        masked["document_id"] = mask(masked["document_id"])
    if "name" in masked:
        parts = masked["name"].split()
        masked["name"] = " ".join([parts[0]] + [p[0] + "." for p in parts[1:]]) if parts else ""
    return masked


class ToolGate:
    def __init__(self, agent_code: str, onboarding_id: str, context: dict):
        self.agent_code = agent_code
        self.onboarding_id = onboarding_id
        self.context = {**context, "onboarding_id": onboarding_id, "agent_code": agent_code}
        self.allowed = repository.allowed_tools(agent_code)
        self.results: dict[str, dict] = {}
        self.history: dict[str, list[dict]] = {}
        self.failures: dict[str, str] = {}      # tool -> código de error de negocio (core.tool.error_code)
        self.denied: list[str] = []
        self.forced: list[str] = []
        self.selection: dict = {}

    # ------------------------------------------------------------ selección
    def select_tools(self, task: str, required: list[str]) -> list[str]:
        candidates = list(retrieve_tools(task))
        selected = [code for code, _ in candidates if code in self.allowed]
        for code in required:
            if code in self.allowed and code not in selected:
                selected.append(code)
        self.selection = {"rag_candidates": candidates, "allowlist": sorted(self.allowed), "bound": selected}
        return selected

    def openai_specs(self, codes: list[str]) -> list[dict]:
        specs = []
        for code in codes:
            tool = repository.get_tool(code)
            specs.append({"type": "function", "function": {
                "name": code, "description": tool["description"], "parameters": tool["input_schema"]}})
        return specs

    # ------------------------------------------------------------ ejecución
    def execute_for_llm(self, tool_code: str, llm_args: dict | None = None) -> dict:
        """Ejecuta (o reutiliza) un tool y devuelve la proyección sin PII para el LLM."""
        if tool_code not in self.allowed or tool_code not in TOOLS:
            self.denied.append(tool_code)
            repository.insert_tool_call(self.onboarding_id, self.agent_code, tool_code, llm_args or {}, None,
                                        "denied", 1, 0, "Tool fuera de la allowlist del agente")
            return {"error": f"La herramienta '{tool_code}' no está permitida para este agente."}
        if tool_code in self.failures:
            return {"error": f"Servicio no disponible ({self.failures[tool_code]})."}
        if tool_code in self.results and tool_code != "search_policies":
            return TOOLS[tool_code].for_llm(self.results[tool_code])
        result = self.run(tool_code, llm_args or {})
        if result is None:
            return {"error": f"Servicio no disponible ({self.failures[tool_code]})."}
        return TOOLS[tool_code].for_llm(result)

    def run(self, tool_code: str, llm_args: dict) -> dict | None:
        spec, tool = TOOLS[tool_code], repository.get_tool(tool_code)
        args, kwargs = spec.build_args(self.context, llm_args)
        try:
            args = spec.input_schema.load(args)
        except ValidationError as exc:
            repository.insert_tool_call(self.onboarding_id, self.agent_code, tool_code, _mask_args(args), None,
                                        "error", 1, 0, f"Entrada inválida: {exc.messages}")
            self.failures[tool_code] = tool["error_code"]
            return None

        masked = _mask_args(args)
        try:
            for attempt in Retrying(stop=stop_after_attempt(1 + tool["max_retries"]),
                                    wait=wait_exponential(multiplier=0.2, max=1.0),
                                    retry=retry_if_exception_type(ToolError), reraise=True):
                with attempt:
                    number = attempt.retry_state.attempt_number
                    started = time.perf_counter()
                    try:
                        future = _pool.submit(spec.fn, **args, **kwargs)
                        try:
                            raw = future.result(timeout=tool["timeout_ms"] / 1000)
                        except FutureTimeout as exc:
                            raise ToolTimeout(f"{tool_code}: timeout de {tool['timeout_ms']} ms") from exc
                        result = spec.output_schema.load(spec.output_schema.dump(raw))
                    except ToolError as exc:
                        status = "timeout" if isinstance(exc, ToolTimeout) else "error"
                        repository.insert_tool_call(self.onboarding_id, self.agent_code, tool_code, masked, None, status,
                                                    number, int((time.perf_counter() - started) * 1000), str(exc))
                        raise
                    repository.insert_tool_call(self.onboarding_id, self.agent_code, tool_code, masked,
                                                spec.output_schema.dump(result), "success", number,
                                                int((time.perf_counter() - started) * 1000), None)
        except Exception as exc:                     # agotó reintentos o error no recuperable
            if not isinstance(exc, ToolError):
                repository.insert_tool_call(self.onboarding_id, self.agent_code, tool_code, masked, None, "error",
                                            1, None, f"{type(exc).__name__}: {exc}"[:500])
            self.failures[tool_code] = tool["error_code"]
            return None

        result = spec.output_schema.dump(result)
        self.results[tool_code] = result
        self.history.setdefault(tool_code, []).append(result)
        return result
