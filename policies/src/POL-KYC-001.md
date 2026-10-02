# POL-KYC-001 Política Conozca a su Cliente: Identificación y Verificación de Identidad

Banco Andino Demo. Versión 1.0. Vigente desde el 1 de julio de 2026. Responsable: Gerencia de Cumplimiento y Gerencia de Canales Digitales. Documento ficticio elaborado para una prueba de concepto.

Artículo 1. Objeto y alcance

La presente política establece los requisitos mínimos para identificar y verificar la identidad de las personas naturales que solicitan la apertura de un producto a través de los canales digitales del banco. Aplica a todo proceso de vinculación digital, ya sea por la banca web o por la aplicación móvil, y es de cumplimiento obligatorio para los sistemas automatizados, incluidos los agentes de inteligencia artificial que participan en el proceso de onboarding.

Quedan fuera del canal digital las personas extranjeras que se identifiquen con pasaporte o con cédula de extranjería, las personas jurídicas y las solicitudes realizadas por apoderados. Estos casos deben atenderse en una agencia física del banco.

Artículo 2. Documento de identidad válido

El único documento aceptado para la vinculación digital es la cédula de ciudadanía ecuatoriana de diez dígitos. Antes de consultar cualquier servicio externo, el sistema debe validar la estructura del número de cédula con las siguientes reglas.

Los dos primeros dígitos corresponden al código de provincia y deben estar entre 01 y 24, o ser 30 para ecuatorianos registrados en el exterior. El tercer dígito debe ser menor que 6, ya que identifica a personas naturales. El décimo dígito es el dígito verificador y se calcula con el algoritmo módulo 10: se multiplican los nueve primeros dígitos por los coeficientes 2, 1, 2, 1, 2, 1, 2, 1, 2; a cada producto mayor que 9 se le resta 9; se suman los resultados y el dígito verificador es igual a diez menos el residuo de la suma para diez, o cero si el residuo es cero.

Si el número de cédula no cumple estas reglas, la solicitud se rechaza de inmediato sin consultar servicios externos, y se informa al cliente que el número ingresado no es válido para que lo verifique e intente nuevamente.

Artículo 3. Verificación con el Registro Civil

Toda solicitud con cédula estructuralmente válida debe verificarse contra el servicio del Registro Civil. La persona debe constar en el registro con la condición de ciudadano. Si la persona no consta en el registro, si consta como fallecida, o si la cédula está anulada, la identidad se considera no verificada y la vinculación digital no puede continuar. En estos casos el cliente debe acercarse a una agencia del banco con su cédula original para una validación presencial.

La verificación de identidad es un servicio crítico. Si el servicio del Registro Civil no responde después de los reintentos configurados, la solicitud no puede aprobarse y se informa al cliente que el servicio de verificación no está disponible temporalmente, con un código de referencia, invitándolo a intentar nuevamente en unos minutos.

Artículo 4. Nivel de confianza de la verificación

El servicio de verificación devuelve un nivel de confianza entre 0 y 1, que refleja la calidad de la coincidencia biométrica y de los datos registrados. Para continuar con la vinculación digital, el nivel de confianza debe ser igual o mayor a 0.80.

Cuando el nivel de confianza es menor a 0.80, la vinculación digital se suspende y requiere escalamiento. Por temas de políticas del banco, el cliente debe acercarse a una agencia con su cédula original para completar una validación biométrica presencial. El sistema no debe aprobar ni rechazar definitivamente la solicitud: se registra como escalada a la cola de agencias.

Artículo 5. Coincidencia de nombres

El nombre declarado por el solicitante debe coincidir con el nombre registrado en el Registro Civil. La comparación tolera diferencias de tildes, mayúsculas y el uso parcial de nombres y apellidos, por ejemplo declarar un solo nombre y un solo apellido. Una discrepancia significativa entre el nombre declarado y el registrado se considera una ambigüedad en la identidad: la vinculación digital se suspende y el cliente debe acercarse a una agencia.

Artículo 6. Edad mínima

Para abrir productos por canales digitales, el solicitante debe tener al menos 18 años cumplidos a la fecha de la solicitud, calculados con la fecha de nacimiento registrada en el Registro Civil. Los menores de edad solo pueden abrir productos en una agencia, acompañados de su representante legal y con los documentos que acrediten la representación.

Artículo 7. Conservación de la evidencia

El banco conserva la evidencia de cada verificación de identidad, incluido el resultado, la fecha, el nivel de confianza y el sistema que la realizó, durante diez años contados desde la finalización de la relación comercial. Los registros técnicos deben almacenar la cédula enmascarada, mostrando únicamente los primeros seis dígitos.
