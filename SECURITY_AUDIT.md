# Auditoría de seguridad y arquitectura — DealFlow Gastos

Fecha: 2026-09-22

## Resumen ejecutivo

La revisión encontró fallos críticos de autenticación y gestión de secretos que permitían leer o modificar información financiera mediante suplantación de encabezados HTTP. La remediación implementada centraliza autenticación y RBAC, elimina secretos del código, recalcula la contabilidad en el servidor y endurece la carga de archivos y las integraciones externas.

## Hallazgos y estado

### Crítico

1. **Clave Supabase `service_role` expuesta en `backend/main.py`.** Eliminada del árbol de trabajo. El servicio ahora falla de forma segura si faltan `SUPABASE_URL` o `SUPABASE_KEY`. La clave expuesta debe revocarse/rotarse en Supabase porque permanece recuperable en el historial Git y cualquier clon anterior.
2. **Suplantación de identidad y RBAC mediante `X-User-Email`/query params.** Corregida. `backend/security.py` verifica el access token OAuth con Google, comprueba audiencia, expiración, correo verificado y dominio corporativo. La identidad de cada escritura se deriva del token.
3. **Endpoints sin autenticación.** Corregido para carga, guardado, historial, capital, edición, exportación, estados y eliminación.

### Alto

1. **Lectura horizontal (IDOR) de historial/capital.** Corregida eliminando el email controlado por el cliente.
2. **Edición horizontal de rendiciones.** Corregida: un colaborador solo puede editar registros propios y pendientes; administradores pueden visualizar; aprobadores mantienen las acciones exclusivas.
3. **Estado e IVA controlados por el navegador.** Corregido: nuevas rendiciones siempre nacen pendientes y el IVA se recalcula en servidor solo para Factura/Nota de Crédito.
4. **Clave de Drive pública para cualquiera con enlace.** Corregido para nuevos archivos mediante permiso restringido al dominio configurado en `GOOGLE_DRIVE_READER_DOMAIN`. También se auditaron los 172 comprobantes históricos y se retiraron los 65 permisos públicos detectados, conservando acceso lector para `e-voltage.cl`.
5. **Exportación de Sheets destructiva y sin autorización.** Corregida con rol admin y neutralización de fórmulas para evitar CSV/Sheets injection.

### Medio

1. **Flotantes para reglas contables.** Las validaciones usan ahora `Decimal` y cuantización explícita. Para una garantía completa, las columnas PostgreSQL deberían ser `numeric(14,2)` con constraints SQL.
2. **Archivos temporales compartidos y fuga de `optimized_receipt.jpg`.** Corregido con un directorio temporal único por solicitud y limpieza garantizada.
3. **Confianza en extensión/MIME del cliente.** Añadida validación de firmas JPEG/PNG/PDF, límite de 10 MB y límite razonable de páginas PDF.
4. **Vision API sin timeout/reintentos.** Añadidos timeouts y backoff para fallos transitorios/429 sin registrar fragmentos del token.
5. **CORS demasiado permisivo para previews Vercel.** Eliminada la regex global; métodos y encabezados están limitados.
6. **SMTP sin timeout y recursos sin cierre garantizado.** Corregido con context manager, timeout y no-op si no hay contraseña.

### Mejora recomendada / trabajo externo

1. Aplicar rate limiting en Render/CDN para carga y OCR, y observabilidad estructurada sin PII.
2. Migrar la exportación de Sheets a escritura transaccional o a una pestaña versionada; hoy un fallo entre `clear` y `update` puede dejar la hoja vacía.
3. Restringir el alcance de la cuenta de servicio y separar identidades para Vision y Workspace.

## Variables requeridas

Backend (Render): `SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_CREDENTIALS_JSON` o secret file, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SHEETS_ID`, `GOOGLE_DRIVE_READER_DOMAIN`, `ALLOWED_ORIGINS`, y opcionalmente `GOOGLE_CLIENT_ID`, `SENDER_EMAIL`/`EMAIL_PASSWORD`.

Frontend (Vercel): `VITE_API_URL` y `VITE_GOOGLE_CLIENT_ID`.

`GOOGLE_CLIENT_ID` debe coincidir exactamente con `VITE_GOOGLE_CLIENT_ID`.

## Estado de implementación en producción (2026-09-22)

1. Completado: Render usa una secret key moderna de Supabase y las claves legacy `anon`/`service_role` quedaron deshabilitadas.
2. Completado: commit de seguridad desplegado en Render y verificado `live`; las rutas privadas devuelven `401` sin autenticación.
3. Completado: acceso Data API de `anon`/`authenticated` revocado sobre `transacciones` y `capital_entregado`; RLS permanece activo con denegación explícita para `transacciones`.
4. Completado: constraints para montos no negativos, estados válidos y balance de fondos mixtos, más índice por usuario/fecha.
5. Pendiente: corregir tres facturas históricas sin RUT proveedor y luego validar `transacciones_invoice_vendor_rut`.
6. Completado: 172 comprobantes históricos de Drive verificados; se revocaron 65 permisos `anyone`, sin fallos, y todos conservan acceso para el dominio corporativo.
7. Recomendado: reescribir el historial Git para retirar el secreto antiguo, sin considerar esto sustituto de la rotación ya realizada.

## Verificación incluida

`backend/test_accounting.py` cubre IVA, fondos mixtos y montos negativos. La verificación final también debe incluir build del frontend, compilación Python, pruebas unitarias y smoke test autenticado contra un entorno de staging.
