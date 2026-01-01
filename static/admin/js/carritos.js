// Variables globales
let carritos = [];
let currentPage = 1;
let totalPages = 1;
let itemsPerPage = 10;
let carritoSeleccionado = null;
let ordenActual = { campo: 'id', direccion: 'desc' };

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    verificarAutenticacion();
    cargarDatosIniciales();
    
    // Event listeners con verificación
    const searchInput = document.getElementById('searchInput');
    const filterEstado = document.getElementById('filterEstado');
    const prevPage = document.getElementById('prevPage');
    const nextPage = document.getElementById('nextPage');
    
    if (searchInput) {
        searchInput.addEventListener('input', filtrarCarritos);
    }
    
    if (filterEstado) {
        filterEstado.addEventListener('change', filtrarCarritos);
    }
    
    if (prevPage) {
        prevPage.addEventListener('click', () => cambiarPagina(currentPage - 1));
    }
    
    if (nextPage) {
        nextPage.addEventListener('click', () => cambiarPagina(currentPage + 1));
    }
});

// Autenticación
function verificarAutenticacion() {
    const token = localStorage.getItem('admin_token');
    const userStr = localStorage.getItem('admin_user');
    
    if (!token || !userStr) {
        window.location.href = '/admin/login';
        return;
    }
    
    try {
        const user = JSON.parse(userStr);
        document.getElementById('username').textContent = user.nombre || user.username || 'Usuario';
    } catch (e) {
        document.getElementById('username').textContent = userStr;
    }
}

function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = '/admin/login';
}

// Cargar datos iniciales
async function cargarDatosIniciales() {
    try {
        await cargarEstadisticas();
        await cargarCarritos();
    } catch (error) {
        console.error('Error cargando datos:', error);
        mostrarError('Error al cargar los datos');
    }
}

// Cargar estadísticas
async function cargarEstadisticas() {
    const token = localStorage.getItem('admin_token');
    
    if (!token) {
        console.error('No hay token de autenticación');
        return;
    }
    
    try {
        const response = await fetch('/admin/carritos/api/estadisticas', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Error en estadísticas:', response.status);
            console.error('Response completo:', errorText);
            
            // Intentar parsear como JSON para mostrar mejor el error
            try {
                const errorJson = JSON.parse(errorText);
                console.error('Error JSON:', errorJson);
                console.error('Detail:', errorJson.detail);
            } catch (e) {
                console.error('No se pudo parsear como JSON');
            }
            
            if (response.status === 401 || response.status === 422) {
                console.error('Token inválido o expirado, redirigiendo a login...');
                window.location.href = '/admin/login';
                return;
            }
            
            throw new Error(`Error ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        mostrarEstadisticas(data);
        
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
        // Mostrar stats con valores en 0 si falla
        mostrarEstadisticas({ por_estado: [] });
    }
}

// Mostrar estadísticas en las cards
function mostrarEstadisticas(data) {
    const estadosMap = {
        'activo': 0,
        'aceptado': 0,
        'preparando': 0,
        'completado': 0,
        'pendiente_entrega': 0,
        'finalizado': 0,
        'abandonado': 0,
        'total_valor': 0
    };
    
    // Llenar con datos del servidor
    if (data && data.por_estado) {
        data.por_estado.forEach(item => {
            const estado = item.estado || 'sin_estado';
            if (estadosMap.hasOwnProperty(estado)) {
                estadosMap[estado] = item.total_carritos || 0;
            }
            estadosMap.total_valor += (item.suma_total || 0);
        });
    }
    
    // Actualizar las cards con verificación de elementos
    const updateElement = (id, value) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    };
    
    updateElement('stat-activo', estadosMap['activo']);
    updateElement('stat-aceptado', estadosMap['aceptado']);
    updateElement('stat-preparando', estadosMap['preparando']);
    updateElement('stat-completado', estadosMap['completado']);
    updateElement('stat-pendiente_entrega', estadosMap['pendiente_entrega']);
    updateElement('stat-finalizado', estadosMap['finalizado']);
    updateElement('stat-abandonado', estadosMap['abandonado']);
    updateElement('stat-total-valor', formatearPrecio(estadosMap.total_valor));
    
    // Mostrar las cards
    const statsCards = document.getElementById('statsCards');
    if (statsCards) {
        statsCards.style.display = 'grid';
    }
}

// Cargar carritos
async function cargarCarritos() {
    const token = localStorage.getItem('admin_token');
    
    const searchInput = document.getElementById('searchInput');
    const filterEstado = document.getElementById('filterEstado');
    const searchTerm = searchInput ? searchInput.value : '';
    const estadoFiltro = filterEstado ? filterEstado.value : '';
    
    // Mostrar loading
    const loadingState = document.getElementById('loadingState');
    const carritosContent = document.getElementById('carritos-content');
    
    if (loadingState) loadingState.style.display = 'block';
    if (carritosContent) carritosContent.style.display = 'none';
    
    try {
        const params = new URLSearchParams({
            skip: (currentPage - 1) * itemsPerPage,
            limit: itemsPerPage
        });
        
        if (searchTerm) params.append('search', searchTerm);
        if (estadoFiltro) params.append('estado', estadoFiltro);
        
        const response = await fetch(`/admin/carritos/api/list?${params}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al cargar carritos');
        }
        
        const data = await response.json();
        carritos = data.carritos;
        totalPages = Math.ceil(data.total / itemsPerPage);
        
        mostrarCarritos();
        actualizarPaginacion();
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar los carritos');
    } finally {
        const loadingState = document.getElementById('loadingState');
        const carritosContent = document.getElementById('carritos-content');
        
        if (loadingState) loadingState.style.display = 'none';
        if (carritosContent) carritosContent.style.display = 'block';
    }
}

// Mostrar carritos en la tabla
function mostrarCarritos() {
    const tbody = document.getElementById('carritosBody');
    tbody.innerHTML = '';
    
    if (carritos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                    <i class="fas fa-shopping-basket" style="font-size: 3rem; margin-bottom: 15px; display: block;"></i>
                    No se encontraron carritos
                </td>
            </tr>
        `;
        return;
    }
    
    carritos.forEach(carrito => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        tr.style.transition = 'all 0.3s';
        tr.onmouseenter = function() { this.style.background = 'rgba(255,255,255,0.02)'; };
        tr.onmouseleave = function() { this.style.background = 'transparent'; };
        
        const estadoBadge = obtenerEstadoBadge(carrito.estado);
        const fechaFormateada = formatearFecha(carrito.created_at);
        
        tr.innerHTML = `
            <td style="padding: 15px; color: #c5a572; font-weight: 600;">#${carrito.id}</td>
            <td style="padding: 15px; color: white;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-user-circle" style="color: rgba(255,255,255,0.5);"></i>
                    <span>${carrito.usuario_nombre}</span>
                </div>
            </td>
            <td style="padding: 15px; color: rgba(255,255,255,0.7);">${fechaFormateada}</td>
            <td style="padding: 15px; text-align: center; color: white;">
                <span style="background: rgba(59, 130, 246, 0.2); color: #3b82f6; padding: 4px 12px; border-radius: 8px; font-weight: 600;">
                    ${carrito.items_count} items
                </span>
            </td>
            <td style="padding: 15px; text-align: right; color: #c5a572; font-weight: 700; font-size: 1.1rem;">
                ${formatearPrecio(carrito.total_carrito)}
            </td>
            <td style="padding: 15px; text-align: center;">${estadoBadge}</td>
            <td style="padding: 15px; text-align: center;">
                <button onclick="verDetalle(${carrito.id})" 
                    style="padding: 8px 16px; background: linear-gradient(135deg, #c5a572 0%, #8b7355 100%); border: none; border-radius: 8px; color: #0a0e1a; font-weight: 600; cursor: pointer; transition: all 0.3s; font-family: 'Inter', sans-serif;"
                    title="Ver detalles">
                    <i class="fas fa-eye"></i> Ver
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

// Obtener badge de estado
function obtenerEstadoBadge(estado) {
    const estadosConfig = {
        'activo': { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.2)', icon: 'shopping-cart', text: 'Activo', emoji: '🛒' },
        'aceptado': { color: '#10b981', bg: 'rgba(16, 185, 129, 0.2)', icon: 'check', text: 'Aceptado', emoji: '✅' },
        'preparando': { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.2)', icon: 'box', text: 'Preparando', emoji: '📦' },
        'completado': { color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.2)', icon: 'check-circle', text: 'Completado', emoji: '🎉' },
        'pendiente_entrega': { color: '#ec4899', bg: 'rgba(236, 72, 153, 0.2)', icon: 'truck', text: 'Pendiente de Entrega', emoji: '🚚' },
        'finalizado': { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.2)', icon: 'check-double', text: 'Finalizado', emoji: '✔️' },
        'abandonado': { color: '#fb923c', bg: 'rgba(251, 146, 60, 0.2)', icon: 'exclamation-triangle', text: 'Abandonado', emoji: '⚠️' }
    };
    
    const config = estadosConfig[estado] || { color: '#6b7280', bg: 'rgba(107, 114, 128, 0.2)', icon: 'question-circle', text: estado, emoji: '❓' };
    
    return `
        <span style="background: ${config.bg}; color: ${config.color}; padding: 6px 14px; border-radius: 8px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; font-size: 0.9rem;">
            <span>${config.emoji}</span>
            ${config.text}
        </span>
    `;
}

// Ver detalle del carrito
async function verDetalle(carritoId) {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch(`/admin/carritos/api/${carritoId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al obtener detalles del carrito');
        }
        
        const carrito = await response.json();
        mostrarModalDetalle(carrito);
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar los detalles del carrito');
    }
}

// Mostrar modal de detalle
function mostrarModalDetalle(carrito) {
    // Guardar el carrito seleccionado globalmente
    carritoSeleccionado = carrito;
    
    document.getElementById('detalle-id').textContent = `#${carrito.id}`;
    document.getElementById('detalle-usuario').textContent = carrito.usuario_nombre;
    document.getElementById('detalle-email').textContent = carrito.usuario_email || 'No disponible';
    document.getElementById('detalle-telefono').textContent = carrito.usuario_telefono || 'No disponible';
    document.getElementById('detalle-fecha').textContent = formatearFecha(carrito.created_at);
    document.getElementById('detalle-total').textContent = formatearPrecio(carrito.total_carrito);
    
    // Estado badge - usar innerHTML en lugar de outerHTML
    const estadoBadge = obtenerEstadoBadge(carrito.estado);
    const estadoContainer = document.getElementById('detalle-estado');
    if (estadoContainer) {
        estadoContainer.innerHTML = estadoBadge;
    }
    
    // Items
    const itemsContainer = document.getElementById('detalle-items');
    itemsContainer.innerHTML = '';
    
    if (carrito.items && carrito.items.length > 0) {
        carrito.items.forEach(item => {
            const itemDiv = document.createElement('div');
            itemDiv.style.cssText = 'padding: 15px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; margin-bottom: 10px;';
            itemDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="flex: 1; min-width: 200px;">
                        <div style="color: white; font-weight: 600; margin-bottom: 5px;">${item.nombre_producto}</div>
                        <div style="color: rgba(255,255,255,0.5); font-size: 0.9rem;">Producto ID: ${item.id_producto}</div>
                    </div>
                    <div style="display: flex; gap: 20px; align-items: center;">
                        <div style="text-align: center;">
                            <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin-bottom: 3px;">Cantidad</div>
                            <div style="color: white; font-weight: 600; font-size: 1.1rem;">${item.cantidad}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin-bottom: 3px;">Precio Unit.</div>
                            <div style="color: #c5a572; font-weight: 600;">${formatearPrecio(item.precio_unitario)}</div>
                        </div>
                        <div style="text-align: right; min-width: 100px;">
                            <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin-bottom: 3px;">Subtotal</div>
                            <div style="color: #c5a572; font-weight: 700; font-size: 1.2rem;">${formatearPrecio(item.subtotal)}</div>
                        </div>
                    </div>
                </div>
            `;
            itemsContainer.appendChild(itemDiv);
        });
    } else {
        itemsContainer.innerHTML = '<p style="text-align: center; padding: 20px; color: rgba(255,255,255,0.5);">No hay items en este carrito</p>';
    }
    
    // Mostrar modal
    const modal = document.getElementById('modalDetalle');
    modal.style.display = 'flex';
}

// Cerrar modal
function cerrarModal() {
    document.getElementById('modalDetalle').style.display = 'none';
    carritoSeleccionado = null;
}

// Abrir modal de cambio de estado
function abrirModalEstado() {
    if (!carritoSeleccionado) {
        mostrarError('No hay carrito seleccionado');
        return;
    }
    
    // Llenar información del modal
    document.getElementById('estado-carrito-id').textContent = `#${carritoSeleccionado.id}`;
    
    const estadoBadge = obtenerEstadoBadge(carritoSeleccionado.estado);
    document.getElementById('estado-actual-badge').innerHTML = estadoBadge;
    
    // Seleccionar el estado actual en el dropdown
    document.getElementById('nuevo-estado').value = carritoSeleccionado.estado;
    
    // Mostrar modal
    document.getElementById('modalEstado').style.display = 'flex';
}

// Cerrar modal de estado
function cerrarModalEstado() {
    document.getElementById('modalEstado').style.display = 'none';
}

// Confirmar cambio de estado
async function confirmarCambioEstado() {
    const carritoId = carritoSeleccionado.id;
    const nuevoEstado = document.getElementById('nuevo-estado').value;
    const token = localStorage.getItem('admin_token');
    
    if (!nuevoEstado || !carritoId) {
        mostrarError('Por favor selecciona un estado');
        return;
    }
    
    try {
        const response = await fetch(`/admin/carritos/api/${carritoId}/estado`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al cambiar estado');
        }
        
        const data = await response.json();
        
        // Mostrar mensaje de éxito
        let mensaje = `Estado cambiado exitosamente a "${data.estado_nuevo}"`;
        if (data.email_enviado) {
            mensaje += '\n✅ Se ha enviado un email de notificación al cliente.';
        }
        alert(mensaje);
        
        // Cerrar modales y recargar datos
        cerrarModalEstado();
        cerrarModal();
        await cargarDatosIniciales();
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cambiar estado: ' + error.message);
    }
}

// Filtrar carritos
function filtrarCarritos() {
    currentPage = 1;
    cargarCarritos();
}

// Filtrar por estado
function filtrarPorEstado(estado) {
    const selectEstado = document.getElementById('filterEstado');
    selectEstado.value = estado;
    filtrarCarritos();
}

// Ordenar por campo
function ordenarPor(campo) {
    if (ordenActual.campo === campo) {
        ordenActual.direccion = ordenActual.direccion === 'asc' ? 'desc' : 'asc';
    } else {
        ordenActual.campo = campo;
        ordenActual.direccion = 'asc';
    }
    
    carritos.sort((a, b) => {
        let valorA, valorB;
        
        switch(campo) {
            case 'id':
                valorA = a.id;
                valorB = b.id;
                break;
            case 'usuario':
                valorA = a.usuario_nombre.toLowerCase();
                valorB = b.usuario_nombre.toLowerCase();
                break;
            case 'fecha':
                valorA = new Date(a.created_at);
                valorB = new Date(b.created_at);
                break;
            case 'items':
                valorA = a.items_count;
                valorB = b.items_count;
                break;
            case 'total':
                valorA = a.total_carrito;
                valorB = b.total_carrito;
                break;
            case 'estado':
                valorA = a.estado;
                valorB = b.estado;
                break;
            default:
                return 0;
        }
        
        if (ordenActual.direccion === 'asc') {
            return valorA > valorB ? 1 : -1;
        } else {
            return valorA < valorB ? 1 : -1;
        }
    });
    
    mostrarCarritos();
}

// Paginación
function cambiarPagina(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    cargarCarritos();
}

function actualizarPaginacion() {
    document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;
    
    // Estilos de botones deshabilitados
    if (currentPage === 1) {
        document.getElementById('prevPage').style.opacity = '0.5';
        document.getElementById('prevPage').style.cursor = 'not-allowed';
    } else {
        document.getElementById('prevPage').style.opacity = '1';
        document.getElementById('prevPage').style.cursor = 'pointer';
    }
    
    if (currentPage === totalPages) {
        document.getElementById('nextPage').style.opacity = '0.5';
        document.getElementById('nextPage').style.cursor = 'not-allowed';
    } else {
        document.getElementById('nextPage').style.opacity = '1';
        document.getElementById('nextPage').style.cursor = 'pointer';
    }
}

// Utilidades
function formatearPrecio(precio) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    }).format(precio);
}

function formatearFecha(fecha) {
    if (!fecha) return 'N/A';
    const date = new Date(fecha);
    return date.toLocaleString('es-AR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Sistema de notificaciones Toast
function mostrarToast(mensaje, tipo = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${icons[tipo] || icons.info}"></i>
        </div>
        <div class="toast-message">${mensaje}</div>
        <button class="toast-close" onclick="cerrarToast(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        cerrarToast(toast.querySelector('.toast-close'));
    }, 5000);
}

function cerrarToast(button) {
    const toast = button.closest('.toast');
    if (!toast) return;
    
    toast.classList.add('removing');
    setTimeout(() => {
        toast.remove();
    }, 300);
}

function mostrarError(mensaje) {
    mostrarToast(mensaje, 'error');
}

function mostrarExito(mensaje) {
    mostrarToast(mensaje, 'success');
}

function mostrarInfo(mensaje) {
    mostrarToast(mensaje, 'info');
}

// Cerrar modal al hacer clic fuera
window.onclick = function(event) {
    const modalDetalle = document.getElementById('modalDetalle');
    const modalEstado = document.getElementById('modalEstado');
    
    if (event.target === modalDetalle) {
        cerrarModal();
    }
    
    if (event.target === modalEstado) {
        cerrarModalEstado();
    }
}
