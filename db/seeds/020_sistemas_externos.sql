-- Datos dummy de sistemas externos (Registro Civil, listas de riesgo) y fallas simuladas.
-- Todas las cédulas cumplen el algoritmo módulo 10. Personas y casos FICTICIOS.
BEGIN;

INSERT INTO ext.registro_civil (document_id, nombres, apellidos, fecha_nacimiento, lugar_nacimiento, estado_civil, condicion, calidad_dato) VALUES
 -- Usuarios de prueba (docs/pruebas/USUARIOS_PRUEBA.md)
 ('1712345675', 'Juan Andrés',      'Pérez Molina',      '1990-05-14', 'Quito',      'SOLTERO',    'CIUDADANO', 0.95),
 ('0918765439', 'María Fernanda',   'Loor Zambrano',     '1988-11-02', 'Guayaquil',  'CASADO',     'CIUDADANO', 0.72),
 ('1709988776', 'Carlos Alberto',   'Andrade Ruiz',      '1975-03-21', 'Quito',      'DIVORCIADO', 'CIUDADANO', 0.93),
 ('1805566773', 'Patricia Elena',   'Salazar Núñez',     '1970-07-09', 'Ambato',     'CASADO',     'CIUDADANO', 0.91),
 ('1302244668', 'Mateo José',       'Cedeño Intriago',   '2010-01-20', 'Portoviejo', 'SOLTERO',    'CIUDADANO', 0.94),
 ('1107788992', 'Rosa Amelia',      'Vera Jaramillo',    '1950-02-11', 'Loja',       'VIUDO',      'FALLECIDO', 0.90),
 ('0603344557', 'Diego Fernando',   'Paredes Vallejo',   '1985-09-30', 'Riobamba',   'CASADO',     'CIUDADANO', 0.94),
 ('1711122232', 'Sofía Isabel',     'Mena Cárdenas',     '1993-12-05', 'Quito',      'SOLTERO',    'CIUDADANO', 0.92),
 ('0922233341', 'Ana Lucía',        'Villacís Ruiz',     '1991-04-17', 'Guayaquil',  'SOLTERO',    'CIUDADANO', 0.96),
 ('1717171712', 'Valeria Cristina', 'Ríos Benítez',      '1996-08-23', 'Quito',      'SOLTERO',    'CIUDADANO', 0.97),
 -- Población de relleno
 ('1004455661', 'Gabriela',         'Montenegro Pozo',   '1987-06-12', 'Ibarra',     'CASADO',     'CIUDADANO', 0.93),
 ('0701122335', 'Jorge Luis',       'Aguilar Romero',    '1979-10-03', 'Machala',    'CASADO',     'CIUDADANO', 0.88),
 ('1209988771', 'Daniela',          'Franco Mora',       '1999-01-29', 'Babahoyo',   'SOLTERO',    'CIUDADANO', 0.91),
 ('2304455666', 'Kevin Alexander',  'Chávez Toapanta',   '2001-03-15', 'Santo Domingo','SOLTERO',  'CIUDADANO', 0.85),
 ('1715556666', 'Lorena',           'Espinosa Guerrero', '1983-07-07', 'Quito',      'DIVORCIADO', 'CIUDADANO', 0.90),
 ('0907778880', 'Ricardo',          'Bustamante León',   '1968-12-24', 'Guayaquil',  'CASADO',     'CEDULA_ANULADA', 0.80),
 ('0502223332', 'Paola Andrea',     'Tapia Caiza',       '1994-05-19', 'Latacunga',  'SOLTERO',    'CIUDADANO', 0.89),
 ('2103334443', 'Byron',            'Narváez Ortiz',     '1990-11-11', 'Nueva Loja', 'UNION_HECHO','CIUDADANO', 0.86),
 ('1724680242', 'Camila',           'Herrera Salgado',   '2003-02-02', 'Quito',      'SOLTERO',    'CIUDADANO', 0.95),
 ('0913579132', 'Fernando',         'Icaza Moreira',     '1972-08-08', 'Guayaquil',  'CASADO',     'CIUDADANO', 0.92),
 ('1402468027', 'Martha',           'Vásquez Peña',      '1965-04-04', 'Macas',      'VIUDO',      'CIUDADANO', 0.87)
ON CONFLICT (document_id) DO NOTHING;
-- 0104567896 (Luis Ortega) NO existe a propósito: caso "no consta en Registro Civil".

INSERT INTO ext.risk_list (code, name, source, severity) VALUES
 ('OFAC_SDN', 'Specially Designated Nationals (OFAC)',        'U.S. Treasury (simulado)',             'high'),
 ('ONU_CSNU', 'Lista consolidada Consejo de Seguridad ONU',   'Naciones Unidas (simulado)',           'high'),
 ('UAFE',     'Personas reportadas UAFE',                     'UAFE Ecuador (simulado)',              'high'),
 ('INTERNA',  'Lista interna de clientes no deseados',        'Banco Andino Demo',                    'high'),
 ('PEP_EC',   'Personas Expuestas Políticamente Ecuador',     'Base PEP (simulado)',                  'medium')
ON CONFLICT (code) DO NOTHING;

INSERT INTO ext.risk_list_entry (list_code, document_id, full_name, aliases, reason) VALUES
 ('UAFE',     '1709988776', 'Carlos Alberto Andrade Ruiz', '{"Carlos Andrade R."}', 'Reporte de operación inusual (ficticio)'),
 ('OFAC_SDN', NULL,         'Carlos Alberto Andrade Ruiz', '{}',                    'Coincidencia por nombre (ficticio)'),
 ('PEP_EC',   '1805566773', 'Patricia Elena Salazar Núñez','{}',                    'Ex directora de empresa pública 2023-2025 (ficticio)'),
 ('PEP_EC',   '1402468027', 'Martha Vásquez Peña',         '{}',                    'Autoridad seccional (ficticio)'),
 ('OFAC_SDN', NULL,         'Viktor Draganov Petrenko',    '{"V. Petrenko"}',       'Entrada internacional ficticia'),
 ('ONU_CSNU', NULL,         'Abdel Karim Al-Fayoumi',      '{}',                    'Entrada internacional ficticia'),
 ('INTERNA',  '0907778880', 'Ricardo Bustamante León',     '{}',                    'Fraude documental previo (ficticio)')
ON CONFLICT DO NOTHING;

-- Fallas deterministas para probar tools caídos
INSERT INTO ext.service_fault (tool_code, document_id, fault_type) VALUES
 ('verify_identity',       '0603344557', 'timeout'),
 ('check_risk_lists',      '1711122232', 'error_500'),
 ('prepare_documentation', '1717171712', 'error_500')
ON CONFLICT DO NOTHING;

COMMIT;

-- Falla en la creación del usuario de banca digital (Lambda/Cognito) tras aprobación
INSERT INTO ext.service_fault (tool_code, document_id, fault_type) VALUES
 ('provision_user', '1724680242', 'error_500')
ON CONFLICT DO NOTHING;
