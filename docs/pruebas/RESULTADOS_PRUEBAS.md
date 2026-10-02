# Resultados de los usuarios de prueba

Ejecutado el 2026-10-02 12:01 contra `http://localhost:8010` con `backend/scripts/run_scenarios.py`.

| # | Nombre | Cédula | Producto | Esperado | Obtenido | OK | Escenario |
|---|---|---|---|---|---|---|---|
| 1 | Juan Perez | 1712345675 | cuenta_ahorros | 200 APPROVED ONB-OK-000 | 200 APPROVED ONB-OK-000 | ✅ | Caso feliz |
| 2 | Juan Perez | 1712345678 | cuenta_ahorros | 200 REJECTED ONB-DOC-001 | 200 REJECTED ONB-DOC-001 | ✅ | Cédula del enunciado: dígito verificador inválido |
| 3 | Maria Fernanda Loor | 0918765439 | cuenta_ahorros | 200 ESCALATED ONB-IDV-002 | 200 ESCALATED ONB-IDV-002 | ✅ | Confianza 0.72 < 0.80 |
| 4 | Luis Ortega | 0104567896 | cuenta_ahorros | 200 ESCALATED ONB-IDV-001 | 200 ESCALATED ONB-IDV-001 | ✅ | No consta en Registro Civil |
| 5 | Carlos Andrade | 1709988776 | cuenta_ahorros | 200 ESCALATED ONB-RSK-001 | 200 ESCALATED ONB-RSK-001 | ✅ | Riesgo alto (UAFE + OFAC) |
| 6 | Patricia Salazar | 1805566773 | cuenta_corriente | 200 AWAITING_CUSTOMER ONB-RSK-002 | 200 AWAITING_CUSTOMER ONB-RSK-002 | ✅ | PEP: riesgo medio, pide información |
| 7 | Mateo Cedeño | 1302244668 | cuenta_ahorros | 200 REJECTED ONB-IDV-004 | 200 REJECTED ONB-IDV-004 | ✅ | Menor de edad (16) |
| 8 | Rosa Vera | 1107788992 | cuenta_ahorros | 200 ESCALATED ONB-IDV-001 | 200 ESCALATED ONB-IDV-001 | ✅ | FALLECIDO en Registro Civil |
| 9 | Diego Paredes | 0603344557 | cuenta_ahorros | 503 ERROR ONB-IDV-503 | 503 ERROR ONB-IDV-503 | ✅ | Registro Civil timeout |
| 10 | Sofia Mena | 1711122232 | cuenta_ahorros | 503 ERROR ONB-RSK-503 | 503 ERROR ONB-RSK-503 | ✅ | Listas de riesgo HTTP 500 |
| 11 | Pedro Gomez | 0922233341 | cuenta_ahorros | 200 ESCALATED ONB-IDV-003 | 200 ESCALATED ONB-IDV-003 | ✅ | Nombre no coincide con la cédula |
| 12 | Juan Perez | 1712345675 | cuenta_ahorros | 409 - ONB-DUP-409 | 409 - ONB-DUP-409 | ✅ | Duplicado (después del #1) |
| 13 | Juan Perez | 1712345675 | tarjeta_oro | 400 - ONB-VAL-400 | 400 - ONB-VAL-400 | ✅ | Producto inválido (marshmallow) |
| 14 | Valeria Rios | 1717171712 | cuenta_ahorros | 200 APPROVED ONB-OK-000 | 200 APPROVED ONB-OK-000 | ✅ | Documentación vía RAG (tool caído) |
| 15 | Camila Herrera | 1724680242 | cuenta_ahorros | 200 APPROVED_PENDING_PROVISIONING ONB-PRV-503 | 200 APPROVED_PENDING_PROVISIONING ONB-PRV-503 | ✅ | Falla creación de usuario |

## Mensaje al usuario final por escenario

**1. Juan Perez (1712345675) → ONB-OK-000**

> ¡Hola Juan! Tu Cuenta de Ahorros ha sido aprobada exitosamente y ya tienes tu usuario de banca digital (usuario: tu número de cédula). Por favor, carga en la app, dentro de los próximos 15 días, estos documentos: Cédula de ciudadanía, Planilla de servicio básico, Formulario Conozca a su Cliente y Aceptación de términos y condiciones. ¡Bienvenido a Banco Andino Demo!

**2. Juan Perez (1712345678) → ONB-DOC-001**

> Hola Juan, por temas de políticas del banco no podemos continuar con la apertura de tu Cuenta de Ahorros porque el número de cédula ingresado no es válido. Por favor, verifica el número e intenta nuevamente. Código de referencia: ONB-DOC-001. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias.

**3. Maria Fernanda Loor (0918765439) → ONB-IDV-002**

> Hola Maria, por temas de políticas del banco no podemos completar la apertura de tu Cuenta de Ahorros en línea. Para continuar, acércate a cualquiera de nuestras agencias con tu cédula original (terminada en 5439) para realizar una validación biométrica presencial, sin necesidad de cita. Código de referencia: ONB-IDV-002. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias.

**4. Luis Ortega (0104567896) → ONB-IDV-001**

> Hola Luis, por temas de políticas del banco no pudimos validar tu identidad en línea, por lo que no podemos continuar con tu Cuenta de Ahorros por este medio. Acércate a una de nuestras agencias con tu cédula original (terminada en 7896) y te atenderemos de inmediato. Código de referencia: ONB-IDV-001. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias.

**5. Carlos Andrade (1709988776) → ONB-RSK-001**

> Hola Carlos, por temas de políticas del banco no es posible continuar con tu solicitud de Cuenta de Ahorros en línea. Te invitamos a acercarte a una de nuestras agencias para recibir atención personalizada. Código de referencia: ONB-REF-100. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias.

**6. Patricia Salazar (1805566773) → ONB-RSK-002** — tras /continue: 200 APPROVED ONB-OK-001

> ¡Hola Patricia! Tu Cuenta Corriente fue aprobada y ya creamos tu usuario de banca digital (usuario: tu número de cédula). Por favor, carga en la app dentro de los próximos 15 días estos documentos: Cédula de ciudadanía, Planilla de servicio básico, Formulario Conozca a su Cliente, Aceptación de términos y condiciones, Certificado de ingresos, Registro de firma electrónica, Formulario de Persona Expuesta Políticamente, Declaración de origen lícito de fondos y Referencia bancaria o comercial. ¡Gracias por confiar en Banco Andino Demo!

**7. Mateo Cedeño (1302244668) → ONB-IDV-004**

> Hola Mateo, por temas de políticas del banco la apertura de productos en línea está disponible solo para mayores de 18 años. Para abrir tu Cuenta de Ahorros, debes acudir a una de nuestras agencias acompañado de tu representante legal. Código de referencia: ONB-IDV-004. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias.

**8. Rosa Vera (1107788992) → ONB-IDV-001**

> Hola Rosa, por temas de políticas del banco no pudimos validar tu identidad en línea, por lo que no podemos continuar con tu Cuenta de Ahorros por este medio. Acércate a una de nuestras agencias con tu cédula original (terminada en 8992) y te atenderemos de inmediato. Código de referencia: ONB-IDV-001. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita nuestras agencias.

**9. Diego Paredes (0603344557) → ONB-IDV-503**

> Hola Diego, actualmente nuestro servicio de verificación de identidad presenta una falla técnica y no pudimos completar tu solicitud para la Cuenta de Ahorros. Por favor, intenta nuevamente en unos minutos. Si el inconveniente persiste, comunícate al 1800-ANDINO (1800-263466) y menciona el código ONB-IDV-503 para que te podamos asistir.

**10. Sofia Mena (1711122232) → ONB-RSK-503**

> Hola Sofia, no pudimos completar la apertura de tu Cuenta de Ahorros porque un servicio de validación está temporalmente fuera de servicio. Por favor, intenta nuevamente en unos minutos. Si el inconveniente persiste, comunícate al 1800-ANDINO (1800-263466) y menciona el código ONB-RSK-503.

**11. Pedro Gomez (0922233341) → ONB-IDV-003**

> Hola Pedro, por temas de políticas del banco no podemos continuar con la apertura de tu Cuenta de Ahorros en línea porque no pudimos confirmar tus datos de identidad. Por favor, acércate a una de nuestras agencias con tu cédula original (terminada en 3341) para realizar la validación presencial. Código de referencia: ONB-IDV-003. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas, o visita cualquiera de nuestras agencias.

**12. Juan Perez (1712345675) → ONB-DUP-409**

> Ya tienes una solicitud registrada o aprobada para este producto. Puedes consultar su estado con el enlace de tu solicitud.

**13. Juan Perez (1712345675) → ONB-VAL-400**

> La solicitud tiene datos inválidos.

**14. Valeria Rios (1717171712) → ONB-OK-000** — fuente documentos: rag_fallback

> ¡Hola Valeria! Tu Cuenta de Ahorros fue aprobada y ya creamos tu usuario de banca digital (usuario: tu número de cédula). Por favor, carga en la app, dentro de los próximos 15 días, estos documentos: Cédula de ciudadanía, Planilla de servicio básico con antigüedad máxima de tres meses, Aceptación de términos y condiciones y Formulario conozca a su cliente. ¡Bienvenida a Banco Andino Demo!

**15. Camila Herrera (1724680242) → ONB-PRV-503**

> ¡Hola Camila! Tu Cuenta de Ahorros fue aprobada y tu acceso a la banca digital estará habilitado en las próximas 24 horas; te avisaremos cuando puedas ingresar. Código de referencia: ONB-PRV-503. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible las 24 horas, o visita nuestras agencias.
