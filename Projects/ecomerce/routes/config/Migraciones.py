# migraciones.py

# Imports de bibliotecas estándar
import asyncio
import concurrent.futures
import io
import json
import logging
import multiprocessing
import os
import re
from datetime import datetime, timedelta
from io import BytesIO

# Imports de terceros
import pandas as pd
import psutil  # Para monitorear memoria
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

# Imports del proyecto
# from Services.Analisis.analisis import clean_data
# from Services.migracion.migracion import procesar_archivo

# Funciones stub temporales
def clean_data(data):
    """Función temporal stub para clean_data"""
    return data

def procesar_archivo(json_path, result_path, db, current_user, table_name):
    """
    Procesa un archivo JSON y crea una tabla dinámica en la base de datos con los datos migrados.
    Incluye inferencia de tipos de datos, creación de tabla, inserción por lotes y metadata.
    """
    start_time = datetime.now()
    total_records = 0
    error_message = None

    try:
        logging.info(f"Iniciando procesamiento de archivo JSON: {json_path}")

        # Leer el archivo JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data:
            raise ValueError("El archivo JSON está vacío")

        total_records = len(data)
        logging.info(f"Archivo JSON contiene {total_records} registros")

        # Tomar una muestra para inferir tipos de datos
        sample_size = min(1000, len(data))  # Máximo 1000 registros para inferencia
        sample_data = data[:sample_size]

        # Inferir tipos de datos y crear esquema de tabla
        column_types = infer_column_types(sample_data)
        logging.info(f"Tipos de columnas inferidos: {column_types}")

        # Crear la tabla dinámica
        create_dynamic_table(db, table_name, column_types)

        # Validar esquema de la tabla creada
        validation_result = validate_table_schema(table_name, column_types, db)

        # Registrar resultados de validación
        if not validation_result["valid"]:
            logging.error(f"Errores de validación en tabla {table_name}: {validation_result['errors']}")
            # No fallar el proceso por errores de validación, solo registrar
        elif validation_result["warnings"]:
            logging.warning(f"Advertencias de validación en tabla {table_name}: {len(validation_result['warnings'])} advertencias")

        # Insertar datos por lotes
        batch_size = 1000
        inserted_count = 0

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            # Convertir tipos de datos según el esquema inferido
            converted_batch = convert_data_types(batch, column_types)
            # Insertar lote
            insert_batch(db, table_name, converted_batch, column_types)
            inserted_count += len(converted_batch)
            logging.info(f"Insertados {inserted_count}/{total_records} registros")

        # Crear metadata de la migración
        processing_time = (datetime.now() - start_time).total_seconds()

        metadata = MigracionMetadata(
            usuario_id=current_user.codigo,
            nombre_tabla=table_name,
            nombre_original_archivo=None,  # Se puede agregar después si es necesario
            tipo_archivo="json",
            total_registros=total_records,
            estado="completado",
            fecha_creacion=datetime.now(),
            tiempo_procesamiento_segundos=processing_time,
            mensaje_error=None,
            tamanio_bytes=os.path.getsize(json_path) if os.path.exists(json_path) else 0,
            validacion_errores=validation_result.get("errors", []),
            validacion_advertencias=validation_result.get("warnings", []),
            validacion_resumen=validation_result.get("summary", {})
        )

        db.add(metadata)
        db.commit()

        # Crear archivo de resultado
        result_data = {
            "status": "success",
            "table_name": table_name,
            "total_records": total_records,
            "processing_time_seconds": processing_time,
            "column_types": column_types,
            "timestamp": datetime.now().isoformat()
        }

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        logging.info(f"Procesamiento completado exitosamente: {table_name} con {total_records} registros")

    except Exception as e:
        error_message = str(e)
        logging.error(f"Error procesando archivo JSON: {error_message}")

        # Actualizar metadata con error si ya existe
        try:
            processing_time = (datetime.now() - start_time).total_seconds()
            metadata = MigracionMetadata(
                usuario_id=current_user.codigo,
                nombre_tabla=table_name,
                tipo_archivo="json",
                total_registros=total_records,
                estado="error",
                fecha_creacion=datetime.now(),
                tiempo_procesamiento_segundos=processing_time,
                mensaje_error=error_message,
                tamanio_bytes=os.path.getsize(json_path) if os.path.exists(json_path) else 0
            )
            db.add(metadata)
            db.commit()
        except Exception as meta_error:
            logging.error(f"Error guardando metadata de error: {meta_error}")
            db.rollback()

        # Crear archivo de resultado con error
        result_data = {
            "status": "error",
            "error": error_message,
            "table_name": table_name,
            "total_records": total_records,
            "timestamp": datetime.now().isoformat()
        }

        try:
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
        except Exception as file_error:
            logging.error(f"Error creando archivo de resultado: {file_error}")

        raise  # Re-lanzar la excepción para que sea manejada por el llamador

def infer_column_types(sample_data):
    """
    Infiera los tipos de datos de las columnas basándose en una muestra de datos.
    """
    if not sample_data:
        return {}

    column_types = {}

    # Obtener todas las claves posibles
    all_keys = set()
    for record in sample_data:
        if isinstance(record, dict):
            all_keys.update(record.keys())

    for key in all_keys:
        values = []
        for record in sample_data:
            if isinstance(record, dict) and key in record:
                value = record[key]
                if value is not None and value != "":
                    values.append(value)

        if not values:
            column_types[key] = "NVARCHAR(255)"  # Default para columnas vacías
            continue

        # Inferir tipo basado en los valores
        inferred_type = infer_single_column_type(values)
        column_types[key] = inferred_type

    return column_types

def infer_single_column_type(values):
    """
    Infiera el tipo de una sola columna basándose en sus valores.
    Estrategia mejorada para manejar tipos mixtos y rangos numéricos.
    """
    # Contadores para diferentes tipos
    int_count = 0
    bigint_count = 0
    float_count = 0
    date_count = 0
    bool_count = 0
    string_count = 0
    null_count = 0

    # Rangos para tipos numéricos en SQL Server
    INT_MIN = -2147483648
    INT_MAX = 2147483647
    BIGINT_MIN = -9223372036854775808
    BIGINT_MAX = 9223372036854775807

    # Analizar valores no nulos
    non_null_values = []
    for value in values[:500]:  # Aumentar la muestra para mejor precisión
        if value is None or value == "":
            null_count += 1
            continue
        non_null_values.append(value)

        if isinstance(value, bool):
            bool_count += 1
        elif isinstance(value, int):
            # Verificar si cabe en INT o necesita BIGINT
            if INT_MIN <= value <= INT_MAX:
                int_count += 1
            elif BIGINT_MIN <= value <= BIGINT_MAX:
                bigint_count += 1
            else:
                # Valor demasiado grande incluso para BIGINT - usar NVARCHAR
                string_count += 1
        elif isinstance(value, float):
            float_count += 1
        elif isinstance(value, str):
            # Intentar convertir a fecha
            if is_date_string(value):
                date_count += 1
            else:
                string_count += 1
        else:
            string_count += 1

    total_non_null = len(non_null_values)

    if total_non_null == 0:
        return "NVARCHAR(255)"  # Default para columnas vacías

    # Lógica de decisión mejorada con manejo de rangos y tipos mixtos
    if bool_count == total_non_null:
        return "BIT"
    elif date_count == total_non_null:
        return "DATETIME"
    elif int_count == total_non_null:
        return "INT"
    elif bigint_count == total_non_null:
        return "BIGINT"
    elif (int_count + bigint_count) == total_non_null:
        # Si hay mezcla de INT y BIGINT, usar BIGINT para ser seguro
        return "BIGINT"
    elif float_count == total_non_null or (int_count + float_count + bigint_count) == total_non_null:
        return "FLOAT"
    elif bool_count > total_non_null * 0.9:
        return "BIT"  # Mayoría clara de booleanos
    elif date_count > total_non_null * 0.9:
        return "DATETIME"  # Mayoría clara de fechas
    elif (int_count + bigint_count) > total_non_null * 0.9:
        # Mayoría de números enteros - usar BIGINT si hay algún valor grande
        if bigint_count > 0:
            return "BIGINT"
        else:
            return "INT"
    elif (int_count + float_count + bigint_count) > total_non_null * 0.9:
        return "FLOAT"  # Mayoría clara de números
    else:
        # Tipos mixtos - determinar el mejor tipo contenedor
        # IMPORTANTE: Si hay mezcla de números y texto, usar NVARCHAR
        has_numbers = (int_count + float_count + bigint_count) > 0
        has_dates = date_count > 0
        has_strings = string_count > 0
        has_bools = bool_count > 0

        # Calcular longitud máxima para strings ANTES de usarla
        max_length = 50  # Mínimo
        has_very_long_text = False
        for value in non_null_values:
            if isinstance(value, str):
                value_len = len(value)
                max_length = max(max_length, value_len)
                if value_len > 500:  # Si hay texto muy largo, usar MAX
                    has_very_long_text = True
            elif has_numbers or has_bools:
                # Convertir otros tipos a string para medir longitud
                max_length = max(max_length, len(str(value)))

        # Si hay números Y texto (datos mixtos), usar NVARCHAR
        if has_numbers and has_strings:
            # Usar NVARCHAR(MAX) para textos muy largos o tipos mixtos complejos
            if max_length > 1000 or has_very_long_text:
                return "NVARCHAR(MAX)"
            else:
                # Limitar a 4000 caracteres para NVARCHAR normal
                max_length = min(max_length, 4000)
                return f"NVARCHAR({max_length})"

        # Otros casos de tipos mixtos
        if has_dates and (has_strings or has_numbers):
            # Fechas mezcladas con otros tipos - usar NVARCHAR largo
            max_length = max(max_length, 25)  # Fechas necesitan al menos 25 caracteres
        elif has_bools and (has_strings or has_numbers):
            # Booleanos con otros tipos - usar NVARCHAR
            pass
        elif (int_count + bigint_count) > 0 and float_count > 0 and not has_strings and not has_dates:
            # Solo números mixtos (int/bigint y float) - usar FLOAT
            return "FLOAT"
        elif (int_count + bigint_count) > 0 and not has_strings and not has_dates and not has_bools:
            # Solo números enteros - usar BIGINT si hay algún valor grande
            if bigint_count > 0:
                return "BIGINT"
            else:
                return "INT"

        # Usar NVARCHAR(MAX) para textos muy largos o tipos mixtos complejos
        if max_length > 1000 or has_very_long_text or (has_dates and (has_strings or has_numbers)):
            return "NVARCHAR(MAX)"
        else:
            # Limitar a 4000 caracteres para NVARCHAR normal
            max_length = min(max_length, 4000)
            return f"NVARCHAR({max_length})"

def is_date_string(value):
    """
    Verifica si una cadena representa una fecha.
    """
    if not isinstance(value, str):
        return False

    # Patrones comunes de fecha
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{2}-\d{2}-\d{4}$',  # DD-MM-YYYY
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
        r'^\d{2}/\d{2}/\d{4}$',  # DD/MM/YYYY
        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',  # YYYY-MM-DD HH:MM:SS
    ]

    import re
    for pattern in date_patterns:
        if re.match(pattern, value):
            return True

    # Intentar parsear con pandas
    try:
        pd.to_datetime(value, errors='raise')
        return True
    except:
        return False

def sanitize_column_name(col_name):
    """
    Sanitiza un nombre de columna para que sea compatible con SQL Server.
    Reemplaza espacios, guiones y caracteres especiales con guiones bajos.
    """
    if not col_name:
        return col_name
    # Reemplazar espacios y guiones con guiones bajos
    safe_col = col_name.replace(' ', '_').replace('-', '_')
    # Reemplazar cualquier caracter que no sea alfanumérico o guion bajo con guion bajo
    safe_col = re.sub(r'[^\w]', '_', safe_col)
    return safe_col

def types_compatible(expected_type, actual_type):
    """
    Verifica si dos tipos de datos son compatibles.
    Maneja las diferencias entre tipos esperados (nuestra lógica) y tipos reales (SQL Server).
    """
    # Normalizar tipos para comparación
    expected_lower = expected_type.upper()
    actual_lower = actual_type.upper()

    # Mapeos de compatibilidad
    type_mappings = {
        'NVARCHAR': ['NVARCHAR', 'VARCHAR', 'TEXT', 'NTEXT'],
        'VARCHAR': ['NVARCHAR', 'VARCHAR', 'TEXT', 'NTEXT'],
        'INT': ['INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT'],
        'BIGINT': ['BIGINT', 'INT', 'INTEGER'],
        'FLOAT': ['FLOAT', 'REAL', 'DOUBLE', 'DECIMAL', 'NUMERIC'],
        'BIT': ['BIT', 'TINYINT'],
        'DATETIME': ['DATETIME', 'DATETIME2', 'SMALLDATETIME', 'DATE', 'TIME'],
        'DATE': ['DATETIME', 'DATETIME2', 'SMALLDATETIME', 'DATE']
    }

    # Verificar compatibilidad directa
    if expected_lower == actual_lower:
        return True

    # Verificar compatibilidad por familia de tipos
    for base_type, compatible_types in type_mappings.items():
        if expected_lower.startswith(base_type) and actual_lower in compatible_types:
            return True
        if actual_lower.startswith(base_type) and expected_lower in compatible_types:
            return True

    # Manejo especial para NVARCHAR con longitud
    if expected_lower.startswith('NVARCHAR(') and actual_lower.startswith('NVARCHAR('):
        # Extraer longitudes
        try:
            expected_part = expected_lower.split('(')[1].rstrip(')')
            actual_part = actual_lower.split('(')[1].rstrip(')')

            # NVARCHAR(MAX) es compatible con cualquier longitud
            if actual_part.upper() == 'MAX' or expected_part.upper() == 'MAX':
                return True

            # Ambos son longitudes numéricas
            expected_len = int(expected_part)
            actual_len = int(actual_part)
            # Verificar que la longitud real sea al menos la esperada
            return actual_len >= expected_len
        except (ValueError, IndexError):
            pass

    # NVARCHAR(MAX) es compatible con cualquier NVARCHAR
    if (expected_lower == 'NVARCHAR(MAX)' and actual_lower.startswith('NVARCHAR(')) or \
       (actual_lower == 'NVARCHAR(MAX)' and expected_lower.startswith('NVARCHAR(')):
        return True

    return False

def validate_table_schema(table_name, expected_types, db):
    """
    Valida que el esquema de la tabla creada coincida con los tipos esperados.
    Registra advertencias si hay discrepancias entre tipos esperados y reales.
    """
    try:
        logging.info(f"Validando esquema de tabla: {table_name}")

        # Inspeccionar la tabla creada
        inspector = inspect(db.get_bind())

        # Verificar que la tabla existe
        if table_name not in inspector.get_table_names():
            error_msg = f"La tabla '{table_name}' no fue encontrada después de la creación"
            logging.error(error_msg)
            return {"valid": False, "errors": [error_msg], "warnings": []}

        # Obtener columnas reales de la tabla
        actual_columns = inspector.get_columns(table_name)

        # Crear diccionario de tipos reales (normalizando nombres)
        actual_types = {}
        for col in actual_columns:
            col_name = col['name']
            # Remover corchetes si existen y sanitizar
            clean_name = col_name.replace('[', '').replace(']', '')
            normalized_name = sanitize_column_name(clean_name)
            actual_types[normalized_name] = str(col['type'])

        errors = []
        warnings = []

        # Comparar tipos esperados vs reales
        for expected_col, expected_type in expected_types.items():
            # Normalizar nombre esperado usando la misma función de sanitización
            normalized_expected = sanitize_column_name(expected_col)

            if normalized_expected not in actual_types:
                # Columna esperada no encontrada en la tabla
                errors.append(f"Columna '{expected_col}' no encontrada en la tabla creada")
                continue

            actual_type = actual_types[normalized_expected]

            # Comparar tipos (con lógica de compatibilidad)
            if not types_compatible(expected_type, actual_type):
                warnings.append({
                    "column": expected_col,
                    "expected": expected_type,
                    "actual": actual_type,
                    "message": f"Tipo incompatible: esperado '{expected_type}', actual '{actual_type}'"
                })

        # Verificar columnas extras en la tabla que no estaban en expected_types
        expected_normalized = {sanitize_column_name(col) for col in expected_types.keys()}
        for actual_col in actual_types.keys():
            if actual_col not in expected_normalized and actual_col not in ['id_sys', 'date_sys']:
                warnings.append({
                    "column": actual_col,
                    "expected": "N/A",
                    "actual": actual_types[actual_col],
                    "message": f"Columna extra encontrada: '{actual_col}' ({actual_types[actual_col]})"
                })

        # Loggear resultados
        if errors:
            for error in errors:
                logging.error(f"Error de validación: {error}")

        if warnings:
            for warning in warnings:
                logging.warning(f"Advertencia de validación: {warning['message']}")

        # Crear resumen de validación
        validation_result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "total_columns_expected": len(expected_types),
                "total_columns_actual": len(actual_types),
                "errors_count": len(errors),
                "warnings_count": len(warnings)
            }
        }

        if validation_result["valid"]:
            logging.info(f"Validación exitosa: {table_name} - {len(actual_types)} columnas, {len(warnings)} advertencias")
        else:
            logging.error(f"Validación fallida: {table_name} - {len(errors)} errores, {len(warnings)} advertencias")

        return validation_result

    except Exception as e:
        error_msg = f"Error durante validación del esquema: {str(e)}"
        logging.error(error_msg)
        return {"valid": False, "errors": [error_msg], "warnings": []}

def create_dynamic_table(db, table_name, column_types):
    """
    Crea una tabla dinámica en la base de datos con el esquema especificado.
    Siempre incluye campos id_sys (autoincremental) y date_sys (fecha actual).
    """
    # Construir la consulta CREATE TABLE
    columns_sql = []

    # Agregar campos predeterminados del sistema
    columns_sql.append("id_sys INT IDENTITY(1,1) PRIMARY KEY")
    columns_sql.append("date_sys DATETIME DEFAULT GETDATE()")

    # Verificar si hay una columna 'id' en los datos (case-insensitive)
    id_column_names = [col_name for col_name in column_types.keys() if col_name.lower() == 'id']
    has_id_column = len(id_column_names) > 0

    # Si hay columna 'id' en los datos, no crear IDENTITY adicional (ya tenemos id_sys)
    # Pero procesar las otras columnas normalmente

    for col_name, col_type in column_types.items():
        # Sanitizar nombre de columna
        safe_col_name = sanitize_column_name(col_name)

        # Si esta columna es 'id' y ya tenemos IDENTITY, omitirla para evitar duplicados
        if has_id_column and safe_col_name.lower() == 'id':
            # Para columna 'id' de los datos, hacerla NOT NULL (sin PRIMARY KEY ya que id_sys es PK)
            if col_type in ['INT', 'BIGINT']:
                columns_sql.append(f"[{safe_col_name}] {col_type} NOT NULL")
            else:
                columns_sql.append(f"[{safe_col_name}] {col_type} NULL")
        else:
            # Columnas normales que no son 'id'
            columns_sql.append(f"[{safe_col_name}] {col_type} NULL")

    create_table_sql = f"""
    CREATE TABLE [{table_name}] (
        {', '.join(columns_sql)}
    )
    """

    try:
        db.commit()
        logging.info(f"Tabla creada exitosamente: {table_name}")
    except Exception as e:
        db.rollback()
        logging.error(f"Error creando tabla {table_name}: {e}")
        raise

def convert_data_types(batch, column_types):
    """
    Convierte los tipos de datos en un lote de registros según el esquema.
    Versión mejorada con manejo robusto de tipos mixtos y fechas.
    """
    converted_batch = []

    for record in batch:
        converted_record = {}
        for col_name, col_type in column_types.items():
            value = record.get(col_name)

            # Sanitizar nombre de columna
            safe_col_name = sanitize_column_name(col_name)

            if value is None or value == "":
                converted_record[safe_col_name] = None
            elif col_type == "BIT":
                # Manejo flexible de booleanos
                if isinstance(value, bool):
                    converted_record[safe_col_name] = value
                elif isinstance(value, str):
                    # Convertir strings comunes a booleanos
                    lower_val = value.lower().strip()
                    if lower_val in ('true', '1', 'yes', 'si', 'sí', 'y', 't'):
                        converted_record[safe_col_name] = True
                    elif lower_val in ('false', '0', 'no', 'n', 'f'):
                        converted_record[safe_col_name] = False
                    else:
                        converted_record[safe_col_name] = None
                elif isinstance(value, (int, float)):
                    converted_record[safe_col_name] = bool(value)
                else:
                    converted_record[safe_col_name] = None
            elif col_type == "INT":
                try:
                    if isinstance(value, str):
                        # Limpiar string: remover comas, espacios y caracteres no numéricos
                        clean_value = value.strip().replace(',', '').replace(' ', '')
                        if not clean_value or clean_value.lower() in ('none', 'null', 'nan', '', 'n/a'):
                            converted_record[safe_col_name] = None
                        else:
                            # Intentar conversión a número
                            converted_record[safe_col_name] = int(float(clean_value))
                    elif isinstance(value, float) and value.is_integer():
                        converted_record[safe_col_name] = int(value)
                    else:
                        converted_record[safe_col_name] = int(float(value))
                except (ValueError, TypeError, OverflowError):
                    converted_record[safe_col_name] = None
            elif col_type == "BIGINT":
                try:
                    if isinstance(value, str):
                        # Limpiar string: remover comas, espacios y caracteres no numéricos
                        clean_value = value.strip().replace(',', '').replace(' ', '')
                        if not clean_value or clean_value.lower() in ('none', 'null', 'nan', '', 'n/a'):
                            converted_record[safe_col_name] = None
                        else:
                            # Intentar conversión a número
                            converted_record[safe_col_name] = int(float(clean_value))
                    elif isinstance(value, float):
                        if value.is_integer() or abs(value - round(value)) < 1e-10:
                            converted_record[safe_col_name] = int(value)
                        else:
                            # Float no entero - no válido para BIGINT
                            converted_record[safe_col_name] = None
                    else:
                        converted_record[safe_col_name] = int(float(value))
                except (ValueError, TypeError, OverflowError):
                    converted_record[safe_col_name] = None
            elif col_type == "FLOAT":
                try:
                    if isinstance(value, str):
                        # Limpiar string: remover comas, espacios y caracteres no numéricos
                        clean_value = value.strip().replace(',', '').replace(' ', '')
                        if not clean_value or clean_value.lower() in ('none', 'null', 'nan', '', 'n/a'):
                            converted_record[safe_col_name] = None
                        else:
                            converted_record[safe_col_name] = float(clean_value)
                    else:
                        converted_record[safe_col_name] = float(value)
                except (ValueError, TypeError, OverflowError):
                    converted_record[safe_col_name] = None
            elif col_type == "DATETIME":
                try:
                    # Múltiples estrategias para conversión de fechas
                    if isinstance(value, str):
                        # Limpiar string de fecha
                        clean_value = value.strip()
                        if not clean_value:
                            converted_record[safe_col_name] = None
                            continue

                        # Intentar conversión directa con pandas
                        try:
                            dt = pd.to_datetime(clean_value, errors='raise')
                            converted_record[safe_col_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            # Intentar formatos específicos comunes
                            date_formats = [
                                '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d',
                                '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
                                '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
                                '%m-%d-%Y', '%m/%d/%Y'
                            ]

                            converted = False
                            for fmt in date_formats:
                                try:
                                    dt = datetime.strptime(clean_value, fmt)
                                    converted_record[safe_col_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    converted = True
                                    break
                                except ValueError:
                                    continue

                            if not converted:
                                converted_record[safe_col_name] = None
                    elif isinstance(value, (int, float)):
                        # Convertir números a fechas (asumiendo timestamps Unix o años)
                        try:
                            if value > 1000000000:  # Probablemente timestamp Unix
                                dt = pd.to_datetime(value, unit='s')
                            elif 1900 <= value <= 2100:  # Probablemente año
                                dt = pd.Timestamp(year=int(value), month=1, day=1)
                            else:
                                dt = pd.to_datetime(value)
                            converted_record[safe_col_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError, OverflowError):
                            converted_record[safe_col_name] = None
                    else:
                        # Otros tipos - intentar conversión genérica
                        try:
                            dt = pd.to_datetime(value)
                            converted_record[safe_col_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            converted_record[safe_col_name] = None
                except Exception:
                    # Fallback seguro
                    converted_record[safe_col_name] = None
            else:  # NVARCHAR
                # Convertir cualquier valor a string de forma segura
                try:
                    if isinstance(value, (list, dict)):
                        # Convertir estructuras complejas a JSON string
                        converted_record[safe_col_name] = json.dumps(value, ensure_ascii=False)
                    else:
                        converted_record[safe_col_name] = str(value)
                except Exception:
                    converted_record[safe_col_name] = None

        converted_batch.append(converted_record)

    return converted_batch

def insert_batch(db, table_name, batch, column_types):
    """
    Inserta un lote de registros en la tabla.
    """
    if not batch:
        return

    # Obtener nombres de columnas seguros y parámetros nombrados
    safe_columns = []
    param_names = []
    for col_name in column_types.keys():
        safe_col = sanitize_column_name(col_name)
        safe_columns.append(f"[{safe_col}]")
        param_names.append(f":{safe_col}")

    # Crear consulta INSERT con parámetros nombrados
    columns_str = ", ".join(safe_columns)
    placeholders = ", ".join(param_names)
    insert_sql = f"INSERT INTO [{table_name}] ({columns_str}) VALUES ({placeholders})"

    try:
        # Insertar cada registro individualmente
        for record in batch:
            params = {}
            for col_name in column_types.keys():
                safe_col = sanitize_column_name(col_name)
                value = record.get(safe_col)

                # Convertir tipos de datos problemáticos
                if isinstance(value, float) and value.is_integer():
                    value = int(value)  # Convertir float entero a int
                elif isinstance(value, str) and value.strip() == '':
                    value = None  # Convertir string vacío a None
                elif column_types[col_name] == "DATETIME" and isinstance(value, str):
                    # Convertir strings de fecha a objetos datetime de Python para evitar conversiones automáticas
                    try:
                        value = pd.to_datetime(value).to_pydatetime()
                    except (ValueError, TypeError):
                        value = None

                params[safe_col] = value

            # Ejecutar inserción individual con parámetros nombrados

        db.commit()

    except Exception as e:
        db.rollback()
        logging.error(f"Error insertando lote en {table_name}: {e}")
        raise
from security.auth_middleware import require_role_api
from db.crud.tablas import get_tables
from db.models.config.migraciones import MigracionMetadata
from db.schemas.config.Usuarios import UserDB

ALLOWED_EXTENSIONS = {
    'EXCEL': [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ],
    'CSV': [
        "text/csv",
        "application/csv",
        "text/plain"  # Algunos navegadores envían CSV como text/plain
    ]
}

def is_file_locked(file_path):
    """Verifica si un archivo está siendo utilizado por otro proceso"""
    try:
        # Intentar abrir el archivo en modo exclusivo
        with open(file_path, 'rb'):
            pass
        return False
    except IOError:
        return True

async def safe_read_excel(file_path, engine='openpyxl'):
    """Lee un archivo Excel con verificación de bloqueo de archivo"""
    try:
        # Verificar si el archivo está bloqueado
        if is_file_locked(file_path):
            raise PermissionError(f"El archivo '{os.path.basename(file_path)}' está siendo utilizado por otro proceso (posiblemente Excel). "
                                "Cierre el archivo en Excel u otra aplicación antes de procesarlo.")

        # Intentar leer el archivo Excel
        return pd.ExcelFile(file_path, engine=engine)

    except PermissionError:
        raise  # Re-lanzar errores de permiso
    except Exception as e:
        # Mejorar mensajes de error para casos comunes
        error_msg = str(e)
        if "No module named" in error_msg:
            raise Exception("Faltan dependencias para procesar archivos Excel. Instale openpyxl con: pip install openpyxl")
        elif "Unsupported format" in error_msg or "not a valid" in error_msg.lower():
            raise Exception(f"El archivo '{os.path.basename(file_path)}' no es un archivo Excel válido o está corrupto")
        elif "File is not a zip file" in error_msg:
            raise Exception(f"El archivo '{os.path.basename(file_path)}' parece estar corrupto o no es un archivo Excel válido")
        else:
            raise Exception(f"Error al leer archivo Excel: {error_msg}")

# Configuración para procesamiento paralelo
MAX_WORKERS = min(multiprocessing.cpu_count(), 8)  # Máximo 8 procesos
CHUNK_SIZE = 100_000  # 100K filas por chunk
MEMORY_THRESHOLD = 80  # Porcentaje de memoria máximo antes de pausar


progress_storage = {}
# Agregamos una clase para manejar el estado de la migración
class MigracionProgress:
    def __init__(self):
        self.total_sheets = 0
        self.processed_sheets = 0
        self.current_sheet = ""
        self.status = "iniciando"
        self.errors = []
        self.progress_percentage = 0
        self.retry_count = 0
        self.max_retries = 3
        # Métricas de subida (upload)
        self.stage = "idle"  # idle | uploading | processing | completed | error
        self.total_size_bytes = 0
        self.uploaded_bytes = 0
        self.upload_percentage = 0
        self.upload_speed_bps = 0  # bytes por segundo
        self.upload_eta_seconds = 0
        self.started_at = datetime.now().isoformat()

    def update(self, sheet_name: str, status: str, error: str = None):
        self.current_sheet = sheet_name
        self.status = status
        if error:
            self.errors.append({"sheet": sheet_name, "error": error})
        if status == "completado":
            self.processed_sheets += 1
            self.progress_percentage = (self.processed_sheets / self.total_sheets) * 100

    def update_upload(self, bytes_read: int, total_bytes: int, start_time: datetime):
        """Actualiza métricas de subida para feedback inmediato."""
        self.stage = "uploading"
        self.status = "subiendo archivo"
        # Configurar total si está disponible
        if total_bytes and total_bytes > 0:
            self.total_size_bytes = total_bytes
        self.uploaded_bytes += bytes_read
        # Calcular porcentaje (si se conoce total)
        if self.total_size_bytes and self.total_size_bytes > 0:
            self.upload_percentage = min(100.0, (self.uploaded_bytes / self.total_size_bytes) * 100.0)
        else:
            # Si no hay total conocido, aproximar usando progreso incremental
            self.upload_percentage = 0.0
        # Velocidad y ETA
        elapsed = (datetime.now() - start_time).total_seconds() or 0.000001
        self.upload_speed_bps = self.uploaded_bytes / elapsed
        if self.total_size_bytes and self.upload_speed_bps > 0:
            remaining = max(0, self.total_size_bytes - self.uploaded_bytes)
            self.upload_eta_seconds = remaining / self.upload_speed_bps
        else:
            self.upload_eta_seconds = 0

    def to_dict(self):
        """Convierte el objeto a un diccionario para serialización JSON"""
        return {
            "total_sheets": self.total_sheets,
            "processed_sheets": self.processed_sheets,
            "current_sheet": self.current_sheet,
            "status": self.status,
            "errors": self.errors,
            "progress_percentage": self.progress_percentage,
            "retry_count": self.retry_count,
            # Nuevos campos de estado/tiempo real
            "stage": getattr(self, "stage", "idle"),
            "total_size_bytes": getattr(self, "total_size_bytes", 0),
            "uploaded_bytes": getattr(self, "uploaded_bytes", 0),
            "upload_percentage": getattr(self, "upload_percentage", 0),
            "upload_speed_bps": getattr(self, "upload_speed_bps", 0),
            "upload_eta_seconds": getattr(self, "upload_eta_seconds", 0),
            "started_at": getattr(self, "started_at", None)
        }

class ParallelMigracionProgress(MigracionProgress):
    def __init__(self):
        super().__init__()
        self.total_chunks = 0
        self.processed_chunks = 0
        self.parallel_workers = 0
        self.memory_usage = 0
        self.processing_speed = 0  # filas por segundo
        self.estimated_time_remaining = 0

    def update_parallel(self, chunks_processed: int, memory_usage: float, speed: float):
        self.processed_chunks = chunks_processed
        self.memory_usage = memory_usage
        self.processing_speed = speed
        if speed > 0:
            remaining_chunks = self.total_chunks - self.processed_chunks
            self.estimated_time_remaining = remaining_chunks * CHUNK_SIZE / speed
        self.progress_percentage = (self.processed_chunks / self.total_chunks) * 100 if self.total_chunks > 0 else 0
        self.stage = "processing"

    def to_dict(self):
        """Convierte el objeto a un diccionario para serialización JSON"""
        base_dict = super().to_dict()
        base_dict.update({
            "total_chunks": self.total_chunks,
            "processed_chunks": self.processed_chunks,
            "parallel_workers": self.parallel_workers,
            "memory_usage": self.memory_usage,
            "processing_speed": self.processing_speed,
            "estimated_time_remaining": self.estimated_time_remaining
        })
        return base_dict

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_sheet_with_retry(sheet_data, sheet_name, timestamp, user_results_dir):
    """Procesa una hoja con sistema de reintentos"""
    
    try:
        # Convertir columnas datetime
        datetime_columns = sheet_data.select_dtypes(include=['datetime64[ns]', 'datetime']).columns
        for column in datetime_columns:
            sheet_data[column] = sheet_data[column].dt.strftime('%Y-%m-%d %H:%M:%S')

        return sheet_data
    except Exception as e:
        logging.error(f"Error procesando hoja {sheet_name}: {str(e)}")
        raise

def process_chunk_worker(chunk_data, chunk_index, table_name, db_config):
    """Worker function para procesar un chunk en paralelo"""
    try:
        import pandas as pd
        import json
        
        # Crear conexión independiente para este worker
        engine = create_engine(db_config['connection_string'])
        
        # Convertir chunk a DataFrame si no lo es ya
        if isinstance(chunk_data, list):
            df = pd.DataFrame(chunk_data)
        else:
            df = chunk_data
            
        # Limpiar datos
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        # Convertir tipos de datos problemáticos
        for col in df.columns:
            if df[col].dtype == 'object':
                # Intentar convertir fechas
                try:
                    df[col] = pd.to_datetime(df[col], errors='ignore')
                except:
                    pass
        
        # Convertir columnas datetime a string para compatibilidad
        datetime_columns = df.select_dtypes(include=['datetime64[ns]', 'datetime']).columns
        for column in datetime_columns:
            df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Insertar en base de datos por chunks más pequeños
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch.to_sql(
                name=table_name,
                con=engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            total_inserted += len(batch)
        
        engine.dispose()
        
        return {
            'chunk_index': chunk_index,
            'rows_processed': total_inserted,
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'chunk_index': chunk_index,
            'rows_processed': 0,
            'status': 'error',
            'error': str(e)
        }

async def read_excel_in_chunks(file_path: str, chunk_size: int):
    """Lee archivo Excel por chunks, combinando todas las hojas en una sola secuencia de chunks"""
    chunks = []
    
    try:
        # Determinar motor según extensión
        engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
        
        with pd.ExcelFile(file_path, engine=engine) as xls:
            for sheet_name in xls.sheet_names:
                logging.info(f"Leyendo hoja: {sheet_name}")
                
                # Leer hoja completa primero (para archivos muy grandes, considerar usar chunksize)
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
                
                # Dividir en chunks
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i:i+chunk_size].copy()
                    if not chunk.empty:
                        chunks.append(chunk)
                
                del df  # Liberar memoria
                
    except Exception as e:
        logging.error(f"Error leyendo Excel: {str(e)}")
        raise
    
    return chunks

async def read_csv_in_chunks(file_path: str, chunk_size: int):
    """Lee archivo CSV por chunks"""
    chunks = []
    
    try:
        # Usar chunksize de pandas para archivos muy grandes
        chunk_reader = pd.read_csv(
            file_path,
            chunksize=chunk_size,
            encoding='utf-8-sig',
            low_memory=False
        )
        
        for chunk in chunk_reader:
            if not chunk.empty:
                chunks.append(chunk)
                
    except Exception as e:
        logging.error(f"Error leyendo CSV: {str(e)}")
        raise
    
    return chunks

async def process_large_file_parallel(
    file_path: str,
    nombre_migracion: str,
    timestamp: str,
    user_results_dir: str,
    db: Session,
    current_user: UserDB,
    progress: ParallelMigracionProgress,
    file_type: str = 'excel'
):
    """Procesa archivos grandes en paralelo"""
    try:
        progress.status = "analizando archivo"
        progress.stage = "processing"
        logging.info(f"Iniciando procesamiento paralelo de {file_path}")
        
        # Obtener configuración de base de datos
        db_config = {
            'connection_string': str(db.get_bind().url)
        }
        
        # Leer archivo por chunks según el tipo
        if file_type == 'excel':
            chunks = await read_excel_in_chunks(file_path, CHUNK_SIZE)
        else:  # CSV
            chunks = await read_csv_in_chunks(file_path, CHUNK_SIZE)

        progress.total_chunks = len(chunks)
        progress.parallel_workers = MAX_WORKERS
        progress.status = "procesando en paralelo"
        
        # Crear tabla base
        table_name = f"migracion_{nombre_migracion}_{timestamp}".replace(" ", "_").lower()
        
        # Usar ThreadPoolExecutor para I/O intensivo o ProcessPoolExecutor para CPU intensivo
        executor_class = ProcessPoolExecutor if len(chunks) > 50 else ThreadPoolExecutor
        
        async def process_chunks_batch(chunk_batch, batch_start_index):
            """Procesa un lote de chunks"""
            loop = asyncio.get_event_loop()
            
            with executor_class(max_workers=MAX_WORKERS) as executor:
                # Crear tareas para cada chunk en el lote
                tasks = []
                for i, chunk in enumerate(chunk_batch):
                    chunk_index = batch_start_index + i
                    task = loop.run_in_executor(
                        executor,
                        process_chunk_worker,
                        chunk,
                        chunk_index,
                        table_name,
                        db_config
                    )
                    tasks.append(task)
                
                # Esperar a que todos los chunks del lote se completen
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
        
        # Procesar en lotes para controlar memoria
        batch_size = MAX_WORKERS * 2  # Procesar 2 lotes por worker
        total_processed = 0
        total_errors = 0
        start_time = datetime.now()
        
        for batch_start in range(0, len(chunks), batch_size):
            # Verificar uso de memoria antes de cada lote
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > MEMORY_THRESHOLD:
                logging.warning(f"Memoria alta ({memory_percent}%), pausando 10 segundos...")
                await asyncio.sleep(10)
                continue
            
            batch_end = min(batch_start + batch_size, len(chunks))
            chunk_batch = chunks[batch_start:batch_end]
            
            # Procesar lote
            results = await process_chunks_batch(chunk_batch, batch_start)
            
            # Procesar resultados
            for result in results:
                if isinstance(result, Exception):
                    total_errors += 1
                    progress.errors.append({"chunk": "unknown", "error": str(result)})
                elif result['status'] == 'success':
                    total_processed += result['rows_processed']
                else:
                    total_errors += 1
                    progress.errors.append({
                        "chunk": result['chunk_index'], 
                        "error": result.get('error', 'Unknown error')
                    })
            
            # Actualizar progreso
            elapsed_time = (datetime.now() - start_time).total_seconds()
            speed = total_processed / elapsed_time if elapsed_time > 0 else 0
            memory_usage = psutil.virtual_memory().percent
            
            progress.update_parallel(
                chunks_processed=batch_end,
                memory_usage=memory_usage,
                speed=speed
            )
            
            logging.info(f"Lote {batch_start//batch_size + 1} completado. "
                        f"Procesadas {total_processed} filas, {total_errors} errores. "
                        f"Velocidad: {speed:.0f} filas/seg")
        
        # Actualizar estado final
        if total_errors > 0:
            progress.status = f"completado con {total_errors} errores"
        else:
            progress.status = "completado exitosamente"
        progress.stage = "completed"
        
        # Crear archivo de resultado
        result_data = {
            "status": progress.status,
            "total_rows_processed": total_processed,
            "total_errors": total_errors,
            "processing_time_seconds": elapsed_time,
            "average_speed": speed,
            "table_name": table_name,
            "timestamp": timestamp
        }
        
        result_path = os.path.join(user_results_dir, f"result_parallel_{timestamp}.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # Limpiar chunks de memoria
        del chunks
        import gc
        gc.collect()
        
        # Eliminar archivo temporal
        if os.path.exists(file_path):
            os.remove(file_path)
        
        logging.info(f"Procesamiento paralelo completado: {total_processed} filas, {elapsed_time:.1f}s")
        
    except Exception as e:
        error_msg = f"Error en procesamiento paralelo: {str(e)}"
        logging.error(error_msg)
        progress.status = "error"
        progress.errors.append({"chunk": "general", "error": error_msg})

# Funciones para procesar archivos en segundo plano
async def process_excel_file_in_background(
    temp_file_path: str,
    nombre_migracion: str,
    timestamp: str,
    user_results_dir: str, 
    db: Session,
    current_user: UserDB,
    progress: MigracionProgress
):
    """
    Procesa un archivo Excel en segundo plano.
    """
    try:
        logging.info(f"Iniciando procesamiento de archivo Excel: {temp_file_path}")
        progress.status = "procesando"
        
        # Usar xlrd para Excel antiguos (.xls) o openpyxl para nuevos (.xlsx)
        if temp_file_path.endswith('.xls'):
            try:
                excel = pd.ExcelFile(temp_file_path, engine='xlrd')
            except Exception as e:
                logging.error(f"Error al leer archivo XLS: {str(e)}")
                progress.status = "error"
                progress.errors.append({"sheet": "todas", "error": f"Error al leer archivo XLS: {str(e)}"})
                return
        else:
            try:
                excel = pd.ExcelFile(temp_file_path, engine='openpyxl')
            except Exception as e:
                logging.error(f"Error al leer archivo XLSX: {str(e)}")
                progress.status = "error"
                progress.errors.append({"sheet": "todas", "error": f"Error al leer archivo XLSX: {str(e)}"})
                return

        # Contar las hojas para actualizar el progreso
        sheet_names = excel.sheet_names
        progress.total_sheets = len(sheet_names)
        logging.info(f"Encontradas {progress.total_sheets} hojas en el archivo Excel")
        
        for sheet_name in sheet_names:
            try:
                progress.update(sheet_name, "procesando")
                logging.info(f"Procesando hoja: {sheet_name}")
                
                # Leer la hoja
                df = excel.parse(sheet_name, header=0)
                
                # Eliminar filas completamente vacías
                df.dropna(how='all', inplace=True)
                
                # Si el dataframe está vacío después de eliminar filas vacías, saltamos
                if df.empty:
                    progress.update(sheet_name, "completado", "Hoja vacía")
                    continue
                
                # Eliminar columnas completamente vacías  
                df.dropna(axis=1, how='all', inplace=True)
                
                # Procesar la hoja con el sistema de reintentos
                df = await process_sheet_with_retry(df, sheet_name, timestamp, user_results_dir)
                
                # Convertir a JSON (asegurando que los datos datetime se convierten correctamente)
                json_path = os.path.join(user_results_dir, f"{sheet_name}_{timestamp}.json")
                
                # Convertir al formato JSON usando orient='records' para una lista de diccionarios
                df.to_json(json_path, orient='records', date_format='iso')
                
                # Nombre de la tabla en la base de datos
                table_name = f"migracion_{nombre_migracion}_{sheet_name}_{timestamp}"
                table_name = table_name.replace(" ", "_").replace("-", "_").lower()
                
                # Guardar el resultado de la migración
                result_filename = f"result_{sheet_name}_{timestamp}.json"
                result_path = os.path.join(user_results_dir, result_filename)
                
                # Procesar el archivo JSON
                procesar_archivo(json_path, result_path, db, current_user, table_name)
                
                progress.update(sheet_name, "completado")
                
            except Exception as e:
                error_msg = f"Error procesando hoja {sheet_name}: {str(e)}"
                logging.error(error_msg)
                progress.update(sheet_name, "error", error_msg)
                continue
                
        # Actualizar el estado final
        if progress.errors:
            progress.status = "completado con errores"
        else:
            progress.status = "completado"
            
        # Eliminar el archivo temporal
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logging.warning(f"No se pudo eliminar el archivo temporal {temp_file_path}: {str(e)}")
        
    except Exception as e:
        logging.error(f"Error en el proceso de migración: {str(e)}")
        progress.status = "error"
        progress.errors.append({"sheet": "general", "error": f"Error general: {str(e)}"})
        
    finally:
        logging.info(f"Proceso de migración completado con estado: {progress.status}")


# =============================
# CONFIGURACIÓN DEL ROUTER Y TEMPLATES
# =============================
router = APIRouter()
templates = Jinja2Templates(directory="static")

# =============================
# CONSTANTES Y CONFIGURACIÓN
# =============================
RESULTS_DIR = os.path.join(os.getcwd(), "results")

# Agregar ruta principal para breadcrumb
@router.get("/")
async def migraciones_index(
    request: Request,
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Página índice de migraciones - redirige a admin_migraciones"""
    return RedirectResponse(url="/migraciones/admin_migraciones", status_code=302)

# Endpoint para la página de administración de migraciones
@router.get("/admin_migraciones")
async def admin_migraciones(
    request: Request,
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Página de administración de migraciones"""
    try:
        return templates.TemplateResponse(
            "html/migraciones/migraciones_admin.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Administración de Migraciones"
            }
        )
    except Exception as e:
        logging.error(f"Error al cargar página de administración de migraciones: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al cargar página de administración")

# Agregar endpoint para estadísticas de migraciones
@router.get("/api/stats")
async def get_migration_stats(
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """API para obtener estadísticas de migraciones"""
    try:
        user_id = current_user.codigo
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Usuario no válido")
        
        # Estadísticas básicas usando MigracionMetadata en lugar de ActivityLog
        total_migraciones = db.query(MigracionMetadata).filter(
            MigracionMetadata.usuario_id == user_id
        ).count()

        # Migraciones por mes usando SQL directo para compatibilidad con SQL Server
            SELECT FORMAT(fecha_creacion, 'yyyy-MM') as month, COUNT(*) as count
            FROM migraciones_metadata
            WHERE usuario_id = :user_id AND fecha_creacion IS NOT NULL
            GROUP BY FORMAT(fecha_creacion, 'yyyy-MM')
            ORDER BY month
        """), {'user_id': user_id}).fetchall()

        monthly_migrations = [{'month': row[0], 'count': row[1]} for row in monthly_result]
        
        # Tablas de migración existentes
        inspector = inspect(db.get_bind())
        migration_tables = [
            table for table in inspector.get_table_names() 
            if table.startswith('migracion_')
        ]
        
        return {
            "total_migraciones": total_migraciones,
            "monthly_data": [{"month": m.month, "count": m.count} for m in monthly_migrations],
            "migration_tables_count": len(migration_tables),
            "migration_tables": migration_tables[:10]  # Últimas 10 tablas
        }
    except Exception as e:
        logging.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")

# Endpoint para limpiar archivos temporales antiguos
@router.delete("/api/cleanup")
async def cleanup_old_files(
    days: int = 30,
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Limpia archivos temporales y de resultados antiguos"""
    try:
        user_name = current_user.usuario
        
        if not user_name:
            raise HTTPException(status_code=400, detail="Usuario no válido")
        
        user_results_dir = os.path.join(RESULTS_DIR, user_name)
        
        if not os.path.exists(user_results_dir):
            return {"message": "No hay archivos para limpiar", "files_deleted": 0}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        files_deleted = 0
        
        for filename in os.listdir(user_results_dir):
            file_path = os.path.join(user_results_dir, filename)
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_modified < cutoff_date and (filename.startswith('temp_') or filename.startswith('result_')):
                try:
                    os.remove(file_path)
                    files_deleted += 1
                    logging.info(f"Archivo eliminado: {filename}")
                except Exception as e:
                    logging.warning(f"No se pudo eliminar {filename}: {str(e)}")
        
        return {
            "message": f"Limpieza completada. Archivos más antiguos que {days} días eliminados.",
            "files_deleted": files_deleted
        }
    except Exception as e:
        logging.error(f"Error en limpieza: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en limpieza: {str(e)}")

# Endpoint adicional para monitorear recursos del sistema
@router.get("/api/system_resources")
async def get_system_resources(
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Obtiene información sobre recursos del sistema"""
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "disk_usage_percent": psutil.disk_usage('.').percent,
            "active_connections": len(psutil.net_connections()),
            "max_workers": MAX_WORKERS,
            "chunk_size": CHUNK_SIZE,
            "memory_threshold": MEMORY_THRESHOLD
        }
    except Exception as e:
        logging.error(f"Error obteniendo recursos del sistema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para estadísticas del dashboard (formato esperado por el frontend)
@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """API para obtener estadísticas del dashboard de migraciones"""
    try:
        user_id = current_user.codigo

        if not user_id:
            raise HTTPException(status_code=400, detail="Usuario no válido")

        # Estadísticas básicas
        total_migraciones = db.query(MigracionMetadata).filter(
            MigracionMetadata.usuario_id == user_id
        ).count()

        # Total de registros (suma de todos los registros procesados)
        total_registros_result = db.query(func.sum(MigracionMetadata.total_registros)).filter(
            MigracionMetadata.usuario_id == user_id
        ).scalar()
        total_registros = total_registros_result or 0

        # Espacio usado (aproximado basado en registros)
        espacio_usado_mb = (total_registros * 0.1)  # Aproximadamente 100 bytes por registro

        # Migraciones en el último mes
        last_month = datetime.now() - timedelta(days=30)
        migraciones_mes = db.query(MigracionMetadata).filter(
            MigracionMetadata.usuario_id == user_id,
            MigracionMetadata.fecha_creacion >= last_month
        ).count()

        return {
            "total_migraciones": total_migraciones,
            "total_registros": total_registros,
            "espacio_usado_mb": round(espacio_usado_mb, 2),
            "migraciones_mes": migraciones_mes
        }
    except Exception as e:
        logging.error(f"Error al obtener estadísticas del dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al cargar estadísticas")

# Endpoint para lista de migraciones (para DataTables)
@router.get("/api/lista")
async def get_migrations_list(
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """API para obtener lista de migraciones para DataTables"""
    try:
        user_id = current_user.codigo

        if not user_id:
            raise HTTPException(status_code=400, detail="Usuario no válido")

        # Obtener migraciones del usuario
        migraciones = db.query(MigracionMetadata).filter(
            MigracionMetadata.usuario_id == user_id
        ).order_by(
            MigracionMetadata.fecha_creacion.desc()
        ).all()

        # Convertir a formato para DataTables
        migrations_list = []
        for migracion in migraciones:
            migrations_list.append({
                "id": migracion.id,
                "nombre_tabla": migracion.nombre_tabla or f"migracion_{migracion.id}",
                "tipo_archivo": migracion.tipo_archivo or "excel",
                "total_registros": migracion.total_registros or 0,
                "estado": migracion.estado or "completado",
                "fecha_creacion": migracion.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if migracion.fecha_creacion else None
            })

        return {
            "migraciones": migrations_list
        }
    except Exception as e:
        logging.error(f"Error al obtener lista de migraciones: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener lista de migraciones")

# Endpoint para servir la página del dashboard de migración
@router.get("/dashboard_migracion")
async def dashboard_migracion(
    request: Request,
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Página del dashboard de migración"""
    try:
        return templates.TemplateResponse(
            "html/migraciones/migraciones_dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Dashboard de Migración"
            }
        )
    except Exception as e:
        logging.error(f"Error al cargar dashboard de migración: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al cargar dashboard")

# Endpoint para servir la página de nueva migración
@router.get("/nueva_migracion")
async def nueva_migracion(
    request: Request,
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Página para crear una nueva migración"""
    try:
        return templates.TemplateResponse(
            "html/migraciones/migraciones_nueva.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Nueva Migración"
            }
        )
    except Exception as e:
        logging.error(f"Error al cargar página de nueva migración: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al cargar página de nueva migración")

# Endpoint para subir y procesar archivos de migración
@router.post("/upload")
async def upload_migration_file(
    migration_name: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """Endpoint para subir y procesar archivos de migración"""
    try:
        # Validar nombre de migración
        if not migration_name or not migration_name.strip():
            raise HTTPException(status_code=400, detail="El nombre de la migración es requerido")

        migration_name = migration_name.strip()
        if len(migration_name) < 3:
            raise HTTPException(status_code=400, detail="El nombre de la migración debe tener al menos 3 caracteres")

        # Validar archivo
        if not file:
            raise HTTPException(status_code=400, detail="No se recibió ningún archivo")

        # Validar tipo de archivo
        allowed_extensions = ['.xlsx', '.xls', '.csv', '.txt']
        file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Solo se permiten: {', '.join(allowed_extensions)}"
            )

        # Validar tamaño del archivo (máximo 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo es demasiado grande. Tamaño máximo permitido: 50MB. Tamaño del archivo: {file_size / (1024*1024):.1f}MB"
            )

        # Crear directorio de resultados para el usuario
        user_name = current_user.usuario
        user_results_dir = os.path.join(RESULTS_DIR, user_name)
        os.makedirs(user_results_dir, exist_ok=True)

        # Generar timestamp y nombres de archivos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"temp_{timestamp}_{file.filename}"
        temp_file_path = os.path.join(user_results_dir, temp_filename)

        # Guardar archivo temporal
        with open(temp_file_path, 'wb') as f:
            f.write(file_content)

        logging.info(f"Archivo guardado temporalmente: {temp_file_path}")

        # Procesar archivo según el tipo
        if file_extension in ['.xlsx', '.xls']:
            # Procesar Excel
            progress = MigracionProgress()
            await process_excel_file_in_background(
                temp_file_path, migration_name, timestamp, user_results_dir, db, current_user, progress
            )

            # Verificar si hubo errores
            if progress.errors:
                error_details = "; ".join([f"{err.get('sheet', 'General')}: {err.get('error', 'Error desconocido')}" for err in progress.errors])
                raise HTTPException(status_code=500, detail=f"Error procesando archivo Excel: {error_details}")

            # Redirigir automáticamente al dashboard después del procesamiento exitoso
            return RedirectResponse(url="/migraciones/dashboard_migracion", status_code=302)

        elif file_extension == '.csv':
            # Procesar CSV
            try:
                # Leer CSV con pandas
                df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8-sig')

                # Procesar DataFrame
                df.dropna(how='all', inplace=True)
                df.dropna(axis=1, how='all', inplace=True)

                if df.empty:
                    raise HTTPException(status_code=400, detail="El archivo CSV está vacío o no contiene datos válidos")

                # Convertir a JSON
                json_filename = f"csv_{timestamp}.json"
                json_path = os.path.join(user_results_dir, json_filename)
                df.to_json(json_path, orient='records', date_format='iso')

                # Crear tabla
                table_name = f"migracion_{migration_name}_{timestamp}".replace(" ", "_").replace("-", "_").lower()

                # Procesar archivo JSON
                result_filename = f"result_csv_{timestamp}.json"
                result_path = os.path.join(user_results_dir, result_filename)
                procesar_archivo(json_path, result_path, db, current_user, table_name)

                # Redirigir automáticamente al dashboard después del procesamiento exitoso
                return RedirectResponse(url="/migraciones/dashboard_migracion", status_code=302)

            except pd.errors.EmptyDataError:
                raise HTTPException(status_code=400, detail="El archivo CSV está vacío")
            except pd.errors.ParserError as e:
                raise HTTPException(status_code=400, detail=f"Error al parsear CSV: {str(e)}")
            except Exception as e:
                logging.error(f"Error procesando CSV: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error procesando archivo CSV: {str(e)}")

        elif file_extension == '.txt':
            # Procesar TXT (asumiendo delimitado por comas o tabs)
            try:
                # Intentar detectar delimitador
                content_str = file_content.decode('utf-8-sig')

                # Detectar delimitador (prioridad: tab, luego coma, luego punto y coma)
                if '\t' in content_str:
                    delimiter = '\t'
                elif ';' in content_str:
                    delimiter = ';'
                else:
                    delimiter = ','

                # Leer con pandas
                df = pd.read_csv(io.StringIO(content_str), delimiter=delimiter, encoding='utf-8')

                # Procesar DataFrame
                df.dropna(how='all', inplace=True)
                df.dropna(axis=1, how='all', inplace=True)

                if df.empty:
                    raise HTTPException(status_code=400, detail="El archivo TXT está vacío o no contiene datos válidos")

                # Convertir a JSON
                json_filename = f"txt_{timestamp}.json"
                json_path = os.path.join(user_results_dir, json_filename)
                df.to_json(json_path, orient='records', date_format='iso')

                # Crear tabla
                table_name = f"migracion_{migration_name}_{timestamp}".replace(" ", "_").replace("-", "_").lower()

                # Procesar archivo JSON
                result_filename = f"result_txt_{timestamp}.json"
                result_path = os.path.join(user_results_dir, result_filename)
                procesar_archivo(json_path, result_path, db, current_user, table_name)

                # Redirigir automáticamente al dashboard después del procesamiento exitoso
                return RedirectResponse(url="/migraciones/dashboard_migracion", status_code=302)

            except Exception as e:
                logging.error(f"Error procesando TXT: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error procesando archivo TXT: {str(e)}")

        else:
            raise HTTPException(status_code=400, detail=f"Tipo de archivo no soportado: {file_extension}")

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error general en upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

# Endpoint API para obtener datos del dashboard de la migración más reciente
@router.api_route("/api/dashboard_data", methods=["GET", "HEAD"])
async def get_dashboard_data(
    current_user: UserDB = Depends(require_role_api(["admin", "usuario"]))
):
    """API para obtener datos del dashboard de la migración más reciente"""
    try:
        user_id = current_user.codigo

        if not user_id:
            raise HTTPException(status_code=400, detail="Usuario no válido")

        # Obtener la migración más reciente del usuario
        latest_migration = db.query(MigracionMetadata).filter(
            MigracionMetadata.usuario_id == user_id
        ).order_by(
            MigracionMetadata.fecha_creacion.desc()
        ).first()

        if not latest_migration:
            return {
                "migration_name": None,
                "file_name": None,
                "file_type": None,
                "file_size": None,
                "migration_date": None,
                "status": "no_data",
                "processing_type": None,
                "chunks_processed": None,
                "total_errors": 0,
                "tables": [],
                "total_records": 0,
                "processing_time": 0,
                "avg_speed": 0
            }

        # Obtener información de las tablas creadas por esta migración
        # Buscar tablas que contengan el nombre de la migración
        migration_name_pattern = f"%{latest_migration.nombre_tabla}%"
        inspector = inspect(db.bind)

        # Obtener todas las tablas del usuario
        all_tables = inspector.get_table_names()

        # Filtrar tablas relacionadas con esta migración
        migration_tables = []
        total_records = 0

        for table_name in all_tables:
            if latest_migration.nombre_tabla.lower() in table_name.lower():
                try:
                    # Obtener conteo de registros
                    record_count = result or 0
                    total_records += record_count;

                    migration_tables.append({
                        "name": table_name,
                        "record_count": record_count,
                        "created_date": latest_migration.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if latest_migration.fecha_creacion else None
                    })
                except Exception as e:
                    logging.warning(f"Error al obtener información de tabla {table_name}: {str(e)}")
                    migration_tables.append({
                        "name": table_name,
                        "record_count": 0,
                        "created_date": latest_migration.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if latest_migration.fecha_creacion else None
                    })

        # Calcular velocidad promedio
        processing_time = latest_migration.tiempo_procesamiento_segundos or 0
        avg_speed = total_records / processing_time if processing_time > 0 else 0

        return {
            "migration_name": latest_migration.nombre_tabla,
            "file_name": getattr(latest_migration, 'nombre_original_archivo', latest_migration.nombre_tabla),
            "file_type": latest_migration.tipo_archivo,
            "file_size": getattr(latest_migration, 'tamanio_bytes', None),
            "migration_date": latest_migration.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if latest_migration.fecha_creacion else None,
            "status": latest_migration.estado,
            "processing_type": getattr(latest_migration, 'tipo_procesamiento', 'background'),
            "chunks_processed": getattr(latest_migration, 'chunks_procesados', None),
            "total_errors": getattr(latest_migration, 'total_errores', 0),
            "tables": migration_tables,
            "total_records": total_records,
            "processing_time": processing_time,
            "avg_speed": round(avg_speed, 2) if avg_speed > 0 else 0,
            "validation_errors": getattr(latest_migration, 'validacion_errores', []),
            "validation_warnings": getattr(latest_migration, 'validacion_advertencias', []),
            "validation_summary": getattr(latest_migration, 'validacion_resumen', {})
        }

    except Exception as e:
        logging.error(f"Error al obtener datos del dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener datos del dashboard")
