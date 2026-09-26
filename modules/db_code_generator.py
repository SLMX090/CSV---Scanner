"""
Módulo para generar código SQL completo de limpieza, validación y carga segura
de datos CSV hacia una base de datos.

Versión v3.x
------------

Características principales:
- Generación SQL mediante Jinja2.
- Soporte multidialecto: PostgreSQL, MySQL, Snowflake y BigQuery.
- Inferencia inteligente de tipos SQL.
- Tabla limpia con ID técnico autogenerado.
- Tabla de cuarentena con ID autogenerado.
- Inserción masiva de errores en cuarentena mediante UNION ALL.
- Empaquetado de fila completa en JSON dentro de la CTE.
- Compatibilidad hacia atrás con métodos públicos existentes.
"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd
from jinja2 import BaseLoader, Environment

from config import DEFAULT_SQL_DIALECT, SQL_DIALECTS
from utils.helpers import StringHelper


class DatabaseCodeGenerator:
    """
    Genera scripts SQL y Python para limpieza, validación y carga de datos.

    La clase mantiene compatibilidad con versiones anteriores mediante los
    métodos públicos:

    - generate_complete_script()
    - generate_python_cleanup_code()
    - generate_config_yaml()
    - export_scripts()

    El SQL generado utiliza una plantilla Jinja2 interna y adapta tipos,
    castings, parseo de fechas, JSON e identificadores técnicos según el
    dialecto seleccionado.
    """

    SUPPORTED_DIALECTS = ("PostgreSQL", "MySQL", "Snowflake", "BigQuery")

    DATE_FORMAT_CANDIDATES = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%b-%y",
        "%d-%b-%Y",
    )

    PYTHON_TO_SQL_DATE_FORMATS = {
        "PostgreSQL": {
            "%Y-%m-%d": "YYYY-MM-DD",
            "%m/%d/%Y": "MM/DD/YYYY",
            "%d/%m/%Y": "DD/MM/YYYY",
            "%m-%d-%Y": "MM-DD-YYYY",
            "%d-%m-%Y": "DD-MM-YYYY",
            "%Y/%m/%d": "YYYY/MM/DD",
            "%Y-%m-%d %H:%M:%S": "YYYY-MM-DD HH24:MI:SS",
            "%m/%d/%Y %H:%M:%S": "MM/DD/YYYY HH24:MI:SS",
            "%d/%m/%Y %H:%M:%S": "DD/MM/YYYY HH24:MI:SS",
        },
        "MySQL": {
            "%Y-%m-%d": "%Y-%m-%d",
            "%m/%d/%Y": "%m/%d/%Y",
            "%d/%m/%Y": "%d/%m/%Y",
            "%m-%d-%Y": "%m-%d-%Y",
            "%d-%m-%Y": "%d-%m-%Y",
            "%Y/%m/%d": "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S": "%Y-%m-%d %H:%i:%s",
            "%m/%d/%Y %H:%M:%S": "%m/%d/%Y %H:%i:%s",
            "%d/%m/%Y %H:%M:%S": "%d/%m/%Y %H:%i:%s",
        },
        "Snowflake": {
            "%Y-%m-%d": "YYYY-MM-DD",
            "%m/%d/%Y": "MM/DD/YYYY",
            "%d/%m/%Y": "DD/MM/YYYY",
            "%m-%d-%Y": "MM-DD-YYYY",
            "%d-%m-%Y": "DD-MM-YYYY",
            "%Y/%m/%d": "YYYY/MM/DD",
            "%Y-%m-%d %H:%M:%S": "YYYY-MM-DD HH24:MI:SS",
            "%m/%d/%Y %H:%M:%S": "MM/DD/YYYY HH24:MI:SS",
            "%d/%m/%Y %H:%M:%S": "DD/MM/YYYY HH24:MI:SS",
        },
        "BigQuery": {
            "%Y-%m-%d": "%Y-%m-%d",
            "%m/%d/%Y": "%m/%d/%Y",
            "%d/%m/%Y": "%d/%m/%Y",
            "%m-%d-%Y": "%m-%d-%Y",
            "%d-%m-%Y": "%d-%m-%Y",
            "%Y/%m/%d": "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S": "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S": "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S": "%d/%m/%Y %H:%M:%S",
        },
    }

    def __init__(
        self,
        df,
        profile,
        validation_results,
        table_name: str = "datos_limpios",
        dialect: str | None = None,
        source_table: str = "source_table",
        source_schema: str | None = None,
        target_schema: str | None = None,
        quarantine_table: str | None = None,
        load_strategy: str = "REPLACE",
    ) -> None:
        """
        Inicializa el generador.

        Args:
            df (pd.DataFrame): DataFrame analizado.
            profile (dict): Perfil generado por DataProfiler.
            validation_results (dict): Resultados generados por DataValidator.
            table_name (str): Nombre de la tabla limpia destino.
            dialect (str | None): Dialecto SQL objetivo.
            source_table (str): Nombre de la tabla origen/staging.
            source_schema (str | None): Esquema de la tabla origen.
            target_schema (str | None): Esquema de las tablas destino.
            quarantine_table (str | None): Tabla de cuarentena.
            load_strategy (str): APPEND o REPLACE. REPLACE es el valor
                predeterminado para que el script sea seguro al reejecutarse.
        """
        self.df = df
        self.profile = profile or {}
        self.validation_results = validation_results or {}
        self.table_name = table_name or "datos_limpios"
        self.source_table = source_table or "source_table"
        self.source_schema = source_schema.strip() if source_schema else None
        self.target_schema = target_schema.strip() if target_schema else None
        self.quarantine_table = quarantine_table or (
            "datos_cuarentena"
            if self.table_name == "datos_limpios"
            else f"{self.table_name}_cuarentena"
        )
        self.load_strategy = self._normalize_load_strategy(load_strategy)

        self.dialect_name = self._normalize_dialect(dialect or DEFAULT_SQL_DIALECT)
        self.dialect_config = SQL_DIALECTS.get(
            self.dialect_name,
            SQL_DIALECTS.get(DEFAULT_SQL_DIALECT, {}),
        )

        self.jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def generate_complete_script(self, dialect: str | None = None) -> str:
        """
        Genera el script SQL completo.

        Args:
            dialect (str | None): Dialecto opcional para sobreescribir el dialecto
                definido al instanciar la clase.

        Returns:
            str: Script SQL completo.
        """
        active_dialect = self._normalize_dialect(dialect or self.dialect_name)
        dialect_conf = SQL_DIALECTS.get(
            active_dialect,
            SQL_DIALECTS.get(DEFAULT_SQL_DIALECT, {}),
        )

        columns_meta = self._build_columns_meta(active_dialect, dialect_conf)

        context = {
            "now": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "dialect_name": active_dialect,
            "dialect": dialect_conf,
            "table_name": self._quote_table(self._qualified_target_table(), active_dialect),
            "table_name_raw": self.table_name,
            "source_table": self._quote_table(self._qualified_source_table(), active_dialect),
            "source_alias": "src",
            "quarantine_table": self._quote_table(
                self._qualified_quarantine_table(), active_dialect
            ),
            "load_strategy": self.load_strategy,
            "columns": columns_meta,
            "quarantine_columns": [
                col for col in columns_meta if col["flag_expr"] != "TRUE"
            ],
            "clean_table_id_definition": self._get_identity_column_definition(
                "id_registro",
                active_dialect,
            ),
            "quarantine_id_definition": self._get_identity_column_definition(
                "id",
                active_dialect,
            ),
            "secondary_index_sql": self._build_secondary_index_sql(
                columns_meta,
                active_dialect,
            ),
            "cleaned_data_cte": self._render_cleaned_data_cte(
                columns_meta,
                active_dialect,
            ),
        }

        template = self.jinja_env.from_string(self._sql_template())
        return template.render(context).strip() + "\n"

    def generate_python_cleanup_code(self):
        """
        Genera código Python para limpiar datos antes de insertarlos en BD.

        Returns:
            str: Código Python generado.
        """
        script = [
            "# Código Python para limpiar datos antes de insertar en BD",
            "import pandas as pd",
            "import numpy as np",
            "import re",
            "import unicodedata",
            "from datetime import datetime",
            "",
            "_MONTHS = {",
            "    'enero': 1, 'ene': 1, 'january': 1, 'jan': 1,",
            "    'febrero': 2, 'feb': 2, 'february': 2,",
            "    'marzo': 3, 'mar': 3, 'march': 3,",
            "    'abril': 4, 'abr': 4, 'april': 4,",
            "    'mayo': 5, 'may': 5,",
            "    'junio': 6, 'jun': 6, 'june': 6,",
            "    'julio': 7, 'jul': 7, 'july': 7,",
            "    'agosto': 8, 'ago': 8, 'august': 8, 'aug': 8,",
            "    'septiembre': 9, 'setiembre': 9, 'sep': 9, 'september': 9, 'sept': 9,",
            "    'octubre': 10, 'oct': 10, 'october': 10,",
            "    'noviembre': 11, 'nov': 11, 'november': 11,",
            "    'diciembre': 12, 'dic': 12, 'december': 12, 'dec': 12,",
            "}",
            "",
            "def _normalize_numeric_value(value):",
            "    if pd.isna(value):",
            "        return value",
            "    text = str(value).strip()",
            "    negative = text.startswith('(') and text.endswith(')')",
            "    if not re.fullmatch(r'\\(?[+-]?(\\$|€|£|¥|[A-Za-z]{3})?[ ]*[0-9][0-9., ]*\\)?', text):",
            "        return pd.NA",
            "    text = re.sub(r'[^0-9,.-]', '', text)",
            "    if ',' in text and '.' in text:",
            "        if text.rfind(',') > text.rfind('.'):",
            "            text = text.replace('.', '').replace(',', '.')",
            "        else:",
            "            text = text.replace(',', '')",
            "    elif ',' in text:",
            "        last_group = text.rsplit(',', 1)[1]",
            "        text = text.replace(',', '.') if len(last_group) in (1, 2) else text.replace(',', '')",
            "    if negative and text and not text.startswith('-'):",
            "        text = '-' + text",
            "    return text",
            "",
            "def _normalize_date_value(value):",
            "    if pd.isna(value):",
            "        return value",
            "    text = unicodedata.normalize('NFKD', str(value).strip()).encode('ascii', 'ignore').decode()",
            "    text = re.sub(r'\\s+de\\s+', ' ', text, flags=re.IGNORECASE)",
            "    month_pattern = '|'.join(sorted(_MONTHS, key=len, reverse=True))",
            "    match = re.fullmatch(rf'(\\d{{1,2}})\\s+({month_pattern})\\s+(\\d{{4}})', text, flags=re.IGNORECASE)",
            "    if match:",
            "        return f'{match.group(1)}/{_MONTHS[match.group(2).lower()]}/{match.group(3)}'",
            "    match = re.fullmatch(rf'({month_pattern})\\s+(\\d{{1,2}}),?\\s+(\\d{{4}})', text, flags=re.IGNORECASE)",
            "    if match:",
            "        return f'{match.group(2)}/{_MONTHS[match.group(1).lower()]}/{match.group(3)}'",
            "    return text",
            "",
            "def _normalize_boolean_value(value):",
            "    if pd.isna(value):",
            "        return pd.NA",
            "    normalized = unicodedata.normalize('NFKD', str(value).strip()).encode('ascii', 'ignore').decode().lower()",
            "    if normalized in {'true', '1', 'yes', 'si', 'verdadero', 'y', 't'}:",
            "        return True",
            "    if normalized in {'false', '0', 'no', 'falso', 'n', 'f'}:",
            "        return False",
            "    return pd.NA",
            "",
            "",
            "def cleanup_data(df):",
            "    \"\"\"Limpia el DataFrame antes de insertar en BD.\"\"\"",
            "    df_clean = df.copy()",
            "",
        ]

        duplicates_info = self.profile.get("duplicates", {})
        if duplicates_info.get("total_duplicates", 0) > 0:
            script.append("    # 1. Eliminar filas completamente duplicadas")
            script.append("    df_clean = df_clean.drop_duplicates(keep='first')")
            script.append("")

        null_by_column = self.profile.get("null_analysis", {}).get("by_column", {})
        null_analysis = self.profile.get("null_analysis", {})
        problematic_columns = null_analysis.get("problematic_columns", {})
        critical_cols = [
            col
            for col in self._get_column_names()
            if col in problematic_columns
            and col in null_by_column
            and null_by_column[col].get("utilization_percent", 100) < 100
        ]
        if critical_cols:
            script.append("    # 2. Eliminar filas con nulos en columnas críticas")
            script.append(
                f"    df_clean = df_clean.dropna(subset={self._python_literal(critical_cols)})"
            )
            script.append("")

        script.append("    # 3. Limpiar espacios en blanco")
        for col in self._get_column_names()[:20]:
            column_literal = self._python_literal(col)
            script.append(
                f"    if {column_literal} in df_clean.columns and df_clean[{column_literal}].dtype == 'object':"
            )
            script.append(
                f"        df_clean[{column_literal}] = df_clean[{column_literal}].str.strip()"
            )

        script.extend([
            "",
            "    # 4. Estandarizar tipos de datos",
        ])

        for col, profile_col in list(self.profile.get("column_profiles", {}).items())[:20]:
            semantic_type = self._infer_semantic_type(col, profile_col)
            column_literal = self._python_literal(col)
            if semantic_type == "Integer":
                script.append(
                    f"    if {column_literal} in df_clean.columns:"
                )
                script.append(
                        f"        df_clean[{column_literal}] = pd.to_numeric(df_clean[{column_literal}].map(_normalize_numeric_value), errors='coerce').astype('Int64')"
                )
            elif semantic_type == "Float":
                script.append(
                    f"    if {column_literal} in df_clean.columns:"
                )
                script.append(
                    f"        df_clean[{column_literal}] = pd.to_numeric(df_clean[{column_literal}].map(_normalize_numeric_value), errors='coerce')"
                )
            elif semantic_type in ("Date", "DateTime"):
                script.append(
                    f"    if {column_literal} in df_clean.columns:"
                )
                script.append(
                    f"        df_clean[{column_literal}] = pd.to_datetime(df_clean[{column_literal}].map(_normalize_date_value), errors='coerce', dayfirst=True, format='mixed')"
                )
            elif semantic_type == "Boolean":
                script.append(
                    f"    if {column_literal} in df_clean.columns:"
                )
                script.append(
                    f"        df_clean[{column_literal}] = df_clean[{column_literal}].map(_normalize_boolean_value).astype('boolean')"
                )
            elif semantic_type == "Email":
                script.append(
                    f"    if {column_literal} in df_clean.columns and df_clean[{column_literal}].dtype == 'object':"
                )
                script.append(
                    f"        df_clean[{column_literal}] = df_clean[{column_literal}].str.lower()"
                )

        script.extend([
            "",
            "    return df_clean",
            "",
            "",
            "# Uso:",
            "# df_cleaned = cleanup_data(df)",
            "# df_cleaned.to_sql('datos_limpios', con=engine, if_exists='append', index=False)",
        ])

        return "\n".join(script)

    @staticmethod
    def _normalize_numeric_value(value: Any) -> Any:
        """Normaliza moneda, separadores locales y negativos contables."""
        if value is None or pd.isna(value):
            return value

        text = str(value).strip()
        negative = text.startswith("(") and text.endswith(")")
        if not re.fullmatch(r"\(?[+-]?(\$|€|£|¥|[A-Za-z]{3})?[ ]*[0-9][0-9., ]*\)?", text):
            return pd.NA
        text = re.sub(r"[^0-9,.-]", "", text)

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            last_group = text.rsplit(",", 1)[1]
            text = text.replace(",", ".") if len(last_group) in (1, 2) else text.replace(",", "")

        if negative and text and not text.startswith("-"):
            text = "-" + text
        return text

    @staticmethod
    def _normalize_date_value(value: Any) -> Any:
        """Convierte meses escritos en español o inglés a formato día/mes/año."""
        if value is None or pd.isna(value):
            return value

        text = unicodedata.normalize("NFKD", str(value).strip()).encode("ascii", "ignore").decode()
        text = re.sub(r"\s+de\s+", " ", text, flags=re.IGNORECASE)
        months = {
            "enero": 1, "ene": 1, "january": 1, "jan": 1,
            "febrero": 2, "feb": 2, "february": 2,
            "marzo": 3, "mar": 3, "march": 3,
            "abril": 4, "abr": 4, "april": 4,
            "mayo": 5, "may": 5,
            "junio": 6, "jun": 6, "june": 6,
            "julio": 7, "jul": 7, "july": 7,
            "agosto": 8, "ago": 8, "august": 8, "aug": 8,
            "septiembre": 9, "setiembre": 9, "sep": 9,
            "september": 9, "sept": 9,
            "octubre": 10, "oct": 10, "october": 10,
            "noviembre": 11, "nov": 11, "november": 11,
            "diciembre": 12, "dic": 12, "december": 12, "dec": 12,
        }
        month_pattern = "|".join(sorted(months, key=len, reverse=True))
        match = re.fullmatch(
            rf"(\d{{1,2}})\s+({month_pattern})\s+(\d{{4}})",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return f"{match.group(1)}/{months[match.group(2).lower()]}/{match.group(3)}"

        match = re.fullmatch(
            rf"({month_pattern})\s+(\d{{1,2}}),?\s+(\d{{4}})",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return f"{match.group(2)}/{months[match.group(1).lower()]}/{match.group(3)}"
        return text

    @staticmethod
    def _normalize_boolean_value(value: Any) -> Any:
        """Normaliza booleanos frecuentes en español e inglés."""
        if value is None or pd.isna(value):
            return pd.NA

        normalized = unicodedata.normalize("NFKD", str(value).strip()).encode("ascii", "ignore").decode().lower()
        if normalized in {"true", "1", "yes", "si", "verdadero", "y", "t"}:
            return True
        if normalized in {"false", "0", "no", "falso", "n", "f"}:
            return False
        return pd.NA

    @staticmethod
    def _python_literal(value: Any) -> str:
        """Devuelve un literal Python válido para nombres de columnas y listas."""
        return repr(value)

    def generate_config_yaml(self):
        """
        Genera archivo YAML con configuración de validación personalizada.

        Returns:
            str: Configuración YAML generada.
        """
        yaml_config = [
            "# Configuración personalizada de validación de datos",
            f"# Generada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "",
            "database:",
            f"  table_name: {self.table_name}",
            f"  dialect: {self.dialect_name}",
            f"  source_table: {self._qualified_source_table()}",
            f"  quarantine_table: {self._qualified_quarantine_table()}",
            f"  load_strategy: {self.load_strategy}",
            "",
            "columns:",
        ]

        for col, profile_col in list(self.profile.get("column_profiles", {}).items())[:50]:
            null_percent = (
                self.profile
                .get("null_analysis", {})
                .get("by_column", {})
                .get(col, {})
                .get("percent", 0)
            )
            semantic_type = self._infer_semantic_type(col, profile_col)

            yaml_config.extend([
                f"  {col}:",
                f"    type: {semantic_type}",
                f"    nullable: {null_percent > 0}",
                f"    unique: {profile_col.get('cardinality_ratio', 0) >= 0.95}",
            ])

            validations = []
            lowered = col.lower()
            if "email" in lowered or "correo" in lowered or semantic_type == "Email":
                validations.append("email")
            if "phone" in lowered or "telefono" in lowered or "celular" in lowered:
                validations.append("phone")
            if "fecha" in lowered or "date" in lowered or semantic_type in ("Date", "DateTime"):
                validations.append("date")
            if semantic_type in ("Integer", "Float"):
                validations.append("numeric")

            if validations:
                yaml_config.append(f"    validations: [{', '.join(validations)}]")

            yaml_config.append("")

        yaml_config.extend([
            "cleaning:",
            "  trim_whitespace: true",
            "  remove_duplicates: true",
            "  handle_nulls: keep",
            "  quarantine_invalid_rows: true",
            "",
            "validation_rules:",
            "  min_rows: 10",
            "  max_null_percent: 30",
            "  email_valid: true",
            "  phone_valid: true",
            "  date_valid: true",
            "  numeric_valid: true",
        ])

        return "\n".join(yaml_config)

    def export_scripts(self, output_dir="./output"):
        """
        Exporta todos los scripts generados como archivos.

        Args:
            output_dir (str): Directorio de salida.

        Returns:
            dict: Rutas de archivos creados.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        files_created = {}

        sql_file = f"{output_dir}/script_limpieza_{timestamp}.sql"
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write(self.generate_complete_script())
        files_created["sql"] = sql_file

        py_file = f"{output_dir}/cleanup_data_{timestamp}.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(self.generate_python_cleanup_code())
        files_created["python"] = py_file

        yaml_file = f"{output_dir}/config_validacion_{timestamp}.yaml"
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.write(self.generate_config_yaml())
        files_created["config"] = yaml_file

        return files_created

    def _sql_template(self) -> str:
        """
        Plantilla Jinja2 principal del script SQL.

        Se usan dos CTEs equivalentes para mantener compatibilidad SQL
        multidialecto, ya que una CTE estándar solo vive para una sentencia.
        La primera CTE alimenta la tabla limpia; la segunda alimenta la tabla
        de cuarentena.
        """
        return """
-- ============================================================================
-- Script SQL generado para limpieza y carga segura
-- Generado: {{ now }}
-- Dialecto: {{ dialect_name }}
-- ============================================================================

-- ============================================================================
-- 1. Crear tabla limpia
-- ============================================================================
CREATE TABLE IF NOT EXISTS {{ table_name }} (
    {{ clean_table_id_definition }},
{%- for col in columns %}
    {{ col.identifier }} {{ col.sql_type }}{% if not loop.last %},{% endif %}
{%- endfor %}
);

{% if secondary_index_sql %}
{{ secondary_index_sql }}
{% endif %}

-- ============================================================================
-- 2. Crear tabla de cuarentena
-- ============================================================================
CREATE TABLE IF NOT EXISTS {{ quarantine_table }} (
    {{ quarantine_id_definition }},
    fecha_rechazo TIMESTAMP,
    columna_erronea TEXT,
    categoria_error TEXT,
    valor_original TEXT,
    fila_completa_json TEXT
);

{% if load_strategy == 'REPLACE' %}
TRUNCATE TABLE {{ table_name }};
TRUNCATE TABLE {{ quarantine_table }};
{% endif %}

-- ============================================================================
-- 3. Insertar filas válidas en tabla limpia
-- ============================================================================

{{ cleaned_data_cte }}

INSERT INTO {{ table_name }} (
{%- for col in columns %}
    {{ col.identifier }}{% if not loop.last %},{% endif %}
{%- endfor %}
)
SELECT
{% for col in columns %}
    {{ col.value_alias }}{% if not loop.last %},{% endif %}
{% endfor %}
FROM cleaned_data
WHERE
{% for col in columns %}
    {{ col.ok_alias }}{% if not loop.last %} AND{% endif %}
{% endfor %}
;

-- ============================================================================
-- 4. Insertar filas inválidas en cuarentena
-- ============================================================================
{% if quarantine_columns %}

{{ cleaned_data_cte }}

INSERT INTO {{ quarantine_table }} (
    fecha_rechazo,
    columna_erronea,
    categoria_error,
    valor_original,
    fila_completa_json
)
{% for col in quarantine_columns %}
SELECT
    CURRENT_TIMESTAMP,
    {{ col.name_literal }},
    '{{ col.error_category }}',
    {{ col.raw_text_alias }},
    fila_completa_json_raw
FROM cleaned_data
WHERE NOT {{ col.ok_alias }}
{% if not loop.last %}
UNION ALL
{% endif %}
{% endfor %}
;
{% endif %}

-- ============================================================================
-- 5. Validaciones posteriores
-- ============================================================================

SELECT COUNT(*) AS registros_cargados
FROM {{ table_name }};

SELECT COUNT(*) AS registros_en_cuarentena
FROM {{ quarantine_table }};

SELECT
    columna_erronea,
    categoria_error,
    COUNT(*) AS total_errores
FROM {{ quarantine_table }}
GROUP BY columna_erronea, categoria_error
ORDER BY total_errores DESC;

SELECT
{% for col in columns[:20] %}
    SUM(CASE WHEN {{ col.identifier }} IS NULL THEN 1 ELSE 0 END) AS {{ col.null_check_alias }}{% if not loop.last %},{% endif %}
{% endfor %}
FROM {{ table_name }};

SELECT
    {{ columns[:3] | map(attribute='identifier') | join(', ') }},
    COUNT(*) AS count_duplicates
FROM {{ table_name }}
GROUP BY {{ columns[:3] | map(attribute='identifier') | join(', ') }}
HAVING COUNT(*) > 1;
"""

    def _render_cleaned_data_cte(
        self,
        columns_meta: list[dict[str, Any]],
        dialect_name: str,
    ) -> str:
        """
        Renderiza la CTE cleaned_data.

        La CTE incluye:
        - valores transformados;
        - flags de validación;
        - valores originales casteados a texto;
        - fila completa serializada a JSON.
        """
        row_json_expr = self._build_row_json_expr(columns_meta, dialect_name)
        source_table = self._quote_table(self._qualified_source_table(), dialect_name)

        cte_template = """
    -- WITH cleaned_data AS (resultado final de las etapas de origen y parseo)
WITH source_data AS (
    SELECT
        src.*
{%- for col in date_columns %}
        , {{ col.date_normalize_expr }} AS {{ col.date_normalize_alias }}
{%- endfor %}
    FROM {{ source_table }} AS src
), parsed_data AS (
    SELECT
        src.*
{%- for col in date_columns %}
    , {{ col.date_parse_expr }} AS {{ col.date_parse_alias }}
{%- endfor %}
    FROM source_data AS src
), cleaned_data AS (
    SELECT
{%- for col in columns %}
        {{ col.clean_expr }} AS {{ col.value_alias }},
        {{ col.flag_expr }} AS {{ col.ok_alias }},
        {{ col.raw_text_expr }} AS {{ col.raw_text_alias }},
{%- endfor %}
        {{ row_json_expr }} AS fila_completa_json_raw
    FROM parsed_data AS src
)
"""
        template = self.jinja_env.from_string(cte_template)
        return template.render(
            columns=columns_meta,
            date_columns=[col for col in columns_meta if col.get("date_parse_expr")],
            row_json_expr=row_json_expr,
            source_table=source_table,
        ).strip()

    def _build_columns_meta(
        self,
        dialect_name: str,
        dialect_conf: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Construye metadatos SQL por columna.
        """
        columns_meta = []
        used_aliases = set()

        for position, col in enumerate(self._get_column_names()):
            profile_col = self.profile.get("column_profiles", {}).get(col, {})
            semantic_type = self._infer_semantic_type(col, profile_col)
            sql_type = self._infer_sql_type(col, profile_col, semantic_type, dialect_name, dialect_conf)

            base_alias = self._safe_alias(col)
            if base_alias in used_aliases:
                base_alias = f"{base_alias}_{position + 1}"
            used_aliases.add(base_alias)

            source_expr = self._source_column_expr(col, dialect_name)
            text_expr = self._cast_to_text(source_expr, dialect_name)
            trimmed_expr = f"TRIM({text_expr})"

            clean_expr, flag_expr, error_category = self._build_clean_and_flag_expr(
                col=col,
                semantic_type=semantic_type,
                sql_type=sql_type,
                source_expr=source_expr,
                trimmed_expr=trimmed_expr,
                dialect_name=dialect_name,
            )

            columns_meta.append({
                "name": col,
                "name_literal": self._quote_sql_literal(col),
                "safe_alias": base_alias,
                "identifier": self._quote_identifier(col, dialect_name),
                "source_expr": source_expr,
                "sql_type": sql_type,
                "semantic_type": semantic_type,
                "clean_expr": clean_expr,
                "flag_expr": flag_expr,
                "error_category": error_category,
                "value_alias": f"{base_alias}_value",
                "ok_alias": f"{base_alias}_ok",
                "raw_text_alias": f"{base_alias}_raw_text",
                "raw_text_expr": self._cast_to_text(source_expr, dialect_name),
                "null_check_alias": self._quote_identifier(f"{base_alias}_nulos", dialect_name),
                "is_index_candidate": self._is_index_candidate(col),
            })
            if semantic_type in ("Date", "DateTime"):
                normalized_date_expr = self._normalize_date_expr(trimmed_expr)
                target_type = "TIMESTAMP" if semantic_type == "DateTime" else "DATE"
                columns_meta[-1].update({
                    "date_normalize_alias": f"{base_alias}_normalized",
                    "date_normalize_expr": normalized_date_expr,
                    "date_parse_alias": f"{base_alias}_parsed",
                    "date_parse_expr": self._date_cast_expr(
                        f"{base_alias}_normalized",
                        target_type,
                        dialect_name,
                    ),
                })

        self._apply_date_range_validation(columns_meta)

        return columns_meta

    def _apply_date_range_validation(self, columns_meta: list[dict[str, Any]]) -> None:
        """Marca una fecha final como inválida cuando precede a su inicio."""
        by_name = {str(col["name"]).lower(): col for col in columns_meta}
        pairs = (
            ("fecha_inicio", "fecha_fin"),
            ("inicio", "fin"),
            ("start_date", "end_date"),
            ("start", "end"),
        )
        for start_name, end_name in pairs:
            start = by_name.get(start_name)
            end = by_name.get(end_name)
            if not start or not end:
                continue
            if not start.get("date_parse_alias") or not end.get("date_parse_alias"):
                continue
            range_expr = (
                f"({start['date_parse_alias']} IS NULL OR "
                f"{end['date_parse_alias']} IS NULL OR "
                f"{end['date_parse_alias']} >= {start['date_parse_alias']})"
            )
            end["flag_expr"] = f"({end['flag_expr']} AND {range_expr})"
            end["error_category"] = "RANGO_FECHAS_INVALIDO"
            break

    def _build_clean_and_flag_expr(
        self,
        col: str,
        semantic_type: str,
        sql_type: str,
        source_expr: str,
        trimmed_expr: str,
        dialect_name: str,
    ) -> tuple[str, str, str]:
        """
        Construye expresión limpia, flag de validez y categoría de error.
        Modificado: Soporte tolerante multiformato para fechas (guiones, diagonales e ISO).
        """
        blank_expr = f"({source_expr} IS NULL OR {trimmed_expr} = '')"

        if semantic_type == "Integer":
            normalized = self._normalize_numeric_expr(trimmed_expr, dialect_name)
            valid_expr = self._numeric_source_valid_expr(trimmed_expr, dialect_name)
            valid_expr = f"({valid_expr} AND {self._numeric_valid_expr(normalized, integer=True, dialect_name=dialect_name)})"
            cast_expr = self._safe_cast_expr(normalized, sql_type, dialect_name)
            clean_expr = f"CASE WHEN {blank_expr} THEN NULL WHEN {valid_expr} THEN {cast_expr} ELSE NULL END"
            flag_expr = f"({blank_expr} OR {valid_expr})"
            return clean_expr, flag_expr, "TIPO_DATO_NUMERICO"

        if semantic_type == "Float":
            normalized = self._normalize_numeric_expr(trimmed_expr, dialect_name)
            valid_expr = self._numeric_source_valid_expr(trimmed_expr, dialect_name)
            valid_expr = f"({valid_expr} AND {self._numeric_valid_expr(normalized, integer=False, dialect_name=dialect_name)})"
            cast_expr = self._safe_cast_expr(normalized, sql_type, dialect_name)
            clean_expr = f"CASE WHEN {blank_expr} THEN NULL WHEN {valid_expr} THEN {cast_expr} ELSE NULL END"
            flag_expr = f"({blank_expr} OR {valid_expr})"
            return clean_expr, flag_expr, "TIPO_DATO_NUMERICO"

        if semantic_type in ("Date", "DateTime"):
            parse_alias = f"{self._safe_alias(col)}_parsed"
            clean_expr = f"CASE WHEN {blank_expr} THEN NULL ELSE {parse_alias} END"
            flag_expr = f"({blank_expr} OR {parse_alias} IS NOT NULL)"
            return clean_expr, flag_expr, "FORMATO_FECHA_INVALIDO"

        if semantic_type == "Boolean":
            normalized = self._normalize_boolean_expr(trimmed_expr, dialect_name)
            cast_expr = self._safe_cast_expr(normalized, sql_type, dialect_name)
            valid_expr = self._boolean_valid_expr(trimmed_expr, dialect_name)
            clean_expr = f"CASE WHEN {blank_expr} THEN NULL WHEN {valid_expr} THEN {cast_expr} ELSE NULL END"
            flag_expr = f"({blank_expr} OR {valid_expr})"
            return clean_expr, flag_expr, "TIPO_DATO_BOOLEANO"

        if semantic_type == "Email":
            clean_expr = self._lower_expr(trimmed_expr, dialect_name)
            flag_expr = f"({blank_expr} OR {self._email_valid_expr(trimmed_expr, dialect_name)})"
            return clean_expr, flag_expr, "FORMATO_EMAIL_INVALIDO"

        return trimmed_expr, "TRUE", "VALOR_INVALIDO"

    def _infer_semantic_type(self, col: str, profile_col: dict[str, Any]) -> str:
        """
        Infere el tipo semántico de una columna combinando:
        - type_hint del perfilador;
        - dtype de pandas;
        - análisis ligero del contenido.
        """
        type_hint = profile_col.get("type_hint")
        dtype = str(profile_col.get("dtype", ""))

        if type_hint in {"Integer", "Float", "Date", "DateTime", "Email", "Phone", "URL", "Boolean", "Text"}:
            if type_hint != "Text":
                return type_hint

        lowered = col.lower()
        if self._is_identifier_column(col, profile_col):
            return "Text"

        if dtype.startswith("int"):
            return "Integer"

        if dtype.startswith("float"):
            return "Float"

        if dtype == "bool":
            return "Boolean"

        if any(token in lowered for token in ("fecha", "date", "timestamp", "created", "updated")):
            return "Date"

        if any(token in lowered for token in ("email", "correo", "mail")):
            return "Email"

        non_null = self.df[col].dropna() if col in self.df.columns else pd.Series([], dtype=object)
        if non_null.empty:
            return "Text"

        sample = non_null.astype(str).str.strip()
        sample = sample[sample != ""].head(200)

        if sample.empty:
            return "Text"

        numeric_series = pd.to_numeric(
            sample.map(self._normalize_numeric_value),
            errors="coerce",
        )
        numeric_ratio = numeric_series.notna().mean()

        if numeric_ratio >= 0.50:
            numeric_non_null = numeric_series.dropna()
            if numeric_non_null.empty:
                return "Text"
            is_integer = (numeric_non_null % 1 == 0).all()
            return "Integer" if is_integer else "Float"

        boolean_values = sample.map(self._normalize_boolean_value)
        if boolean_values.notna().mean() >= 0.90:
            return "Boolean"

        #date_ratio = pd.to_datetime(sample, errors="coerce").notna().mean()
        date_ratio = pd.to_datetime(
            sample.map(self._normalize_date_value),
            errors="coerce",
            dayfirst=True,
            format="mixed",
        ).notna().mean()
        if date_ratio >= 0.90:
            return "Date"

        return "Text"

    def _infer_sql_type(
        self,
        col: str,
        profile_col: dict[str, Any],
        semantic_type: str,
        dialect_name: str,
        dialect_conf: dict[str, Any],
    ) -> str:
        """
        Infere el tipo SQL compatible con el dialecto.
        """
        if semantic_type == "Integer":
            return dialect_conf.get("int_type", self._default_int_type(dialect_name))

        if semantic_type == "Float":
            precision, scale = self._compute_numeric_precision_scale(self.df[col])
            numeric_type = dialect_conf.get("numeric_type", self._default_numeric_type(dialect_name))
            return f"{numeric_type}({precision},{scale})"

        if semantic_type == "Date":
            return "DATE"

        if semantic_type == "DateTime":
            return "TIMESTAMP"

        if semantic_type == "Boolean":
            return dialect_conf.get("boolean_type", self._default_boolean_type(dialect_name))

        return dialect_conf.get("text_type", self._default_text_type(dialect_name))

    def _compute_numeric_precision_scale(self, series) -> tuple[int, int]:
        """
        Calcula precisión y escala para columnas decimales.
        """
        numeric = pd.to_numeric(
            series.map(self._normalize_numeric_value),
            errors="coerce",
        ).dropna()

        max_integer_digits = 1
        max_decimal_digits = 0

        for value in numeric:
            try:
                decimal_value = Decimal(str(value)).normalize()
                fixed_value = format(decimal_value, "f")

                if "." in fixed_value:
                    integer_part, decimal_part = fixed_value.split(".", 1)
                    decimal_part = decimal_part.rstrip("0")
                else:
                    integer_part, decimal_part = fixed_value, ""

                integer_digits = len(integer_part.replace("-", "").lstrip("0")) or 1
                decimal_digits = len(decimal_part)

                max_integer_digits = max(max_integer_digits, integer_digits)
                max_decimal_digits = max(max_decimal_digits, decimal_digits)
            except Exception:
                continue

        scale = max(max_decimal_digits, 2)
        precision = max_integer_digits + scale

        return max(precision, 10), min(scale, 10)

    def _detect_date_format(self, col: str) -> str:
        """
        Detecta el formato de fecha predominante en una columna.
        """
        if col not in self.df.columns:
            return "%Y-%m-%d"

        sample = (
            self.df[col]
            .dropna()
            .astype(str)
            .str.strip()
        )
        sample = sample[sample != ""].head(500)

        if sample.empty:
            return "%Y-%m-%d"

        best_format = "%Y-%m-%d"
        best_score = -1

        for fmt in self.DATE_FORMAT_CANDIDATES:
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
            score = int(parsed.notna().sum())

            if score > best_score:
                best_score = score
                best_format = fmt

        return best_format

    def _date_parse_expr(
        self,
        expr: str,
        python_format: str,
        semantic_type: str,
        dialect_name: str,
    ) -> str:
        """
        Genera expresión SQL para parseo de fechas.
        """
        sql_format = (
            self.PYTHON_TO_SQL_DATE_FORMATS
            .get(dialect_name, self.PYTHON_TO_SQL_DATE_FORMATS["PostgreSQL"])
            .get(python_format, "YYYY-MM-DD")
        )

        if dialect_name == "PostgreSQL":
            if semantic_type == "DateTime":
                return f"TO_TIMESTAMP({expr}, '{sql_format}')"
            return f"TO_DATE({expr}, '{sql_format}')"

        if dialect_name == "MySQL":
            return f"STR_TO_DATE({expr}, '{sql_format}')"

        if dialect_name == "Snowflake":
            if semantic_type == "DateTime":
                return f"TRY_TO_TIMESTAMP({expr}, '{sql_format}')"
            return f"TRY_TO_DATE({expr}, '{sql_format}')"

        if dialect_name == "BigQuery":
            if semantic_type == "DateTime":
                return f"SAFE.PARSE_TIMESTAMP('{sql_format}', {expr})"
            return f"SAFE.PARSE_DATE('{sql_format}', {expr})"

        return f"CAST({expr} AS DATE)"

    def _date_cast_expr(self, expr: str, target_type: str, dialect_name: str) -> str:
        """Convierte fechas de forma segura evitando que valores inválidos detengan PostgreSQL."""
        if dialect_name != "PostgreSQL":
            return self._safe_cast_expr(expr, target_type, dialect_name)

        # Para DD/MM/YYYY se construye primero una fecha ISO no ambigua.
        european_iso = (
            f"(split_part({expr}, '/', 3) || '-' || "
            f"lpad(split_part({expr}, '/', 2), 2, '0') || '-' || "
            f"lpad(split_part({expr}, '/', 1), 2, '0'))"
        )

        date_value = (
            "CASE "

            # YYYY-MM-DD
            f"WHEN {expr} ~ '^\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}$' "
            f"AND pg_input_is_valid({expr}, 'date') "
            f"THEN CAST({expr} AS DATE) "

            # DD/MM/YYYY
            f"WHEN {expr} ~ '^\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}$' "
            f"AND pg_input_is_valid({european_iso}, 'date') "
            f"THEN CAST({european_iso} AS DATE) "

            # DD-MON-YY / DD-MON-YYYY
            f"WHEN {expr} ~ '^\\d{{1,2}}-[a-z]{{3,9}}-\\d{{2,4}}$' "
            f"AND pg_input_is_valid({expr}, 'date') "
            f"THEN CAST({expr} AS DATE) "

            "ELSE NULL END"
        )

        if target_type == "TIMESTAMP":
            return f"({date_value})::TIMESTAMP"

        return date_value

    def _postgres_date_valid_expr(self, expr: str, date_regex: str) -> str:
        """Valida estructura y fecha real mediante round-trip explícito."""
        structural = f"{expr} ~* '{date_regex}'"
        iso = (
            f"({expr} ~ '^\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}$' AND "
            f"TO_CHAR(TO_DATE({expr}, 'YYYY-MM-DD'), 'YYYY-MM-DD') = {expr})"
        )
        european = (
            f"({expr} ~ '^\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}$' AND "
            f"TO_CHAR(TO_DATE({expr}, 'DD/MM/YYYY'), 'DD/MM/YYYY') = {expr})"
        )
        named = (
            f"({expr} ~ '^\\d{{1,2}}-[a-z]{{3,9}}-\\d{{2,4}}$' AND "
            f"(CASE WHEN length(split_part({expr}, '-', 3)) = 2 "
            f"THEN TO_DATE({expr}, 'DD-MON-YY') "
            f"ELSE TO_DATE({expr}, 'DD-MON-YYYY') END) IS NOT NULL)"
        )
        return f"(({structural}) AND ({iso} OR {european} OR {named}))"

    def _safe_cast_expr(self, expr: str, sql_type: str, dialect_name: str) -> str:
        """
        Genera expresión de cast seguro o controlado según dialecto.
        """
        if dialect_name == "Snowflake":
            return f"TRY_CAST({expr} AS {sql_type})"

        if dialect_name == "BigQuery":
            return f"SAFE_CAST({expr} AS {sql_type})"

        return f"CAST({expr} AS {sql_type})"

    def _numeric_valid_expr(self, expr: str, integer: bool, dialect_name: str) -> str:
        """
        Genera condición SQL para validar números antes de castear.
        """
        pattern = r"^-?[0-9]+$" if integer else r"^-?[0-9]+(\.[0-9]+)?$"

        if dialect_name == "PostgreSQL":
            return f"({expr} ~ '{pattern}')"

        if dialect_name == "MySQL":
            escaped = pattern.replace("\\", "\\\\")
            return f"({expr} REGEXP '{escaped}')"

        if dialect_name == "Snowflake":
            escaped = pattern.replace("\\", "\\\\")
            return f"REGEXP_LIKE({expr}, '{escaped}')"

        if dialect_name == "BigQuery":
            escaped = pattern.replace("\\", "\\\\")
            return f"REGEXP_CONTAINS({expr}, r'{escaped}')"

        return f"({self._safe_cast_expr(expr, 'NUMERIC', dialect_name)} IS NOT NULL)"

    def _numeric_source_valid_expr(self, expr: str, dialect_name: str) -> str:
        """Acepta decoración monetaria, pero no texto arbitrario alrededor."""
        pattern = r"^\(?[+-]?(\$|€|£|¥|[A-Za-z]{3})?[ ]*[0-9][0-9., ]*\)?$"
        return self._sql_regex_match(expr, pattern, dialect_name)

    def _boolean_valid_expr(self, expr: str, dialect_name: str) -> str:
        """
        Genera condición SQL para validar booleanos textuales.
        """
        lower_expr = self._lower_expr(expr, dialect_name)
        return (
            f"({lower_expr} IN "
            "('true', 'false', '1', '0', 'yes', 'no', 'si', 'sí', "
            "'verdadero', 'falso', 'y', 'n', 't', 'f'))"
        )

    def _normalize_boolean_expr(self, expr: str, dialect_name: str) -> str:
        """Convierte booleanos textuales a literales true/false SQL."""
        lower_expr = self._lower_expr(expr, dialect_name)
        true_values = "'true', '1', 'yes', 'si', 'sí', 'verdadero', 'y', 't'"
        false_values = "'false', '0', 'no', 'falso', 'n', 'f'"
        return (
            f"CASE WHEN {lower_expr} IN ({true_values}) THEN 'true' "
            f"WHEN {lower_expr} IN ({false_values}) THEN 'false' ELSE NULL END"
        )

    def _email_valid_expr(self, expr: str, dialect_name: str) -> str:
        """
        Genera condición SQL para validar emails de forma preliminar.
        """
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

        if dialect_name == "PostgreSQL":
            return f"({expr} ~* '{pattern}')"

        if dialect_name == "MySQL":
            escaped = pattern.replace("\\", "\\\\")
            return f"({expr} REGEXP '{escaped}')"

        if dialect_name == "Snowflake":
            escaped = pattern.replace("\\", "\\\\")
            return f"REGEXP_LIKE({expr}, '{escaped}', 'i')"

        if dialect_name == "BigQuery":
            escaped = pattern.replace("\\", "\\\\")
            return f"REGEXP_CONTAINS({expr}, r'(?i){escaped}')"

        return f"({expr} LIKE '%@%')"

    def _normalize_numeric_expr(self, expr: str, dialect_name: str) -> str:
        """
        Normaliza moneda, negativos contables y separadores locales.
        """
        signed_expr = f"REPLACE(REPLACE({expr}, '(', '-'), ')', '')"
        if dialect_name == "BigQuery":
            cleaned = f"REGEXP_REPLACE({signed_expr}, r'[^0-9,.-]', '')"
        else:
            cleaned = f"REGEXP_REPLACE({signed_expr}, '[^0-9,.-]', '')"

        has_both_separators = self._sql_regex_match(
            cleaned,
            r"^-?[0-9].*,.*\..*$|^-?[0-9].*\..*,.*$",
            dialect_name,
        )
        european_format = self._sql_regex_match(
            cleaned,
            r"^-?[0-9]{1,3}(\.[0-9]{3})+,[0-9]+$",
            dialect_name,
        )
        comma_decimal = self._sql_regex_match(
            cleaned,
            r"^-?[0-9]+,[0-9]{1,2}$",
            dialect_name,
        )
        european_value = f"REPLACE(REPLACE({cleaned}, '.', ''), ',', '.')"
        comma_value = f"REPLACE({cleaned}, ',', '.')"
        thousands_value = f"REPLACE({cleaned}, ',', '')"

        return (
            f"CASE WHEN {has_both_separators} AND {european_format} "
            f"THEN {european_value} "
            f"WHEN {has_both_separators} THEN {thousands_value} "
            f"WHEN {comma_decimal} THEN {comma_value} "
            f"ELSE {thousands_value} END"
        )

    def _sql_regex_match(self, expr: str, pattern: str, dialect_name: str) -> str:
        """Genera una coincidencia regex compatible con el dialecto SQL."""
        escaped = pattern.replace("\\", "\\\\")
        if dialect_name == "PostgreSQL":
            return f"({expr} ~ '{pattern}')"
        if dialect_name == "MySQL":
            return f"({expr} REGEXP '{escaped}')"
        if dialect_name == "Snowflake":
            return f"REGEXP_LIKE({expr}, '{escaped}')"
        if dialect_name == "BigQuery":
            return f"REGEXP_CONTAINS({expr}, r'{escaped}')"
        return f"({expr} LIKE '%')"

    def _normalize_date_expr(self, expr: str) -> str:
        """Normaliza meses en español a abreviaturas inglesas aceptadas por SQL."""
        normalized = f"REPLACE(REPLACE(LOWER({expr}), ' de ', ' '), 'setiembre', 'sep')"
        month_replacements = (
            ("septiembre", "sep"),
            ("diciembre", "dec"),
            ("noviembre", "nov"),
            ("octubre", "oct"),
            ("agosto", "aug"),
            ("julio", "jul"),
            ("junio", "jun"),
            ("mayo", "may"),
            ("abril", "apr"),
            ("marzo", "mar"),
            ("febrero", "feb"),
            ("enero", "jan"),
        )
        for source, target in month_replacements:
            normalized = f"REPLACE({normalized}, '{source}', '{target}')"
        short_month_replacements = (
            ("ene", "jan"), ("abr", "apr"), ("ago", "aug"),
            ("dic", "dec"),
        )
        for source, target in short_month_replacements:
            normalized = f"REPLACE({normalized}, '-{source}-', '-{target}-')"
        return normalized

    def _is_identifier_column(self, col: str, profile_col: dict[str, Any]) -> bool:
        """Identifica claves/códigos que deben conservarse como texto."""
        type_hint = str(profile_col.get("type_hint", "")).lower()
        lowered = col.lower().strip()
        identifier_tokens = (
            "id", "sku", "folio", "codigo", "código", "code", "pedido",
            "cliente", "producto", "customer", "product", "order",
        )
        return (
            "ident" in type_hint
            or lowered in identifier_tokens
            or lowered.endswith("_id")
            or any(token in lowered for token in ("sku", "folio", "codigo", "código", "code", "pedido"))
        )

    def _cast_to_text(self, expr: str, dialect_name: str) -> str:
        """
        Castea una expresión a texto según dialecto.
        """
        if dialect_name == "MySQL":
            return f"CAST({expr} AS CHAR)"

        if dialect_name == "Snowflake":
            return f"CAST({expr} AS VARCHAR)"

        if dialect_name == "BigQuery":
            return f"CAST({expr} AS STRING)"

        return f"CAST({expr} AS TEXT)"

    def _lower_expr(self, expr: str, dialect_name: str) -> str:
        """
        Devuelve LOWER(expr). Separado para mantener simetría multidialecto.
        """
        return f"LOWER({expr})"

    def _build_row_json_expr(
        self,
        columns_meta: list[dict[str, Any]],
        dialect_name: str,
    ) -> str:
        """
        Construye expresión SQL para serializar la fila completa a JSON.

        La expresión se evalúa dentro de la CTE, donde sí existe el alias src.
        """
        if dialect_name == "PostgreSQL":
            return "CAST(ROW_TO_JSON(src) AS TEXT)"

        if dialect_name == "MySQL":
            pairs = []
            for col in columns_meta:
                pairs.append(f"'{col['name']}'")
                pairs.append(col["source_expr"])
            return f"CAST(JSON_OBJECT({', '.join(pairs)}) AS CHAR)"

        if dialect_name == "Snowflake":
            pairs = []
            for col in columns_meta:
                pairs.append(f"'{col['name']}'")
                pairs.append(col["source_expr"])
            return f"TO_JSON(OBJECT_CONSTRUCT_KEEP_NULL({', '.join(pairs)}))"

        if dialect_name == "BigQuery":
            fields = [
                f"{col['source_expr']} AS {col['safe_alias']}"
                for col in columns_meta
            ]
            return f"TO_JSON_STRING(STRUCT({', '.join(fields)}))"

        return "NULL"

    def _build_secondary_index_sql(
        self,
        columns_meta: list[dict[str, Any]],
        dialect_name: str,
    ) -> str:
        """
        Construye índice secundario sobre columnas candidatas.

        No se declara como UNIQUE ni como PK para evitar conflictos con
        combinaciones repetidas como (order_id, product_id).
        """
        index_columns = [
            col["identifier"]
            for col in columns_meta
            if col.get("is_index_candidate")
        ]

        if not index_columns:
            return ""

        table_identifier = self._quote_table(
            self._qualified_target_table(), dialect_name
        )
        index_name = self._safe_alias(f"idx_{self.table_name}_business_keys")

        if dialect_name == "PostgreSQL":
            return (
                f"CREATE INDEX IF NOT EXISTS {self._quote_identifier(index_name, dialect_name)}\n"
                f"    ON {table_identifier} ({', '.join(index_columns)});"
            )

        if dialect_name == "MySQL":
            return (
                f"CREATE INDEX {self._quote_identifier(index_name, dialect_name)}\n"
                f"    ON {table_identifier} ({', '.join(index_columns)});"
            )

        return ""

    def _get_identity_column_definition(self, column_name: str, dialect_name: str) -> str:
        """
        Devuelve la definición de columna ID autogenerada por dialecto.
        """
        quoted_col = self._quote_identifier(column_name, dialect_name)

        if dialect_name == "PostgreSQL":
            return f"{quoted_col} BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"

        if dialect_name == "MySQL":
            return f"{quoted_col} BIGINT AUTO_INCREMENT PRIMARY KEY"

        if dialect_name == "Snowflake":
            return f"{quoted_col} BIGINT AUTOINCREMENT PRIMARY KEY"

        if dialect_name == "BigQuery":
            return f"{quoted_col} STRING NOT NULL DEFAULT GENERATE_UUID()"

        return f"{quoted_col} BIGINT PRIMARY KEY"

    def _get_column_names(self) -> list[str]:
        """
        Obtiene columnas desde profile o desde df.
        """
        profile_columns = (
            self.profile
            .get("general_info", {})
            .get("column_names")
        )

        if profile_columns:
            return list(profile_columns)

        if hasattr(self.df, "columns"):
            return list(self.df.columns)

        return []

    def _qualified_source_table(self) -> str:
        if self.source_schema and "." not in self.source_table:
            return f"{self.source_schema}.{self.source_table}"
        return self.source_table

    def _qualified_target_table(self) -> str:
        if self.target_schema and "." not in self.table_name:
            return f"{self.target_schema}.{self.table_name}"
        return self.table_name

    def _qualified_quarantine_table(self) -> str:
        if self.target_schema and "." not in self.quarantine_table:
            return f"{self.target_schema}.{self.quarantine_table}"
        return self.quarantine_table

    @staticmethod
    def _normalize_load_strategy(strategy: str) -> str:
        normalized = str(strategy or "APPEND").strip().upper()
        if normalized not in {"APPEND", "REPLACE"}:
            raise ValueError("load_strategy debe ser APPEND o REPLACE")
        return normalized

    def _is_index_candidate(self, col: str) -> bool:
        """
        Detecta columnas de negocio candidatas a índice secundario.
        """
        lowered = col.lower()

        business_key_tokens = (
            "order_id",
            "product_id",
            "customer_id",
            "codigo",
            "code",
            "sku",
        )

        if lowered in business_key_tokens:
            return True

        if lowered.endswith("_id"):
            return True

        return False

    def _source_column_expr(self, col: str, dialect_name: str) -> str:
        """
        Construye referencia a columna de source_table usando alias src.
        """
        return f"src.{self._quote_identifier(col, dialect_name)}"

    def _quote_identifier(self, identifier: str, dialect_name: str) -> str:
        """
        Escapa identificadores SQL.
        """
        identifier = str(identifier)

        if dialect_name in ("PostgreSQL", "Snowflake"):
            escaped = identifier.replace('"', '""')
            return f'"{escaped}"'

        if dialect_name in ("MySQL", "BigQuery"):
            escaped = identifier.replace("`", "``")
            return f"`{escaped}`"

        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _quote_sql_literal(value: Any) -> str:
        """Escapa un valor textual para usarlo como literal SQL."""
        return "'" + str(value).replace("'", "''") + "'"

    def _quote_table(self, table_name: str, dialect_name: str) -> str:
        """
        Escapa nombres de tabla, soportando notación con puntos.
        """
        table_name = str(table_name)

        parts = table_name.split(".")
        safe_name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        if all(safe_name_pattern.match(part) for part in parts):
            return ".".join(parts)

        if dialect_name == "BigQuery":
            escaped = table_name.replace("`", "``")
            return f"`{escaped}`"

        return ".".join(self._quote_identifier(part, dialect_name) for part in parts)

    def _safe_alias(self, value: str) -> str:
        """
        Convierte un nombre de columna en alias SQL seguro.
        """
        alias = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip().lower())
        alias = re.sub(r"_+", "_", alias).strip("_")

        if not alias:
            alias = "columna"

        if alias[0].isdigit():
            alias = f"col_{alias}"

        return alias

    def _normalize_dialect(self, dialect: str) -> str:
        """
        Normaliza el nombre del dialecto.
        """
        if not dialect:
            return DEFAULT_SQL_DIALECT

        dialect_lookup = {
            "postgres": "PostgreSQL",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "snowflake": "Snowflake",
            "bigquery": "BigQuery",
            "google bigquery": "BigQuery",
            "google_bigquery": "BigQuery",
        }

        normalized = dialect_lookup.get(str(dialect).strip().lower())
        if normalized:
            return normalized

        if dialect in self.SUPPORTED_DIALECTS:
            return dialect

        return DEFAULT_SQL_DIALECT

    def _default_int_type(self, dialect_name: str) -> str:
        if dialect_name == "BigQuery":
            return "INT64"
        return "INTEGER"

    def _default_numeric_type(self, dialect_name: str) -> str:
        if dialect_name == "MySQL":
            return "DECIMAL"
        if dialect_name == "Snowflake":
            return "NUMBER"
        return "NUMERIC"

    def _default_boolean_type(self, dialect_name: str) -> str:
        if dialect_name == "BigQuery":
            return "BOOL"
        return "BOOLEAN"

    def _default_text_type(self, dialect_name: str) -> str:
        if dialect_name == "BigQuery":
            return "STRING"
        if dialect_name == "Snowflake":
            return "VARCHAR"
        return "TEXT"