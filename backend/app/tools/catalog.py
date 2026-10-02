"""Ejemplos de uso por tool: se embeben junto con la descripción en rag.tool_embedding (RAG de tools)."""

TOOL_USAGE_EXAMPLES: dict[str, list[str]] = {
    "verify_identity": [
        "verificar la identidad del cliente con el Registro Civil",
        "validar que la cédula pertenezca a una persona viva y obtener la confianza biométrica",
    ],
    "check_risk_lists": [
        "consultar si el cliente aparece en listas de sanciones, OFAC, ONU o UAFE",
        "determinar si el prospecto es una Persona Expuesta Políticamente (PEP)",
    ],
    "prepare_documentation": [
        "obtener la lista de documentos requeridos para abrir una cuenta",
        "qué documentos debe presentar el cliente según el producto y su riesgo",
    ],
    "search_policies": [
        "buscar en las políticas del banco qué artículo regula un requisito",
        "consultar la política de comunicación con el cliente",
    ],
}
