"""
Módulo de carga de archivos CSV.
Maneja la lectura de archivos CSV con validación de errores comunes.
"""

import pandas as pd
import io
import csv
from config import MAX_FILE_SIZE_MB, SUPPORTED_ENCODINGS, COMMON_DELIMITERS, CSV_LOAD_MODE


class CSVLoadError(Exception):
    """Excepción personalizada para errores en carga de CSV."""
    pass


class CSVLoader:
    """Clase para cargar y validar archivos CSV."""
    
    @staticmethod
    def validate_file(file_size_bytes):
        """
        Valida el tamaño del archivo.
        
        Args:
            file_size_bytes (int): Tamaño del archivo en bytes
        
        Raises:
            CSVLoadError: Si el archivo es demasiado grande
        """
        file_size_mb = file_size_bytes / (1024 ** 2)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise CSVLoadError(
                f'Archivo demasiado grande: {file_size_mb:.2f}MB. '
                f'Límite: {MAX_FILE_SIZE_MB}MB'
            )
    
    @staticmethod
    def detect_delimiter(sample_data, encoding='utf-8'):
        """
        Detecta automáticamente el delimitador del CSV con heurística robusta.
        
        Evalúa varios delimitadores y elige el que produce:
        1. Al menos 2 columnas
        2. La estructura más estable (todas las filas con consistencia)
        3. El mayor número de columnas consistentes
        
        Args:
            sample_data (str): Primeras líneas del archivo
            encoding (str): Codificación del archivo
        
        Returns:
            str: Delimitador detectado
        
        Raises:
            CSVLoadError: Si no puede detectar el delimitador
        """
        delimiter_scores = {}
        
        for delimiter in COMMON_DELIMITERS:
            try:
                # Lee muestra pequeña con este delimitador
                reader = csv.reader(
                    sample_data.strip().split('\n'),
                    delimiter=delimiter
                )
                rows = list(reader)
                
                if not rows:
                    continue
                
                # Cuenta columnas por fila
                column_counts = [len(row) for row in rows]
                
                if len(set(column_counts)) == 0:
                    continue
                
                # Calcula estabilidad (cuántas filas tienen el mismo número de columnas)
                col_mode = max(set(column_counts), key=column_counts.count)
                consistent_rows = column_counts.count(col_mode)
                stability = consistent_rows / len(column_counts) if column_counts else 0
                
                # Solo considera delimitadores que produzcan al menos 2 columnas
                if col_mode < 2:
                    continue
                
                # Calcula puntuación: estabilidad + número de columnas
                # Prioriza estabilidad pero también valoriza más columnas
                score = (stability * 100) + col_mode
                
                delimiter_scores[delimiter] = {
                    'score': score,
                    'column_count': col_mode,
                    'stability': stability,
                    'consistent_rows': consistent_rows,
                    'total_rows': len(column_counts)
                }
                
            except Exception:
                continue
        
        if not delimiter_scores:
            raise CSVLoadError(
                'No se pudo detectar el delimitador automáticamente. '
                'Intente especificar el delimitador manualmente.'
            )
        
        # Elige el delimitador con mejor puntuación
        best_delimiter = max(
            delimiter_scores.items(),
            key=lambda x: x[1]['score']
        )[0]
        
        return best_delimiter
    
    @staticmethod
    def detect_encoding(file_bytes):
        """
        Detecta automáticamente la codificación del archivo.
        
        Args:
            file_bytes (bytes): Contenido del archivo
        
        Returns:
            str: Codificación detectada
        """
        for encoding in SUPPORTED_ENCODINGS:
            try:
                file_bytes.decode(encoding)
                return encoding
            except (UnicodeDecodeError, AttributeError):
                continue
        
        return 'utf-8'  # Por defecto
    
    @staticmethod
    def load_csv(file_object, delimiter=None, encoding=None):
        """
        Carga un archivo CSV con manejo de errores y captura de líneas problemáticas.
        
        Args:
            file_object: Objeto de archivo (desde Streamlit)
            delimiter (str): Delimitador (si None, detecta automáticamente)
            encoding (str): Codificación (si None, detecta automáticamente)
        
        Returns:
            tuple: (pd.DataFrame, dict con información de carga)
            El dict incluye:
            - delimiter: delimitador usado
            - encoding: codificación usada
            - rows: número de filas cargadas
            - columns: número de columnas
            - bad_lines_count: número de líneas omitidas
            - bad_lines_sample: ejemplos de líneas problemáticas (máx 5)
        
        Raises:
            CSVLoadError: Si hay errores críticos en la carga
        """
        try:
            # Valida tamaño del archivo
            file_bytes = file_object.read()
            CSVLoader.validate_file(len(file_bytes))
            file_object.seek(0)
            
            # Detecta codificación
            if encoding is None:
                encoding = CSVLoader.detect_encoding(file_bytes)
            
            # Detecta delimitador
            if delimiter is None:
                sample = file_bytes.decode(encoding).split('\n')[:5]
                sample_text = '\n'.join(sample)
                delimiter = CSVLoader.detect_delimiter(sample_text, encoding)
            
            # Recarga el archivo
            file_object.seek(0)
            
            # Captura líneas problemáticas
            bad_lines = []
            line_number = 0
            
            # Primera pasada: identifica líneas problemáticas
            file_object.seek(0)
            file_content = file_object.read().decode(encoding)
            file_object.seek(0)
            
            reader = csv.reader(
                io.StringIO(file_content),
                delimiter=delimiter
            )
            
            # Obtiene número de columnas esperado del encabezado
            try:
                header = next(reader)
                expected_columns = len(header)
            except Exception:
                expected_columns = None
            
            # Verifica cada fila
            for line_num, row in enumerate(reader, start=2):  # +2: encabezado en 1
                if expected_columns and len(row) != expected_columns:
                    bad_lines.append({
                        'line_number': line_num,
                        'expected_columns': expected_columns,
                        'actual_columns': len(row),
                        'content': str(row)[:100]
                    })
            
            # Si está en modo estricto y hay líneas malas, levanta excepción
            if CSV_LOAD_MODE == 'strict' and bad_lines:
                raise CSVLoadError(
                    f'Modo ESTRICTO: Se detectaron {len(bad_lines)} líneas mal formadas. '
                    f'Primera línea problemática: {bad_lines[0]}'
                )
            
            # Carga el CSV con on_bad_lines='skip' pero ahora sabemos cuáles se omitirán
            file_object.seek(0)
            df = pd.read_csv(
                file_object,
                delimiter=delimiter,
                encoding=encoding,
                on_bad_lines='skip'
            )
            
            # Validaciones post-carga
            if df.empty:
                raise CSVLoadError('El archivo CSV está vacío después de procesar')
            
            if df.shape[1] == 0:
                raise CSVLoadError('El archivo no tiene columnas')
            
            # Limpia nombres de columnas
            df.columns = CSVLoader.clean_column_names(df.columns)
            
            return df, {
                'delimiter': delimiter,
                'encoding': encoding,
                'rows': df.shape[0],
                'columns': df.shape[1],
                'bad_lines_count': len(bad_lines),
                'bad_lines_sample': bad_lines[:5],  # Máximo 5 ejemplos
                'load_mode': CSV_LOAD_MODE
            }
        
        except CSVLoadError:
            raise
        except Exception as e:
            raise CSVLoadError(f'Error al cargar el archivo: {str(e)}')

    
    @staticmethod
    def clean_column_names(columns):
        """
        Limpia y valida los nombres de las columnas, garantizando unicidad.
        
        Args:
            columns (Index): Columnas del DataFrame
        
        Returns:
            list: Columnas limpias y únicas
        """
        cleaned = []
        name_counts = {}  # Rastrear nombres duplicados
        
        for col in columns:
            # Convierte a string
            col_str = str(col).strip()
            
            # Si está vacío, le asigna un nombre por defecto
            if not col_str or col_str == 'Unnamed: ' or 'Unnamed' in col_str:
                col_str = f'Column_{len(cleaned) + 1}'
            
            # Reemplaza espacios con guiones bajos
            col_str = col_str.replace(' ', '_')
            
            # Elimina caracteres especiales
            col_str = ''.join(c if c.isalnum() or c == '_' else '' for c in col_str)
            
            # Asegura que el nombre sea válido (no comience con número)
            if col_str and col_str[0].isdigit():
                col_str = '_' + col_str
            
            # Si está vacío después de limpiar, usa nombre genérico
            if not col_str:
                col_str = f'Column_{len(cleaned) + 1}'
            
            # Maneja duplicados
            original_name = col_str
            count = name_counts.get(original_name, 0)
            
            if count > 0:
                # Si es un duplicado, añade sufijo
                col_str = f'{original_name}_{count + 1}'
            
            name_counts[original_name] = count + 1
            cleaned.append(col_str)
        
        return cleaned
