/**
 * Módulo para cargar servicios dinámicamente en la página de servicios
 * Incluye búsqueda y filtrado en tiempo real
 */

const serviciosModule = (() => {
    let allServicios = [];
    let filteredServicios = [];
    const container = document.getElementById('featured-products-container');
    const searchInput = document.getElementById('products-search-input');
    const categorySelect = document.getElementById('products-category-filter');

    // Cargar servicios públicos desde la API
    async function loadServicios() {
        try {
            // Mostrar indicador de carga
            if (container) {
                container.innerHTML = `
                    <div class="col-span-full text-center py-12">
                        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                        <p class="mt-2 text-gray-600">Cargando servicios...</p>
                    </div>
                `;
            }

            const response = await fetch('/api/servicios/publicos?' + new Date().getTime(), {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error('Error al cargar servicios');
            }

            allServicios = await response.json();
            console.log('🔄 Servicios cargados desde API:', allServicios.length, 'servicios');
            allServicios.forEach((s, i) => console.log(`  ${i+1}. ID: ${s.id} - ${s.nombre}`));
            
            // Verificar que no haya IDs mock
            const mockIds = ['507f1f77bcf86cd799439011'];
            const hasMockData = allServicios.some(s => mockIds.includes(s.id));
            if (hasMockData) {
                console.warn('⚠️ ADVERTENCIA: Se detectaron IDs mock en los datos. Posible cache antigua.');
                console.warn('💡 Recomendación: Limpiar cache del navegador (Ctrl+F5) y recargar.');
                
                // Mostrar advertencia al usuario
                showCacheWarning();
            } else {
                console.log('✅ Todos los IDs son válidos (no mock)');
            }
            
            filteredServicios = [...allServicios];
            renderServicios();

            initializeEventListeners();
        } catch (error) {
            console.error('Error cargando servicios:', error);
            showErrorMessage('No se pudieron cargar los servicios');
        }
    }

    // Renderizar servicios en el DOM
    function renderServicios() {
        if (!container) return;

        if (filteredServicios.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-search text-4xl text-gray-400 mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">No se encontraron servicios</h3>
                    <p class="text-gray-500">Intenta con otros términos de búsqueda</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filteredServicios.map((servicio, index) => `
            <div class="product-card animate-fade-in-up" style="animation-delay: ${index * 50}ms">
                <a href="/servicio/${servicio.id}" class="block h-48 bg-gray-200 flex items-center justify-center overflow-hidden group cursor-pointer">
                    <div class="w-full h-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <i class="fas fa-cogs text-6xl text-white"></i>
                    </div>
                </a>
                <div class="p-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">${servicio.nombre}</h3>
                    <p class="text-gray-600 text-sm mb-4 line-clamp-3">${servicio.descripcion || 'Servicio sin descripción'}</p>

                    <!-- Tipo de servicio -->
                    <div class="mb-4">
                        <span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                            <i class="fas fa-tag mr-1"></i>${servicio.tipo_servicio}
                        </span>
                    </div>

                    <div class="flex items-center justify-between">
                        <span class="text-2xl font-bold text-blue-600">Desde $${servicio.precio_base}</span>
                        <a href="/servicio/${servicio.id}" class="btn-primary text-sm px-4 py-2">
                            Ver Detalles
                        </a>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Filtrar servicios
    function filterServicios() {
        const searchTerm = (searchInput?.value || '').toLowerCase().trim();
        const selectedCategory = categorySelect?.value || '';

        filteredServicios = allServicios.filter(servicio => {
            const matchesSearch = !searchTerm ||
                servicio.nombre.toLowerCase().includes(searchTerm) ||
                (servicio.descripcion && servicio.descripcion.toLowerCase().includes(searchTerm)) ||
                (servicio.tipo_servicio && servicio.tipo_servicio.toLowerCase().includes(searchTerm));

            const matchesCategory = !selectedCategory || servicio.tipo_servicio === selectedCategory;

            return matchesSearch && matchesCategory;
        });

        renderServicios();
    }

    // Debounce para búsqueda en tiempo real
    function debounce(func, delay) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Inicializar event listeners
    function initializeEventListeners() {
        if (searchInput) {
            searchInput.addEventListener('input', debounce(filterServicios, 300));
        }
        if (categorySelect) {
            categorySelect.addEventListener('change', filterServicios);
        }
    }

    // Mostrar mensaje de error
    function showErrorMessage(message) {
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-exclamation-triangle text-4xl text-red-400 mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">Error</h3>
                    <p class="text-gray-500">${message}</p>
                </div>
            `;
        }
    }

    // Mostrar advertencia de cache antigua
    function showCacheWarning() {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'fixed top-4 right-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded shadow-lg z-50 max-w-md';
        warningDiv.innerHTML = `
            <div class="flex items-start">
                <i class="fas fa-exclamation-triangle mr-3 mt-1"></i>
                <div class="flex-1">
                    <strong class="font-bold">Cache Antigua Detectada</strong>
                    <p class="text-sm mt-1">Se encontraron datos obsoletos. Limpia el cache del navegador (Ctrl+F5) para ver los servicios actualizados.</p>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="mt-2 bg-yellow-200 hover:bg-yellow-300 px-3 py-1 rounded text-xs">
                        Entendido
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(warningDiv);
        
        // Auto-remover después de 10 segundos
        setTimeout(() => {
            if (warningDiv.parentElement) {
                warningDiv.remove();
            }
        }, 10000);
    }

    // Función de diagnóstico para consola
    function diagnoseCache() {
        console.log('🔍 Diagnóstico de Cache:');
        console.log('  - Servicios cargados:', allServicios.length);
        console.log('  - IDs de servicios:', allServicios.map(s => s.id));
        
        const mockIds = ['507f1f77bcf86cd799439011'];
        const mockServices = allServicios.filter(s => mockIds.includes(s.id));
        
        if (mockServices.length > 0) {
            console.error('❌ CACHE PROBLEM: Servicios con IDs mock encontrados:', mockServices);
            return false;
        } else {
            console.log('✅ No se encontraron IDs mock - Cache OK');
            return true;
        }
    }

    // Exponer función de diagnóstico globalmente
    window.diagnoseServiceCache = diagnoseCache;

    // Retornar API pública
    return {
        init: () => {
            loadServicios();
        },
        diagnose: diagnoseCache
    };
})();

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    serviciosModule.init();
});