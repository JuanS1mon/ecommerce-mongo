// ===========================
// PRESUPUESTOS ADMIN PANEL JS
// ===========================

// Estado global
let presupuestos = [];
let presupuestoActual = null;
let filtroEstado = '';
let busqueda = '';
let ordenColumna = 'fecha';
let ordenDireccion = 'desc';
let presupuestosSeleccionados = new Set();

// ===========================
// INICIALIZACIÓN
// ===========================
document.addEventListener('DOMContentLoaded', () => {
    // Verificar autenticación primero
    verificarAutenticacion();
    
    // Cargar datos
    cargarEstadisticas();
    cargarPresupuestos();
    
    // Event listeners
    const searchInput = document.getElementById('searchInput');
    const filterEstado = document.getElementById('filterEstado');
    
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
    
    if (filterEstado) {
        filterEstado.addEventListener('change', handleFiltroEstado);
    }
    
    // Modals event listeners
    setupModalEventListeners();
});

// ===========================
// AUTENTICACIÓN
// ===========================
function verificarAutenticacion() {
    const token = localStorage.getItem('admin_token');
    
    if (!token) {
        console.error('No hay token de autenticación');
        window.location.href = '/admin/login';
        return;
    }
}

// ===========================
// CARGAR DATOS
// ===========================
async function cargarEstadisticas() {
    try {
        const token = localStorage.getItem('admin_token');
        
        if (!token) {
            console.error('No hay token de autenticación');
            window.location.href = '/admin/login';
            return;
        }
        
        const response = await fetch('/admin/presupuestos/api/estadisticas', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.error('Token inválido o expirado');
                window.location.href = '/admin/login';
                return;
            }
            throw new Error('Error al cargar estadísticas');
        }
        
        const data = await response.json();
        actualizarTarjetasEstadisticas(data.por_estado);
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al cargar estadísticas', 'error');
    }
}

async function cargarPresupuestos() {
    try {
        const token = localStorage.getItem('admin_token');
        
        if (!token) {
            console.error('No hay token de autenticación');
            window.location.href = '/admin/login';
            return;
        }
        
        const params = new URLSearchParams({
            skip: '0',
            limit: '1000'
        });
        
        if (filtroEstado) params.append('estado', filtroEstado);
        if (busqueda) params.append('search', busqueda);
        
        const response = await fetch(`/admin/presupuestos/api/list?${params}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/admin/login';
                return;
            }
            throw new Error('Error al cargar presupuestos');
        }
        
        const data = await response.json();
        presupuestos = data.presupuestos;
        mostrarPresupuestos();
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al cargar presupuestos', 'error');
    }
}

// ===========================
// ACTUALIZAR UI
// ===========================
function actualizarTarjetasEstadisticas(estadisticas) {
    const estadoMap = {
        'pendiente': { id: 'stat-pendiente', icon: '⏳' },
        'contactado': { id: 'stat-contactado', icon: '📞' },
        'presupuestado': { id: 'stat-presupuestado', icon: '📝' },
        'aprobado': { id: 'stat-aprobado', icon: '✅' },
        'rechazado': { id: 'stat-rechazado', icon: '❌' }
    };
    
    // Resetear todas las tarjetas a 0
    Object.values(estadoMap).forEach(stat => {
        const elemento = document.getElementById(stat.id);
        if (elemento) elemento.textContent = '0';
    });
    
    // Validar que estadisticas sea un array
    if (!estadisticas || !Array.isArray(estadisticas)) {
        console.warn('No hay estadísticas o formato inválido');
        return;
    }
    
    // Actualizar con datos reales
    estadisticas.forEach(stat => {
        const config = estadoMap[stat.estado];
        if (config) {
            const elemento = document.getElementById(config.id);
            if (elemento) elemento.textContent = stat.total_presupuestos || stat.total || 0;
        }
    });
}

function mostrarPresupuestos() {
    const tbody = document.getElementById('presupuestosTableBody');
    
    if (presupuestos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center">
                    <div class="loading">
                        <i class="fas fa-inbox"></i>
                        <p>No hay presupuestos para mostrar</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Ordenar presupuestos
    const presupuestosOrdenados = [...presupuestos].sort((a, b) => {
        let valorA = a[ordenColumna];
        let valorB = b[ordenColumna];
        
        // Manejo especial para fechas
        if (ordenColumna === 'fecha') {
            valorA = new Date(a.fecha_creacion);
            valorB = new Date(b.fecha_creacion);
        }
        
        if (valorA < valorB) return ordenDireccion === 'asc' ? -1 : 1;
        if (valorA > valorB) return ordenDireccion === 'asc' ? 1 : -1;
        return 0;
    });
    
    tbody.innerHTML = presupuestosOrdenados.map(presupuesto => `
        <tr>
            <td>
                <input 
                    type="checkbox" 
                    class="presupuesto-checkbox" 
                    data-id="${presupuesto.id}"
                    ${presupuestosSeleccionados.has(presupuesto.id) ? 'checked' : ''}
                    onchange="toggleSeleccion(${presupuesto.id})">
            </td>
            <td><strong>#${presupuesto.id}</strong></td>
            <td>${escapeHtml(presupuesto.nombre)}</td>
            <td>${escapeHtml(presupuesto.email)}</td>
            <td>${escapeHtml(presupuesto.telefono || '-')}</td>
            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${escapeHtml(presupuesto.mensaje || '-')}
            </td>
            <td>${renderBadgeEstado(presupuesto.estado)}</td>
            <td>${formatearFecha(presupuesto.fecha_creacion)}</td>
            <td>
                <div class="action-buttons">
                    <button 
                        class="btn-icon btn-icon-info" 
                        onclick="verDetalles(${presupuesto.id})"
                        title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button 
                        class="btn-icon btn-icon-warning" 
                        onclick="abrirModalEstado(${presupuesto.id}, '${presupuesto.estado}')"
                        title="Cambiar estado">
                        <i class="fas fa-exchange-alt"></i>
                    </button>
                    <button 
                        class="btn-icon btn-icon-success" 
                        onclick="abrirModalEnviarPresupuesto(${presupuesto.id})"
                        title="Enviar presupuesto">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    // Actualizar estado del checkbox "Seleccionar todos"
    actualizarCheckboxTodos();
    actualizarBulkActions();
}

function renderBadgeEstado(estado) {
    const estadoConfig = {
        'pendiente': { icon: '⏳', clase: 'badge-pendiente', texto: 'Pendiente' },
        'contactado': { icon: '📞', clase: 'badge-contactado', texto: 'Contactado' },
        'presupuestado': { icon: '📝', clase: 'badge-presupuestado', texto: 'Presupuestado' },
        'aprobado': { icon: '✅', clase: 'badge-aprobado', texto: 'Aprobado' },
        'rechazado': { icon: '❌', clase: 'badge-rechazado', texto: 'Rechazado' }
    };
    
    const config = estadoConfig[estado] || { icon: '❓', clase: 'badge-pendiente', texto: estado };
    return `<span class="badge ${config.clase}">${config.icon} ${config.texto}</span>`;
}

// ===========================
// FILTROS Y BÚSQUEDA
// ===========================
function filtrarPorEstado(estado) {
    filtroEstado = estado === filtroEstado ? '' : estado;
    const filterEstado = document.getElementById('filterEstado');
    if (filterEstado) {
        filterEstado.value = filtroEstado;
    }
    cargarPresupuestos();
}

function handleFiltroEstado(e) {
    filtroEstado = e.target.value;
    cargarPresupuestos();
}

function handleSearch(e) {
    busqueda = e.target.value.trim();
    cargarPresupuestos();
}

// ===========================
// ORDENAMIENTO
// ===========================
function ordenarPor(columna) {
    if (ordenColumna === columna) {
        ordenDireccion = ordenDireccion === 'asc' ? 'desc' : 'asc';
    } else {
        ordenColumna = columna;
        ordenDireccion = 'asc';
    }
    
    // Actualizar iconos de ordenamiento
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const thActual = document.querySelector(`[onclick="ordenarPor('${columna}')"]`);
    if (thActual) {
        thActual.classList.add(`sort-${ordenDireccion}`);
    }
    
    mostrarPresupuestos();
}

// ===========================
// VER DETALLES
// ===========================
async function verDetalles(id) {
    try {
        const token = localStorage.getItem('admin_token');
        
        const response = await fetch(`/admin/presupuestos/api/${id}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/admin/login';
                return;
            }
            throw new Error('Error al obtener detalles');
        }
        
        const presupuesto = await response.json();
        mostrarModalDetalles(presupuesto);
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al cargar detalles', 'error');
    }
}

function mostrarModalDetalles(presupuesto) {
    const detallesHTML = `
        <div class="form-group">
            <label><i class="fas fa-hashtag"></i> ID</label>
            <p style="font-size: 1.2rem; color: var(--gold); font-weight: 600;">#${presupuesto.id}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-user"></i> Cliente</label>
            <p>${escapeHtml(presupuesto.nombre)}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-envelope"></i> Email</label>
            <p>${escapeHtml(presupuesto.email)}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-phone"></i> Teléfono</label>
            <p>${escapeHtml(presupuesto.telefono || 'No proporcionado')}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-comment"></i> Consulta Original</label>
            <p style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; white-space: pre-wrap;">${escapeHtml(presupuesto.mensaje || 'Sin mensaje')}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-circle"></i> Estado</label>
            <p>${renderBadgeEstado(presupuesto.estado)}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-calendar"></i> Fecha de Creación</label>
            <p>${formatearFecha(presupuesto.fecha_creacion)}</p>
        </div>
        
        <div class="form-group">
            <label><i class="fas fa-clock"></i> Última Actualización</label>
            <p>${formatearFecha(presupuesto.fecha_actualizacion)}</p>
        </div>
    `;
    
    document.getElementById('detallesContent').innerHTML = detallesHTML;
    abrirModal('modalDetalles');
}

// ===========================
// CAMBIAR ESTADO
// ===========================
function abrirModalEstado(id, estadoActual) {
    presupuestoActual = presupuestos.find(p => p.id === id);
    if (!presupuestoActual) return;
    
    document.getElementById('estadoPresupuestoId').textContent = id;
    document.getElementById('presupuesto-id-estado').value = id;
    document.getElementById('nuevo-estado-select').value = estadoActual;
    abrirModal('modalEstado');
}

async function cambiarEstadoSubmit() {
    const presupuestoIdInput = document.getElementById('presupuesto-id-estado');
    const nuevoEstado = document.getElementById('nuevo-estado-select').value;
    
    if (!nuevoEstado) {
        mostrarNotificacion('Por favor seleccione un estado', 'warning');
        return;
    }
    
    // Verificar si es cambio masivo o individual
    const isBulk = presupuestoIdInput && presupuestoIdInput.value === 'bulk';
    
    if (isBulk) {
        await cambiarEstadoMasivoSubmit(nuevoEstado);
        return;
    }
    
    // Cambio individual
    if (!presupuestoActual) return;
    
    try {
        const token = localStorage.getItem('admin_token');
        
        mostrarCargando('Actualizando estado...');
        
        const response = await fetch(`/admin/presupuestos/api/${presupuestoActual.id}/estado`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/admin/login';
                return;
            }
            throw new Error('Error al cambiar estado');
        }
        
        cerrarModal('modalEstado');
        
        await Promise.all([
            cargarEstadisticas(),
            cargarPresupuestos()
        ]);
        
        ocultarCargando();
        mostrarNotificacion('Estado actualizado correctamente', 'success');
    } catch (error) {
        console.error('Error:', error);
        ocultarCargando();
        mostrarNotificacion('Error al cambiar estado', 'error');
    }
}

async function cambiarEstadoMasivoSubmit(nuevoEstado) {
    const token = localStorage.getItem('admin_token');
    const presupuestosArray = Array.from(presupuestosSeleccionados);
    
    try {
        mostrarCargando(`Actualizando ${presupuestosArray.length} presupuesto(s)...`);
        
        // Cambiar estado de cada presupuesto
        const promises = presupuestosArray.map(id => 
            fetch(`/admin/presupuestos/api/${id}/estado`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ estado: nuevoEstado })
            })
        );
        
        const results = await Promise.allSettled(promises);
        
        const exitosos = results.filter(r => r.status === 'fulfilled' && r.value.ok).length;
        const fallidos = results.length - exitosos;
        
        cerrarModal('modalEstado');
        limpiarSeleccion();
        
        await Promise.all([
            cargarEstadisticas(),
            cargarPresupuestos()
        ]);
        
        ocultarCargando();
        
        if (fallidos === 0) {
            mostrarNotificacion(`${exitosos} presupuesto(s) actualizado(s) correctamente`, 'success');
        } else {
            mostrarNotificacion(`${exitosos} actualizados, ${fallidos} fallaron`, 'warning');
        }
        
    } catch (error) {
        console.error('Error:', error);
        ocultarCargando();
        mostrarNotificacion('Error al cambiar estados', 'error');
    }
}

// ===========================
// ENVIAR PRESUPUESTO
// ===========================
function abrirModalEnviarPresupuesto(id) {
    presupuestoActual = presupuestos.find(p => p.id === id);
    if (!presupuestoActual) return;
    
    // Limpiar formulario
    const container = document.getElementById('productosContainer');
    if (container) {
        container.innerHTML = '';
    }
    
    const observaciones = document.getElementById('observaciones');
    if (observaciones) {
        observaciones.value = '';
    }
    
    const validezDias = document.getElementById('validezDias');
    if (validezDias) {
        validezDias.value = '30';
    }
    
    // Agregar un producto por defecto
    agregarProducto();
    
    // Calcular total inicial
    calcularTotal();
    
    abrirModal('modalEnviarPresupuesto');
}

function agregarProducto() {
    const container = document.getElementById('productosContainer');
    const productoHTML = `
        <div class="producto-item">
            <input 
                type="text" 
                class="form-control" 
                placeholder="Nombre del producto/servicio"
                data-field="nombre"
                oninput="calcularTotal()">
            <input 
                type="number" 
                class="form-control" 
                placeholder="Cant." 
                min="1" 
                value="1"
                data-field="cantidad"
                oninput="calcularTotal()">
            <input 
                type="number" 
                class="form-control" 
                placeholder="Precio" 
                min="0" 
                step="0.01"
                data-field="precio"
                oninput="calcularTotal()">
            <button 
                type="button" 
                class="btn-icon btn-icon-danger" 
                onclick="eliminarProducto(this)"
                title="Eliminar">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', productoHTML);
    calcularTotal();
    
    // Dar foco al input de nombre del último producto agregado
    const productosItems = document.querySelectorAll('.producto-item');
    if (productosItems.length > 0) {
        const ultimoProducto = productosItems[productosItems.length - 1];
        const inputNombre = ultimoProducto.querySelector('[data-field="nombre"]');
        if (inputNombre) {
            inputNombre.focus();
        }
    }
}

function eliminarProducto(btn) {
    const productosItems = document.querySelectorAll('.producto-item');
    if (productosItems.length > 1) {
        btn.closest('.producto-item').remove();
        calcularTotal();
    } else {
        mostrarNotificacion('Debe haber al menos un producto', 'warning');
    }
}

function calcularTotal() {
    let total = 0;
    const productos = document.querySelectorAll('.producto-item');
    
    productos.forEach(item => {
        const cantidadInput = item.querySelector('[data-field="cantidad"]');
        const precioInput = item.querySelector('[data-field="precio"]');
        
        const cantidad = cantidadInput ? parseFloat(cantidadInput.value) || 0 : 0;
        const precio = precioInput ? parseFloat(precioInput.value) || 0 : 0;
        total += cantidad * precio;
    });
    
    const totalElement = document.getElementById('presupuestoTotal');
    if (totalElement) {
        totalElement.textContent = `$${total.toFixed(2)}`;
    }
}

async function enviarPresupuestoSubmit() {
    if (!presupuestoActual) return;
    
    // Recopilar productos
    const productos = [];
    const productosItems = document.querySelectorAll('.producto-item');
    
    let valido = true;
    productosItems.forEach(item => {
        const nombreInput = item.querySelector('[data-field="nombre"]');
        const cantidadInput = item.querySelector('[data-field="cantidad"]');
        const precioInput = item.querySelector('[data-field="precio"]');
        
        const nombre = nombreInput ? nombreInput.value.trim() : '';
        const cantidad = cantidadInput ? parseFloat(cantidadInput.value) : 0;
        const precio = precioInput ? parseFloat(precioInput.value) : 0;
        
        if (!nombre || !cantidad || !precio) {
            valido = false;
            return;
        }
        
        // Calcular subtotal
        const subtotal = cantidad * precio;
        productos.push({ 
            nombre, 
            cantidad, 
            precio_unitario: precio,
            subtotal: subtotal
        });
    });
    
    if (!valido || productos.length === 0) {
        mostrarNotificacion('Complete todos los campos de productos', 'warning');
        return;
    }
    
    // Calcular total
    const total = productos.reduce((sum, p) => sum + p.subtotal, 0);
    
    const observaciones = document.getElementById('observaciones').value.trim();
    const validezDias = parseInt(document.getElementById('validezDias').value);
    
    try {
        const token = localStorage.getItem('admin_token');
        
        // Mostrar indicador de carga
        mostrarCargando('Enviando presupuesto por email...');
        
        const response = await fetch(`/admin/presupuestos/api/${presupuestoActual.id}/enviar-presupuesto`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                productos: productos,
                total: total,
                observaciones: observaciones,
                validez_dias: validezDias
            })
        });
        
        if (!response.ok) {
            ocultarCargando();
            if (response.status === 401) {
                window.location.href = '/admin/login';
                return;
            }
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al enviar presupuesto');
        }
        
        // Ocultar indicador de carga
        ocultarCargando();
        
        mostrarNotificacion('Presupuesto enviado correctamente', 'success');
        cerrarModal('modalEnviarPresupuesto');
        cargarEstadisticas();
        cargarPresupuestos();
    } catch (error) {
        // Ocultar indicador de carga en caso de error
        ocultarCargando();
        console.error('Error:', error);
        mostrarNotificacion(error.message || 'Error al enviar presupuesto', 'error');
    }
}

async function vistaPrevia() {
    if (!presupuestoActual) return;
    
    // Recopilar productos del formulario
    const productos = [];
    const productosItems = document.querySelectorAll('.producto-item');
    
    productosItems.forEach(item => {
        const nombreInput = item.querySelector('[data-field="nombre"]');
        const cantidadInput = item.querySelector('[data-field="cantidad"]');
        const precioInput = item.querySelector('[data-field="precio"]');
        
        const nombre = nombreInput ? nombreInput.value.trim() : '';
        const cantidad = cantidadInput ? parseFloat(cantidadInput.value) : 0;
        const precio = precioInput ? parseFloat(precioInput.value) : 0;
        
        if (nombre && cantidad && precio) {
            const subtotal = cantidad * precio;
            productos.push({ 
                nombre, 
                cantidad, 
                precio_unitario: precio,
                subtotal: subtotal
            });
        }
    });
    
    if (productos.length === 0) {
        mostrarNotificacion('Agregue al menos un producto para la vista previa', 'warning');
        return;
    }
    
    // Calcular total
    const total = productos.reduce((sum, p) => sum + p.subtotal, 0);
    
    const observaciones = document.getElementById('observaciones').value.trim();
    const validezDias = parseInt(document.getElementById('validezDias').value);
    
    try {
        const token = localStorage.getItem('admin_token');
        
        // Enviar productos para generar la vista previa
        const response = await fetch(`/admin/presupuestos/api/${presupuestoActual.id}/vista-previa-dinamica`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                productos: productos,
                total: total,
                observaciones: observaciones,
                validez_dias: validezDias
            })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/admin/login';
                return;
            }
            throw new Error('Error al generar vista previa');
        }
        
        const htmlContent = await response.text();
        
        // Abrir nueva ventana con el contenido HTML
        const ventana = window.open('', '_blank', 'width=900,height=700');
        ventana.document.write(htmlContent);
        ventana.document.close();
        
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al generar vista previa', 'error');
    }
}

// ===========================
// MODAL MANAGEMENT
// ===========================
function setupModalEventListeners() {
    // Cerrar modals al hacer clic fuera
    window.onclick = (event) => {
        if (event.target.classList.contains('modal')) {
            cerrarModal(event.target.id);
        }
    };
    
    // ESC para cerrar
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                cerrarModal(modal.id);
            });
        }
    });
}

function abrirModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function cerrarModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// ===========================
// SELECCIÓN MÚLTIPLE
// ===========================
function toggleSeleccion(id) {
    if (presupuestosSeleccionados.has(id)) {
        presupuestosSeleccionados.delete(id);
    } else {
        presupuestosSeleccionados.add(id);
    }
    actualizarCheckboxTodos();
    actualizarBulkActions();
}

function toggleTodos() {
    const checkbox = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.presupuesto-checkbox');
    
    if (checkbox.checked) {
        // Seleccionar todos
        checkboxes.forEach(cb => {
            const id = parseInt(cb.dataset.id);
            presupuestosSeleccionados.add(id);
            cb.checked = true;
        });
    } else {
        // Deseleccionar todos
        presupuestosSeleccionados.clear();
        checkboxes.forEach(cb => {
            cb.checked = false;
        });
    }
    
    actualizarBulkActions();
}

function actualizarCheckboxTodos() {
    const checkbox = document.getElementById('select-all');
    if (!checkbox) return;
    
    const checkboxes = document.querySelectorAll('.presupuesto-checkbox');
    const totalCheckboxes = checkboxes.length;
    const seleccionados = presupuestosSeleccionados.size;
    
    if (seleccionados === 0) {
        checkbox.checked = false;
        checkbox.indeterminate = false;
    } else if (seleccionados === totalCheckboxes) {
        checkbox.checked = true;
        checkbox.indeterminate = false;
    } else {
        checkbox.checked = false;
        checkbox.indeterminate = true;
    }
}

function actualizarBulkActions() {
    const bulkActions = document.getElementById('bulk-actions');
    const count = document.getElementById('selected-count');
    
    if (!bulkActions || !count) return;
    
    if (presupuestosSeleccionados.size > 0) {
        bulkActions.style.display = 'flex';
        count.textContent = presupuestosSeleccionados.size;
    } else {
        bulkActions.style.display = 'none';
    }
}

function limpiarSeleccion() {
    presupuestosSeleccionados.clear();
    const checkboxes = document.querySelectorAll('.presupuesto-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    actualizarCheckboxTodos();
    actualizarBulkActions();
}

function cambiarEstadoMasivo() {
    if (presupuestosSeleccionados.size === 0) {
        mostrarNotificacion('No hay presupuestos seleccionados', 'warning');
        return;
    }
    
    // Abrir modal especial para cambio masivo
    const modal = document.getElementById('modalEstado');
    const titulo = document.getElementById('modal-estado-titulo');
    const estadoActual = document.getElementById('estado-actual-text');
    const presupuestoIdInput = document.getElementById('presupuesto-id-estado');
    
    if (titulo) titulo.textContent = 'Cambio de Estado Masivo';
    if (estadoActual) estadoActual.innerHTML = `<strong>${presupuestosSeleccionados.size}</strong> presupuesto${presupuestosSeleccionados.size > 1 ? 's' : ''} seleccionado${presupuestosSeleccionados.size > 1 ? 's' : ''}`;
    if (presupuestoIdInput) presupuestoIdInput.value = 'bulk';
    
    document.getElementById('nuevo-estado-select').value = '';
    
    abrirModal('modalEstado');
}

// ===========================
// UTILIDADES
// ===========================
function formatearFecha(fecha) {
    if (!fecha) return '-';
    const date = new Date(fecha);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Crear elemento de notificación
    const notif = document.createElement('div');
    notif.className = `notificacion notificacion-${tipo}`;
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${tipo === 'success' ? 'var(--success)' : tipo === 'error' ? 'var(--danger)' : tipo === 'warning' ? 'var(--warning)' : 'var(--info)'};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notif.textContent = mensaje;
    
    document.body.appendChild(notif);
    
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// ===========================
// INDICADOR DE CARGA
// ===========================
function mostrarCargando(mensaje = 'Procesando...') {
    ocultarCargando();
    
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
    
    const loaderContainer = document.createElement('div');
    loaderContainer.style.cssText = `
        background: white;
        padding: 30px 40px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        text-align: center;
        max-width: 400px;
    `;
    
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
    
    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
        color: #333;
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 10px;
    `;
    messageDiv.textContent = mensaje;
    
    const subMessage = document.createElement('div');
    subMessage.style.cssText = `
        color: #666;
        font-size: 13px;
        margin-top: 8px;
    `;
    subMessage.textContent = 'Por favor espere...';
    
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

// ===========================
// LOGOUT
// ===========================
function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = '/admin/login';
}
