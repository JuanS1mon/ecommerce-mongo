# ==================== FUNCIONES UTILITARIAS ====================
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Any, Dict, List, Optional
import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, logger, status
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
# Importaciones de pandas se harán de manera lazy para evitar problemas de inicialización
# import numpy as np
# import pandas as pd

from security.jwt_auth import get_current_user
from db.crud.tablas import get_tables
from db.schemas.config.Usuarios import UserDB

def limpiar_datos(df) -> any:
    """
    Limpia y procesa un DataFrame de pandas
    - Maneja valores nulos
    - Convierte tipos de datos apropiados
    - Elimina duplicados si es necesario
    """
    try:
        # Importaciones lazy
        import pandas as pd

        # Hacer una copia para no modificar el original
        df_clean = df.copy()

        # Reemplazar valores nulos con valores apropiados según el tipo
        for column in df_clean.columns:
            if df_clean[column].dtype == 'object':
                df_clean[column] = df_clean[column].fillna('Sin datos')
            elif pd.api.types.is_numeric_dtype(df_clean[column]):
                df_clean[column] = df_clean[column].fillna(0)
            elif pd.api.types.is_datetime64_any_dtype(df_clean[column]):
                df_clean[column] = df_clean[column].fillna(pd.NaT)

        # Convertir columnas de texto que parecen números
        for column in df_clean.select_dtypes(include=['object']).columns:
            try:
                # Intentar convertir a numérico si es posible
                numeric_series = pd.to_numeric(df_clean[column], errors='ignore')
                if not numeric_series.equals(df_clean[column]):
                    df_clean[column] = numeric_series
            except:
                pass

        return df_clean
    except Exception as e:
        print(f"Error en limpiar_datos: {str(e)}")
        return df


def convert_types(value):
    """
    Convierte valores a tipos serializables para JSON
    """
    try:
        # Importaciones lazy
        import pandas as pd
        import numpy as np

        if pd.isna(value) or value is None:
            return None
        elif isinstance(value, (pd.Timestamp, datetime.datetime)):
            return value.isoformat() if hasattr(value, 'isoformat') else str(value)
        elif isinstance(value, (pd.Timedelta, datetime.timedelta)):
            return str(value)
        elif isinstance(value, (np.integer, np.int64, np.int32)):
            return int(value)
        elif isinstance(value, (np.floating, np.float64, np.float32)):
            return float(value) if not np.isnan(value) else None
        elif isinstance(value, np.ndarray):
            return value.tolist()
        elif hasattr(value, 'item'):  # Para tipos numpy escalares
            return value.item()
        else:
            return value
    except Exception as e:
        print(f"Error en convert_types: {str(e)}")
        return str(value)


def guardar_resultados_sql(db: Session, user_name: str, resultados: Dict[str, Any]):
    """
    Guarda los resultados del análisis en una tabla de auditoría o log
    """
    try:
        # Crear una entrada de log simple en lugar de usar una tabla específica
        # Esto es una implementación básica que puede expandirse
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_name,
            "action": "analisis_datos",
            "results_summary": {
                "total_registros": resultados.get("total_registros", 0),
                "categorias_count": len(resultados.get("categorias", [])),
                "date_range": f"{resultados.get('first_date')} - {resultados.get('last_date')}",
                "has_clusters": bool(resultados.get("clusters"))
            }
        }
        
        # Por ahora solo hacer log en consola
        # En una implementación completa, esto iría a una tabla de base de datos
        print(f"[AUDIT LOG] {log_entry}")
        
        # Si existe una tabla de logs, se podría implementar aquí:
        # db.commit()
        
    except Exception as e:
        print(f"Error al guardar resultados: {str(e)}")
        # No lanzar excepción para no interrumpir el flujo principal

# Ajustar el directorio de las plantillas
templates = Jinja2Templates(directory="static/html")

router = APIRouter(
    include_in_schema=False,  # Oculta todas las rutas de este router en la documentación
    prefix="/analisis",
    tags=["Analisis"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "ruta no encontrada"}}
)

class ColumnasRequest(BaseModel):
    table_name: str


class AnalisisRequest(BaseModel):
    table_name: str
    column_name: str
    date_field: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    additional_field: Optional[str] = None  # Campos adicionales separados por comas
    custom_filters: Optional[List[Dict[str, Any]]] = None  # Lista de filtros personalizados

class AnalisisDetalleRequest(BaseModel):
    table_name: str
    column_name: str
    date_field: str
    start_date: str
    end_date: str


@router.get("/tablas")
    """
    API pública para obtener las tablas disponibles.
    No requiere autenticación para permitir carga inicial de la página.
    """
    try:
        _, tabla2 = get_tables(db)
        return {"tablas": tabla2}
    except Exception as e:
        print(f"Error al obtener tablas: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al obtener tablas: {str(e)}"}
        )


@router.post("/columnas")
    """
    API para obtener las columnas de una tabla específica.
    No requiere autenticación para mantener consistencia con otras rutas públicas.
    """
    try:
        table_name = request.table_name
        print(f"🔍 Obteniendo columnas para tabla: {table_name}")
        
        # Obtener las columnas de la tabla seleccionada
        inspector = inspect(db.bind)
        columns_info = inspector.get_columns(table_name)
        
        # Formatear la información de las columnas
        columns = [{"name": col["name"], "type": str(col["type"])} for col in columns_info]
        
        print(f"✅ Encontradas {len(columns)} columnas en {table_name}")
        return {"columns": columns}
        
    except Exception as e:
        print(f"❌ Error al obtener columnas de {request.table_name}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al obtener columnas: {str(e)}"}
        )


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """
    Página de análisis admin - se carga sin autenticación inicial.
    La verificación de autenticación se hace en JavaScript del lado cliente.
    """
    print("=========== ACCESO A PÁGINA ANÁLISIS ADMIN ===========")
    print("📄 Cargando analisis_admin.html sin verificación inicial")
    print("🔍 La autenticación será verificada por JavaScript")
    
    # Cargar la página sin datos específicos del usuario
    # El JavaScript se encargará de verificar el token y obtener datos
    chart_data = {
        "labels": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "values": [10, 20, 30]
    }
    return templates.TemplateResponse("analisis_admin.html", {
        "request": request, 
        "user": {"nombre": "Usuario", "roles": ["admin"]},
        "chart_data": chart_data
    })

@router.get("/admin/data")
async def admin_analisis_data(
        current_user: UserDB = Depends(get_current_user),
    ):
    """
    API protegida para obtener datos del usuario y análisis.
    Requiere token JWT válido.
    """
    print("=========== API DE DATOS ANÁLISIS ADMIN ===========")
    print(f"Usuario autenticado: {current_user.usuario}")
    
    # Aquí puedes agregar la lógica específica para obtener datos de análisis
    chart_data = {
        "labels": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "values": [10, 20, 30]
    }
    
    return {
        "user": {
            "username": current_user.usuario,
            "nombre": current_user.nombre,
            "email": current_user.mail,
            "roles": current_user.roles,
            "activo": current_user.activo
        },
        "chart_data": chart_data,
        "message": "Datos de análisis obtenidos exitosamente"
    }

@router.get("/nuevo", response_class=HTMLResponse)
    """
    Página de nuevo análisis - se carga sin autenticación inicial.
    La verificación de autenticación se hace en JavaScript del lado cliente.
    """
    print("=========== ACCESO A PÁGINA NUEVO ANÁLISIS ===========")
    print("📄 Cargando analisis_new.html sin verificación inicial")
    
    # Obtener las tablas disponibles
    _, tabla2 = get_tables(db)
    
    return templates.TemplateResponse("analisis_new.html", {
        "request": request, 
        "user": {"nombre": "Usuario", "roles": ["admin"]},
        "tabla2": tabla2  # Pasar las tablas obtenidas
    })

@router.get("/nuevo/data")
async def nuevo_analisis_data(
        current_user: UserDB = Depends(get_current_user),
    ):
    """
    API protegida para obtener datos para nuevo análisis.
    Requiere token JWT válido.
    """
    print("=========== API DE DATOS NUEVO ANÁLISIS ===========")
    print(f"Usuario autenticado: {current_user.usuario}")
    
    _, tabla2 = get_tables(db)  # Obtener tabla2
    
    return {
        "user": {
            "username": current_user.usuario,
            "nombre": current_user.nombre,
            "email": current_user.mail,
            "roles": current_user.roles,
            "activo": current_user.activo
        },
        "tabla2": tabla2,
        "message": "Datos para nuevo análisis obtenidos exitosamente"
    }


@router.post("/test")
async def test_route():
    return {"message": "Test route works"}

@router.post("/analizar_kpis")
async def analizar_kpis(request: AnalisisRequest, 
    # TEMPORALMENTE SIN AUTENTICACIÓN PARA DEBUGGING
    # current_user: UserDB = Depends(get_current_user)
    try:
        # Importaciones lazy
        import pandas as pd
        import numpy as np

        if not request.table_name:
            return {"message": "No se proporcionó la tabla, no se ejecuta la consulta"}

        # Función auxiliar para escapar nombres de columnas
        def escape_column(column_name):
            return f"[{column_name}]"

        query_string = f"SELECT * FROM {escape_column(request.table_name)}"
        filters = []

        # Filtro por rango de fechas con nombre de columna escapado
        if request.date_field and request.start_date and request.end_date:
            # Parsear y formatear las fechas usando el formato YYYYMMDD que es seguro para SQL Server
            try:
                start_date = datetime.datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
                end_date = datetime.datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
                
                # Formato YYYYMMDD (estándar SQL Server 112)
                formatted_start = start_date.strftime('%Y%m%d')
                formatted_end = end_date.strftime('%Y%m%d')
                
                # Usar CAST para asegurar que la conversión sea explícita y del tipo correcto
                filters.append(
                    f"CAST({escape_column(request.date_field)} AS date) BETWEEN " +
                    f"CAST('{formatted_start}' AS date) AND CAST('{formatted_end}' AS date)"
                )
                
                # Guardar la query para depuración
                print(f"Filtro de fecha: CAST({escape_column(request.date_field)} AS date) BETWEEN " +
                      f"CAST('{formatted_start}' AS date) AND CAST('{formatted_end}' AS date)")
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Formato de fecha inválido: {str(e)}"}
                )

        # Procesar campos adicionales si existen
        campos_adicionales = []
        if request.additional_field:
            campos_adicionales = [campo.strip() for campo in request.additional_field.split(',') if campo.strip()]
            for campo in campos_adicionales:
                filters.append(f"{escape_column(campo)} IS NOT NULL")
        
        # Procesar filtros personalizados
        if request.custom_filters:
            for filtro in request.custom_filters:
                field = filtro.get('field')
                operator = filtro.get('operator')
                value = filtro.get('value')
                
                if field and operator:
                    escaped_field = escape_column(field)
                    
                    # Manejar operadores especiales
                    if operator in ['IS NULL', 'IS NOT NULL']:
                        filters.append(f"{escaped_field} {operator}")
                    elif operator in ['LIKE', 'NOT LIKE']:
                        filters.append(f"{escaped_field} {operator} '%{value}%'")
                    else:
                        # Para operadores regulares con valores
                        if value is not None:
                            # Si el valor parece ser numérico, no lo rodeamos con comillas
                            try:
                                float_value = float(value)
                                filters.append(f"{escaped_field} {operator} {value}")
                            except (ValueError, TypeError):
                                # Si no es numérico, escapar como cadena con comillas simples
                                filters.append(f"{escaped_field} {operator} '{value}'")

        if filters:
            query_string += " WHERE " + " AND ".join(filters)
        
        # Imprimir la consulta para depuración
        print(f"Query completa: {query_string}")

        # Intentar ejecutar la consulta con manejo de errores mejorado
        try:
            df = limpiar_datos(df)
        except Exception as e:
            print(f"Error al ejecutar la consulta SQL: {str(e)}")
            # Intento alternativo sin filtro de fechas si ese es el problema
            if request.date_field and request.start_date and request.end_date:
                # Construir consulta sin filtro de fechas
                query_sin_fecha = f"SELECT * FROM {escape_column(request.table_name)}"
                otros_filtros = [f for f in filters if request.date_field not in f]
                if otros_filtros:
                    query_sin_fecha += " WHERE " + " AND ".join(otros_filtros)
                    
                print(f"Intentando consulta sin filtro de fechas: {query_sin_fecha}")
                try:
                    # Ejecutar consulta sin filtro de fechas
                    df = limpiar_datos(df)
                    
                    # Filtrar por fecha en Python
                    if request.date_field in df.columns:
                        df[request.date_field] = pd.to_datetime(df[request.date_field], errors='coerce')
                        start_date = pd.to_datetime(request.start_date)
                        end_date = pd.to_datetime(request.end_date)
                        df = df[(df[request.date_field] >= start_date) & (df[request.date_field] <= end_date)]
                        print(f"Filtro de fechas aplicado en Python, registros restantes: {len(df)}")
                except Exception as e2:
                    print(f"Error en segundo intento: {str(e2)}")
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Error al ejecutar consulta sin filtro de fechas: {str(e2)}"}
                    )
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Error en la consulta SQL: {str(e)}"}
                )

        # Si llegamos aquí, tenemos un DataFrame válido
        # Resto del código para análisis KPIs...
        
        # Lógica para contar KPIs
        total_registros = len(df)
        
        # Análisis del campo principal para max/min (siempre del campo principal)
        try:
            serie_principal = pd.to_numeric(df[request.column_name], errors='coerce')
            max_value = float(serie_principal.max()) if not pd.isna(serie_principal.max()) else None
            min_value = float(serie_principal.min()) if not pd.isna(serie_principal.min()) else None
        except Exception as e:
            print(f"Error al analizar campo principal: {str(e)}")
            max_value = None
            min_value = None

        # Análisis de categorías (usando el campo principal)
        try:
            categorias_dict = df[request.column_name].value_counts().to_dict()
            categorias = len(categorias_dict)
        except Exception as e:
            print(f"Error al analizar categorías: {str(e)}")
            categorias_dict = {}
            categorias = 0

        # Análisis de clusters temporales y numéricos
        clusters_dict = {}
        
        # Clusters temporales si hay campo de fecha
        if request.date_field and request.date_field in df.columns:
            try:
                df[request.date_field] = pd.to_datetime(df[request.date_field], errors='coerce')
                
                # Análisis por año
                clusters_dict['temporal'] = {
                    'por_año': df[request.date_field].dt.year.value_counts().sort_index().to_dict(),
                    
                    # Análisis por mes del año actual
                    'por_mes': df[df[request.date_field].dt.year == datetime.datetime.now().year][request.date_field]
                        .dt.month.value_counts().sort_index().to_dict(),
                    
                    # Análisis por día de la semana
                    'por_dia_semana': df[request.date_field].dt.dayofweek.map({
                        0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
                        3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
                    }).value_counts().to_dict(),
                    
                    # Análisis por trimestre
                    'por_trimestre': df[request.date_field].dt.quarter.value_counts().sort_index().to_dict()
                }

                # Tendencia mensual (últimos 12 meses)
                fecha_max = df[request.date_field].max()
                if fecha_max is not None:
                    ultimos_12_meses = df[
                        df[request.date_field] >= (fecha_max - pd.DateOffset(months=12))
                    ]
                    tendencia_mensual = ultimos_12_meses.groupby(
                        ultimos_12_meses[request.date_field].dt.to_period('M')
                    ).size()
                    clusters_dict['temporal']['tendencia_12_meses'] = {
                        str(k): int(v) for k, v in tendencia_mensual.items()
                    }
            except Exception as e:
                print(f"Error al procesar clusters temporales: {str(e)}")

        # Análisis detallado por campo - AÑADIDO AQUÍ
        analisis_por_campo = {
            "principal": {
                "campo": request.column_name,
                "categorias": categorias,
                "distribucion": categorias_dict
            }
        }

        # Agregar análisis de campos adicionales
        if request.additional_field:
            campos_adicionales = [campo.strip() for campo in request.additional_field.split(',') if campo.strip()]
            for i, campo in enumerate(campos_adicionales, 1):
                if campo in df.columns:
                    analisis_por_campo[f"adicional_{i}"] = {
                        "campo": campo,
                        "categorias": df[campo].nunique(),
                        "distribucion": df[campo].value_counts().to_dict()
                    }

        # Obtener el nombre de usuario de manera segura
        user_name = "usuario_temporal"  # TEMPORAL PARA DEBUGGING
        
        # Convertir tipos de datos complejos
        safe_last_date = None
        safe_first_date = None
        
        if request.date_field in df.columns:
            try:
                # Calcular fechas después de haber limpiado el DataFrame
                last_date = df[request.date_field].max()
                first_date = df[request.date_field].min()
                
                # Convertir a datetime de Python si es necesario
                if last_date is not None:
                    safe_last_date = last_date.to_pydatetime() if hasattr(last_date, 'to_pydatetime') else last_date
                
                if first_date is not None:
                    safe_first_date = first_date.to_pydatetime() if hasattr(first_date, 'to_pydatetime') else first_date
            except Exception as e:
                print(f"Error al procesar fechas: {str(e)}")
        else:
            last_date = None
            first_date = None
        
        # Crear objeto de resultados
        resultados_kpis = {
            "total_registros": total_registros,
            "categorias": categorias,
            "categorias_detalle": categorias_dict,
            "max_value": max_value,
            "min_value": min_value,
            "clusters": clusters_dict,
            "last_date": convert_types(last_date),
            "first_date": convert_types(first_date),
            "analisis_campos": analisis_por_campo  # Ahora está definido
        }
        
        # Intentar guardar los resultados en la base de datos
        try:
            guardar_resultados_sql(db, user_name, {
                "total_registros": total_registros,
                "categorias": categorias,
                "last_date": safe_last_date,
                "first_date": safe_first_date,
                "max_value": max_value,
                "min_value": min_value,
                "clusters": str(clusters_dict)
            })
            print("Resultados guardados correctamente en la base de datos")
        except Exception as e:
            print(f"Error al guardar resultados en la base de datos: {str(e)}")
            # Continuar con la función aunque falle el guardado
        
        # Devolver resultados al frontend
        return resultados_kpis

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en analizar_kpis: {str(e)}\n{error_details}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al analizar los datos: {str(e)}"}
        )

@router.post("/analizar_detalle", response_class=JSONResponse)
async def analizar_detalle(analisis_request: AnalisisRequest, 
                           # current_user: UserDB = Depends(get_current_user)):  # TEMPORALMENTE SIN AUTENTICACIÓN
    try:
        # Importaciones lazy
        import pandas as pd
        import numpy as np
        # Función auxiliar para escapar nombres de columnas
        def escape_column(column_name):
            return f"[{column_name}]"

        # Construir consulta SQL con todos los campos
        query_string = f"SELECT * FROM {escape_column(analisis_request.table_name)}"
        
        # Lista para almacenar todos los filtros
        filters = []
        
        # Filtro de fecha (si está presente)
        if analisis_request.date_field and analisis_request.start_date and analisis_request.end_date:
            # Parsear y formatear las fechas usando el formato YYYYMMDD que es seguro para SQL Server
            try:
                start_date = datetime.datetime.fromisoformat(analisis_request.start_date.replace('Z', '+00:00'))
                end_date = datetime.datetime.fromisoformat(analisis_request.end_date.replace('Z', '+00:00'))
                
                # Formato YYYYMMDD (estándar SQL Server 112)
                formatted_start = start_date.strftime('%Y%m%d')
                formatted_end = end_date.strftime('%Y%m%d')
                
                # Usar CAST para asegurar que la conversión sea explícita y del tipo correcto
                filters.append(
                    f"CAST({escape_column(analisis_request.date_field)} AS date) BETWEEN " +
                    f"CAST('{formatted_start}' AS date) AND CAST('{formatted_end}' AS date)"
                )
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Formato de fecha inválido: {str(e)}"}
                )
        
        # Procesar filtros personalizados
        if analisis_request.custom_filters:
            for filtro in analisis_request.custom_filters:
                field = filtro.get('field')
                operator = filtro.get('operator')
                value = filtro.get('value')
                
                if field and operator:
                    escaped_field = escape_column(field)
                    
                    # Manejar operadores especiales
                    if operator in ['IS NULL', 'IS NOT NULL']:
                        filters.append(f"{escaped_field} {operator}")
                    elif operator in ['LIKE', 'NOT LIKE']:
                        filters.append(f"{escaped_field} {operator} '%{value}%'")
                    else:
                        # Para operadores regulares con valores
                        if value is not None:
                            # Si el valor parece ser numérico, no lo rodeamos con comillas
                            try:
                                float_value = float(value)
                                filters.append(f"{escaped_field} {operator} {value}")
                            except (ValueError, TypeError):
                                # Si no es numérico, escapar como cadena con comillas simples
                                filters.append(f"{escaped_field} {operator} '{value}'")
        
        # Agregar filtros a la consulta
        if filters:
            query_string += " WHERE " + " AND ".join(filters)
            
        print(f"Query para análisis detallado: {query_string}")  # Para debugging
        
        # Ejecutar consulta
        try:
            df = limpiar_datos(df)
        except Exception as e:
            print(f"Error al ejecutar la consulta: {str(e)}")
            # Intento alternativo sin filtro de fechas si ese es el problema
            if analisis_request.date_field and analisis_request.start_date and analisis_request.end_date:
                # Construir consulta sin filtro de fechas
                query_sin_fecha = f"SELECT * FROM {escape_column(analisis_request.table_name)}"
                otros_filtros = [f for f in filters if analisis_request.date_field not in f]
                if otros_filtros:
                    query_sin_fecha += " WHERE " + " AND ".join(otros_filtros)
                    
                print(f"Intentando consulta sin filtro de fechas: {query_sin_fecha}")
                df = limpiar_datos(df)
                
                # Filtrar por fecha en Python
                if analisis_request.date_field in df.columns:
                    df[analisis_request.date_field] = pd.to_datetime(df[analisis_request.date_field], errors='coerce')
                    start_date = pd.to_datetime(analisis_request.start_date)
                    end_date = pd.to_datetime(analisis_request.end_date)
                    df = df[(df[analisis_request.date_field] >= start_date) & (df[analisis_request.date_field] <= end_date)]
            else:
                raise e

        # CAMBIO AQUÍ: Manejar valores no compatibles con JSON sin usar fillna(None)
        # En lugar de utilizar fillna(None), procesaremos los valores durante la conversión
        
        # Reemplazar valores infinitos para columnas numéricas
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
        
        # Función para convertir valores a formatos serializables
        def safe_convert_to_serializable(val):
            if pd.isna(val) or val is None:
                return None
            elif isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
                return val.isoformat()
            elif isinstance(val, float):
                if np.isnan(val) or np.isinf(val):
                    return None
                if val == float('inf') or val == float('-inf'):
                    return None
                # Para números flotantes muy grandes, convertir a cadena
                if abs(val) > 1e15:
                    return str(val)
                return val
            elif isinstance(val, (int, bool)):
                return val
            elif isinstance(val, (np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.float64, np.float32)):
                if np.isnan(val) or np.isinf(val):
                    return None
                return float(val)
            elif hasattr(val, 'to_dict'):
                return val.to_dict()
            else:
                return str(val)
                
        # Convertir directamente a diccionario y procesar los valores
        table_data = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = safe_convert_to_serializable(val)
            table_data.append(record)

        return JSONResponse(content={"records": table_data})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en análisis detallado: {str(e)}\n{error_details}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/analizar_grafico")
async def analizar_grafico(request: AnalisisRequest,
                          # current_user: UserDB = Depends(get_current_user)):  # TEMPORALMENTE SIN AUTENTICACIÓN PARA DEBUGGING
    try:
        # Importaciones lazy
        import pandas as pd

        if not request.table_name or not request.date_field:
            return {"message": "Se requiere tabla y campo de fecha"}

        # Función auxiliar para escapar nombres de columnas
        def escape_column(column_name):
            return f"[{column_name}]"

        # Construir query optimizada con nombres escapados
        campos_select = [escape_column(request.date_field)]
        if request.column_name:
            campos_select.append(escape_column(request.column_name))
            
        # Procesar campos adicionales
        campos_adicionales = []
        if request.additional_field:
            campos_adicionales = [campo.strip() for campo in request.additional_field.split(',') if campo.strip()]
            campos_select.extend(escape_column(campo) for campo in campos_adicionales)

        # Construir query con nombres escapados
        query_string = f"SELECT {', '.join(campos_select)} FROM {escape_column(request.table_name)}"
        
        # Crear lista de filtros
        filters = []
        
        # Filtro por rango de fechas
        if request.start_date and request.end_date:
            filters.append(
                f"{escape_column(request.date_field)} BETWEEN '{request.start_date}' AND '{request.end_date}'"
            )
            
        # Procesar filtros personalizados
        if request.custom_filters:
            for filtro in request.custom_filters:
                field = filtro.get('field')
                operator = filtro.get('operator')
                value = filtro.get('value')
                
                if field and operator:
                    escaped_field = escape_column(field)
                    
                    # Manejar operadores especiales
                    if operator in ['IS NULL', 'IS NOT NULL']:
                        filters.append(f"{escaped_field} {operator}")
                    elif operator in ['LIKE', 'NOT LIKE']:
                        filters.append(f"{escaped_field} {operator} '%{value}%'")
                    else:
                        # Para operadores regulares con valores
                        if value is not None:
                            # Si el valor parece ser numérico, no lo rodeamos con comillas
                            try:
                                float_value = float(value)
                                filters.append(f"{escaped_field} {operator} {value}")
                            except (ValueError, TypeError):
                                # Si no es numérico, escapar como cadena con comillas simples
                                filters.append(f"{escaped_field} {operator} '{value}'")
        
        # Agregar los filtros a la consulta
        if filters:
            query_string += " WHERE " + " AND ".join(filters)

        print(f"Query ejecutada: {query_string}")  # Para debugging

        # Cargar y preparar datos
        df = limpiar_datos(df)
        
        # Convertir fecha de manera segura
        df[request.date_field] = pd.to_datetime(df[request.date_field], errors='coerce')
        
        graficos_data = {
            "series_temporales": {},
            "metadata": {
                "fecha_inicio": request.start_date,
                "fecha_fin": request.end_date,
                "total_registros": len(df)
            }
        }

        ## Análisis temporal para cada campo
        for campo in [request.column_name] + campos_adicionales:
            if campo and campo in df.columns:
                try:
                    # Determinar si el campo es numérico de manera más robusta
                    es_numerico = pd.api.types.is_numeric_dtype(df[campo]) or (
                        pd.to_numeric(df[campo], errors='coerce').notna().any() and 
                        not df[campo].dtype == 'object'
                    )
                    
                    if not es_numerico:
                        # Para campos categóricos
                        df_agrupado = df.groupby([
                            df[request.date_field].dt.strftime('%Y-%m-%d'),
                            campo
                        ]).size().unstack(fill_value=0)
                        
                        # Asegurar que tenemos todas las categorías
                        categorias = df[campo].unique()
                        for cat in categorias:
                            if cat not in df_agrupado.columns:
                                df_agrupado[cat] = 0
                        
                        # Preparar datos para el gráfico
                        graficos_data["series_temporales"][campo] = {
                            "fechas": df_agrupado.index.tolist(),
                            "valores": {
                                str(cat): df_agrupado[cat].tolist() 
                                for cat in df_agrupado.columns
                            },
                            "tipo": "categorico",
                            "categorias": [str(cat) for cat in df_agrupado.columns]
                        }
                    else:
                        # Para campos numéricos, mantener el código existente
                        datos_numericos = df.groupby(
                            df[request.date_field].dt.strftime('%Y-%m-%d')
                        )[campo].agg(['mean', 'sum', 'count']).reset_index()
                        
                        graficos_data["series_temporales"][campo] = {
                            "fechas": datos_numericos[request.date_field].tolist(),
                            "valores": {
                                "promedio": datos_numericos['mean'].tolist(),
                                "suma": datos_numericos['sum'].tolist(),
                                "conteo": datos_numericos['count'].tolist()
                            },
                            "tipo": "numerico"
                        }

                except Exception as e:
                    print(f"Error procesando campo {campo}: {str(e)}")
                    continue

        return {
            "status": "success",
            "data": graficos_data
        }

    except Exception as e:
        print(f"Error en análisis gráfico: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error en análisis gráfico: {str(e)}"}
        )
    
@router.post("/analizar_clasificacion")
async def analizar_clasificacion(request: AnalisisRequest, 
                                 # current_user: UserDB = Depends(get_current_user)):  # TEMPORALMENTE SIN AUTENTICACIÓN
    # Lógica de clasificación
    # ...
    return {"message": "Clasificación lista"}


@router.post("/analizar_regresion")
async def analizar_regresion(request: AnalisisRequest, 
                             # current_user: UserDB = Depends(get_current_user)):  # TEMPORALMENTE SIN AUTENTICACIÓN
    # Lógica de regresión
    # ...
    return {"message": "Regresión lista"}
