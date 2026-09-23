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


def analyze_uploaded_file(uploaded_file, delimiter=None, encoding=None) -> Dict[str, Any]:
    """Carga un archivo y devuelve el resultado completo del análisis."""
    if uploaded_file is None:
        raise ValueError("No se proporcionó un archivo para analizar.")

    source_name = getattr(uploaded_file, "name", "archivo.csv")
    df, load_info = CSVLoader.load_file(
        uploaded_file,
        file_name=source_name,
        delimiter=delimiter,
        encoding=encoding,
    )
    return analyze_dataframe(df, source_name=source_name, load_info=load_info)


def analyze_uploaded_files(uploaded_files: Iterable[Any], delimiter=None, encoding=None, keep_all_dataframes=False) -> List[Dict[str, Any]]:
    """Procesa archivos uno a uno y evita conservar todos los DataFrames en RAM."""
    results = []
    for file_index, uploaded_file in enumerate(uploaded_files):
        if uploaded_file is None:
            continue
        result = analyze_uploaded_file(uploaded_file, delimiter=delimiter, encoding=encoding)
        if file_index > 0 and not keep_all_dataframes:
            result["df"] = None
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
