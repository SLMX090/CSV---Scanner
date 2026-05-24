"""
Módulo de carga de archivos CSV.
Maneja la lectura de archivos CSV con validación de errores comunes.
"""

import pandas as pd
import io
from config import MAX_FILE_SIZE_MB, SUPPORTED_ENCODINGS, COMMON_DELIMITERS


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
        Detecta automáticamente el delimitador del CSV.
        
        Args:
            sample_data (str): Primeras líneas del archivo
            encoding (str): Codificación del archivo
        
        Returns:
            str: Delimitador detectado
        
        Raises:
            CSVLoadError: Si no puede detectar el delimitador
        """
        for delimiter in COMMON_DELIMITERS:
            try:
                df = pd.read_csv(
                    io.StringIO(sample_data),
                    delimiter=delimiter,
                    nrows=5
                )
                # Verifica si tiene al menos 2 columnas
                if len(df.columns) >= 2:
                    return delimiter
            except Exception:
                continue
        
        raise CSVLoadError(
            'No se pudo detectar el delimitador automáticamente. '
            'Intente especificar el delimitador manualmente.'
        )
    
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
        Carga un archivo CSV con manejo de errores.
        
        Args:
            file_object: Objeto de archivo (desde Streamlit)
            delimiter (str): Delimitador (si None, detecta automáticamente)
            encoding (str): Codificación (si None, detecta automáticamente)
        
        Returns:
            pd.DataFrame: DataFrame cargado
        
        Raises:
            CSVLoadError: Si hay errores en la carga
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
            
            # Intenta cargar el CSV
            df = pd.read_csv(
                file_object,
                delimiter=delimiter,
                encoding=encoding,
                on_bad_lines='skip'
            )
            
            # Validaciones post-carga
            if df.empty:
                raise CSVLoadError('El archivo CSV está vacío')
            
            if df.shape[1] == 0:
                raise CSVLoadError('El archivo no tiene columnas')
            
            # Limpia nombres de columnas
            df.columns = CSVLoader.clean_column_names(df.columns)
            
            return df, {
                'delimiter': delimiter,
                'encoding': encoding,
                'rows': df.shape[0],
                'columns': df.shape[1]
            }
        
        except CSVLoadError:
            raise
        except Exception as e:
            raise CSVLoadError(f'Error al cargar el archivo: {str(e)}')
    
    @staticmethod
    def clean_column_names(columns):
        """
        Limpia y valida los nombres de las columnas.
        
        Args:
            columns (Index): Columnas del DataFrame
        
        Returns:
            Index: Columnas limpias
        """
        cleaned = []
        
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
            
            cleaned.append(col_str)
        
        return cleaned
