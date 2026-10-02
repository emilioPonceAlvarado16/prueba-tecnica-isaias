# POL-ESC-004 Escalamiento y Manejo de Excepciones en Onboarding Digital

Banco Andino Demo. Versión 1.0. Vigente desde el 1 de julio de 2026. Responsable: Gerencia de Operaciones. Documento ficticio para una prueba de concepto.

## 1. Principio general

Ante cualquier duda, ambigüedad o falla en la verificación de un solicitante, el canal digital nunca aprueba una solicitud. En su lugar, propone al cliente la vía alternativa más cercana para completar el proceso y registra un caso de escalamiento en la cola que corresponda. El sistema debe explicar al cliente el siguiente paso concreto que debe realizar.

## 2. Escalamiento a agencia

Se escala a la cola de agencias cuando la identidad no puede verificarse en línea: el solicitante no consta en el Registro Civil, consta como fallecido o con cédula anulada, el nivel de confianza de la verificación es menor a 0.80, o el nombre declarado no coincide con el registrado. La solución propuesta al cliente es acercarse a cualquier agencia del banco con su cédula original para una validación biométrica presencial. La atención en agencia es inmediata y no requiere cita previa.

## 3. Escalamiento a cumplimiento

Se escala a la cola de cumplimiento cuando el solicitante presenta riesgo alto según la política POL-PLA-002. El Oficial de Cumplimiento revisa el caso en un plazo máximo de 48 horas. Al cliente solo se le indica, de forma genérica, que por temas de políticas del banco debe acercarse a una agencia, sin revelar el motivo.

## 4. Solicitudes en espera de información del cliente

Cuando el solicitante presenta riesgo medio, la solicitud queda en espera de que el cliente complete en línea la información de debida diligencia reforzada. No se escala a ninguna cola mientras el plazo de siete días esté vigente. Vencido el plazo, la solicitud se cierra y el cliente puede iniciar una nueva.

## 5. Fallas técnicas de servicios críticos

Se escala a la cola de soporte de tecnología cuando un servicio crítico, como el Registro Civil o el servicio de listas de control, no responde después de los reintentos configurados. La solución propuesta al cliente es intentar nuevamente en unos minutos, y se le entrega un código de error para que pueda referirlo en la línea de atención. El equipo de soporte atiende estos casos en un máximo de 4 horas.

## 6. Falla en la creación del acceso digital

Si la solicitud fue aprobada pero falla la creación del usuario de banca digital, la cuenta se mantiene aprobada y se escala a soporte de tecnología, que debe habilitar el acceso en un máximo de 24 horas. Al cliente se le informa que su cuenta fue aprobada y que su acceso digital estará listo en breve.

## 7. Menores de edad

Las solicitudes de menores de edad se rechazan en el canal digital y no se escalan. Se informa al cliente que puede abrir su producto en una agencia acompañado de su representante legal.

## 8. Solicitudes duplicadas

Si el cliente ya tiene una solicitud en curso o aprobada para el mismo producto, no se crea una nueva solicitud. Se le informa que ya existe una solicitud registrada y se le indica cómo consultarla.
