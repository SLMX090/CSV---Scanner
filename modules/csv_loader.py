"""
Módulo de carga de archivos CSV.
Maneja la lectura de archivos CSV con validación de errores comunes.
Soporta carga de archivos grandes mediante chunks automático.
"""

import pandas as pd
import io
import csv
from config import (
    MAX_FILE_SIZE_MB, SUPPORTED_ENCODINGS, COMMON_DELIMITERS, CSV_LOAD_MODE,
    CHUNKED_LOAD_THRESHOLD_MB, CHUNK_SIZE_ROWS, ENABLE_CHUNKED_LOADING
)


class CSVLoadError(Exception):
    """Excepción personalizada para errores en carga de CSV."""
    pass


class CSVLoader:
    """Clase para cargar y validar archivos CSV."""

    DETECTION_SAMPLE_BYTES = 1024 * 1024

    @staticmethod
    def validate_file(file_size_bytes):
        file_size_mb = file_size_bytes / (1024 ** 2)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise CSVLoadError(
                f'Archivo demasiado grande: {file_size_mb:.2f}MB. '
                f'Límite: {MAX_FILE_SIZE_MB}MB'
            )

    @staticmethod
    def _read_file_content(file_object, encoding=None):
        """Lee contenido de archivo y normaliza a texto + bytes.

        Soporta objetos binarios de Streamlit/BytesIO y objetos de texto StringIO,
        lo cual evita fallos por llamar `.decode()` sobre strings.
        """
        try:
            file_object.seek(0)
        except Exception:
            pass

        raw = file_object.read()
        if isinstance(raw, bytes):
            file_bytes = raw
            if encoding is None:
                encoding = CSVLoader.detect_encoding(file_bytes)
            file_text = file_bytes.decode(encoding, errors='replace')
        elif isinstance(raw, str):
            if encoding is None:
                encoding = 'utf-8'
            file_text = raw
            file_bytes = file_text.encode(encoding, errors='replace')
        else:
            raise CSVLoadError('Tipo de archivo no soportado para lectura CSV')

        try:
            file_object.seek(0)
        except Exception:
            pass

        return file_text, file_bytes, encoding

    @staticmethod
    def _get_file_size(file_object):
        """Obtiene el tamaño sin conservar una posición parcial de lectura."""
        try:
            current_position = file_object.tell()
            file_object.seek(0, 2)
            file_size = file_object.tell()
            file_object.seek(current_position)
            return file_size
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _read_detection_sample(file_object, encoding=None):
        """Lee solo una muestra para detectar codificación y delimitador."""
        try:
            file_object.seek(0)
        except Exception:
            pass

        sample = file_object.read(CSVLoader.DETECTION_SAMPLE_BYTES)
        if isinstance(sample, bytes):
            if encoding is None:
                encoding = CSVLoader.detect_encoding(sample)
            sample_text = sample.decode(encoding, errors='replace')
        elif isinstance(sample, str):
            encoding = encoding or 'utf-8'
            sample_text = sample
        else:
            raise CSVLoadError('Tipo de archivo no soportado para detección CSV')

        try:
            file_object.seek(0)
        except Exception:
            pass

        return sample_text, encoding

    @staticmethod
    def detect_delimiter(sample_data, encoding='utf-8'):
        delimiter_scores = {}
        sample_data = sample_data.lstrip('\ufeff')

        for delimiter in COMMON_DELIMITERS:
            try:
                reader = csv.reader(io.StringIO(sample_data), delimiter=delimiter)
                rows = list(reader)
                if not rows:
                    continue

                column_counts = [len(row) for row in rows if row]
                if not column_counts:
                    continue

                header_cols = column_counts[0]
                col_mode = max(set(column_counts), key=column_counts.count)
                expected_cols = header_cols if header_cols >= 2 else col_mode

                if expected_cols < 2:
                    continue

                consistent_rows = column_counts.count(expected_cols)
                stability = consistent_rows / len(column_counts)
                score = (stability * 100) + expected_cols

                delimiter_scores[delimiter] = {
                    'score': score,
                    'column_count': expected_cols,
                    'stability': stability,
                    'consistent_rows': consistent_rows,
                    'total_rows': len(column_counts)
                }
            except Exception:
                continue

        if not delimiter_scores:
            try:
                detected = csv.Sniffer().sniff(sample_data, delimiters=''.join(COMMON_DELIMITERS))
                if detected.delimiter in COMMON_DELIMITERS:
                    return detected.delimiter
            except csv.Error:
                pass
            raise CSVLoadError(
                'No se pudo detectar el delimitador automáticamente. '
                'Intente especificar el delimitador manualmente.'
            )

        return max(delimiter_scores.items(), key=lambda x: x[1]['score'])[0]

    @staticmethod
    def detect_encoding(file_bytes):
        if isinstance(file_bytes, str):
            return 'utf-8'
        for encoding in SUPPORTED_ENCODINGS:
            try:
                file_bytes.decode(encoding)
                return encoding
            except (UnicodeDecodeError, AttributeError):
                continue
        return 'utf-8'

    @staticmethod
    def _detect_bad_lines(file_text, delimiter):
        bad_lines = []
        reader = csv.reader(io.StringIO(file_text), delimiter=delimiter)
        try:
            header = next(reader)
            expected_columns = len(header)
        except Exception:
            return []

        for line_num, row in enumerate(reader, start=2):
            if expected_columns and len(row) != expected_columns:
                bad_lines.append({
                    'line_number': line_num,
                    'expected_columns': expected_columns,
                    'actual_columns': len(row),
                    'content': str(row)[:100]
                })
        return bad_lines

    @staticmethod
    def iter_csv_chunks(file_object, delimiter=None, encoding=None):
        """Devuelve un iterador de chunks sin cargar el CSV completo."""
        file_size = CSVLoader._get_file_size(file_object)
        if file_size is not None:
            CSVLoader.validate_file(file_size)

        sample_text, detected_encoding = CSVLoader._read_detection_sample(file_object, encoding)
        encoding = encoding or detected_encoding
        delimiter = delimiter or CSVLoader.detect_delimiter(sample_text, encoding)

        try:
            file_object.seek(0)
        except Exception:
            pass

        return pd.read_csv(
            file_object,
            delimiter=delimiter,
            encoding=encoding,
            chunksize=CHUNK_SIZE_ROWS,
            on_bad_lines='skip',
        )

    @staticmethod
    def load_csv_chunked(file_object, delimiter=None, encoding=None, progress_callback=None):
        try:
            file_size = CSVLoader._get_file_size(file_object)
            if file_size is not None:
                CSVLoader.validate_file(file_size)

            if delimiter is None:
                sample_text, detected_encoding = CSVLoader._read_detection_sample(file_object, encoding)
                encoding = encoding or detected_encoding
                delimiter = CSVLoader.detect_delimiter(sample_text, encoding)

            chunks = []
            chunk_index = 0
            chunk_iterator = CSVLoader.iter_csv_chunks(
                file_object,
                delimiter=delimiter,
                encoding=encoding,
            )
            for chunk in chunk_iterator:
                if not chunk.empty:
                    chunks.append(chunk)
                    chunk_index += 1
                    if progress_callback:
                        progress_callback(chunk_index, None)

            if not chunks:
                raise CSVLoadError('El archivo CSV está vacío después de procesar')

            df = pd.concat(chunks, ignore_index=True)
            df.columns = CSVLoader.clean_column_names(df.columns)

            return df, {
                'delimiter': delimiter,
                'encoding': encoding,
                'rows': df.shape[0],
                'columns': df.shape[1],
                'bad_lines_count': 0,
                'bad_lines_sample': [],
                'load_mode': CSV_LOAD_MODE,
                'chunked': True,
                'chunks_loaded': chunk_index
            }
        except CSVLoadError:
            raise
        except Exception as e:
            raise CSVLoadError(f'Error al cargar archivo por chunks: {str(e)}')

    @staticmethod
    def load_excel(file_object, file_name=None, sheet_name=0):
        """Carga un archivo Excel (.xls/.xlsx)."""
        try:
            file_name = (file_name or getattr(file_object, 'name', '')).lower()
            try:
                file_object.seek(0)
            except Exception:
                pass

            if file_name.endswith('.xls'):
                engine = 'xlrd'
            else:
                engine = 'openpyxl'

            df = pd.read_excel(file_object, sheet_name=sheet_name, engine=engine)
            if df.empty:
                raise CSVLoadError('El archivo Excel está vacío después de procesar')
            if df.shape[1] == 0:
                raise CSVLoadError('El archivo Excel no tiene columnas')

            df.columns = CSVLoader.clean_column_names(df.columns)

            return df, {
                'source_type': 'excel',
                'file_name': file_name,
                'sheet_name': sheet_name,
                'rows': df.shape[0],
                'columns': df.shape[1],
                'delimiter': None,
                'encoding': 'excel',
                'load_mode': 'excel',
                'bad_lines_count': 0,
                'bad_lines_sample': []
            }
        except Exception as e:
            raise CSVLoadError(f'Error al cargar el archivo Excel: {str(e)}')

    @staticmethod
    def list_excel_sheets(file_object, file_name=None):
        """Devuelve los nombres de hojas disponibles sin cargar sus datos."""
        try:
            file_name = (file_name or getattr(file_object, 'name', '')).lower()
            engine = 'xlrd' if file_name.endswith('.xls') else 'openpyxl'
            try:
                file_object.seek(0)
            except Exception:
                pass
            with pd.ExcelFile(file_object, engine=engine) as workbook:
                return list(workbook.sheet_names)
        except Exception as e:
            raise CSVLoadError(f'Error al leer las hojas del archivo Excel: {str(e)}')
        finally:
            try:
                file_object.seek(0)
            except Exception:
                pass

    @staticmethod
    def load_file(file_object, file_name=None, delimiter=None, encoding=None, sheet_name=0):
        """Carga un archivo CSV o Excel según la extensión."""
        if file_object is None:
            raise CSVLoadError('No se proporcionó ningún archivo')

        file_name = (file_name or getattr(file_object, 'name', '') or '').lower()
        if file_name.endswith('.csv') or not file_name:
            return CSVLoader.load_csv(file_object, delimiter=delimiter, encoding=encoding)
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            return CSVLoader.load_excel(file_object, file_name=file_name, sheet_name=sheet_name)
        raise CSVLoadError(f'Formato no soportado: {file_name or "desconocido"}')

    @staticmethod
    def load_csv(file_object, delimiter=None, encoding=None):
        try:
            file_size = CSVLoader._get_file_size(file_object)
            if file_size is None:
                file_text, file_bytes, encoding = CSVLoader._read_file_content(file_object, encoding)
                file_size = len(file_bytes)
            else:
                CSVLoader.validate_file(file_size)
                sample_text, detected_encoding = CSVLoader._read_detection_sample(file_object, encoding)
                encoding = encoding or detected_encoding
                delimiter = delimiter or CSVLoader.detect_delimiter(sample_text, encoding)

            file_size_mb = file_size / (1024 ** 2)
            use_chunked = ENABLE_CHUNKED_LOADING and file_size_mb > CHUNKED_LOAD_THRESHOLD_MB
            if use_chunked:
                return CSVLoader.load_csv_chunked(file_object, delimiter=delimiter, encoding=encoding)

            if 'file_text' not in locals():
                file_text, file_bytes, encoding = CSVLoader._read_file_content(file_object, encoding)

            if delimiter is None:
                delimiter = CSVLoader.detect_delimiter(file_text[:CSVLoader.DETECTION_SAMPLE_BYTES], encoding)

            bad_lines = CSVLoader._detect_bad_lines(file_text, delimiter)

            if CSV_LOAD_MODE == 'strict' and bad_lines:
                raise CSVLoadError(
                    f'Modo ESTRICTO: Se detectaron {len(bad_lines)} líneas mal formadas. '
                    f'Primera línea problemática: {bad_lines[0]}'
                )

            df = pd.read_csv(
                io.StringIO(file_text),
                delimiter=delimiter,
                on_bad_lines='skip'
            )

            if df.empty:
                raise CSVLoadError('El archivo CSV está vacío después de procesar')
            if df.shape[1] == 0:
                raise CSVLoadError('El archivo no tiene columnas')

            df.columns = CSVLoader.clean_column_names(df.columns)

            return df, {
                'delimiter': delimiter,
                'encoding': encoding,
                'rows': df.shape[0],
                'columns': df.shape[1],
                'bad_lines_count': len(bad_lines),
                'bad_lines_sample': bad_lines[:5],
                'load_mode': CSV_LOAD_MODE
            }
        except CSVLoadError:
            raise
        except Exception as e:
            raise CSVLoadError(f'Error al cargar el archivo: {str(e)}')

    @staticmethod
    def clean_column_names(columns):
        cleaned = []
        name_counts = {}

        for col in columns:
            col_str = str(col).strip()
            if not col_str or col_str == 'Unnamed: ' or 'Unnamed' in col_str:
                col_str = f'Column_{len(cleaned) + 1}'

            col_str = col_str.replace(' ', '_')
            col_str = ''.join(c if c.isalnum() or c == '_' else '' for c in col_str)

            if col_str and col_str[0].isdigit():
                col_str = '_' + col_str
            if not col_str:
                col_str = f'Column_{len(cleaned) + 1}'

            original_name = col_str
            count = name_counts.get(original_name, 0)
            if count > 0:
                col_str = f'{original_name}_{count + 1}'
            name_counts[original_name] = count + 1
            cleaned.append(col_str)

        return cleaned
