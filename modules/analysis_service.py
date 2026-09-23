"""
Servicio de análisis para un archivo o lote de archivos.

Centraliza la lógica de preparación del DataFrame, perfilado,
validación, recomendaciones y clasificación de severidad.

Esta capa existe para separar la lógica de negocio de la capa de UI.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from modules.csv_loader import CSVLoader
from modules.data_profiler import DataProfiler
from modules.validators import DataValidator
from modules.recommendations import RecommendationGenerator
from modules.severity_analyzer import SeverityAnalyzer
from config import CHUNKED_LOAD_THRESHOLD_MB


def _build_error_result(source_name: str, error: Exception, sheet_name=None) -> Dict[str, Any]:
    """Construye un resultado serializable para un archivo u hoja fallida."""
    return {
        'source_name': source_name,
        'df': None,
        'load_info': {
            'status': 'error',
            'error': str(error),
            'sheet_name': sheet_name,
        },
        'profile': {},
        'validation_results': {},
        'recommendations': {},
        'severity_issues': {'critical': [], 'severe': [], 'warnings': []},
        'severity_counts': {'critical': 0, 'severe': 0, 'warnings': 0},
        'status': 'error',
        'error': str(error),
    }


def analyze_dataframe(df: pd.DataFrame, source_name: str = "dataset", load_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Procesa un DataFrame ya cargado y devuelve el resultado completo del análisis."""
    profile = DataProfiler(df).generate_profile()
    validation_results = DataValidator(df).validate_all()
    recommendations = RecommendationGenerator(profile, validation_results).generate_all_recommendations()
    severity_issues = SeverityAnalyzer.analyze_severity(profile, validation_results)

    return {
        "source_name": source_name,
        "df": df,
        "load_info": load_info or {
            "rows": len(df),
            "columns": len(df.columns),
            "delimiter": ",",
            "encoding": "utf-8",
            "load_mode": "direct",
        },
        "profile": profile,
        "validation_results": validation_results,
        "recommendations": recommendations,
        "severity_issues": severity_issues,
        "severity_counts": SeverityAnalyzer.get_severity_counts(severity_issues),
    }


def analyze_uploaded_file(uploaded_file, delimiter=None, encoding=None, sheet_name=0) -> Dict[str, Any]:
    """Carga un archivo y devuelve el resultado completo del análisis."""
    if uploaded_file is None:
        raise ValueError("No se proporcionó un archivo para analizar.")

    source_name = getattr(uploaded_file, "name", "archivo.csv")
    file_size = CSVLoader._get_file_size(uploaded_file)
    is_large_csv = (
        source_name.lower().endswith('.csv')
        and file_size is not None
        and file_size / (1024 ** 2) > CHUNKED_LOAD_THRESHOLD_MB
    )

    if is_large_csv:
        detected_delimiter = delimiter
        if detected_delimiter is None:
            sample_text, detected_encoding = CSVLoader._read_detection_sample(uploaded_file, encoding)
            encoding = encoding or detected_encoding
            detected_delimiter = CSVLoader.detect_delimiter(sample_text, encoding)
        chunks_for_profile = CSVLoader.iter_csv_chunks(
            uploaded_file,
            delimiter=detected_delimiter,
            encoding=encoding,
        )
        profile = DataProfiler.generate_profile_from_chunks(chunks_for_profile)
        sample_iterator = CSVLoader.iter_csv_chunks(
            uploaded_file,
            delimiter=detected_delimiter,
            encoding=encoding,
        )
        sample_df = next(iter(sample_iterator), pd.DataFrame())
        load_info = {
            'delimiter': detected_delimiter,
            'encoding': encoding,
            'rows': profile['general_info']['total_rows'],
            'columns': profile['general_info']['total_columns'],
            'load_mode': 'incremental',
            'chunked': True,
            'incremental': profile['incremental'],
        }
        result = analyze_dataframe(sample_df, source_name=source_name, load_info=load_info)
        result['profile'] = profile
        result['severity_issues'] = SeverityAnalyzer.analyze_severity(
            profile, result['validation_results']
        )
        result['severity_counts'] = SeverityAnalyzer.get_severity_counts(result['severity_issues'])
        return result

    df, load_info = CSVLoader.load_file(
        uploaded_file,
        file_name=source_name,
        delimiter=delimiter,
        encoding=encoding,
        sheet_name=sheet_name,
    )
    return analyze_dataframe(df, source_name=source_name, load_info=load_info)


def analyze_uploaded_files(uploaded_files: Iterable[Any], delimiter=None, encoding=None, sheet_name=0, keep_all_dataframes=False) -> List[Dict[str, Any]]:
    """Procesa archivos uno a uno y evita conservar todos los DataFrames en RAM."""
    results = []
    for file_index, uploaded_file in enumerate(uploaded_files):
        if uploaded_file is None:
            continue
        source_name = getattr(uploaded_file, 'name', f'archivo_{file_index + 1}')
        try:
            result = analyze_uploaded_file(
                uploaded_file,
                delimiter=delimiter,
                encoding=encoding,
                sheet_name=sheet_name,
            )
            result['status'] = 'ok'
            if file_index > 0 and not keep_all_dataframes:
                result['df'] = None
        except Exception as error:
            result = _build_error_result(source_name, error, sheet_name)
        results.append(result)
    return results


def analyze_uploaded_workbook(uploaded_file, delimiter=None, encoding=None, keep_all_dataframes=False) -> List[Dict[str, Any]]:
    """Analiza todas las hojas de un libro Excel como resultados independientes."""
    source_name = getattr(uploaded_file, 'name', 'archivo.xlsx')
    sheet_names = CSVLoader.list_excel_sheets(uploaded_file, source_name)
    results = []

    for sheet_name in sheet_names:
        display_name = f'{source_name} :: {sheet_name}'
        try:
            result = analyze_uploaded_file(
                uploaded_file,
                delimiter=delimiter,
                encoding=encoding,
                sheet_name=sheet_name,
            )
            result['status'] = 'ok'
            result['source_name'] = display_name
            result['load_info']['workbook_name'] = source_name
            result['load_info']['sheet_name'] = sheet_name
            if results and not keep_all_dataframes:
                result['df'] = None
        except Exception as error:
            result = _build_error_result(display_name, error, sheet_name)
        results.append(result)

    return results


def summarize_batch_results(results: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Genera un resumen comparativo por archivo para la fase 1 (multiarchivo)."""
    rows = []
    for result in results:
        profile = result.get("profile", {})
        null_analysis = profile.get("null_analysis", {})
        duplicates = profile.get("duplicates", {})
        severity_counts = result.get("severity_counts", {})

        rows.append({
            "source_name": result.get("source_name", "desconocido"),
            "status": result.get("status", "ok"),
            "error": result.get("error", ""),
            "sheet_name": result.get("load_info", {}).get("sheet_name", ""),
            "analysis_mode": result.get("load_info", {}).get("load_mode", ""),
            "approximate_statistics": result.get("profile", {}).get("incremental", {}).get(
                "column_statistics_approximate", False
            ),
            "rows": profile.get("general_info", {}).get("total_rows", 0),
            "columns": profile.get("general_info", {}).get("total_columns", 0),
            "total_null_cells": null_analysis.get("total_null_cells", 0),
            "null_percent_overall": null_analysis.get("null_percent_overall", 0),
            "duplicate_rows": duplicates.get("total_duplicates", 0),
            "duplicate_percent": duplicates.get("duplicates_percent", 0),
            "critical_issues": severity_counts.get("critical", 0),
            "severe_issues": severity_counts.get("severe", 0),
            "warning_issues": severity_counts.get("warnings", 0),
        })

    return pd.DataFrame(rows)
