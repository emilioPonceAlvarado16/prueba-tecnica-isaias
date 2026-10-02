"""Catálogo de códigos de resultado: estado, cola de escalamiento, siguiente acción, política y plantilla.

Las plantillas son el fallback del response_agent (LLM caído o mensaje que no pasa guardrails) y la
respuesta obligatoria en casos sensibles (riesgo alto).
"""
from dataclasses import dataclass

HELP = "Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias."


@dataclass(frozen=True)
class Outcome:
    code: str
    status: str
    next_action: str
    policy_ref: str
    proposed_solution: str
    template: str
    queue: str | None = None
    http_status: int = 200
    llm_allowed: bool = True


OUTCOMES: dict[str, Outcome] = {o.code: o for o in [
    Outcome("ONB-OK-000", "APPROVED", "LOGIN", "POL-PRD-003 §2",
            "Ingresar a la banca digital y cargar los documentos requeridos en 15 días.",
            "¡Hola {first_name}! Tu {product_name} fue aprobada. Ya creamos tu usuario de banca digital "
            "(usuario: tu número de cédula). Carga en la app, dentro de los próximos 15 días, estos documentos: "
            "{documents}. ¡Bienvenido a Banco Andino Demo!"),
    Outcome("ONB-OK-001", "APPROVED", "LOGIN", "POL-PLA-002 Art. 6",
            "Aprobado con debida diligencia reforzada: documentos adicionales y monitoreo transaccional 12 meses.",
            "¡Hola {first_name}! Gracias por completar la información adicional: tu {product_name} fue aprobada. "
            "Ya creamos tu usuario de banca digital (usuario: tu número de cédula). Carga en la app, dentro de los "
            "próximos 15 días, estos documentos: {documents}. ¡Bienvenido a Banco Andino Demo!"),
    Outcome("ONB-DOC-001", "REJECTED", "FIX_INPUT", "POL-KYC-001 Art. 2",
            "Verificar el número de cédula ingresado e intentar nuevamente.",
            "Hola {first_name}, el número de cédula que ingresaste no es válido, por lo que no podemos continuar "
            "con tu solicitud. Revísalo e intenta nuevamente. Código de referencia: ONB-DOC-001. " + HELP),
    Outcome("ONB-IDV-001", "ESCALATED", "VISIT_BRANCH", "POL-KYC-001 Art. 3",
            "Acercarse a una agencia con la cédula original para validación presencial de identidad.",
            "Hola {first_name}, por temas de políticas del banco no pudimos validar tu identidad en línea, por lo que "
            "no podemos continuar con tu {product_name} por este medio. Acércate a una de nuestras agencias con tu "
            "cédula original (terminada en {last4}) y te atenderemos de inmediato. Código de referencia: ONB-IDV-001. " + HELP,
            queue="agencia"),
    Outcome("ONB-IDV-002", "ESCALATED", "VISIT_BRANCH", "POL-KYC-001 Art. 4",
            "Acercarse a una agencia con la cédula original para validación biométrica presencial.",
            "Hola {first_name}, por temas de políticas del banco no podemos completar la apertura de tu {product_name} "
            "en línea. Para continuar, acércate a cualquiera de nuestras agencias con tu cédula original (terminada en "
            "{last4}) para una validación presencial, sin necesidad de cita. Código de referencia: ONB-IDV-002. " + HELP,
            queue="agencia"),
    Outcome("ONB-IDV-003", "ESCALATED", "VISIT_BRANCH", "POL-KYC-001 Art. 5",
            "Acercarse a una agencia con la cédula original para confirmar los datos de identidad.",
            "Hola {first_name}, por temas de políticas del banco no podemos continuar tu solicitud en línea porque no "
            "pudimos confirmar tus datos de identidad. Acércate a una de nuestras agencias con tu cédula original "
            "(terminada en {last4}). Código de referencia: ONB-IDV-003. " + HELP,
            queue="agencia"),
    Outcome("ONB-IDV-004", "REJECTED", "VISIT_BRANCH", "POL-KYC-001 Art. 6",
            "Abrir el producto en agencia acompañado del representante legal.",
            "Hola {first_name}, por temas de políticas del banco la apertura de productos en línea está disponible solo "
            "para mayores de 18 años. Puedes abrir tu {product_name} en cualquiera de nuestras agencias, acompañado de "
            "tu representante legal. Código de referencia: ONB-IDV-004. " + HELP),
    Outcome("ONB-RSK-001", "ESCALATED", "VISIT_BRANCH", "POL-PLA-002 Art. 5",
            "Caso enviado a revisión del Oficial de Cumplimiento (48 h). Al cliente: acercarse a agencia.",
            "Hola {first_name}, por temas de políticas del banco no es posible continuar con tu solicitud de "
            "{product_name} en línea. Te invitamos a acercarte a una de nuestras agencias para recibir atención "
            "personalizada. Código de referencia: ONB-REF-100. " + HELP,
            queue="cumplimiento", llm_allowed=False),
    Outcome("ONB-RSK-002", "AWAITING_CUSTOMER", "PROVIDE_INFO", "POL-PLA-002 Art. 6",
            "Completar en línea actividad económica, origen de fondos e ingresos mensuales (plazo 7 días).",
            "Hola {first_name}, ya casi terminamos. Por temas de políticas del banco necesitamos que nos compartas "
            "algunos datos adicionales: tu actividad económica, el origen de los fondos que usarás en tu "
            "{product_name} y tus ingresos mensuales estimados. Completa el formulario para continuar; tienes 7 días."),
    Outcome("ONB-IDV-503", "ERROR", "RETRY_LATER", "POL-ESC-004 §5",
            "Reintentar en unos minutos; caso registrado en soporte de tecnología.",
            "Hola {first_name}, en este momento nuestro servicio de verificación de identidad no está disponible y no "
            "pudimos completar tu solicitud. Intenta nuevamente en unos minutos. Si el problema continúa, comunícate al "
            "1800-ANDINO (1800-263466) e indica el código ONB-IDV-503.",
            queue="soporte_ti", http_status=503),
    Outcome("ONB-RSK-503", "ERROR", "RETRY_LATER", "POL-PLA-002 Art. 2",
            "Reintentar en unos minutos; sin consulta de listas no se puede aprobar (falla segura).",
            "Hola {first_name}, en este momento uno de nuestros servicios de validación no está disponible y no pudimos "
            "completar tu solicitud. Intenta nuevamente en unos minutos. Si el problema continúa, comunícate al "
            "1800-ANDINO (1800-263466) e indica el código ONB-RSK-503.",
            queue="soporte_ti", http_status=503),
    Outcome("ONB-PRV-503", "APPROVED_PENDING_PROVISIONING", "NONE", "POL-ESC-004 §6",
            "Soporte habilita el acceso digital en máximo 24 horas.",
            "¡Hola {first_name}! Tu {product_name} fue aprobada. Tu acceso a la banca digital estará listo en las "
            "próximas 24 horas; te avisaremos cuando puedas ingresar. Código de referencia: ONB-PRV-503. " + HELP,
            queue="soporte_ti"),
]}


def outcome(code: str) -> Outcome:
    return OUTCOMES[code]
