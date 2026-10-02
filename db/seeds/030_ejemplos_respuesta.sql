-- Ejemplos de respuesta ideal (few-shot del response_agent; base para un futuro fine-tuning).
BEGIN;
TRUNCATE core.response_example RESTART IDENTITY;

INSERT INTO core.response_example (reason_code, context, ideal_message) VALUES
('ONB-OK-000',
 '{"first_name":"Andrea","product":"Cuenta de Ahorros","documents":["Cédula de ciudadanía","Planilla de servicio básico"],"username":"****5678"}',
 '¡Hola Andrea! Tu Cuenta de Ahorros fue aprobada. Ya creamos tu usuario de banca digital (usuario: tu número de cédula). Para completar tu expediente, carga en la app dentro de los próximos 15 días: Cédula de ciudadanía y Planilla de servicio básico. ¡Bienvenida a Banco Andino Demo!'),

('ONB-IDV-002',
 '{"first_name":"Luis","product":"Cuenta de Ahorros","last4":"4321"}',
 'Hola Luis, por temas de políticas del banco no podemos completar la apertura de tu Cuenta de Ahorros en línea. Para continuar, acércate a cualquiera de nuestras agencias con tu cédula original (terminada en 4321) y te ayudaremos con una validación presencial, sin necesidad de cita. Código de referencia: ONB-IDV-002. Si tienes dudas, llámanos al 1800-ANDINO (1800-263466), disponible 24 horas.'),

('ONB-IDV-001',
 '{"first_name":"Carmen","product":"Cuenta Corriente","last4":"9876"}',
 'Hola Carmen, por temas de políticas del banco no pudimos validar tu identidad en línea, por lo que no podemos continuar con tu Cuenta Corriente por este medio. Acércate a una de nuestras agencias con tu cédula original y te atenderemos de inmediato. Código de referencia: ONB-IDV-001. Línea de atención: 1800-ANDINO (1800-263466), 24 horas.'),

('ONB-RSK-002',
 '{"first_name":"Ramiro","product":"Cuenta Corriente","questions":["actividad económica","origen de fondos","ingresos mensuales"]}',
 'Hola Ramiro, ya casi terminamos. Por temas de políticas del banco necesitamos que nos compartas algunos datos adicionales: tu actividad económica, el origen de los fondos que usarás en tu Cuenta Corriente y tus ingresos mensuales estimados. Completa el formulario y continuaremos con tu apertura. Tienes 7 días para hacerlo.'),

('ONB-IDV-004',
 '{"first_name":"Sebastián","product":"Cuenta de Ahorros"}',
 'Hola Sebastián, por temas de políticas del banco la apertura de productos en línea está disponible solo para mayores de 18 años. Puedes abrir tu Cuenta de Ahorros en cualquiera de nuestras agencias, acompañado de tu representante legal. Código de referencia: ONB-IDV-004. Línea de atención: 1800-ANDINO (1800-263466), 24 horas.'),

('ONB-IDV-503',
 '{"first_name":"Mónica","product":"Cuenta de Ahorros"}',
 'Hola Mónica, en este momento nuestro servicio de verificación de identidad no está disponible y no pudimos completar tu solicitud. Por favor, intenta nuevamente en unos minutos. Si el problema continúa, comunícate al 1800-ANDINO (1800-263466) e indica el código ONB-IDV-503.');

COMMIT;
