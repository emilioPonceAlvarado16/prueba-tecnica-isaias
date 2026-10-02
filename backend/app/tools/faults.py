import time

from app.db.repository import service_fault
from app.tools.errors import ToolTimeout, ToolUnavailable


def raise_if_faulty(tool_code: str, document_id: str) -> None:
    """Fallas simuladas (ext.service_fault). El timeout se simula sin esperar el timeout real para agilizar la demo."""
    fault = service_fault(tool_code, document_id)
    if fault == "timeout":
        time.sleep(0.3)
        raise ToolTimeout(f"{tool_code}: el proveedor no respondió dentro del tiempo límite")
    if fault == "error_500":
        raise ToolUnavailable(f"{tool_code}: el proveedor respondió HTTP 500")
