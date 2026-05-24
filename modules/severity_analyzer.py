"""
Módulo de análisis de severidad.
Centraliza la lógica para calcular y clasificar problemas por severidad.
"""

from config import NULL_THRESHOLD_PERCENT


class SeverityAnalyzer:
    """Analiza y clasifica problemas por nivel de severidad."""
    
    CRITICAL_THRESHOLD_NULL = 80  # % de nulos para criticidad
    SEVERE_THRESHOLD_NULL = NULL_THRESHOLD_PERCENT  # % de nulos para gravedad
    
    @staticmethod
    def analyze_severity(profile, validation_results):
        """
        Analiza todos los problemas y los clasifica por severidad.
        
        Args:
            profile (dict): Perfil del DataFrame
            validation_results (dict): Resultados de validaciones
        
        Returns:
            dict: Problemas clasificados por severidad
                {
                    'critical': [...],
                    'severe': [...],
                    'warnings': [...]
                }
        """
        issues = {
            'critical': [],
            'severe': [],
            'warnings': []
        }
        
        # Análisis de nulos
        issues = SeverityAnalyzer._analyze_null_issues(profile, issues)
        
        # Análisis de duplicados
        issues = SeverityAnalyzer._analyze_duplicate_issues(profile, issues)
        
        # Análisis de tipos de datos
        issues = SeverityAnalyzer._analyze_type_issues(profile, issues)
        
        # Análisis de validaciones
        issues = SeverityAnalyzer._analyze_validation_issues(
            validation_results, issues
        )
        
        # Análisis de cadenas vacías
        issues = SeverityAnalyzer._analyze_empty_string_issues(profile, issues)
        
        return issues
    
    @staticmethod
    def _analyze_null_issues(profile, issues):
        """Analiza columnas con valores nulos problemáticos."""
        for col, info in profile['null_analysis']['problematic_columns'].items():
            null_percent = info['null_percent']
            
            if null_percent >= SeverityAnalyzer.CRITICAL_THRESHOLD_NULL:
                issues['critical'].append({
                    'type': 'NULOS_CRÍTICOS',
                    'column': col,
                    'description': f'{col}: {null_percent:.1f}% nulos',
                    'severity_score': 10
                })
            elif null_percent >= SeverityAnalyzer.SEVERE_THRESHOLD_NULL:
                issues['severe'].append({
                    'type': 'NULOS_GRAVES',
                    'column': col,
                    'description': f'{col}: {null_percent:.1f}% nulos',
                    'severity_score': 7
                })
        
        return issues
    
    @staticmethod
    def _analyze_duplicate_issues(profile, issues):
        """Analiza filas duplicadas."""
        if profile['duplicates']['total_duplicates'] > 0:
            dup_percent = profile['duplicates']['duplicates_percent']
            
            if dup_percent > 20:
                severity = 'critical'
                score = 8
            elif dup_percent > 5:
                severity = 'severe'
                score = 6
            else:
                severity = 'warnings'
                score = 3
            
            issues[severity].append({
                'type': 'DUPLICADOS',
                'column': 'FILAS_COMPLETAS',
                'description': f'{profile["duplicates"]["total_duplicates"]} filas duplicadas ({dup_percent:.1f}%)',
                'severity_score': score
            })
        
        return issues
    
    @staticmethod
    def _analyze_type_issues(profile, issues):
        """Analiza columnas con mezcla de tipos de datos."""
        for col, issues_data in profile['data_type_issues'].items():
            if issues_data['is_problematic']:
                issues['severe'].append({
                    'type': 'TIPOS_MIXTOS',
                    'column': col,
                    'description': f'{col}: múltiples tipos de datos',
                    'severity_score': 6
                })
            else:
                issues['warnings'].append({
                    'type': 'TIPOS_MIXTOS',
                    'column': col,
                    'description': f'{col}: tipos de datos mixtos (no crítico)',
                    'severity_score': 2
                })
        
        return issues
    
    @staticmethod
    def _analyze_validation_issues(validation_results, issues):
        """Analiza problemas detectados en validaciones."""
        # Email
        for col, info in validation_results.get('email_validation', {}).items():
            if info['is_problematic'] and info['invalid_percent'] > 30:
                issues['severe'].append({
                    'type': 'EMAILS_INVÁLIDOS',
                    'column': col,
                    'description': f'{col}: {info["invalid_count"]} emails inválidos ({info["invalid_percent"]:.1f}%)',
                    'severity_score': 5
                })
            elif info['is_problematic']:
                issues['warnings'].append({
                    'type': 'EMAILS_INVÁLIDOS',
                    'column': col,
                    'description': f'{col}: {info["invalid_count"]} emails inválidos ({info["invalid_percent"]:.1f}%)',
                    'severity_score': 2
                })
        
        # Teléfono
        for col, info in validation_results.get('phone_validation', {}).items():
            if info['is_problematic'] and info['invalid_percent'] > 30:
                issues['severe'].append({
                    'type': 'TELÉFONOS_INVÁLIDOS',
                    'column': col,
                    'description': f'{col}: {info["invalid_count"]} teléfonos inválidos ({info["invalid_percent"]:.1f}%)',
                    'severity_score': 5
                })
            elif info['is_problematic']:
                issues['warnings'].append({
                    'type': 'TELÉFONOS_INVÁLIDOS',
                    'column': col,
                    'description': f'{col}: {info["invalid_count"]} teléfonos inválidos ({info["invalid_percent"]:.1f}%)',
                    'severity_score': 2
                })
        
        # Fechas
        for col, info in validation_results.get('date_validation', {}).items():
            if info['is_problematic'] and info['invalid_percent'] > 20:
                issues['severe'].append({
                    'type': 'FECHAS_INVÁLIDAS',
                    'column': col,
                    'description': f'{col}: {info["invalid_count"]} fechas inválidas ({info["invalid_percent"]:.1f}%)',
                    'severity_score': 7
                })
            elif info['is_problematic']:
                issues['warnings'].append({
                    'type': 'FECHAS_INVÁLIDAS',
                    'column': col,
                    'description': f'{col}: inconsistencias de formato detectadas',
                    'severity_score': 2
                })
        
        # URLs
        for col, info in validation_results.get('url_validation', {}).items():
            if info['is_problematic']:
                issues['warnings'].append({
                    'type': 'URLS_INVÁLIDAS',
                    'column': col,
                    'description': f'{col}: {info["invalid_count"]} URLs inválidas',
                    'severity_score': 2
                })
        
        return issues
    
    @staticmethod
    def _analyze_empty_string_issues(profile, issues):
        """Analiza columnas con cadenas vacías."""
        for col, info in profile['empty_strings']['columns_with_empty'].items():
            if info['percent'] > 30:
                issues['severe'].append({
                    'type': 'CADENAS_VACÍAS',
                    'column': col,
                    'description': f'{col}: {info["count"]} cadenas vacías ({info["percent"]:.1f}%)',
                    'severity_score': 5
                })
            else:
                issues['warnings'].append({
                    'type': 'CADENAS_VACÍAS',
                    'column': col,
                    'description': f'{col}: {info["count"]} cadenas vacías ({info["percent"]:.1f}%)',
                    'severity_score': 2
                })
        
        return issues
    
    @staticmethod
    def get_severity_counts(issues_by_severity):
        """
        Obtiene el conteo de problemas por severidad.
        
        Args:
            issues_by_severity (dict): Problemas clasificados
        
        Returns:
            dict: Conteos por severidad
        """
        return {
            'critical': len(issues_by_severity.get('critical', [])),
            'severe': len(issues_by_severity.get('severe', [])),
            'warnings': len(issues_by_severity.get('warnings', []))
        }
