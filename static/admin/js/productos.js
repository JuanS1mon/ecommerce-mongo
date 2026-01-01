console.log('productos.js cargado correctamente');

// Variables globales
let productos = [];
let categorias = [];
let currentPage = 1;
let totalPages = 1;
let itemsPerPage = 10;
let currentTab = 0;
let productoEditando = null;
let variantesEditando = [];

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    verificarAutenticacion();
    cargarDatosIniciales();
    
    // Event listeners
    document.getElementById('searchInput').addEventListener('input', filtrarProductos);
    document.getElementById('filterCategoria').addEventListener('change', filtrarProductos);
    document.getElementById('filterEstado').addEventListener('change', filtrarProductos);
    document.getElementById('formProducto').addEventListener('submit', guardarProducto);
    
    // Cerrar modales al hacer clic fuera
    window.addEventListener('click', function(event) {
        const modalImagenes = document.getElementById('modalImagenes');
        if (event.target === modalImagenes) {
            cerrarSelectorImagenes();
        }
    });
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
        // Si no es JSON, usar el string directamente
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
        await cargarProductos();
    } catch (error) {
        console.error('Error cargando datos:', error);
        mostrarError('Error al cargar los datos');
    }
}

// Cargar productos
async function cargarProductos() {
    const token = localStorage.getItem('admin_token');
    
    if (!token) {
        console.error('No hay token de autenticación');
        window.location.href = '/admin/login';
        return;
    }
    
    const search = document.getElementById('searchInput').value;
    const categoria = document.getElementById('filterCategoria').value;
    const activo = document.getElementById('filterEstado').value;
    
    let url = '/admin/productos/api/list?';
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (categoria) url += `categoria_id=${categoria}&`;
    if (activo !== '') url += `activo=${activo}&`;
    
    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.error('Token inválido o expirado');
                localStorage.removeItem('admin_token');
                localStorage.removeItem('admin_user');
                window.location.href = '/admin/login';
                return;
            }
            if (response.status === 403) {
                console.error('Permisos insuficientes - Usuario no es admin');
                const errorData = await response.json().catch(() => ({}));
                console.error('Detalle del error:', errorData);
                mostrarError('No tienes permisos de administrador. Por favor, contacta al administrador del sistema.');
                localStorage.removeItem('admin_token');
                localStorage.removeItem('admin_user');
                setTimeout(() => {
                    window.location.href = '/admin/login';
                }, 3000);
                return;
            }
            throw new Error('Error al cargar productos');
        }
        
        const data = await response.json();
        productos = data.productos || [];
        categorias = data.categorias || [];
        
        // Cargar categorías en filtro y modal
        cargarCategoriasEnSelect();
        
        // Calcular paginación
        totalPages = Math.ceil(productos.length / itemsPerPage);
        currentPage = 1;
        
        // Mostrar productos
        mostrarProductos();
        actualizarContador();
        
        // Mostrar contenido
        document.getElementById('productos-loading').style.display = 'none';
        document.getElementById('productos-content').style.display = 'block';
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar los productos');
        document.getElementById('productos-loading').style.display = 'none';
    }
}

// Cargar categorías en los selects
function cargarCategoriasEnSelect() {
    const selectFilter = document.getElementById('filterCategoria');
    const selectModal = document.getElementById('producto-categoria');
    
    // Limpiar opciones existentes (excepto la primera)
    selectFilter.innerHTML = '<option value="">Todas las categorías</option>';
    selectModal.innerHTML = '<option value="">Sin categoría</option>';
    
    // Agregar categorías
    categorias.forEach(cat => {
        const option1 = document.createElement('option');
        option1.value = cat.id;
        option1.textContent = cat.nombre;
        selectFilter.appendChild(option1);
        
        const option2 = document.createElement('option');
        option2.value = cat.id;
        option2.textContent = cat.nombre;
        selectModal.appendChild(option2);
    });
}

// Mostrar productos en tabla
function mostrarProductos() {
    const tbody = document.getElementById('productos-tbody');
    tbody.innerHTML = '';
    
    if (productos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    <i class="fas fa-inbox" style="font-size: 48px; color: var(--text-muted); margin-bottom: 10px; display: block;"></i>
                    <p style="color: var(--text-muted);">No se encontraron productos</p>
                </td>
            </tr>
        `;
        return;
    }
    
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const productosPagina = productos.slice(start, end);
    
    productosPagina.forEach(producto => {
        const tr = document.createElement('tr');
        
        // Imagen
        const tdImagen = document.createElement('td');
        if (producto.imagen_url) {
            tdImagen.innerHTML = `<img src="${producto.imagen_url}" class="product-img" alt="${producto.nombre}">`;
        } else {
            tdImagen.innerHTML = `<div class="product-img-placeholder"><i class="fas fa-image"></i></div>`;
        }
        tr.appendChild(tdImagen);
        
        // Código
        const tdCodigo = document.createElement('td');
        tdCodigo.textContent = producto.codigo || '-';
        tr.appendChild(tdCodigo);
        
        // Nombre
        const tdNombre = document.createElement('td');
        tdNombre.textContent = producto.nombre;
        tr.appendChild(tdNombre);
        
        // Precio
        const tdPrecio = document.createElement('td');
        tdPrecio.textContent = `$${producto.precio.toFixed(2)}`;
        tr.appendChild(tdPrecio);
        
        // Variantes
        const tdVariantes = document.createElement('td');
        const numVariantes = producto.variantes ? producto.variantes.length : 0;
        tdVariantes.innerHTML = `<span class="badge badge-info">${numVariantes}</span>`;
        tr.appendChild(tdVariantes);
        
        // Categoría
        const tdCategoria = document.createElement('td');
        const categoria = categorias.find(c => c.id === producto.id_categoria);
        tdCategoria.textContent = categoria ? categoria.nombre : '-';
        tr.appendChild(tdCategoria);
        
        // Estado
        const tdEstado = document.createElement('td');
        if (producto.active) {
            tdEstado.innerHTML = `<span class="badge badge-success"><i class="fas fa-check"></i> Activo</span>`;
        } else {
            tdEstado.innerHTML = `<span class="badge badge-inactive"><i class="fas fa-times"></i> Inactivo</span>`;
        }
        tr.appendChild(tdEstado);
        
        // Acciones
        const tdAcciones = document.createElement('td');
        tdAcciones.innerHTML = `
            <button class="btn btn-secondary btn-sm btn-icon" onclick="editarProducto('${producto.id}')" title="Editar">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-secondary btn-sm btn-icon" onclick="toggleActivo('${producto.id}', ${producto.active})" title="${producto.active ? 'Desactivar' : 'Activar'}">
                <i class="fas fa-${producto.active ? 'eye-slash' : 'eye'}"></i>
            </button>
            <button class="btn btn-danger btn-sm btn-icon" onclick="confirmarEliminar('${producto.id}', '${producto.nombre.replace(/'/g, "\\'")}')" title="Eliminar">
                <i class="fas fa-trash"></i>
            </button>
        `;
        tr.appendChild(tdAcciones);
        
        tbody.appendChild(tr);
    });
    
    actualizarPaginacion();
}

// Actualizar contador
function actualizarContador() {
    const totalActivos = productos.filter(p => p.active).length;
    const totalInactivos = productos.filter(p => !p.active).length;
    
    document.getElementById('total-productos').textContent = totalActivos;
    document.getElementById('total-inactivos').textContent = `${totalInactivos} inactivos`;
}

// Actualizar paginación
function actualizarPaginacion() {
    const btnPrev = document.getElementById('btnPrev');
    const btnNext = document.getElementById('btnNext');
    const pageInfo = document.getElementById('pageInfo');
    
    btnPrev.disabled = currentPage === 1;
    btnNext.disabled = currentPage === totalPages || totalPages === 0;
    
    pageInfo.textContent = `Página ${currentPage} de ${totalPages || 1}`;
}

// Cambiar página
function cambiarPagina(direccion) {
    const newPage = currentPage + direccion;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        mostrarProductos();
    }
}

// Filtrar productos
function filtrarProductos() {
    cargarProductos();
    actualizarIndicadorFiltros();
}

// Actualizar indicador de filtros activos
function actualizarIndicadorFiltros() {
    const categoriaSelect = document.getElementById('filterCategoria');
    const estadoSelect = document.getElementById('filterEstado');
    const categoriaValor = categoriaSelect.value;
    const estadoValor = estadoSelect.value;
    
    const filtrosActivos = document.getElementById('filtros-activos');
    const filtroCategoria = document.getElementById('filtro-categoria-texto');
    const filtroEstado = document.getElementById('filtro-estado-texto');
    
    let hayFiltros = false;
    
    // Filtro de categoría
    if (categoriaValor) {
        const categoriaNombre = categoriaSelect.options[categoriaSelect.selectedIndex].text;
        document.getElementById('filtro-categoria-nombre-display').textContent = categoriaNombre;
        filtroCategoria.style.display = 'inline';
        hayFiltros = true;
    } else {
        filtroCategoria.style.display = 'none';
    }
    
    // Filtro de estado
    if (estadoValor) {
        const estadoNombre = estadoSelect.options[estadoSelect.selectedIndex].text;
        document.getElementById('estado-nombre').textContent = estadoNombre;
        filtroEstado.style.display = 'inline';
        hayFiltros = true;
    } else {
        filtroEstado.style.display = 'none';
    }
    
    // Mostrar/ocultar el indicador
    filtrosActivos.style.display = hayFiltros ? 'block' : 'none';
}

// Limpiar filtro de categoría
function limpiarFiltroCategoria() {
    document.getElementById('filterCategoria').value = '';
    filtrarProductos();
}

// Limpiar filtro de estado
function limpiarFiltroEstado() {
    document.getElementById('filterEstado').value = '';
    filtrarProductos();
}

// Limpiar todos los filtros
function limpiarTodosFiltros() {
    document.getElementById('filterCategoria').value = '';
    document.getElementById('filterEstado').value = '';
    document.getElementById('searchInput').value = '';
    filtrarProductos();
}

// Abrir modal nuevo producto
function abrirModalNuevo() {
    productoEditando = null;
    variantesEditando = [];
    document.getElementById('modal-title').textContent = 'Nuevo Producto';
    document.getElementById('formProducto').reset();
    document.getElementById('producto-id').value = '';
    document.getElementById('producto-activo').value = 'true';
    
    // Deshabilitar tab de variantes para nuevo producto
    document.getElementById('tabVariantes').disabled = true;
    document.getElementById('tabVariantes').style.opacity = '0.5';
    
    cambiarTab(0);
    document.getElementById('variantes-lista').innerHTML = '';
    
    document.getElementById('modalProducto').classList.add('show');
}

// Editar producto
async function editarProducto(id) {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch(`/admin/productos/api/${id}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al cargar producto');
        }
        
        const data = await response.json();
        // El endpoint devuelve el producto directamente con variantes incluidas
        productoEditando = data;
        variantesEditando = data.variantes || [];
        
        // Llenar formulario
        document.getElementById('modal-title').textContent = 'Editar Producto';
        document.getElementById('producto-id').value = productoEditando.id;
        document.getElementById('producto-codigo').value = productoEditando.codigo || '';
        document.getElementById('producto-nombre').value = productoEditando.nombre;
        document.getElementById('producto-descripcion').value = productoEditando.descripcion || '';
        document.getElementById('producto-precio').value = productoEditando.precio;
        document.getElementById('producto-categoria').value = productoEditando.id_categoria || '';
        document.getElementById('producto-imagen').value = productoEditando.imagen_url || '';
        document.getElementById('producto-activo').value = productoEditando.active ? 'true' : 'false';
        
        // Habilitar tab de variantes
        document.getElementById('tabVariantes').disabled = false;
        document.getElementById('tabVariantes').style.opacity = '1';
        
        // Mostrar variantes
        mostrarVariantes();
        
        cambiarTab(0);
        document.getElementById('modalProducto').classList.add('show');
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar el producto');
    }
}

// Guardar producto
async function guardarProducto(e) {
    e.preventDefault();
    
    const token = localStorage.getItem('admin_token');
    const id = document.getElementById('producto-id').value;
    const isEdit = id !== '';
    
    const producto = {
        codigo: document.getElementById('producto-codigo').value || null,
        nombre: document.getElementById('producto-nombre').value,
        descripcion: document.getElementById('producto-descripcion').value || null,
        precio: parseFloat(document.getElementById('producto-precio').value),
        id_categoria: document.getElementById('producto-categoria').value || null,
        imagen_url: document.getElementById('producto-imagen').value || null,
        active: document.getElementById('producto-activo').value === 'true'
    };
    
    try {
        let response;
        
        if (isEdit) {
            // Actualizar producto
            response = await fetch(`/admin/productos/api/${id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(producto)
            });
        } else {
            // Crear producto
            response = await fetch('/admin/productos/api/create', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(producto)
            });
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al guardar el producto');
        }
        
        const result = await response.json();
        
        // Si es nuevo producto y hay variantes, guardarlas
        if (!isEdit && variantesEditando.length > 0) {
            await guardarVariantes(result.producto.id);
        }
        
        // Si es edición, guardar variantes
        if (isEdit) {
            await guardarVariantes(id);
        }
        
        cerrarModal();
        await cargarProductos();
        mostrarExito(isEdit ? 'Producto actualizado correctamente' : 'Producto creado correctamente');
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError(error.message);
    }
}

// Guardar variantes
async function guardarVariantes(productoId) {
    const token = localStorage.getItem('admin_token');
    
    // Aquí implementarías la lógica para guardar variantes
    // Por ahora solo es placeholder ya que necesitarías endpoints adicionales
    console.log('Guardando variantes para producto', productoId, variantesEditando);
}

// Toggle activo
async function toggleActivo(id, estadoActual) {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch(`/admin/productos/api/${id}/toggle-active`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al cambiar el estado');
        }
        
        // Actualizar el producto localmente sin recargar toda la página
        const producto = productos.find(p => p.id === id);
        if (producto) {
            producto.active = !estadoActual;
        }
        
        // Actualizar solo la visualización y contador
        mostrarProductos();
        actualizarContador();
        mostrarExito(`Producto ${estadoActual ? 'desactivado' : 'activado'} correctamente`);
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cambiar el estado del producto');
    }
}

// Confirmar eliminar
function confirmarEliminar(id, nombre) {
    document.getElementById('confirmar-mensaje').textContent = `¿Está seguro de eliminar el producto "${nombre}"? Esta acción no se puede deshacer.`;
    
    const btnConfirmar = document.getElementById('btnConfirmarEliminar');
    btnConfirmar.onclick = () => eliminarProducto(id);
    
    document.getElementById('modalConfirmar').classList.add('show');
}

// Eliminar producto
async function eliminarProducto(id) {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch(`/admin/productos/api/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al eliminar el producto');
        }
        
        cerrarModalConfirmar();
        await cargarProductos();
        mostrarExito('Producto eliminado correctamente');
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al eliminar el producto');
    }
}

// Cambiar tab
function cambiarTab(index) {
    currentTab = index;
    
    // Actualizar botones
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach((tab, i) => {
        if (i === index) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Actualizar contenido
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach((content, i) => {
        if (i === index) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
}

// Mostrar variantes
function mostrarVariantes() {
    const lista = document.getElementById('variantes-lista');
    lista.innerHTML = '';
    
    if (variantesEditando.length === 0) {
        lista.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                <i class="fas fa-layer-group" style="font-size: 48px; margin-bottom: 10px; display: block;"></i>
                <p>No hay variantes para este producto</p>
                <p style="font-size: 14px; margin-top: 5px;">Haz clic en "Agregar Variante" para comenzar</p>
            </div>
        `;
        return;
    }
    
    variantesEditando.forEach((variante, index) => {
        const div = document.createElement('div');
        div.className = 'variante-item';
        div.innerHTML = `
            <div class="variante-header">
                <h4><i class="fas fa-layer-group"></i> Variante ${index + 1}</h4>
                <button type="button" class="btn btn-danger btn-sm" onclick="eliminarVariante(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div class="variante-grid">
                <div class="form-group">
                    <label class="form-label">Color</label>
                    <input type="text" class="form-control" value="${variante.color || ''}" 
                           onchange="actualizarVariante(${index}, 'color', this.value)">
                </div>
                <div class="form-group">
                    <label class="form-label">Tipo</label>
                    <input type="text" class="form-control" value="${variante.tipo || ''}"
                           onchange="actualizarVariante(${index}, 'tipo', this.value)">
                </div>
                <div class="form-group">
                    <label class="form-label">Stock</label>
                    <input type="number" class="form-control" value="${variante.stock || 0}"
                           onchange="actualizarVariante(${index}, 'stock', parseInt(this.value))">
                </div>
                <div class="form-group">
                    <label class="form-label">Precio Adicional</label>
                    <input type="number" step="0.01" class="form-control" value="${variante.precio_adicional || 0}"
                           onchange="actualizarVariante(${index}, 'precio_adicional', parseFloat(this.value))">
                </div>
                <div class="form-group" style="grid-column: 1 / -1;">
                    <label class="form-label">URL de Imagen</label>
                    <div class="input-group">
                        <input type="text" class="form-control" id="variante-imagen-${index}" value="${variante.imagen_url || ''}"
                               onchange="actualizarVariante(${index}, 'imagen_url', this.value)">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="abrirSelectorImagenes('variante-imagen-${index}')" title="Seleccionar imagen desde el servidor">
                            <i class="fas fa-images"></i>
                        </button>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Estado</label>
                    <select class="form-control" onchange="actualizarVariante(${index}, 'active', this.value === 'true')">
                        <option value="true" ${variante.active ? 'selected' : ''}>Activo</option>
                        <option value="false" ${!variante.active ? 'selected' : ''}>Inactivo</option>
                    </select>
                </div>
            </div>
        `;
        lista.appendChild(div);
    });
}

// Agregar variante
function agregarVariante() {
    variantesEditando.push({
        color: '',
        tipo: '',
        stock: 0,
        precio_adicional: 0,
        imagen_url: '',
        active: true
    });
    mostrarVariantes();
}

// Actualizar variante
function actualizarVariante(index, campo, valor) {
    variantesEditando[index][campo] = valor;
}

// Eliminar variante
function eliminarVariante(index) {
    variantesEditando.splice(index, 1);
    mostrarVariantes();
}

// Cerrar modales
function cerrarModal() {
    document.getElementById('modalProducto').classList.remove('show');
    productoEditando = null;
    variantesEditando = [];
}

function cerrarModalConfirmar() {
    document.getElementById('modalConfirmar').classList.remove('show');
}

// Mensajes
function mostrarExito(mensaje) {
    // Implementar notificación de éxito (podrías usar una librería como toastr)
    alert(mensaje);
}

function mostrarError(mensaje) {
    // Implementar notificación de error
    alert(mensaje);
}

// ============================================
// GESTIÓN DE CATEGORÍAS
// ============================================

function abrirModalCategorias() {
    document.getElementById('modalCategorias').classList.add('show');
    cargarCategoriasEnModal();
}

function cerrarModalCategorias() {
    document.getElementById('modalCategorias').classList.remove('show');
    limpiarFormularioCategoria();
}

function limpiarFormularioCategoria() {
    document.getElementById('categoria-id').value = '';
    document.getElementById('categoria-nombre').value = '';
    document.getElementById('categoria-descripcion').value = '';
    document.getElementById('categoria-imagen').value = '';
    document.getElementById('categoria-padre').value = '0';
    document.getElementById('categoria-activo').value = 'true';
    document.getElementById('btn-categoria-text').textContent = 'Agregar';
}

async function cargarCategoriasEnModal() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('categorias-tbody');
    
    try {
        const response = await fetch('/admin/categorias/api', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) throw new Error('Error al cargar categorías');
        
        const data = await response.json();
        categorias = data.categorias || data;
        
        // Normalizar campos active/activo
        if (categorias && Array.isArray(categorias)) {
            categorias = categorias.map(cat => ({
                ...cat,
                activo: cat.active !== undefined ? cat.active : cat.activo
            }));
        }
        
        if (categorias.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No hay categorías registradas</td></tr>';
            return;
        }
        
        tbody.innerHTML = categorias.map(cat => {
            const categoriaPadre = categorias.find(c => c.id === cat.id_padre);
            const nombrePadre = categoriaPadre ? categoriaPadre.nombre : '-';
            
            return `
                <tr>
                    <td>${cat.id}</td>
                    <td><strong>${cat.nombre}</strong></td>
                    <td>${cat.descripcion || '-'}</td>
                    <td>${cat.id_padre === 0 ? '-' : nombrePadre}</td>
                    <td>
                        <span class="badge ${cat.activo ? 'badge-success' : 'badge-secondary'}">
                            ${cat.activo ? 'Activo' : 'Inactivo'}
                        </span>
                    </td>
                    <td>
                        <button class="btn-icon btn-icon-edit" onclick="editarCategoria(${cat.id})" title="Editar">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon btn-icon-delete" onclick="eliminarCategoria(${cat.id})" title="Eliminar">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
        
        // Actualizar filtro de categorías en la página principal
        actualizarFiltroCategorias();
        
        // Actualizar select de categoría padre
        actualizarSelectCategoriaPadre();
        
    } catch (error) {
        console.error('Error:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red;">Error al cargar categorías</td></tr>';
    }
}

function actualizarSelectCategoriaPadre() {
    const select = document.getElementById('categoria-padre');
    const currentId = document.getElementById('categoria-id').value;
    
    // Limpiar opciones excepto la primera
    select.innerHTML = '<option value="0">--- Sin categoría padre ---</option>';
    
    // Agregar categorías activas, excluyendo la categoría actual (para evitar loops)
    categorias
        .filter(cat => cat.activo && cat.id != currentId)
        .forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.nombre;
            select.appendChild(option);
        });
}

async function guardarCategoria(event) {
    event.preventDefault();
    
    const token = localStorage.getItem('admin_token');
    const categoriaId = document.getElementById('categoria-id').value;
    const nombreInput = document.getElementById('categoria-nombre');
    const nombre = nombreInput?.value?.trim() || '';
    const descripcion = document.getElementById('categoria-descripcion').value?.trim() || '';
    const imagen_url = document.getElementById('categoria-imagen').value?.trim() || '';
    const id_padre = parseInt(document.getElementById('categoria-padre').value) || 0;
    const activo = document.getElementById('categoria-activo').value === 'true';
    
    console.log('Guardando categoría:');
    console.log('- nombre:', nombre, '(length:', nombre.length, ')');
    console.log('- descripcion:', descripcion);
    console.log('- imagen_url:', imagen_url);
    console.log('- id_padre:', id_padre);
    console.log('- activo:', activo);
    console.log('- categoriaId:', categoriaId);
    
    if (!nombre) {
        console.error('NOMBRE ESTÁ VACÍO!');
        mostrarError('El nombre de la categoría es requerido');
        nombreInput?.focus();
        return;
    }
    
    console.log('✓ Validación de nombre pasó, enviando al servidor...');
    
    // Crear FormData para enviar
    const formData = new FormData();
    formData.append('nombre', nombre);
    formData.append('descripcion', descripcion);
    if (imagen_url) {
        formData.append('imagen_url', imagen_url);
    }
    formData.append('id_padre', id_padre);
    formData.append('active', activo);
    
    const url = categoriaId ? `/admin/categorias/${categoriaId}/upload` : '/admin/categorias/upload';
    const method = categoriaId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.detail || data.message || 'Error al guardar categoría');
        }
        
        mostrarExito(data.message || (categoriaId ? 'Categoría actualizada correctamente' : 'Categoría creada correctamente'));
        limpiarFormularioCategoria();
        cargarCategoriasEnModal();
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al guardar la categoría');
    }
}

function editarCategoria(id) {
    const categoria = categorias.find(c => c.id === id);
    if (!categoria) return;
    
    document.getElementById('categoria-id').value = categoria.id;
    document.getElementById('categoria-nombre').value = categoria.nombre;
    document.getElementById('categoria-descripcion').value = categoria.descripcion || '';
    document.getElementById('categoria-imagen').value = categoria.imagen_url || '';
    document.getElementById('categoria-activo').value = categoria.activo ? 'true' : 'false';
    document.getElementById('btn-categoria-text').textContent = 'Actualizar';
    
    // Actualizar select de categoría padre y establecer valor
    actualizarSelectCategoriaPadre();
    document.getElementById('categoria-padre').value = categoria.id_padre || 0;
    
    // Scroll al formulario
    document.querySelector('#formCategoria').scrollIntoView({ behavior: 'smooth' });
}

async function eliminarCategoria(id) {
    if (!confirm('¿Está seguro de eliminar esta categoría? Esta acción no se puede deshacer.')) {
        return;
    }
    
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch(`/admin/categorias/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.detail || 'Error al eliminar categoría');
        }
        
        mostrarExito(data.message || 'Categoría eliminada correctamente');
        cargarCategoriasEnModal();
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al eliminar la categoría. Puede que tenga productos asociados.');
    }
}

function actualizarFiltroCategorias() {
    const select = document.getElementById('filterCategoria');
    const valorActual = select.value;
    
    select.innerHTML = '<option value="">Todas las categorías</option>' +
        categorias
            .filter(c => c.activo)
            .map(c => `<option value="${c.id}">${c.nombre}</option>`)
            .join('');
    
    // Restaurar valor seleccionado si existe
    if (valorActual) {
        select.value = valorActual;
    }
}

// Variables para selector de imágenes
let imagenesDisponibles = [];
let campoImagenActual = null;

// Abrir selector de imágenes
window.abrirSelectorImagenes = async function(campoId) {
    console.log('abrirSelectorImagenes llamada con:', campoId);
    campoImagenActual = campoId;
    const modal = document.getElementById('modalImagenes');
    modal.style.display = 'flex';
    
    // Mostrar loading
    document.getElementById('imagenes-loading').style.display = 'block';
    document.getElementById('imagenes-grid').style.display = 'none';
    
    // Cargar imágenes disponibles
    await cargarImagenesDisponibles();
    
    // Si es para categoría, ordenar para mostrar primero las de categorías
    if (campoId === 'categoria-imagen') {
        imagenesDisponibles.sort((a, b) => {
            const aEsCategoria = a.carpeta === 'categorias' ? 0 : 1;
            const bEsCategoria = b.carpeta === 'categorias' ? 0 : 1;
            if (aEsCategoria !== bEsCategoria) return aEsCategoria - bEsCategoria;
            return a.nombre.localeCompare(b.nombre);
        });
    }
    
    // Mostrar grid
    document.getElementById('imagenes-loading').style.display = 'none';
    document.getElementById('imagenes-grid').style.display = 'grid';
    
    // Limpiar búsqueda y mostrar imágenes
    document.getElementById('buscar-imagen').value = '';
    mostrarImagenesEnGrid(imagenesDisponibles);
}

// Cerrar selector de imágenes
window.cerrarSelectorImagenes = function() {
    document.getElementById('modalImagenes').style.display = 'none';
    campoImagenActual = null;
    imagenesDisponibles = [];
}

// Cargar imágenes disponibles del servidor
async function cargarImagenesDisponibles() {
    const token = localStorage.getItem('admin_token');
    
    try {
        const response = await fetch('/admin/productos/api/imagenes-disponibles', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) throw new Error('Error al cargar imágenes');
        
        const data = await response.json();
        imagenesDisponibles = data.imagenes || [];
        
        mostrarImagenesEnGrid(imagenesDisponibles);
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al cargar las imágenes disponibles');
        imagenesDisponibles = [];
        mostrarImagenesEnGrid([]);
    }
}

// Mostrar imágenes en el grid
function mostrarImagenesEnGrid(imagenes) {
    const grid = document.getElementById('imagenes-grid');
    grid.innerHTML = '';
    
    if (imagenes.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
                <i class="fas fa-images" style="font-size: 48px; margin-bottom: 10px; display: block;"></i>
                <p>No se encontraron imágenes</p>
            </div>
        `;
        return;
    }
    
    // Detectar si estamos seleccionando para una categoría
    const esParaCategoria = campoImagenActual === 'categoria-imagen';
    
    imagenes.forEach(imagen => {
        const div = document.createElement('div');
        div.className = 'imagen-item';
        
        // Destacar las imágenes de categorías si estamos seleccionando para una categoría
        if (esParaCategoria && imagen.carpeta === 'categorias') {
            div.classList.add('imagen-item-destacada');
        }
        
        div.onclick = () => seleccionarImagen(imagen.url);
        
        div.innerHTML = `
            <img src="${imagen.url}" alt="${imagen.nombre}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22150%22 height=%22120%22><rect fill=%22%23333%22 width=%22150%22 height=%22120%22/><text fill=%22%23999%22 x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2214%22>Error</text></svg>'">
            <div class="imagen-item-info">
                <div class="imagen-item-nombre" title="${imagen.nombre}">${imagen.nombre}</div>
                <div class="imagen-item-carpeta">${imagen.carpeta}</div>
            </div>
        `;
        
        grid.appendChild(div);
    });
}

// Seleccionar una imagen
function seleccionarImagen(url) {
    if (campoImagenActual) {
        const campo = document.getElementById(campoImagenActual);
        campo.value = url;
        
        // Si es un campo de variante, actualizar el array también
        if (campoImagenActual.startsWith('variante-imagen-')) {
            const index = parseInt(campoImagenActual.replace('variante-imagen-', ''));
            actualizarVariante(index, 'imagen_url', url);
        }
    }
    cerrarSelectorImagenes();
    mostrarExito('Imagen seleccionada correctamente');
}

// Filtrar imágenes en el selector
window.filtrarImagenesSelector = function() {
    const busqueda = document.getElementById('buscar-imagen').value.toLowerCase();
    
    if (!busqueda) {
        mostrarImagenesEnGrid(imagenesDisponibles);
        return;
    }
    
    const filtradas = imagenesDisponibles.filter(img => 
        img.nombre.toLowerCase().includes(busqueda) ||
        img.carpeta.toLowerCase().includes(busqueda)
    );
    
    mostrarImagenesEnGrid(filtradas);
}

// Confirmar que las funciones están disponibles
console.log('Funciones del selector de imágenes registradas:', {
    abrirSelectorImagenes: typeof window.abrirSelectorImagenes,
    cerrarSelectorImagenes: typeof window.cerrarSelectorImagenes,
    filtrarImagenesSelector: typeof window.filtrarImagenesSelector
});
