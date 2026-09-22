# DealFlow Gastos OCR

## Instrucción operativa para agentes: respaldo semanal

Esta instrucción aplica a Codex, Antigravity, Cursor y cualquier otro agente que opere este repositorio.

Cada lunes a las 12:00, hora de Santiago (`America/Santiago`), el **primer agente disponible** debe realizar el respaldo semanal de DealFlow en Supabase. Antes de iniciar, debe revisar Google Drive para comprobar si ya existe una copia válida de la semana calendario en curso. Si existe y fue verificada, no debe crear un duplicado.

Si el respaldo no existe, el agente debe:

1. Confirmar que el proyecto objetivo es `msfvsjrubvzhkxzqjlhw`.
2. Usar únicamente operaciones de lectura; nunca ejecutar `INSERT`, `UPDATE`, `DELETE`, DDL ni restauraciones.
3. Exportar como mínimo `public.transacciones` y `public.capital_entregado`, incluyendo esquema, conteos y metadatos de ejecución en un archivo fechado.
4. Guardar el archivo en la carpeta dedicada de Google Drive, sin acceso público y restringido a `e-voltage.cl`.
5. Verificar que el archivo exista, no esté vacío y que sus conteos coincidan con los datos consultados.

No reportar contenido de registros, RUT, correos, claves ni tokens. Informar solo si hay error, falta de acceso o discrepancias en la verificación.

La automatización de Codex ya ejecuta este protocolo semanalmente; estas instrucciones permiten que otro agente lo complete antes sin generar copias duplicadas.
