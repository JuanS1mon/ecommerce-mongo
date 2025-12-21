/**
 * Módulo para cargar productos dinámicamente en la página de índice
 * Incluye búsqueda y filtrado en tiempo real
 */

const indexProducts = (() => {
    let allProducts = [];
    let filteredProducts = [];
    const container = document.getElementById('featured-products-container');
    const recommendedContainer = document.getElementById('recommended-products-container');
    const searchInput = document.getElementById('products-search-input');
    const categorySelect = document.getElementById('products-category-filter');

    // Cargar productos públicos desde la API
    async function loadProducts() {
        try {
            const response = await fetch('/ecomerce/api/productos/publicos?limit=12');
            
            if (!response.ok) {
                throw new Error('Error al cargar productos');
            }

            allProducts = await response.json();
            filteredProducts = [...allProducts];
            renderProducts();
            
            // Cargar productos recomendados
            loadRecommendedProducts();
            
            initializeEventListeners();
        } catch (error) {
            console.error('Error cargando productos:', error);
            showErrorMessage('No se pudieron cargar los productos');
        }
    }

    // Cargar productos recomendados (destacados/populares)
    async function loadRecommendedProducts() {
        try {
            if (!recommendedContainer) return;

            // Intentar cargar productos destacados
            const response = await fetch('/ecomerce/api/productos/publicos?limit=8&destacado=true');
            
            let recommendedProducts = [];
            if (response.ok) {
                recommendedProducts = await response.json();
            }

            // Si no hay productos destacados, mostrar los primeros 8 o aleatorios
            if (recommendedProducts.length === 0) {
                recommendedProducts = allProducts.slice(0, 8);
                
                // Si tenemos más de 8, mezclarlos aleatoriamente
                if (allProducts.length > 8) {
                    recommendedProducts = allProducts
                        .sort(() => Math.random() - 0.5)
                        .slice(0, 8);
                }
            }

            renderRecommendedProducts(recommendedProducts);
        } catch (error) {
            console.error('Error cargando productos recomendados:', error);
            // No mostrar error, simplemente no mostrar sección
        }
    }

    // Renderizar productos recomendados
    function renderRecommendedProducts(products) {
        if (!recommendedContainer || products.length === 0) return;

        const section = document.getElementById('recommended-section') || 
                       recommendedContainer.closest('section') || 
                       recommendedContainer.parentElement;

        recommendedContainer.innerHTML = products.map((product, index) => `
            <div class="product-card animate-fade-in-up" style="animation-delay: ${index * 50}ms">
                <a href="/ecomerce/productos/${product.id}" class="block h-48 bg-gray-200 flex items-center justify-center overflow-hidden group cursor-pointer relative">
                    ${product.imagen_url 
                        ? `<img src="${product.imagen_url}" alt="${product.nombre}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300">` 
                        : `<i class="fas fa-image text-4xl text-gray-400"></i>`
                    }
                    <!-- Badge "Recomendado" -->
                    <div class="absolute top-2 right-2 bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1">
                        <i class="fas fa-star"></i>
                        Destacado
                    </div>
                </a>
                <div class="p-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">${product.nombre}</h3>
                    <p class="text-gray-600 text-sm mb-4 line-clamp-2">${product.descripcion || 'Producto sin descripción'}</p>
                    
                    <!-- Variantes si existen -->
                    ${product.variantes && product.variantes.length > 0 
                        ? `<div class="mb-4">
                            <p class="text-xs text-gray-500 mb-2">
                                <i class="fas fa-layer-group mr-1"></i>
                                ${product.variantes.length} variante${product.variantes.length !== 1 ? 's' : ''}
                            </p>
                        </div>`
                        : ''
                    }
                    
                    <div class="flex items-center justify-between">
                        <span class="text-2xl font-bold text-blue-600">$${product.precio}</span>
                        <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors add-to-cart-btn" 
                                data-product-id="${product.id}" 
                                data-product-name="${product.nombre}"
                                data-price="${product.precio}">
                            <i class="fas fa-cart-plus mr-1"></i>Agregar
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        // Agregar event listeners a los botones de agregar al carrito
        attachCartButtonListeners();
    }

    // Renderizar productos en el DOM
    function renderProducts() {
        if (!container) return;

        if (filteredProducts.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-search text-4xl text-gray-400 mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">No se encontraron productos</h3>
                    <p class="text-gray-500">Intenta con otros términos de búsqueda</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filteredProducts.map((product, index) => `
            <div class="product-card animate-fade-in-up" style="animation-delay: ${index * 50}ms">
                <a href="/ecomerce/productos/${product.id}" class="block h-48 bg-gray-200 flex items-center justify-center overflow-hidden group cursor-pointer">
                    ${product.imagen_url 
                        ? `<img src="${product.imagen_url}" alt="${product.nombre}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300">` 
                        : `<i class="fas fa-image text-4xl text-gray-400"></i>`
                    }
                </a>
                <div class="p-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">${product.nombre}</h3>
                    <p class="text-gray-600 text-sm mb-4 line-clamp-3">${product.descripcion || 'Producto sin descripción'}</p>
                    
                    <!-- Variantes si existen -->
                    ${product.variantes && product.variantes.length > 0 
                        ? `<div class="mb-4">
                            <p class="text-xs text-gray-500 mb-2">
                                <i class="fas fa-layer-group mr-1"></i>
                                ${product.variantes.length} variante${product.variantes.length !== 1 ? 's' : ''}
                            </p>
                        </div>`
                        : ''
                    }
                    
                    <div class="flex items-center justify-between">
                        <span class="text-2xl font-bold text-blue-600">$${product.precio}</span>
                        <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors add-to-cart-btn" 
                                data-product-id="${product.id}" 
                                data-product-name="${product.nombre}"
                                data-price="${product.precio}">
                            <i class="fas fa-cart-plus mr-1"></i>Agregar
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        // Agregar event listeners a los botones de agregar al carrito
        attachCartButtonListeners();
    }

    // Filtrar productos
    function filterProducts() {
        const searchTerm = (searchInput?.value || '').toLowerCase().trim();
        const selectedCategory = categorySelect?.value || '';

        filteredProducts = allProducts.filter(product => {
            const matchesSearch = !searchTerm || 
                product.nombre.toLowerCase().includes(searchTerm) ||
                (product.descripcion && product.descripcion.toLowerCase().includes(searchTerm)) ||
                (product.codigo && product.codigo.toLowerCase().includes(searchTerm));

            const matchesCategory = !selectedCategory || product.id_categoria === selectedCategory;

            return matchesSearch && matchesCategory;
        });

        renderProducts();
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
            searchInput.addEventListener('input', debounce(filterProducts, 300));
        }
        if (categorySelect) {
            categorySelect.addEventListener('change', filterProducts);
        }
    }

    // Adjuntar listeners a botones de carrito
    function attachCartButtonListeners() {
        document.querySelectorAll('.add-to-cart-btn').forEach(button => {
            button.addEventListener('click', async function(e) {
                e.preventDefault();
                
                const productId = this.getAttribute('data-product-id');
                const productName = this.getAttribute('data-product-name');
                const price = parseFloat(this.getAttribute('data-price'));

                // Verificar autenticación
                const token = localStorage.getItem('ecommerce_token');
                if (!token) {
                    showToast('Debes iniciar sesión para agregar productos', 'warning');
                    setTimeout(() => {
                        window.location.href = '/ecomerce/login';
                    }, 1500);
                    return;
                }

                // Animación del botón
                const originalHTML = this.innerHTML;
                this.disabled = true;
                this.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Agregando...';

                try {
                    // Usar la función global del carrito si está disponible
                    if (window.cart && typeof window.cart.addProduct === 'function') {
                        await window.cart.addProduct(productId, 1, price);
                        showToast(`${productName} agregado al carrito`, 'success');
                    } else {
                        showToast('El carrito no está disponible', 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showToast('Error al agregar el producto', 'error');
                } finally {
                    setTimeout(() => {
                        this.innerHTML = originalHTML;
                        this.disabled = false;
                    }, 1500);
                }
            });
        });
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

    // Toast para mensajes
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        const bgColor = type === 'success' ? 'bg-green-500' : 
                       type === 'error' ? 'bg-red-500' :
                       type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
        toast.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center space-x-2`;
        toast.innerHTML = `
            <i class="fas ${
                type === 'success' ? 'fa-check-circle' :
                type === 'error' ? 'fa-exclamation-circle' :
                type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'
            }"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3500);
    }

    // Retornar API pública
    return {
        init: () => {
            loadProducts();
        }
    };
})();

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    indexProducts.init();
});
