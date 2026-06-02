# 🔍 Nuevas Sugerencias de Filtros SQL

## Resumen de Cambios

Se agregó la funcionalidad de **sugerencias de filtros SQL** a los reportes sin modificar la funcionalidad existente ni los requerimientos. Esta característica proporciona queries SQL específicas que pueden usarse para limpiar y validar datos según los problemas detectados.

---

## 📁 Archivos Modificados

### 1. ✨ **Nuevo Archivo:** `modules/sql_filter_suggestions.py`

Módulo que genera sugerencias de filtros SQL basadas en problemas detectados.

**Clase Principal:** `SQLFilterSuggestions`

**Métodos de Generación:**
- **`_generate_null_filters()`** - Filtros para eliminar o manejar nulos
  - `WHERE columna IS NOT NULL`
  - `WHERE columna IS NOT NULL AND TRIM(columna) != ''`

- **`_generate_duplicates_filters()`** - Opciones para eliminar duplicados
  - `SELECT DISTINCT * FROM tabla`
  - `ROW_NUMBER()` para mantener primer duplicado

- **`_generate_type_filters()`** - Estandarizar tipos de datos
  - `CAST(columna AS VARCHAR/NUMERIC)`

- **`_generate_validation_filters()`** - Validaciones de email y teléfono
  - Filtros REGEX para emails válidos
  - Validaciones de formato de teléfono

- **`_generate_cleanup_filters()`** - Limpieza de espacios y caracteres especiales
  - `TRIM()` para espacios en blanco
  - Remoción de caracteres especiales

- **`_generate_quality_filters()`** - Calidad de datos general
  - Filas completas (sin nulos)
  - Exclusión de columnas problemáticas

---

### 2. 📊 **Modificado:** `modules/report_generator.py`

Se agregó generación automática de sugerencias SQL y su presentación en reportes.

**Cambios:**
- ✅ Importa `SQLFilterSuggestions`
- ✅ En `__init__()`: Genera automáticamente sugerencias SQL
- ✅ `_write_sql_filters_sheet()` - Nueva hoja Excel "FILTROS_SQL"
- ✅ `_build_sql_filters_section()` - Nueva sección HTML con sugerencias
- ✅ Integración en `generate_excel_report()` (hoja #10)
- ✅ Integración en HTML report

**Nuevas Hojas Excel:**
- Hoja #10: **FILTROS_SQL** - Contiene todas las sugerencias con:
  - Categoría del filtro
  - Nivel de severidad
  - Columna afectada
  - Problema detectado
  - Filtro SQL propuesto
  - Descripción e impacto

**Nueva Sección HTML:**
- Sección: **🔍 Sugerencias de Filtros SQL**
- Tabla con filtros más importantes
- Código SQL formateado
- Descripción e impacto de cada filtro

---

### 3. 💬 **Modificado:** `app.py`

Se agregó visualización interactiva de sugerencias SQL en Streamlit.

**Cambios:**
- ✅ Importa `SQLFilterSuggestions`
- ✅ Nueva subsección en Tab 4 (Recomendaciones)

**Nueva Sección Streamlit:**
- **Ubicación:** Pestaña "💡 Recomendaciones" (Tab 4)
- **Nombre:** "🔍 Sugerencias de Filtros SQL"
- **Características:**
  - Filtros agrupados por categoría
  - Expanders interactivos con:
    - Icono de severidad (🔴 CRÍTICO / 🟠 GRAVE / 🟡 AVISO)
    - Código SQL con syntax highlighting
    - Descripción del problema
    - Impacto estimado
    - Alternativas (simple/avanzada)
    - Queries de limpieza cuando aplique

---

## 📈 Ubicación en Reportes

### Excel (`reporte_datos_YYYYMMDD_HHMMSS.xlsx`)
- **Nueva Hoja #10:** `FILTROS_SQL`
- Ubicación: Después de "NORMALIZACIÓN", antes de "MUESTRAS_PROBLEMATICAS"
- Contiene tabla con todas las sugerencias

### HTML (`reporte_datos_YYYYMMDD_HHMMSS.html`)
- **Nueva Sección:** "🔍 Sugerencias de Filtros SQL"
- Ubicación: Después de "Recomendaciones Principales"
- Con nota aclaratoria sobre ajustes necesarios

### Streamlit Web
- **Nueva Subsección:** En Tab 4 "Recomendaciones Preliminares"
- Subsección: "🔍 Sugerencias de Filtros SQL"
- Con expanders interactivos y syntax highlighting

---

## 🎯 Tipos de Sugerencias Generadas

### 1. **NULL_ELIMINATION** (🔴 CRÍTICO / 🟠 GRAVE / 🟡 AVISO)
```sql
WHERE columna IS NOT NULL
WHERE columna IS NOT NULL AND TRIM(columna) != ''
```
**Impacto:** Elimina filas con nulos en columnas críticas

### 2. **REMOVE_DUPLICATES** (🟠 GRAVE)
```sql
SELECT DISTINCT * FROM tabla
```
**Impacto:** Reduce duplicados, mantiene datos únicos

### 3. **TYPE_STANDARDIZATION** (🟠 GRAVE)
```sql
CAST(columna AS VARCHAR)
CAST(columna AS NUMERIC)
```
**Impacto:** Convierte tipos mixtos a un tipo único

### 4. **EMAIL_VALIDATION** (🟠 GRAVE / 🟡 AVISO)
```sql
WHERE columna LIKE '%@%' AND columna LIKE '%.%'
WHERE columna ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
```
**Impacto:** Filtra emails válidos

### 5. **PHONE_VALIDATION** (🟠 GRAVE / 🟡 AVISO)
```sql
WHERE LENGTH(REGEXP_REPLACE(columna, '[^0-9]', '')) >= 7
```
**Impacto:** Valida formato de teléfono

### 6. **WHITESPACE_CLEANUP** (🟡 AVISO)
```sql
WHERE TRIM(columna) IS NOT NULL AND TRIM(columna) != ''
UPDATE tabla SET columna = TRIM(columna)
```
**Impacto:** Elimina espacios al inicio/final

### 7. **SPECIAL_CHARS_CLEANUP** (🟡 AVISO)
```sql
WHERE columna NOT LIKE '%[<>{}"|\\^`~]%'
UPDATE tabla SET columna = REGEXP_REPLACE(columna, '[<>{}"|\\^`~]', '')
```
**Impacto:** Remueve caracteres especiales

### 8. **COMPLETE_ROWS** (🟠 GRAVE / 🟡 AVISO)
```sql
WHERE col1 IS NOT NULL AND col2 IS NOT NULL AND ...
```
**Impacto:** Mantiene solo filas sin nulos

---

## ✨ Características Principales

✅ **Sin cambios en funcionalidad existente** - Solo se agregan nuevas sugerencias
✅ **Sin nuevas dependencias** - Usa solo módulos ya importados
✅ **Automático** - Se generan al crear reportes
✅ **Contextual** - Basado en problemas reales detectados
✅ **Múltiples opciones** - Desde simple hasta avanzado para cada problema
✅ **En 3 formatos** - Excel, HTML y Streamlit
✅ **Syntax highlighting** - En Streamlit y HTML
✅ **Explicativo** - Incluye descripción e impacto
✅ **Flexible** - Adaptables a cada base de datos

---

## 🚀 Cómo Usar

### En Streamlit
1. Carga un archivo CSV
2. Ejecuta análisis en las pestañas anteriores
3. Ve a Tab 4: "💡 Recomendaciones"
4. Desplázate hasta "🔍 Sugerencias de Filtros SQL"
5. Abre los expanders para ver detalles de cada filtro
6. Copia el SQL que necesites para tu base de datos

### En Reportes Descargados
1. **Excel:** Abre la hoja "FILTROS_SQL" para ver todas las sugerencias
2. **HTML:** Busca la sección "🔍 Sugerencias de Filtros SQL"
3. Copia los filtros que necesites ajustándolos a tu contexto

---

## ⚠️ Notas Importantes

- Los filtros SQL son **sugerencias** basadas en heurística
- **Requieren validación** antes de usarlos en producción
- Ajústalos según **tu base de datos específica**
- Los nombres de tablas y funciones SQL pueden variar (PostgreSQL, MySQL, SQL Server, etc.)
- Valida el impacto en tus datos antes de ejecutar

---

## 📝 Ejemplo de Uso

Si tienes una columna `email` con datos problemáticos:

**Problema Detectado:**
```
- 15% de emails inválidos
- 5% de espacios en blanco
```

**Sugerencias Generadas:**
```sql
-- 1. Eliminar espacios en blanco
UPDATE tabla SET email = TRIM(email) WHERE email IS NOT NULL;

-- 2. Filtrar emails válidos
SELECT * FROM tabla 
WHERE email LIKE '%@%' 
  AND email LIKE '%.%' 
  AND POSITION('@' IN email) > 1;

-- 3. O usar REGEX (PostgreSQL)
SELECT * FROM tabla 
WHERE email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z|a-z]{2,}$';
```

---

**Versión:** 1.0.0  
**Fecha:** 2026-06-01  
**Estado:** ✅ Implementado y Testeado
