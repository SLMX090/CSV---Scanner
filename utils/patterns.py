"""
Patrones de validación utilizados en toda la aplicación.
Contiene expresiones regulares y patrones para validar diferentes tipos de datos.
"""

import re
from datetime import datetime
import pandas as pd
from config import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    URL_PATTERN,
    DATETIME_KEYWORDS,
    EMAIL_KEYWORDS,
    PHONE_KEYWORDS,
    URL_KEYWORDS,
    ID_KEYWORDS
)


class ValidationPatterns:
    """Clase que contiene todos los patrones de validación."""
    
    # Patrones compilados para mejor rendimiento
    EMAIL_REGEX = re.compile(EMAIL_PATTERN, re.IGNORECASE)
    PHONE_REGEX = re.compile(PHONE_PATTERN)
    URL_REGEX = re.compile(URL_PATTERN)
    
    # Patrones para detección de tipos de datos
    INTEGER_PATTERN = re.compile(r'^-?\d+$')
    FLOAT_PATTERN = re.compile(r'^-?\d+\.?\d*$|^\d*\.?\d+$')
    SCIENTIFIC_PATTERN = re.compile(r'^-?\d+\.?\d*[eE][+-]?\d+$')
    
    # Patrones para fechas comunes
    DATE_PATTERNS = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{2}/\d{2}/\d{4}$',  # DD/MM/YYYY o MM/DD/YYYY
        r'^\d{2}-\d{2}-\d{4}$',  # DD-MM-YYYY
        r'^\d{1,2}/\d{1,2}/\d{4}$',  # D/M/YYYY
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
    ]
    
    # Patrones para caracteres especiales
    SPECIAL_CHARS_PATTERN = re.compile(r'[^\w\s\.\,\-áéíóúñÁÉÍÓÚÑ]')
    WHITESPACE_PATTERN = re.compile(r'^\s+|\s+$')
    
    @staticmethod
    def is_valid_email(value):
        """Valida si una cadena es un email válido."""
        if not isinstance(value, str):
            return False

        email = str(value).strip()
        if ValidationPatterns.EMAIL_REGEX.match(email) is None:
            return False

        try:
            local, domain = email.rsplit('@', 1)
        except ValueError:
            return False

        # Reglas prácticas adicionales que la regex básica no cubre.
        if '..' in local or local.startswith('.') or local.endswith('.'):
            return False
        if '..' in domain or domain.startswith('.') or domain.endswith('.'):
            return False

        return True
    
    @staticmethod
    def is_valid_phone(value):
        """Valida si una cadena es un teléfono válido."""
        if not isinstance(value, str):
            return False
        # Limpia espacios y caracteres comunes
        cleaned = re.sub(r'[\s\(\)\-\+\.]', '', str(value).strip())
        return len(cleaned) >= 7 and cleaned.isdigit()
    
    @staticmethod
    def is_valid_url(value):
        """Valida si una cadena es una URL válida."""
        if not isinstance(value, str):
            return False
        return ValidationPatterns.URL_REGEX.match(str(value).strip()) is not None
    
    @staticmethod
    def is_valid_date_format(value):
        """Verifica si una cadena tiene formato de fecha reconocido y fecha real válida."""
        if not isinstance(value, str):
            return False

        value_str = str(value).strip()
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
            '%Y/%m/%d',
        ]

        for fmt in formats:
            try:
                datetime.strptime(value_str, fmt)
                return True
            except ValueError:
                continue

        return False
    
    @staticmethod
    def has_special_chars(value):
        """Detecta si una cadena contiene caracteres especiales/extraños."""
        if not isinstance(value, str):
            return False
        return ValidationPatterns.SPECIAL_CHARS_PATTERN.search(str(value)) is not None
    
    @staticmethod
    def has_leading_trailing_spaces(value):
        """Detecta espacios al inicio o final."""
        if not isinstance(value, str):
            return False
        return str(value) != str(value).strip()
    
    @staticmethod
    def is_integer(value):
        """Verifica si un valor es un entero válido."""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_float(value):
        """Verifica si un valor es un número flotante válido."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def infer_data_type(value):
        """Infiere el tipo de dato más probable para un valor."""
        if pd.isna(value) or value == '' or value is None:
            return 'Nulo'
        
        value_str = str(value).strip()
        
        # Intenta convertir a número
        if ValidationPatterns.INTEGER_PATTERN.match(value_str):
            return 'Entero'
        
        if ValidationPatterns.FLOAT_PATTERN.match(value_str):
            return 'Flotante'
        
        # Verifica tipos especiales
        if ValidationPatterns.is_valid_email(value_str):
            return 'Email'
        
        if ValidationPatterns.is_valid_phone(value_str):
            return 'Teléfono'
        
        if ValidationPatterns.is_valid_url(value_str):
            return 'URL'
        
        if ValidationPatterns.is_valid_date_format(value_str):
            return 'Fecha'
        
        # Si no es nada especial, es texto
        return 'Texto'


def get_column_type_hints(column_name):
    """
    Retorna sugerencias de tipo de dato basadas en el nombre de la columna.
    
    Args:
        column_name (str): Nombre de la columna
    
    Returns:
        str: Tipo de dato sugerido
    """
    column_lower = column_name.lower()
    
    if any(keyword in column_lower for keyword in DATETIME_KEYWORDS):
        return 'Fecha/Hora'
    if any(keyword in column_lower for keyword in EMAIL_KEYWORDS):
        return 'Email'
    if any(keyword in column_lower for keyword in PHONE_KEYWORDS):
        return 'Teléfono'
    if any(keyword in column_lower for keyword in URL_KEYWORDS):
        return 'URL'
    if (
        column_lower == 'id'
        or column_lower.startswith('id_')
        or column_lower.endswith('_id')
        or any(
            keyword in column_lower
            for keyword in ID_KEYWORDS
            if keyword != 'id'
        )
    ):
        return 'Identificador'
    
    return None

