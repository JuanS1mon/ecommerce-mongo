/**
 * JavaScript para la gestión de productos
 * Generado automáticamente
 */

// Variables globales
let allData = [];
let currentItemId = null;

// Determinar la ruta base para las peticiones (sin hardcodear)
let baseRoute = window.location.pathname;
// Si termina en /pagina, quitarlo para obtener la base
if (baseRoute.endsWith('/pagina')) {
    baseRoute = baseRoute.slice(0, -('/pagina'.length));
}
// Quitar barra final si existe
if (baseRoute.endsWith('/')) {
    baseRoute = baseRoute.slice(0, -1);
}

// Cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar eventos
    document.getElementById('data-form').addEventListener('submit', addItem);
    document.getElementById('edit-form').addEventListener('submit', updateItem);
    document.getElementById('search-input').addEventListener('input', filterTable);
    document.getElementById('reset-search').addEventListener('click', resetSearch);
    document.getElementById('confirm-delete').addEventListener('click', confirmDelete);
    document.getElementById('cancel-delete').addEventListener('click', closeDeleteModal);
    
    // Cargar datos iniciales
    fetchData();
});

/**
 * Obtiene los datos del servidor y actualiza la tabla
 */
async function fetchData() {
    try {
        const response = await fetch(baseRoute + '/');
        
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Verificar si la respuesta es un array
        if (!Array.isArray(data)) {
            console.error("La respuesta no es un array:", data);
            showToast('Error al cargar los datos. La respuesta no tiene el formato esperado.', 'error');
            return;
        }
        
        // Guardar datos para filtrado
        allData = data;
        
        // Actualizar la UI
        updateTable(data);
        updateRecordCount(data.length);
        
    } catch (error) {
        console.error("Error al cargar datos:", error);
        showToast(`Error al cargar los datos: ${error.message}`, 'error');
        
        const tableBody = document.getElementById('products-grid');
        tableBody.innerHTML = `
            <div class="col-span-full text-center py-12">
                <i class="fas fa-exclamation-circle text-red-500 text-4xl mb-4"></i>
                <p class="text-red-500 text-lg">Error al cargar productos. Intente recargar la página.</p>
            </div>
        `;
    }
}

/**
 * Actualiza el grid con los datos proporcionados
 */
function updateTable(data) {
    const grid = document.getElementById('products-grid');
    grid.innerHTML = '';
    
    if (data.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-12">
                <i class="fas fa-box-open text-gray-400 text-4xl mb-4"></i>
                <p class="text-gray-500 text-lg">No se encontraron productos</p>
            </div>
        `;
        return;
    }
    
    data.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden group';
        
    const imageUrl = item.imagen_url || '/static/img/logo.png';
        const price = item.precio ? `$${item.precio.toLocaleString()}` : 'Precio no disponible';
        
        card.innerHTML = `
            <div class="relative overflow-hidden">
                <img src="${imageUrl}" alt="${item.nombre}" class="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300" onerror="this.onerror=null; this.src='/static/img/logo.png'">
                ${!item.active ? '<div class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded text-xs">Inactivo</div>' : ''}
            </div>
            <div class="p-4">
                <h3 class="text-lg font-semibold text-gray-800 mb-2 line-clamp-2">${item.nombre}</h3>
                <p class="text-gray-600 text-sm mb-3 line-clamp-3">${item.descripcion || 'Sin descripción'}</p>
                <div class="flex justify-between items-center mb-3">
                    <span class="text-2xl font-bold text-green-600">${price}</span>
                    <span class="text-xs text-gray-500">ID: ${item.id}</span>
                </div>
                <div class="flex space-x-2">
                    <button class="flex-1 bg-blue-500 text-white py-2 px-3 rounded-md hover:bg-blue-600 transition-colors text-sm font-medium" onclick="editItem(${item.id})">
                        <i class="fas fa-edit mr-1"></i> Editar
                    </button>
                    <button class="flex-1 bg-red-500 text-white py-2 px-3 rounded-md hover:bg-red-600 transition-colors text-sm font-medium" onclick="showDeleteModal(${item.id})">
                        <i class="fas fa-trash-alt mr-1"></i> Eliminar
                    </button>
                </div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

/**
 * Actualiza el contador de registros
 */
function updateRecordCount(count) {
    const recordCount = document.getElementById('record-count');
    recordCount.textContent = count === 1 
        ? '1 producto encontrado' 
        : `${count} productos encontrados`;
}

/**
 * Añade un nuevo registro
 */
async function addItem(event) {
    event.preventDefault();
    
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Guardando...';
    
    const formData = {
        codigo: document.getElementById('codigo').value || null,
        nombre: document.getElementById('nombre').value || null,
        descripcion: document.getElementById('descripcion').value || null,
        id_categoria: parseInt(document.getElementById('id_categoria').value),
        precio: parseInt(document.getElementById('precio').value),
        imagen_url: document.getElementById('imagen_url').value || null,
        active: document.getElementById('active').checked
    };
    
    try {
        const response = await fetch('/ecomerce/api/productos/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Error al crear el registro");
        }
        
        const result = await response.json();
        console.log("Registro creado:", result);
        
        // Limpiar formulario
        document.getElementById('data-form').reset();
        
        // Refrescar datos
        fetchData();
        
        // Mostrar notificación
        showToast('Registro creado correctamente', 'success');
        
    } catch (error) {
        console.error("Error:", error);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Guardar';
    }
}

/**
 * Muestra el modal de edición con los datos del registro
 */
function editItem(id) {
    fetch(`/ecomerce/api/productos/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Error al obtener los datos del registro");
            }
            return response.json();
        })
        .then(data => {
            // Guardar el ID actual
            currentItemId = id;
            
            // Rellenar el formulario
            document.getElementById('edit-id').value = data.id;
            
            document.getElementById('edit-codigo').value = data.codigo;document.getElementById('edit-nombre').value = data.nombre;document.getElementById('edit-descripcion').value = data.descripcion;document.getElementById('edit-id_categoria').value = data.id_categoria;document.getElementById('edit-precio').value = data.precio;document.getElementById('edit-imagen_url').value = data.imagen_url;document.getElementById('edit-active').value = data.active;
            
            // Mostrar el modal
            document.getElementById('edit-modal').classList.remove('hidden');
        })
        .catch(error => {
            console.error("Error al obtener datos para editar:", error);
            showToast(`Error: ${error.message}`, 'error');
        });
}

/**
 * Cierra el modal de edición
 */
function closeEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');
    currentItemId = null;
}

/**
 * Actualiza un registro
 */
async function updateItem(event) {
    event.preventDefault();
    
    if (!currentItemId) {
        showToast('Error: No se pudo identificar el registro a actualizar', 'error');
        return;
    }
    
    const id = currentItemId;
    const updatedData = {
        codigo: document.getElementById('edit-codigo').value,
        nombre: document.getElementById('edit-nombre').value,
        descripcion: document.getElementById('edit-descripcion').value,
        id_categoria: parseInt(document.getElementById('edit-id_categoria').value) || 0,
        precio: parseInt(document.getElementById('edit-precio').value) || 0,
        imagen_url: document.getElementById('edit-imagen_url').value,
        active: document.getElementById('edit-active').checked
    };
    
    try {
        const response = await fetch(`/ecomerce/api/productos/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Error al actualizar el registro");
        }
        
        // Cerrar modal y refrescar datos
        closeEditModal();
        fetchData();
        
        // Mostrar notificación
        showToast('Registro actualizado correctamente', 'success');
        
    } catch (error) {
        console.error("Error:", error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

/**
 * Muestra el modal de confirmación para eliminar
 */
function showDeleteModal(id) {
    currentItemId = id;
    document.getElementById('delete-modal').classList.remove('hidden');
}

/**
 * Cierra el modal de confirmación para eliminar
 */
function closeDeleteModal() {
    document.getElementById('delete-modal').classList.add('hidden');
    currentItemId = null;
}

/**
 * Elimina un registro después de confirmar
 */
async function confirmDelete() {
    if (!currentItemId) {
        showToast('Error: No se pudo identificar el registro a eliminar', 'error');
        closeDeleteModal();
        return;
    }
    
    const id = currentItemId;
    
    try {
        const response = await fetch(`/ecomerce/api/productos/${id}`, { method: 'DELETE' });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Error al eliminar el registro");
        }
        
        // Cerrar modal y refrescar datos
        closeDeleteModal();
        fetchData();
        
        // Mostrar notificación
        showToast('Registro eliminado correctamente', 'success');
        
    } catch (error) {
        console.error("Error:", error);
        showToast(`Error: ${error.message}`, 'error');
        closeDeleteModal();
    }
}

/**
 * Filtra la tabla según el texto de búsqueda
 */
function filterTable() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    if (!searchTerm) {
        updateTable(allData);
        updateRecordCount(allData.length);
        return;
    }
    
    const filteredData = allData.filter(item => {
        return String(item.id).toLowerCase().includes(searchTerm) || String(item.codigo).toLowerCase().includes(searchTerm) || String(item.nombre).toLowerCase().includes(searchTerm) || String(item.descripcion).toLowerCase().includes(searchTerm) || String(item.id_categoria).toLowerCase().includes(searchTerm) || String(item.precio).toLowerCase().includes(searchTerm) || String(item.imagen_url).toLowerCase().includes(searchTerm) || String(item.active).toLowerCase().includes(searchTerm);
    });
    
    updateTable(filteredData);
    updateRecordCount(filteredData.length);
}

/**
 * Restablece la búsqueda
 */
function resetSearch() {
    document.getElementById('search-input').value = '';
    updateTable(allData);
    updateRecordCount(allData.length);
}

/**
 * Muestra/oculta la descripción
 */
function toggleDescription() {
    const description = document.getElementById('description');
    description.classList.toggle('hidden');
}

/**
 * Muestra una notificación toast
 */
function showToast(message, type = 'success') {
    // Crear el elemento toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} slide-in`;
    toast.innerHTML = `
        <div class="flex items-center">
            <i class="${type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle'} mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    // Añadir al contenedor
    const container = document.getElementById('toast-container');
    container.appendChild(toast);
    
    // Eliminar después de 5 segundos
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 5000);
}