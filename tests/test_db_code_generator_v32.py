import pandas as pd

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
