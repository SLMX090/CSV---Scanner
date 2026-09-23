import pandas as pd
import ast

from modules.data_profiler import DataProfiler
from modules.validators import DataValidator
from modules.db_code_generator import DatabaseCodeGenerator


def build_test_context():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "nombre": ["Ana", "Luis", "María"],
        "monto": [1250.50, 99.99, 300.00],
        "cantidad": [10, 20, 30],
        "fecha": ["2024-01-15", "2024-02-20", "2024-03-10"],
        "email": ["ana@test.com", "luis@test.com", "maria@test.com"]
    })

    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()

    return df, profile, validation_results


def test_generate_postgresql_script():
    df, profile, validation_results = build_test_context()

    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results,
        table_name="datos_limpios",
        dialect="PostgreSQL"
    )

    sql = generator.generate_complete_script()

    assert "CREATE TABLE IF NOT EXISTS datos_limpios" in sql
    assert "CREATE TABLE IF NOT EXISTS datos_cuarentena" in sql
    assert "WITH cleaned_data AS" in sql
    assert "INSERT INTO datos_limpios" in sql
    assert "INSERT INTO datos_cuarentena" in sql
    assert "NUMERIC" in sql or "INTEGER" in sql


def test_generate_mysql_script():
    df, profile, validation_results = build_test_context()

    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results,
        table_name="datos_limpios",
        dialect="MySQL"
    )

    sql = generator.generate_complete_script()

    assert "CREATE TABLE IF NOT EXISTS datos_limpios" in sql
    assert "CREATE TABLE IF NOT EXISTS datos_cuarentena" in sql
    assert "STR_TO_DATE" in sql or "CAST" in sql
    assert "DECIMAL" in sql or "INT" in sql


def test_generate_snowflake_script():
    df, profile, validation_results = build_test_context()

    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results,
        table_name="datos_limpios",
        dialect="Snowflake"
    )

    sql = generator.generate_complete_script()

    assert "CREATE TABLE IF NOT EXISTS datos_limpios" in sql
    assert "CREATE TABLE IF NOT EXISTS datos_cuarentena" in sql
    assert "TRY_CAST" in sql or "TRY_TO_DATE" in sql
    assert "NUMBER" in sql or "INT" in sql


def test_generate_bigquery_script():
    df, profile, validation_results = build_test_context()

    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results,
        table_name="datos_limpios",
        dialect="BigQuery"
    )

    sql = generator.generate_complete_script()

    assert "CREATE TABLE IF NOT EXISTS datos_limpios" in sql
    assert "CREATE TABLE IF NOT EXISTS datos_cuarentena" in sql
    assert "SAFE_CAST" in sql or "PARSE_DATE" in sql
    assert "NUMERIC" in sql or "INT64" in sql


def test_backward_compatibility_default_constructor():
    df, profile, validation_results = build_test_context()

    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results
    )

    sql = generator.generate_complete_script()

    assert isinstance(sql, str)
    assert "datos_limpios" in sql
    assert "datos_cuarentena" in sql
    assert "WITH cleaned_data AS" in sql


def test_generated_script_contains_quarantine_error_categories():
    df, profile, validation_results = build_test_context()

    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results,
        table_name="datos_limpios",
        dialect="PostgreSQL"
    )

    sql = generator.generate_complete_script()

    assert "columna_erronea" in sql
    assert "categoria_error" in sql
    assert "valor_original" in sql
    assert "fila_completa_json" in sql
    assert "TIPO_DATO_NUMERICO" in sql or "FORMATO_FECHA_INVALIDO" in sql


def test_generated_python_is_valid_and_uses_problematic_columns():
    df = pd.DataFrame({
        "customer's name": [" Ana ", "Ana", None, None],
        "monto": ["10.50", "10.50", "20.00", "30.00"],
        "email": ["ANA@TEST.COM", "ANA@TEST.COM", "luis@test.com", "x@test.com"],
    })
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()

    generator = DatabaseCodeGenerator(df, profile, validation_results)
    python_code = generator.generate_python_cleanup_code()

    ast.parse(python_code)
    assert "dropna(subset=[\"customer's name\"])" in python_code

    namespace = {}
    exec(python_code, namespace)
    cleaned = namespace["cleanup_data"](df)

    assert list(cleaned["customer's name"]) == ["Ana", "Ana"]
    assert cleaned["monto"].tolist() == [10.5, 10.5]
    assert cleaned["email"].tolist() == ["ana@test.com", "ana@test.com"]


def test_generated_sql_escapes_column_names_in_quarantine():
    df = pd.DataFrame({"customer's name": ["Ana", None]})
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()

    sql = DatabaseCodeGenerator(df, profile, validation_results).generate_complete_script()

    assert "'customer''s name'" not in sql
    assert "INSERT INTO datos_cuarentena" not in sql


def test_generated_python_normalizes_currency_and_named_months():
    df = pd.DataFrame({
        "importe": ["$1,234.56", "€ 1.234,56", "(£2,000.00)"],
        "fecha_pago": ["15 enero 2024", "January 16, 2024", "17 february 2024"],
    })
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()

    generator = DatabaseCodeGenerator(df, profile, validation_results)
    python_code = generator.generate_python_cleanup_code()
    namespace = {}
    exec(python_code, namespace)
    cleaned = namespace["cleanup_data"](df)

    assert cleaned["importe"].tolist() == [1234.56, 1234.56, -2000.0]
    assert cleaned["fecha_pago"].dt.strftime("%Y-%m-%d").tolist() == [
        "2024-01-15",
        "2024-01-16",
        "2024-02-17",
    ]


def test_generated_sql_contains_extended_numeric_normalization():
    df = pd.DataFrame({
        "importe": ["$1,234.56", "(€2.000,00)"],
        "fecha_pago": ["15 enero 2024", "January 16, 2024"],
    })
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()

    sql = DatabaseCodeGenerator(df, profile, validation_results).generate_complete_script()

    assert "REGEXP_REPLACE" in sql
    assert "REPLACE(" in sql
    assert "'enero', 'jan'" in sql


def test_generated_code_normalizes_boolean_values():
    df = pd.DataFrame({"activo": ["Sí", "verdadero", "N", "0"]})
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()

    generator = DatabaseCodeGenerator(df, profile, validation_results)
    python_code = generator.generate_python_cleanup_code()
    namespace = {}
    exec(python_code, namespace)
    cleaned = namespace["cleanup_data"](df)
    sql = generator.generate_complete_script()

    assert cleaned["activo"].tolist() == [True, True, False, False]
    assert "CASE WHEN LOWER" in sql
    assert "'sí'" in sql


def test_identifiers_are_preserved_as_text():
    df = pd.DataFrame({
        "folio_pedido": ["PIT-0014", "PIT0065", "000123", "ABC123"],
        "sku": ["0001", "0002", "0003", "0004"],
    })
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()
    generator = DatabaseCodeGenerator(df, profile, validation_results)

    sql = generator.generate_complete_script()
    python_code = generator.generate_python_cleanup_code()
    namespace = {}
    exec(python_code, namespace)
    cleaned = namespace["cleanup_data"](df)

    assert '"folio_pedido" TEXT' in sql
    assert '"sku" TEXT' in sql
    assert cleaned["folio_pedido"].tolist() == df["folio_pedido"].tolist()
    assert cleaned["sku"].tolist() == df["sku"].tolist()


def test_generated_python_rejects_arbitrary_text_in_numeric_values():
    df = pd.DataFrame({"importe": ["$1,250.50", "1.250,50", "(1,250.50)", "abc1250xyz"]})
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()
    generator = DatabaseCodeGenerator(df, profile, validation_results)
    namespace = {}
    exec(generator.generate_python_cleanup_code(), namespace)
    cleaned = namespace["cleanup_data"](df)

    assert cleaned["importe"].iloc[:3].tolist() == [1250.5, 1250.5, -1250.5]
    assert pd.isna(cleaned["importe"].iloc[3])


def test_generated_postgresql_dates_use_explicit_formats():
    df = pd.DataFrame({
        "fecha_devolucion": [
            "2024-01-10", "10/01/2024", "10-ene-24",
            "10 de enero de 2024", "2024-99-99",
        ]
    })
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()
    sql = DatabaseCodeGenerator(df, profile, validation_results).generate_complete_script()

    assert "TO_DATE" in sql
    assert "DD/MM/YYYY" in sql
    assert "DD-MON-YY" in sql
    assert "DD-MON-YYYY" in sql
    assert "2024-99-99" not in sql


def test_generated_sql_has_no_concatenated_clauses():
    df, profile, validation_results = build_test_context()
    sql = DatabaseCodeGenerator(df, profile, validation_results).generate_complete_script()

    for invalid_fragment in ("valueFROM", "okUNION", "ALLSELECT", "nulosFROM"):
        assert invalid_fragment not in sql


def test_generated_sql_supports_dataset_names_and_replace_strategy():
    df, profile, validation_results = build_test_context()
    generator = DatabaseCodeGenerator(
        df,
        profile,
        validation_results,
        table_name="devoluciones",
        source_schema="origin",
        source_table="devoluciones_raw",
        target_schema="staging",
        load_strategy="REPLACE",
    )

    sql = generator.generate_complete_script()

    assert "CREATE TABLE IF NOT EXISTS staging.devoluciones" in sql
    assert "CREATE TABLE IF NOT EXISTS staging.devoluciones_cuarentena" in sql
    assert "FROM origin.devoluciones_raw AS src" in sql
    assert "TRUNCATE TABLE staging.devoluciones;" in sql
    assert "TRUNCATE TABLE staging.devoluciones_cuarentena;" in sql
