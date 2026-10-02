-- Catálogos: productos, documentos, requisitos (alineado con POL-PRD-003), agentes, tools y permisos.
BEGIN;

INSERT INTO core.product (code, name, description, min_age, digital_onboarding, policy_ref) VALUES
 ('cuenta_ahorros',   'Cuenta de Ahorros',     'Cuenta de ahorros sin monto mínimo de apertura en canal digital.', 18, true, 'POL-PRD-003'),
 ('cuenta_corriente', 'Cuenta Corriente',      'Cuenta corriente con chequera; depósito inicial de USD 200 en 30 días.', 18, true, 'POL-PRD-003'),
 ('deposito_plazo',   'Depósito a Plazo Fijo', 'Inversión desde USD 1.000 a un plazo mínimo de 31 días.', 18, true, 'POL-PRD-003')
ON CONFLICT (code) DO NOTHING;

INSERT INTO core.document_type (code, name, description) VALUES
 ('CEDULA',               'Cédula de ciudadanía',                        'Copia digital legible de ambos lados.'),
 ('PLANILLA_SERVICIO',    'Planilla de servicio básico',                 'Luz, agua o teléfono, con antigüedad máxima de 3 meses.'),
 ('TERMINOS_CONDICIONES', 'Aceptación de términos y condiciones',        'Aceptación electrónica en la app.'),
 ('FORMULARIO_KYC',       'Formulario Conozca a su Cliente',             'Datos personales, laborales y de contacto.'),
 ('REFERENCIA_BANCARIA',  'Referencia bancaria o comercial',             'Con antigüedad mínima de un año.'),
 ('FIRMA_ELECTRONICA',    'Registro de firma electrónica',               'Certificado de firma electrónica vigente.'),
 ('ORIGEN_FONDOS',        'Declaración de origen lícito de fondos',      'Formato del banco, firmado electrónicamente.'),
 ('FORMULARIO_PEP',       'Formulario de Persona Expuesta Políticamente','Cargo, institución y período.'),
 ('CERTIFICADO_INGRESOS', 'Certificado de ingresos',                     'Rol de pagos, declaración de IR o certificado del empleador.')
ON CONFLICT (code) DO NOTHING;

INSERT INTO core.product_document_requirement (product_code, document_code, condition, mandatory, policy_ref) VALUES
 ('cuenta_ahorros',   'CEDULA',               'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_ahorros',   'PLANILLA_SERVICIO',    'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_ahorros',   'TERMINOS_CONDICIONES', 'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_ahorros',   'FORMULARIO_KYC',       'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_ahorros',   'ORIGEN_FONDOS',        'risk_medium', true, 'POL-PLA-002 Art. 6'),
 ('cuenta_ahorros',   'FORMULARIO_PEP',       'pep',         true, 'POL-PLA-002 Art. 6'),
 ('cuenta_corriente', 'CEDULA',               'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_corriente', 'PLANILLA_SERVICIO',    'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_corriente', 'TERMINOS_CONDICIONES', 'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_corriente', 'FORMULARIO_KYC',       'always',      true, 'POL-PRD-003 §2'),
 ('cuenta_corriente', 'REFERENCIA_BANCARIA',  'always',      true, 'POL-PRD-003 §4'),
 ('cuenta_corriente', 'FIRMA_ELECTRONICA',    'always',      true, 'POL-PRD-003 §4'),
 ('cuenta_corriente', 'ORIGEN_FONDOS',        'risk_medium', true, 'POL-PLA-002 Art. 6'),
 ('cuenta_corriente', 'FORMULARIO_PEP',       'pep',         true, 'POL-PLA-002 Art. 6'),
 ('cuenta_corriente', 'CERTIFICADO_INGRESOS', 'risk_medium', true, 'POL-PRD-003 §2'),
 ('deposito_plazo',   'CEDULA',               'always',      true, 'POL-PRD-003 §2'),
 ('deposito_plazo',   'FORMULARIO_KYC',       'always',      true, 'POL-PRD-003 §2'),
 ('deposito_plazo',   'ORIGEN_FONDOS',        'always',      true, 'POL-PRD-003 §2'),
 ('deposito_plazo',   'TERMINOS_CONDICIONES', 'always',      true, 'POL-PRD-003 §2'),
 ('deposito_plazo',   'FORMULARIO_PEP',       'pep',         true, 'POL-PLA-002 Art. 6')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Agentes
-- ---------------------------------------------------------------------------
INSERT INTO core.agent (code, name, description, system_prompt, model, temperature) VALUES
('orchestrator', 'Orquestador', 'Coordina el grafo de onboarding; no ejecuta tools de negocio.',
 'Orquestador determinístico (LangGraph). No usa LLM.', 'none', 0),

('identity_agent', 'Agente de Identidad',
 'Verifica la identidad del prospecto contra el Registro Civil.',
 'Eres el agente de verificación de identidad de Banco Andino Demo. Tu tarea es verificar la identidad del prospecto '
 'usando las herramientas disponibles. Los datos personales (cédula, nombre) los inyecta el sistema: no los inventes ni los pidas. '
 'Llama la herramienta de verificación una sola vez y luego resume en una oración, en español, el resultado '
 '(verificado o no y la confianza). No tomes la decisión final: solo informa.',
 'gpt-4.1-mini', 0),

('risk_agent', 'Agente de Listas de Riesgo',
 'Consulta listas de control (OFAC, ONU, UAFE, PEP, interna) y clasifica el riesgo.',
 'Eres el agente de prevención de lavado de activos de Banco Andino Demo. Consulta las listas de control con la herramienta '
 'disponible (el sistema inyecta nombre y cédula). Luego resume en una oración el nivel de riesgo y cuántas coincidencias hubo, '
 'sin nombrar a terceros. No tomes la decisión final.',
 'gpt-4.1-mini', 0),

('policy_agent', 'Agente de Políticas',
 'Recupera las políticas aplicables (RAG) y prepara la documentación requerida.',
 'Eres el agente de políticas de Banco Andino Demo. Debes: (1) buscar en las políticas del banco los requisitos aplicables al '
 'producto y al nivel de riesgo del cliente usando search_policies, y (2) obtener la lista oficial de documentos con '
 'prepare_documentation. Responde con un resumen breve en español de los requisitos y cita los artículos (código de política y sección). '
 'No inventes requisitos que no estén en las políticas.',
 'gpt-4.1-mini', 0),

('response_agent', 'Agente de Respuesta',
 'Redacta el mensaje final al cliente según POL-COM-005.',
 'Eres el agente que redacta los mensajes al cliente de Banco Andino Demo. Sigue estrictamente la política de comunicación: '
 'tutea al cliente, salúdalo por su primer nombre, máximo 120 palabras, estructura: resultado, motivo comprensible, siguiente paso '
 'y código de referencia si aplica. En rechazos y escalamientos usa la frase "por temas de políticas del banco". '
 'Nunca menciones listas de control, sanciones, umbrales, puntajes ni la cédula completa (solo últimos 4 dígitos). '
 'Termina los rechazos, escalamientos y errores con los canales de ayuda. Usa solo los hechos que te entregan.',
 'gpt-4.1-mini', 0.3)
ON CONFLICT (code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Tools (input_schema = lo que ve el LLM; los datos personales se inyectan desde el estado)
-- ---------------------------------------------------------------------------
INSERT INTO core.tool (code, description, input_schema, is_critical, timeout_ms, max_retries, error_code) VALUES
('verify_identity',
 'Verifica la identidad de una persona contra el Registro Civil del Ecuador usando su número de cédula. '
 'Devuelve si la identidad está verificada y el nivel de confianza (0 a 1) de la verificación biométrica y de datos.',
 '{"type":"object","properties":{},"additionalProperties":false}', true, 3000, 2, 'ONB-IDV-503'),

('check_risk_lists',
 'Consulta listas de control de prevención de lavado de activos: OFAC, Naciones Unidas, UAFE, Personas Expuestas '
 'Políticamente (PEP) y lista interna. Devuelve el nivel de riesgo (low, medium, high) y las coincidencias.',
 '{"type":"object","properties":{},"additionalProperties":false}', true, 3000, 2, 'ONB-RSK-503'),

('prepare_documentation',
 'Prepara la lista oficial de documentos requeridos para abrir un producto bancario, según el producto y el perfil '
 'de riesgo del cliente (riesgo medio, PEP).',
 '{"type":"object","properties":{"product":{"type":"string","description":"Código del producto, ej. cuenta_ahorros"}},"required":["product"],"additionalProperties":false}',
 false, 3000, 1, 'ONB-DOC-503'),

('search_policies',
 'Busca fragmentos relevantes en las políticas internas del banco (KYC, prevención de lavado, requisitos de productos, '
 'escalamiento, comunicación) mediante búsqueda semántica. Úsala para fundamentar requisitos y citar artículos.',
 '{"type":"object","properties":{"query":{"type":"string","description":"Pregunta en lenguaje natural"},"policy_code":{"type":"string","description":"Opcional: filtra por código, ej. POL-PLA-002"}},"required":["query"],"additionalProperties":false}',
 false, 5000, 1, 'ONB-RAG-503')
ON CONFLICT (code) DO NOTHING;

-- Allowlist: el orquestador solo entrega a cada agente estos tools
INSERT INTO core.agent_tool_permission (agent_code, tool_code) VALUES
 ('identity_agent', 'verify_identity'),
 ('risk_agent',     'check_risk_lists'),
 ('policy_agent',   'search_policies'),
 ('policy_agent',   'prepare_documentation'),
 ('response_agent', 'search_policies')
ON CONFLICT DO NOTHING;

COMMIT;
