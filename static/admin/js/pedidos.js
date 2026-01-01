// Variables globales
let pedidos = [];
let currentPage = 1;
let totalPages = 1;
let itemsPerPage = 10;
let pedidoSeleccionado = null;
let pedidosSeleccionados = new Set();
let ordenActual = { campo: 'id', direccion: 'desc' };

// Función global para manejar errores de autenticación
function manejarErrorAutenticacion(response) {
    if (response.status === 401) {
        console.warn('⚠️ Token expirado o inválido. Redirigiendo al login...');
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_user');
        
        // Mostrar mensaje breve antes de redirigir
        const mensaje = document.createElement('div');
        mensaje.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(231, 76, 60, 0.95);
            color: white;
            padding: 20px 40px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            z-index: 10001;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            text-align: center;
        `;
        mensaje.innerHTML = '<i class="fas fa-lock"></i> Sesión expirada. Redirigiendo al login...';
        document.body.appendChild(mensaje);
        
        // Redirigir después de 1.5 segundos
        setTimeout(() => {
            window.location.href = '/admin/login';
        }, 1500);
        
        return true;
    }
    return false;
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    verificarAutenticacion();
    cargarDatosIniciales();
    
    // Event listeners
    document.getElementById('searchInput').addEventListener('input', filtrarPedidos);
    document.getElementById('filterEstado').addEventListener('change', filtrarPedidos);
    document.getElementById('filterMetodoPago').addEventListener('change', filtrarPedidos);
    document.getElementById('prevPage').addEventListener('click', () => cambiarPagina(currentPage - 1));
    document.getElementById('nextPage').addEventListener('click', () => cambiarPagina(currentPage + 1));
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
        await cargarPedidos();
    } catch (error) {
        console.error('Error cargando datos:', error);
        mostrarError('Error al cargar los datos');
    }
}

// Cargar estadísticas
async function cargarEstadisticas() {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch('/admin/pedidos/api/estadisticas', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            throw new Error('Error al cargar estadísticas');
        }
        
        const data = await response.json();
        mostrarEstadisticas(data);
        
    } catch (error) {
        console.error('Error:', error);
        // No mostramos error, solo ocultamos las cards
    }
}

// Mostrar estadísticas en las cards
function mostrarEstadisticas(data) {
    const estadosMap = {
        'pendiente': 0,
        'pendiente_pago_efectivo': 0,
        'procesando': 0,
        'enviado': 0,
        'entregado': 0,
        'cancelado': 0
    };
    
    // Llenar con datos del servidor
    if (data.por_estado) {
        data.por_estado.forEach(item => {
            if (estadosMap.hasOwnProperty(item.estado)) {
                estadosMap[item.estado] = item.total_pedidos;
            }
        });
    }
    
    // Agrupar pendiente y pendiente_pago_efectivo juntos para la card de pendientes
    const totalPendientes = estadosMap.pendiente + estadosMap.pendiente_pago_efectivo;
    
    // Actualizar las cards
    document.getElementById('stat-pendiente').textContent = totalPendientes;
    document.getElementById('stat-procesando').textContent = estadosMap.procesando;
    document.getElementById('stat-enviado').textContent = estadosMap.enviado;
    document.getElementById('stat-entregado').textContent = estadosMap.entregado;
    document.getElementById('stat-cancelado').textContent = estadosMap.cancelado;
    
    // Mostrar las cards
    document.getElementById('statsCards').style.display = 'grid';
}

// Cargar pedidos
async function cargarPedidos() {
    const token = localStorage.getItem('admin_token');
    const search = document.getElementById('searchInput').value;
    const estado = document.getElementById('filterEstado').value;
    const metodoPago = document.getElementById('filterMetodoPago').value;
    
    if (!token) {
        console.error('No hay token de autenticación');
        window.location.href = '/admin/login';
        return;
    }
    
    try {
        document.getElementById('loadingState').style.display = 'flex';
        document.getElementById('pedidos-content').style.display = 'none';
        
        const skip = (currentPage - 1) * itemsPerPage;
        let url = `/admin/pedidos/api/list?skip=${skip}&limit=${itemsPerPage}`;
        
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (estado) url += `&estado=${estado}`;
        if (metodoPago) url += `&metodo_pago=${metodoPago}`;
        
        console.log('Haciendo petición a:', url);
        console.log('Token:', token ? 'Presente' : 'Ausente');
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) {
                return;
            }
            throw new Error('Error al cargar pedidos');
        }
        
        const data = await response.json();
        pedidos = data.pedidos;
        totalPages = Math.ceil(data.total / itemsPerPage);
        
        mostrarPedidos();
        actualizarPaginacion();
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar pedidos');
    } finally {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('pedidos-content').style.display = 'block';
    }
}

// Mostrar pedidos en la tabla
function mostrarPedidos() {
    const tbody = document.getElementById('pedidosBody');
    
    if (pedidos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px;">
                    <i class="fas fa-inbox" style="font-size: 48px; opacity: 0.3; margin-bottom: 10px;"></i>
                    <p style="opacity: 0.5;">No se encontraron pedidos</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = pedidos.map(pedido => `
        <tr>
            <td>
                <input type="checkbox" 
                       class="pedido-checkbox" 
                       data-pedido-id="${pedido.id}"
                       ${pedidosSeleccionados.has(pedido.id) ? 'checked' : ''}
                       onchange="togglePedidoSeleccion('${pedido.id}')">
            </td>
            <td>#${pedido.id}</td>
            <td>
                <div class="usuario-info" style="cursor: pointer;" onclick="verDatosUsuario('${pedido.id_usuario}')" title="Ver datos de contacto">
                    <i class="fas fa-user"></i> ${pedido.usuario_nombre || `Usuario #${pedido.id_usuario}`}
                </div>
            </td>
            <td>${formatearFecha(pedido.fecha_pedido)}</td>
            <td class="precio">${formatearPrecio(pedido.total)}</td>
            <td>
                <span class="badge badge-${getEstadoClass(pedido.estado)}">
                    ${pedido.estado}
                </span>
            </td>
            <td>
                <span class="metodo-pago">
                    <i class="fas fa-${getMetodoIcon(pedido.metodo_pago)}"></i>
                    ${pedido.metodo_pago}
                </span>
            </td>
            <td>${pedido.items_count || 0} items</td>
            <td>
                <div class="action-buttons">
                    ${obtenerBotonSiguienteEstado(pedido.id, pedido.estado)}
                    <button class="btn-icon" onclick="verDetalle('${pedido.id}')" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="abrirModalEstado('${pedido.id}', '${pedido.estado}')" title="Cambiar estado">
                        <i class="fas fa-edit"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    actualizarBulkActions();
}

// Ver detalle del pedido
async function verDetalle(id) {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch(`/admin/pedidos/api/${id}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            throw new Error('Error al cargar detalle del pedido');
        }
        
        const pedido = await response.json();
        mostrarDetalleModal(pedido);
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar el detalle del pedido');
    }
}

// Mostrar modal con detalles
function mostrarDetalleModal(pedido) {
    // Guardar pedido actual para edición
    pedidoActualParaEditar = pedido;
    
    document.getElementById('detalle-id').textContent = `#${pedido.id}`;
    document.getElementById('detalle-usuario').textContent = pedido.usuario_nombre || `Usuario #${pedido.id_usuario}`;
    document.getElementById('detalle-fecha').textContent = formatearFecha(pedido.fecha_pedido);
    document.getElementById('detalle-estado').innerHTML = `<span class="badge badge-${getEstadoClass(pedido.estado)}">${pedido.estado}</span>`;
    document.getElementById('detalle-metodo').textContent = pedido.metodo_pago;
    document.getElementById('detalle-total').textContent = formatearPrecio(pedido.total);
    
    // Mostrar items
    const itemsHtml = pedido.items.map(item => `
        <div class="item-card">
            <div class="item-info">
                <strong>${item.nombre_producto}</strong>
                <span class="item-detalle">
                    Cantidad: ${item.cantidad} × ${formatearPrecio(item.precio_unitario)}
                </span>
            </div>
            <div class="item-total">
                ${formatearPrecio(item.cantidad * item.precio_unitario)}
            </div>
        </div>
    `).join('');
    
    document.getElementById('detalle-items').innerHTML = itemsHtml;
    document.getElementById('modalDetalle').classList.add('show');
}

// Cerrar modal de detalle
function cerrarModal() {
    document.getElementById('modalDetalle').classList.remove('show');
}

// Abrir modal para cambiar estado
function abrirModalEstado(id, estadoActual) {
    pedidoSeleccionado = id;
    
    // Actualizar título y mensaje del modal
    document.getElementById('modal-estado-titulo').textContent = 'Cambiar Estado del Pedido';
    document.getElementById('estado-pedido-id').value = id;
    document.getElementById('estado-actual').innerHTML = `Pedido <strong>#${id}</strong> - Estado actual: <strong>${estadoActual}</strong>`;
    document.getElementById('nuevo-estado').value = '';
    document.getElementById('modalEstado').classList.add('show');
}

// Cerrar modal de estado
function cerrarModalEstado() {
    document.getElementById('modalEstado').classList.remove('show');
    pedidoSeleccionado = null;
}

// Cambiar estado del pedido (individual o masivo)
async function cambiarEstado(e) {
    e.preventDefault();
    
    const token = localStorage.getItem('admin_token');
    const id = document.getElementById('estado-pedido-id').value;
    const nuevoEstado = document.getElementById('nuevo-estado').value;
    
    // Si es cambio masivo
    if (id === 'bulk') {
        await cambiarEstadoMasivoSubmit(nuevoEstado);
        return;
    }
    
    // Si es cambio individual
    try {
        // Mostrar indicador de carga
        mostrarCargando('Actualizando estado y enviando notificación...');
        
        const response = await fetch(`/admin/pedidos/api/${id}/estado`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            const error = await response.json();
            throw new Error(error.detail || 'Error al cambiar el estado');
        }
        
        cerrarModalEstado();
        
        // Recargar tanto pedidos como estadísticas
        await Promise.all([
            cargarPedidos(),
            cargarEstadisticas()
        ]);
        
        ocultarCargando();
        mostrarExito('Estado actualizado correctamente');
        
    } catch (error) {
        console.error('Error:', error);
        ocultarCargando();
        mostrarError(error.message);
    }
}

// Cambiar estado de múltiples pedidos
async function cambiarEstadoMasivoSubmit(nuevoEstado) {
    const token = localStorage.getItem('admin_token');
    const pedidosArray = Array.from(pedidosSeleccionados);
    
    console.log('Cambio masivo - Pedidos:', pedidosArray);
    console.log('Cambio masivo - Nuevo estado:', nuevoEstado);
    
    const payload = { 
        pedido_ids: pedidosArray,
        estado: nuevoEstado 
    };
    
    console.log('Payload a enviar:', JSON.stringify(payload));
    
    try {
        // Mostrar indicador de carga
        mostrarCargando(`Actualizando ${pedidosArray.length} pedido(s) y enviando notificaciones...`);
        
        const response = await fetch(`/admin/pedidos/api/estado/bulk`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            
            const error = await response.json();
            console.error('Error del servidor completo:', JSON.stringify(error, null, 2));
            
            // Si es un error de validación de FastAPI
            if (error.detail && Array.isArray(error.detail)) {
                const errores = error.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join('\n');
                throw new Error(`Error de validación:\n${errores}`);
            }
            
            throw new Error(error.detail || 'Error al cambiar los estados');
        }
        
        const data = await response.json();
        
        cerrarModalEstado();
        limpiarSeleccion();
        
        // Recargar tanto pedidos como estadísticas
        await Promise.all([
            cargarPedidos(),
            cargarEstadisticas()
        ]);
        
        ocultarCargando();
        mostrarExito(`${data.actualizados} pedidos actualizados correctamente`);
        
    } catch (error) {
        console.error('Error:', error);
        ocultarCargando();
        mostrarError(error.message);
    }
}

// Filtrar pedidos
function filtrarPedidos() {
    currentPage = 1;
    cargarPedidos();
}

// Filtrar por estado desde las cards
function filtrarPorEstado(estado) {
    const filtroEstado = document.getElementById('filterEstado');
    
    // Si ya está filtrado por ese estado, limpiar filtro
    if (filtroEstado.value === estado) {
        filtroEstado.value = '';
    } else {
        filtroEstado.value = estado;
    }
    
    filtrarPedidos();
}

// Cambiar página
function cambiarPagina(pagina) {
    if (pagina < 1 || pagina > totalPages) return;
    currentPage = pagina;
    cargarPedidos();
}

// Actualizar paginación
function actualizarPaginacion() {
    document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;
    document.getElementById('pagination').style.display = totalPages > 1 ? 'flex' : 'none';
}

// Utilidades
function formatearFecha(fecha) {
    if (!fecha) return 'N/A';
    const date = new Date(fecha);
    return date.toLocaleDateString('es-AR', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatearPrecio(precio) {
    if (precio === null || precio === undefined) return '$0.00';
    return `$${parseFloat(precio).toFixed(2)}`;
}

function getEstadoClass(estado) {
    const clases = {
        'pendiente': 'warning',
        'pendiente_pago_efectivo': 'warning',
        'procesando': 'info',
        'enviado': 'primary',
        'entregado': 'success',
        'cancelado': 'danger'
    };
    return clases[estado] || 'default';
}

function getMetodoIcon(metodo) {
    const iconos = {
        'efectivo': 'money-bill-wave',
        'mercadopago': 'credit-card',
        'presupuesto': 'file-invoice-dollar'
    };
    return iconos[metodo] || 'shopping-cart';
}

// Obtener botón de siguiente estado
function obtenerBotonSiguienteEstado(pedidoId, estadoActual) {
    console.log('obtenerBotonSiguienteEstado llamado:', { pedidoId, estadoActual });
    
    // Flujo de estados para pedidos
    const flujoEstados = {
        'pendiente': { siguiente: 'procesando', texto: '⚡ Procesar Pedido', icon: 'box', color: '#3498db' },
        'pendiente_pago_efectivo': { siguiente: 'procesando', texto: '⚡ Procesar Pedido', icon: 'box', color: '#3498db' },
        'procesando': { siguiente: 'enviado', texto: '🚚 Marcar Enviado', icon: 'truck', color: '#9b59b6' },
        'enviado': { siguiente: 'entregado', texto: '✅ Marcar Entregado', icon: 'check-circle', color: '#27ae60' },
        'entregado': null,
        'cancelado': null
    };
    
    const accion = flujoEstados[estadoActual];
    console.log('Acción encontrada:', accion);
    
    if (!accion) {
        // No hay siguiente estado, no mostrar botón
        console.log('No hay siguiente estado para:', estadoActual);
        return '';
    }
    
    const botonHTML = `
        <button class="btn-quick-action" 
                onclick="avanzarSiguienteEstado('${pedidoId}', '${estadoActual}')" 
                title="Avanzar a: ${accion.texto}"
                style="background: ${accion.color}; font-weight: 700; font-size: 0.9rem;">
            <i class="fas fa-${accion.icon}"></i> ${accion.texto}
        </button>
    `;
    console.log('Botón HTML generado:', botonHTML);
    return botonHTML;
}

// Avanzar al siguiente estado automáticamente
async function avanzarSiguienteEstado(pedidoId, estadoActual) {
    const token = localStorage.getItem('admin_token');
    
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }
    
    // Confirmación
    const flujoTextos = {
        'pendiente': 'marcar como procesando',
        'pendiente_pago_efectivo': 'marcar como procesando',
        'procesando': 'marcar como enviado',
        'enviado': 'marcar como entregado'
    };
    
    const accionTexto = flujoTextos[estadoActual] || 'avanzar';
    
    if (!confirm(`¿Estás seguro de ${accionTexto} el pedido #${pedidoId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/pedidos/api/${pedidoId}/siguiente-estado`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            const error = await response.json();
            throw new Error(error.detail || 'Error al avanzar estado');
        }
        
        const data = await response.json();
        
        // Mostrar mensaje de éxito
        mostrarExito(`Pedido #${pedidoId}: ${data.estado_anterior} → ${data.estado_nuevo}`);
        
        // Recargar tanto pedidos como estadísticas
        await Promise.all([
            cargarPedidos(),
            cargarEstadisticas()
        ]);
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError(error.message || 'Error al avanzar estado del pedido');
    }
}

function mostrarExito(mensaje) {
    alert(mensaje); // Reemplazar con notificación personalizada
}

function mostrarError(mensaje) {
    alert(mensaje); // Reemplazar con notificación personalizada
}

// ===== FUNCIONES DE SELECCIÓN MÚLTIPLE =====

// Toggle selección de un pedido individual
function togglePedidoSeleccion(pedidoId) {
    if (pedidosSeleccionados.has(pedidoId)) {
        pedidosSeleccionados.delete(pedidoId);
    } else {
        pedidosSeleccionados.add(pedidoId);
    }
    actualizarBulkActions();
    actualizarSelectAll();
}

// Toggle seleccionar todos
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.pedido-checkbox');
    
    if (selectAllCheckbox.checked) {
        // Seleccionar todos los pedidos visibles
        checkboxes.forEach(checkbox => {
            const pedidoId = checkbox.dataset.pedidoId; // Mantener como string
            pedidosSeleccionados.add(pedidoId);
            checkbox.checked = true;
        });
    } else {
        // Deseleccionar todos
        pedidosSeleccionados.clear();
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
    }
    
    actualizarBulkActions();
}

// Actualizar estado del checkbox "Seleccionar todos"
function actualizarSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.pedido-checkbox');
    const checkedCheckboxes = document.querySelectorAll('.pedido-checkbox:checked');
    
    if (checkboxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCheckboxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCheckboxes.length === checkboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

// Actualizar barra de acciones en lote
function actualizarBulkActions() {
    const bulkActions = document.getElementById('bulkActions');
    const selectedCount = document.getElementById('selectedCount');
    const count = pedidosSeleccionados.size;
    
    if (count > 0) {
        bulkActions.style.display = 'flex';
        selectedCount.textContent = `${count} pedido${count > 1 ? 's' : ''} seleccionado${count > 1 ? 's' : ''}`;
    } else {
        bulkActions.style.display = 'none';
    }
    
    actualizarSelectAll();
}

// Limpiar selección
function limpiarSeleccion() {
    pedidosSeleccionados.clear();
    const checkboxes = document.querySelectorAll('.pedido-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    actualizarBulkActions();
}

// ===== FUNCIONES DE INDICADOR DE CARGA =====

function mostrarCargando(mensaje = 'Procesando...') {
    // Remover loader existente si hay
    ocultarCargando();
    
    // Crear overlay de carga
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        backdrop-filter: blur(3px);
    `;
    
    // Crear contenedor del loader
    const loaderContainer = document.createElement('div');
    loaderContainer.style.cssText = `
        background: white;
        padding: 30px 40px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        text-align: center;
        max-width: 400px;
    `;
    
    // Crear spinner
    const spinner = document.createElement('div');
    spinner.style.cssText = `
        width: 50px;
        height: 50px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    `;
    
    // Agregar keyframes para la animación
    if (!document.getElementById('spinner-style')) {
        const style = document.createElement('style');
        style.id = 'spinner-style';
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Crear mensaje
    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
        color: #333;
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 10px;
    `;
    messageDiv.textContent = mensaje;
    
    // Crear submensaje
    const subMessage = document.createElement('div');
    subMessage.style.cssText = `
        color: #666;
        font-size: 13px;
        margin-top: 8px;
    `;
    subMessage.textContent = 'Por favor espere...';
    
    // Ensamblar elementos
    loaderContainer.appendChild(spinner);
    loaderContainer.appendChild(messageDiv);
    loaderContainer.appendChild(subMessage);
    overlay.appendChild(loaderContainer);
    document.body.appendChild(overlay);
}

function ocultarCargando() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// Abrir modal para cambio de estado masivo
function cambiarEstadoMasivo() {
    if (pedidosSeleccionados.size === 0) {
        mostrarError('No hay pedidos seleccionados');
        return;
    }
    
    const count = pedidosSeleccionados.size;
    
    // Actualizar título y mensaje del modal
    document.getElementById('modal-estado-titulo').textContent = 'Cambio de Estado Masivo';
    document.getElementById('estado-pedido-id').value = 'bulk';
    document.getElementById('estado-actual').innerHTML = `<strong>${count}</strong> pedido${count > 1 ? 's' : ''} seleccionado${count > 1 ? 's' : ''}`;
    document.getElementById('nuevo-estado').value = '';
    document.getElementById('modalEstado').classList.add('show');
}

// ===== FUNCIONES DE MODAL DE USUARIO =====

// Ver datos de contacto del usuario
async function verDatosUsuario(usuarioId) {
    const token = localStorage.getItem('admin_token');
    
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }
    
    try {
        // Mostrar modal y loading
        document.getElementById('modalUsuario').classList.add('show');
        document.getElementById('loadingUsuario').style.display = 'flex';
        document.getElementById('datosUsuario').style.display = 'none';
        
        // Hacer petición al endpoint
        const response = await fetch(`/admin/pedidos/api/usuario/${usuarioId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) {
                return;
            }
            throw new Error('Error al cargar datos del usuario');
        }
        
        const usuario = await response.json();
        
        // Mostrar datos del usuario
        document.getElementById('usuario-nombre').textContent = usuario.nombre || 'Sin nombre';
        
        // Email con link
        const emailElement = document.getElementById('usuario-email');
        if (usuario.email) {
            emailElement.innerHTML = `<a href="mailto:${usuario.email}" style="color: #667eea; text-decoration: none;"><i class="fas fa-envelope"></i> ${usuario.email}</a>`;
        } else {
            emailElement.textContent = 'No registrado';
        }
        
        // Teléfono con link a WhatsApp
        const telefonoElement = document.getElementById('usuario-telefono');
        if (usuario.telefono) {
            // Limpiar el teléfono para WhatsApp (quitar espacios, guiones, paréntesis)
            const telefonoLimpio = usuario.telefono.replace(/[\s\-\(\)]/g, '');
            const whatsappUrl = `https://wa.me/${telefonoLimpio}`;
            telefonoElement.innerHTML = `<a href="${whatsappUrl}" target="_blank" style="color: #25D366; text-decoration: none;"><i class="fab fa-whatsapp"></i> ${usuario.telefono}</a>`;
        } else {
            telefonoElement.textContent = 'No registrado';
        }
        
        // Ocultar loading y mostrar datos
        document.getElementById('loadingUsuario').style.display = 'none';
        document.getElementById('datosUsuario').style.display = 'block';
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar los datos del usuario');
        cerrarModalUsuario();
    }
}

// Cerrar modal de usuario
function cerrarModalUsuario() {
    document.getElementById('modalUsuario').classList.remove('show');
}

// ===== FUNCIONES DE EDICIÓN DE PEDIDO =====

let pedidoActualParaEditar = null;
let itemsEditando = [];
let timeoutBusqueda = null;

// Abrir modal para editar pedido
function abrirModalEditarPedido() {
    if (!pedidoActualParaEditar) {
        mostrarError('No hay pedido seleccionado');
        return;
    }
    
    // Cargar items actuales del pedido
    itemsEditando = [...pedidoActualParaEditar.items];
    
    document.getElementById('editar-pedido-id').textContent = pedidoActualParaEditar.id;
    document.getElementById('motivo-edicion').value = '';
    
    // Mostrar items
    actualizarListaItemsEdicion();
    
    // Ocultar modal de detalle y mostrar modal de edición
    document.getElementById('modalDetalle').classList.remove('show');
    document.getElementById('modalEditarPedido').classList.add('show');
    
    // Configurar búsqueda de productos
    const inputBusqueda = document.getElementById('buscar-producto-input');
    inputBusqueda.value = '';
    inputBusqueda.addEventListener('input', buscarProductosParaAgregar);
}

// Cerrar modal de editar pedido
function cerrarModalEditarPedido() {
    document.getElementById('modalEditarPedido').classList.remove('show');
    document.getElementById('resultados-busqueda').style.display = 'none';
    // Volver a mostrar modal de detalle
    document.getElementById('modalDetalle').classList.add('show');
}

// Buscar productos para agregar
async function buscarProductosParaAgregar(e) {
    const query = e.target.value.trim();
    
    // Limpiar timeout anterior
    if (timeoutBusqueda) {
        clearTimeout(timeoutBusqueda);
    }
    
    if (query.length < 2) {
        document.getElementById('resultados-busqueda').style.display = 'none';
        return;
    }
    
    // Esperar 300ms después de que el usuario deje de escribir
    timeoutBusqueda = setTimeout(async () => {
        const token = localStorage.getItem('admin_token');
        
        try {
            const response = await fetch(`/admin/pedidos/api/productos/buscar?q=${encodeURIComponent(query)}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                if (manejarErrorAutenticacion(response)) return;
                throw new Error('Error al buscar productos');
            }
            
            const data = await response.json();
            mostrarResultadosBusqueda(data.productos);
            
        } catch (error) {
            console.error('Error:', error);
        }
    }, 300);
}

// Mostrar resultados de búsqueda
function mostrarResultadosBusqueda(productos) {
    const container = document.getElementById('resultados-busqueda');
    
    if (productos.length === 0) {
        container.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">No se encontraron productos</div>';
        container.style.display = 'block';
        return;
    }
    
    container.innerHTML = productos.map(p => `
        <div class="producto-resultado" onclick="agregarProductoAlPedido(${p.id}, '${p.nombre.replace(/'/g, "\\'")}', ${p.precio})" 
             style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; color: #333;"
             onmouseover="this.style.background='#f8f9fa'" 
             onmouseout="this.style.background='white'">
            <strong style="color: #2c3e50; font-weight: 600;">${p.nombre}</strong> ${p.codigo ? `<span style="color: #666;">(${p.codigo})</span>` : ''}<br>
            <span style="color: #27ae60; font-weight: bold;">$${p.precio.toFixed(2)}</span>
            ${p.stock !== null ? `<span style="color: #666; margin-left: 10px;">Stock: ${p.stock}</span>` : ''}
        </div>
    `).join('');
    
    container.style.display = 'block';
}

// Agregar producto al pedido
function agregarProductoAlPedido(id, nombre, precio) {
    // Verificar si el producto ya existe
    const itemExistente = itemsEditando.find(item => item.id_producto === id);
    
    if (itemExistente) {
        itemExistente.cantidad++;
    } else {
        itemsEditando.push({
            id_producto: id,
            nombre_producto: nombre,
            cantidad: 1,
            precio_unitario: precio
        });
    }
    
    // Limpiar búsqueda
    document.getElementById('buscar-producto-input').value = '';
    document.getElementById('resultados-busqueda').style.display = 'none';
    
    // Actualizar lista
    actualizarListaItemsEdicion();
}

// Actualizar lista de items en edición
function actualizarListaItemsEdicion() {
    const container = document.getElementById('items-editar-lista');
    
    if (itemsEditando.length === 0) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666; background: #f8f9fa; border-radius: 8px; border: 1px dashed #dee2e6;">No hay items en el pedido. Busca y agrega productos arriba.</div>';
        document.getElementById('total-editar').textContent = '0.00';
        return;
    }
    
    let total = 0;
    
    container.innerHTML = itemsEditando.map((item, index) => {
        const subtotal = item.cantidad * item.precio_unitario;
        total += subtotal;
        
        return `
            <div class="item-editar" style="display: flex; align-items: center; padding: 15px; border: 1px solid #dee2e6; border-radius: 8px; margin-bottom: 10px; background: #f8f9fa;">
                <div style="flex: 1;">
                    <strong style="color: #2c3e50; font-size: 15px;">${item.nombre_producto}</strong><br>
                    <span style="color: #666; font-size: 0.9em;">$${item.precio_unitario.toFixed(2)} c/u</span>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <button onclick="cambiarCantidadItem(${index}, -1)" 
                            style="width: 30px; height: 30px; border: none; background: #e74c3c; color: white; border-radius: 4px; cursor: pointer; font-size: 16px;"
                            ${item.cantidad <= 1 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
                        <i class="fas fa-minus"></i>
                    </button>
                    <input type="number" value="${item.cantidad}" min="1" 
                           onchange="actualizarCantidadItem(${index}, this.value)"
                           style="width: 60px; text-align: center; padding: 5px; border: 1px solid #ddd; border-radius: 4px;">
                    <button onclick="cambiarCantidadItem(${index}, 1)" 
                            style="width: 30px; height: 30px; border: none; background: #27ae60; color: white; border-radius: 4px; cursor: pointer; font-size: 16px;">
                        <i class="fas fa-plus"></i>
                    </button>
                    <div style="min-width: 80px; text-align: right; font-weight: bold; color: #27ae60;">
                        $${subtotal.toFixed(2)}
                    </div>
                    <button onclick="eliminarItem(${index})" 
                            style="width: 30px; height: 30px; border: none; background: #95a5a6; color: white; border-radius: 4px; cursor: pointer;">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('total-editar').textContent = total.toFixed(2);
}

// Cambiar cantidad de un item
function cambiarCantidadItem(index, cambio) {
    itemsEditando[index].cantidad += cambio;
    if (itemsEditando[index].cantidad < 1) {
        itemsEditando[index].cantidad = 1;
    }
    actualizarListaItemsEdicion();
}

// Actualizar cantidad de item desde input
function actualizarCantidadItem(index, nuevaCantidad) {
    const cantidad = parseInt(nuevaCantidad);
    if (cantidad > 0) {
        itemsEditando[index].cantidad = cantidad;
    } else {
        itemsEditando[index].cantidad = 1;
    }
    actualizarListaItemsEdicion();
}

// Eliminar item
function eliminarItem(index) {
    if (confirm('¿Eliminar este item del pedido?')) {
        itemsEditando.splice(index, 1);
        actualizarListaItemsEdicion();
    }
}

// Guardar cambios del pedido
async function guardarCambiosPedido() {
    if (itemsEditando.length === 0) {
        mostrarError('El pedido debe tener al menos un item');
        return;
    }
    
    if (!confirm('¿Guardar los cambios en el pedido? Se creará un registro en el historial.')) {
        return;
    }
    
    const token = localStorage.getItem('admin_token');
    const pedidoId = pedidoActualParaEditar.id;
    const motivo = document.getElementById('motivo-edicion').value.trim();
    
    try {
        mostrarCargando('Guardando cambios...');
        
        const response = await fetch(`/admin/pedidos/api/${pedidoId}/items`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                items: itemsEditando,
                motivo: motivo || null
            })
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            const error = await response.json();
            throw new Error(error.detail || 'Error al guardar cambios');
        }
        
        const data = await response.json();
        
        ocultarCargando();
        cerrarModalEditarPedido();
        cerrarModal();
        
        // Recargar pedidos
        await cargarPedidos();
        
        mostrarExito(`Pedido actualizado. Total anterior: $${data.total_anterior.toFixed(2)}, Total nuevo: $${data.total_nuevo.toFixed(2)}`);
        
    } catch (error) {
        console.error('Error:', error);
        ocultarCargando();
        mostrarError(error.message || 'Error al guardar cambios');
    }
}

// ===== FUNCIONES DE HISTORIAL =====

// Ver historial del pedido
async function verHistorialPedido() {
    if (!pedidoActualParaEditar) {
        mostrarError('No hay pedido seleccionado');
        return;
    }
    
    const pedidoId = pedidoActualParaEditar.id;
    const token = localStorage.getItem('admin_token');
    
    try {
        // Mostrar modal
        document.getElementById('historial-pedido-id').textContent = pedidoId;
        document.getElementById('modalHistorial').classList.add('show');
        document.getElementById('loadingHistorial').style.display = 'flex';
        document.getElementById('historial-lista').style.display = 'none';
        document.getElementById('sin-historial').style.display = 'none';
        
        // Ocultar modal de detalle
        document.getElementById('modalDetalle').classList.remove('show');
        
        const response = await fetch(`/admin/pedidos/api/${pedidoId}/historial`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (manejarErrorAutenticacion(response)) return;
            throw new Error('Error al cargar historial');
        }
        
        const data = await response.json();
        
        document.getElementById('loadingHistorial').style.display = 'none';
        
        // Mostrar mensaje si la tabla no existe
        if (data.mensaje) {
            const sinHistorial = document.getElementById('sin-historial');
            sinHistorial.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 10px; color: #f39c12;"></i>
                <p>${data.mensaje}</p>
            `;
            sinHistorial.style.display = 'block';
        } else if (data.historial.length === 0) {
            const sinHistorial = document.getElementById('sin-historial');
            sinHistorial.innerHTML = `
                <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 10px;"></i>
                <p>No hay cambios registrados en este pedido</p>
            `;
            sinHistorial.style.display = 'block';
        } else {
            mostrarHistorial(data.historial);
            document.getElementById('historial-lista').style.display = 'block';
        }
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('loadingHistorial').style.display = 'none';
        const sinHistorial = document.getElementById('sin-historial');
        sinHistorial.innerHTML = `
            <i class="fas fa-exclamation-circle" style="font-size: 48px; margin-bottom: 10px; color: #e74c3c;"></i>
            <p>Error al cargar el historial</p>
            <p style="font-size: 0.9em; color: #666;">Asegúrate de que la tabla de historial existe</p>
        `;
        sinHistorial.style.display = 'block';
    }
}

// Mostrar historial
function mostrarHistorial(historial) {
    const container = document.getElementById('historial-lista');
    
    container.innerHTML = historial.map(h => {
        const fecha = new Date(h.fecha_cambio);
        const fechaStr = fecha.toLocaleString('es-AR', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        let contenidoExtra = '';
        
        // Mostrar items anteriores y nuevos si están disponibles
        if (h.datos_anteriores && h.datos_nuevos) {
            const anterior = h.datos_anteriores;
            const nuevo = h.datos_nuevos;
            
            contenidoExtra = `
                <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <strong style="color: #e74c3c;">❌ Items Anteriores:</strong>
                            <ul style="margin: 10px 0; padding-left: 20px;">
                                ${anterior.items.map(item => `
                                    <li>${item.nombre_producto} - Cant: ${item.cantidad} × $${item.precio_unitario.toFixed(2)}</li>
                                `).join('')}
                            </ul>
                            <strong>Total anterior: $${anterior.total_anterior.toFixed(2)}</strong>
                        </div>
                        <div>
                            <strong style="color: #27ae60;">✅ Items Nuevos:</strong>
                            <ul style="margin: 10px 0; padding-left: 20px;">
                                ${nuevo.items.map(item => `
                                    <li>${item.nombre_producto} - Cant: ${item.cantidad} × $${item.precio_unitario.toFixed(2)}</li>
                                `).join('')}
                            </ul>
                            <strong>Total nuevo: $${nuevo.total_nuevo.toFixed(2)}</strong>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return `
            <div style="padding: 20px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div>
                        <strong style="font-size: 16px; color: #667eea;">
                            <i class="fas fa-edit"></i> ${h.accion.replace('_', ' ').toUpperCase()}
                        </strong>
                        <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                            <i class="fas fa-user"></i> ${h.usuario_admin || 'Sistema'}
                        </div>
                    </div>
                    <div style="text-align: right; color: #666; font-size: 0.9em;">
                        <i class="fas fa-clock"></i> ${fechaStr}
                    </div>
                </div>
                
                <div style="margin: 10px 0; padding: 10px; background: #e8f4f8; border-left: 4px solid #3498db; border-radius: 4px;">
                    ${h.detalles}
                </div>
                
                ${h.motivo ? `
                    <div style="margin: 10px 0; padding: 10px; background: #fff3cd; border-left: 4px solid #f39c12; border-radius: 4px;">
                        <strong>Motivo:</strong> ${h.motivo}
                    </div>
                ` : ''}
                
                ${contenidoExtra}
            </div>
        `;
    }).join('');
}

// Cerrar modal de historial
function cerrarModalHistorial() {
    document.getElementById('modalHistorial').classList.remove('show');
    // Volver a mostrar modal de detalle
    document.getElementById('modalDetalle').classList.add('show');
}


// ===== FUNCIONES DE ORDENAMIENTO =====

function ordenarPor(campo) {
    // Si se hace clic en la misma columna, cambiar dirección
    if (ordenActual.campo === campo) {
        ordenActual.direccion = ordenActual.direccion === 'asc' ? 'desc' : 'asc';
    } else {
        // Nueva columna, ordenar descendente por defecto
        ordenActual.campo = campo;
        ordenActual.direccion = 'desc';
    }
    
    // Actualizar iconos de ordenamiento
    actualizarIconosOrdenamiento();
    
    // Ordenar pedidos
    ordenarPedidos();
    
    // Mostrar pedidos ordenados
    mostrarPedidos();
}

function actualizarIconosOrdenamiento() {
    // Remover clases de ordenamiento de todas las columnas
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Agregar clase a la columna activa
    const columnasMap = {
        'id': 0,
        'usuario': 1,
        'fecha': 2,
        'total': 3,
        'estado': 4,
        'metodo_pago': 5,
        'items': 6
    };
    
    const columnas = document.querySelectorAll('th.sortable');
    const indice = columnasMap[ordenActual.campo];
    
    if (columnas[indice]) {
        columnas[indice].classList.add(ordenActual.direccion === 'asc' ? 'sort-asc' : 'sort-desc');
    }
}

function ordenarPedidos() {
    pedidos.sort((a, b) => {
        let valorA, valorB;
        
        switch(ordenActual.campo) {
            case 'id':
                valorA = a.id;
                valorB = b.id;
                break;
            case 'usuario':
                valorA = (a.usuario_nombre || '').toLowerCase();
                valorB = (b.usuario_nombre || '').toLowerCase();
                break;
            case 'fecha':
                valorA = new Date(a.fecha_pedido || 0);
                valorB = new Date(b.fecha_pedido || 0);
                break;
            case 'total':
                valorA = parseFloat(a.total) || 0;
                valorB = parseFloat(b.total) || 0;
                break;
            case 'estado':
                valorA = (a.estado || '').toLowerCase();
                valorB = (b.estado || '').toLowerCase();
                break;
            case 'metodo_pago':
                valorA = (a.metodo_pago || '').toLowerCase();
                valorB = (b.metodo_pago || '').toLowerCase();
                break;
            case 'items':
                valorA = a.items_count || 0;
                valorB = b.items_count || 0;
                break;
            default:
                valorA = a.id;
                valorB = b.id;
        }
        
        // Comparación
        let resultado = 0;
        if (valorA < valorB) resultado = -1;
        if (valorA > valorB) resultado = 1;
        
        // Aplicar dirección
        return ordenActual.direccion === 'asc' ? resultado : -resultado;
    });
}


