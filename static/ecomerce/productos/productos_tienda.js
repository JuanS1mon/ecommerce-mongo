/**
 * JavaScript para la tienda pública de productos
 */

// Variables globales
let allData = [];
let allCategories = [];

// Cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Solo inicializar si estamos en la página de tienda
    if (!window.location.pathname.includes('/productos/tienda') && !window.location.pathname.includes('/productos/')) {
        return; // No ejecutar en otras páginas
    }

    // Inicializar eventos
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', filterProducts);
    }

    const categorySelect = document.getElementById('category-select');
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            filterProducts();
        });
    }

    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', filterProducts);
    }

    // Cargar datos iniciales
    loadCategories();
    loadProducts();
});

/**
 * Carga las categorías disponibles desde el servidor
 */
async function loadCategories() {
    try {
        const response = await fetch('/ecomerce/api/categorias/publicas');

        if (!response.ok) {
            throw new Error('Error HTTP: ' + response.status);
        }

        const categories = await response.json();

        // Verificar si la respuesta es un array
        if (!Array.isArray(categories)) {
            console.error("La respuesta de categorías no es un array:", categories);
            return;
        }

        // Guardar categorías para filtrado
        allCategories = categories;

        // Llenar el select de categorías
        const categoryFilter = document.getElementById('category-select');
        if (categoryFilter) {
            categoryFilter.innerHTML = '<option value="">Todas las categorías</option>';

            categories.forEach(function(category) {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.nombre;
                categoryFilter.appendChild(option);
            });

            // Habilitar el select después de cargar
            categoryFilter.disabled = false;
        }

        if (window.log) window.log('Categorías cargadas exitosamente');
    } catch (error) {
        console.error("Error al cargar categorías:", error);
        if (window.log) window.log('Error al cargar categorías: ' + error.message, 'error');
    }
}

/**
 * Carga los productos desde el servidor
 */
async function loadProducts() {
    try {
        const response = await fetch('/ecomerce/api/productos/tienda');

        if (!response.ok) {
            throw new Error('Error HTTP: ' + response.status);
        }

        const data = await response.json();

        // Verificar si la respuesta es un array
        if (!Array.isArray(data)) {
            console.error("La respuesta no es un array:", data);
            showToast('Error al cargar los productos. La respuesta no tiene el formato esperado.', 'error');
            return;
        }

        // Guardar datos para filtrado
        allData = data;

        // Actualizar la UI
        updateProductsGrid(data);
        updateRecordCount(data.length);

        // Si hay filtros activos, reaplicar después de cargar productos
        const searchInput = document.getElementById('search-input');
        const categorySelect = document.getElementById('category-select');

        const currentSearch = searchInput ? searchInput.value : '';
        const currentCategory = categorySelect ? categorySelect.value : '';

        if (currentSearch || currentCategory) {
            filterProducts();
        }

        if (window.log) window.log('Productos cargados exitosamente: ' + data.length);
    } catch (error) {
        console.error("Error al cargar productos:", error);
        showToast('Error al cargar los productos: ' + error.message, 'error');

        const grid = document.getElementById('products-container');
        if (grid) {
            grid.innerHTML = '<div class="col-span-full text-center py-12">' +
                '<i class="fas fa-exclamation-circle text-red-500 text-4xl mb-4"></i>' +
                '<p class="text-red-500 text-lg">Error al cargar productos. Intente recargar la página.</p>' +
                '</div>';
        }
    }
}

/**
 * Función para mostrar notificaciones toast simples
 */
function showToast(message, type = 'info') {
    // Crear elemento toast si no existe
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(toastContainer);
    }

    // Crear toast
    const toast = document.createElement('div');
    toast.className = 'px-4 py-2 rounded-lg shadow-lg text-white text-sm font-medium transition-all duration-300 transform translate-x-full';

    // Establecer colores según el tipo
    switch (type) {
        case 'success':
            toast.className += ' bg-green-500';
            break;
        case 'error':
            toast.className += ' bg-red-500';
            break;
        case 'warning':
            toast.className += ' bg-yellow-500';
            break;
        default:
            toast.className += ' bg-blue-500';
    }

    toast.textContent = message;

    // Animar entrada
    setTimeout(function() {
        toast.classList.remove('translate-x-full');
    }, 100);

    // Auto-remover después de 3 segundos
    setTimeout(function() {
        toast.classList.add('translate-x-full');
        setTimeout(function() {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

/**
 * Actualiza el contador de registros
 */
function updateRecordCount(count) {
    const counter = document.getElementById('record-count');
    if (counter) {
        counter.textContent = count === 1
            ? '1 producto disponible'
            : count + ' productos disponibles';
    }
}

/**
 * Filtra los productos según búsqueda y categoría
 */
function filterProducts() {
    const searchInput = document.getElementById('search-input');
    const categorySelect = document.getElementById('category-select');

    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const selectedCategory = categorySelect ? categorySelect.value : '';

    let filteredData = allData;

    // Filtrar por búsqueda
    if (searchTerm) {
        filteredData = filteredData.filter(function(item) {
            const nombre = (item.nombre || '').toLowerCase();
            const descripcion = (item.descripcion || '').toLowerCase();
            return nombre.includes(searchTerm) || descripcion.includes(searchTerm);
        });
    }

    // Filtrar por categoría
    if (selectedCategory) {
        filteredData = filteredData.filter(function(item) {
            return item.id_categoria === selectedCategory;
        });
    }

    // Actualizar la UI
    updateProductsGrid(filteredData);
    updateRecordCount(filteredData.length);
    updateCategoryDescription(selectedCategory, filteredData.length, allData.length);

    if (window.log) window.log('Productos filtrados: ' + filteredData.length + ' de ' + allData.length);
}

/**
 * Actualiza el grid con los productos proporcionados
 */
function updateProductsGrid(data) {
    const grid = document.getElementById('products-container');
    const loading = document.getElementById('loading');
    const noProducts = document.getElementById('no-products');
    
    grid.innerHTML = '';

    // Ocultar loading y no-products al inicio
    if (loading) loading.classList.add('hidden');
    if (noProducts) noProducts.classList.add('hidden');

    if (data.length === 0) {
        if (noProducts) {
            noProducts.classList.remove('hidden');
        } else {
            grid.innerHTML = '<div class="col-span-full empty-state">' +
                '<i class="fas fa-box-open empty-icon"></i>' +
                '<p class="text-lg">No se encontraron productos disponibles</p>' +
                '</div>';
        }
        return;
    }

    data.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'product-card fade-in';

        const imageUrl = item.imagen_url || '/static/img/logo.png';
        const basePrice = item.precio || 0;
        const hasVariants = item.variantes && item.variantes.length > 0;

        // Obtener campos visibles de variantes dinámicamente
        let variantFields = [];
        if (hasVariants) {
            // Campos a excluir (no visibles para selección del usuario)
            const excludedFields = ['precio_adicional', 'stock', 'imagen_url', 'active', 'product_id', '_id', 'id'];
            
            // Obtener todos los campos únicos de las variantes
            const allFields = new Set();
            item.variantes.forEach(variant => {
                Object.keys(variant).forEach(key => {
                    if (!excludedFields.includes(key) && variant[key] !== null && variant[key] !== undefined && variant[key] !== '') {
                        allFields.add(key);
                    }
                });
            });
            
            // Convertir a array y ordenar (color primero, luego tipo, luego otros)
            variantFields = Array.from(allFields).sort((a, b) => {
                const order = ['color', 'tipo'];
                const aIndex = order.indexOf(a);
                const bIndex = order.indexOf(b);
                if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
                if (aIndex !== -1) return -1;
                if (bIndex !== -1) return 1;
                return a.localeCompare(b);
            });
        }

        // Generar HTML para variantes
        let variantsHtml = '';
        if (hasVariants && variantFields.length > 0) {
            variantsHtml = '<div class="product-variants mt-3 space-y-3">';
            
            variantFields.forEach(field => {
                // Obtener opciones únicas para este campo
                const options = [...new Set(item.variantes.map(v => v[field]).filter(val => val !== null && val !== undefined && val !== ''))];
                
                if (options.length > 0) {
                    const fieldLabel = field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ');
                    variantsHtml += '<div>' +
                        '<label class="block text-xs font-medium text-gray-700 mb-2">' + fieldLabel + ':</label>' +
                        '<div class="flex flex-wrap gap-2">' +
                        options.map(function(option) { 
                            return '<button class="variant-btn px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white hover:bg-blue-50 hover:border-blue-300 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" data-variant-type="' + field + '" data-value="' + option + '">' + option + '</button>';
                        }).join('') +
                        '</div>' +
                        '</div>';
                }
            });
            
            variantsHtml += '</div>';
        }

        const priceDisplay = hasVariants ? '<span class="product-price" data-base-price="' + basePrice + '">$0</span>' : '<span class="product-price">$' + basePrice.toLocaleString('es-ES') + '</span>';

        // Escapar caracteres especiales en los valores para HTML
        const escapedNombre = (item.nombre || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        const escapedDescripcion = (item.descripcion || 'Sin descripción').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        const escapedCodigo = (item.codigo || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');

        card.innerHTML = '<div class="product-image-container relative">' +
            '<img src="' + imageUrl + '" alt="' + escapedNombre + '" class="product-image" onerror="this.onerror=null; this.src=\'/static/img/logo.png\'">' +
            '<button class="wishlist-btn absolute top-3 right-3 bg-white bg-opacity-90 hover:bg-opacity-100 text-gray-600 hover:text-red-500 p-2 rounded-full shadow-lg transition-all duration-200 z-10" data-product-id="' + item.id + '" title="Agregar a favoritos">' +
            '<i class="fas fa-heart text-xl"></i>' +
            '</button>' +
            '</div>' +
            '<div class="product-info">' +
            '<h3 class="product-title">' + escapedNombre + '</h3>' +
            '<p class="product-description">' + escapedDescripcion + '</p>' +
            '<div class="product-price-container">' +
            priceDisplay +
            '</div>' +
            '<div class="product-code">Código: ' + escapedCodigo + '</div>' +
            variantsHtml +
            '<div class="product-actions">' +
            '<button class="btn-primary product-btn" data-action="view" data-product-id="' + item.id + '">' +
            '<i class="fas fa-eye mr-1"></i> Ver Detalles' +
            '</button>' +
            '<button class="btn-primary product-btn" data-action="add-to-cart" data-product-id="' + escapedCodigo + '" data-price="' + basePrice + '" data-has-variants="' + hasVariants + '">' +
            '<i class="fas fa-cart-plus mr-1"></i> Agregar al Carrito' +
            '</button>' +
            '</div>' +
            '</div>';

        grid.appendChild(card);
    });

    // Agregar event listeners para variantes después de crear las cards
    setupVariantListeners();
    
    // Cargar estados de wishlist para todos los productos visibles
    loadWishlistStates();
}

/**
 * Carga los estados de wishlist para todos los productos visibles
 * Optimizado: hace una sola llamada para obtener toda la lista
 */
async function loadWishlistStates() {
    // Buscar token en todos los lugares posibles
    const token = sessionStorage.getItem('ecommerce_token') ||
                  localStorage.getItem('token') ||
                  localStorage.getItem('access_token');
    if (!token) return; // Usuario no autenticado, no cargar wishlist

    const wishlistButtons = document.querySelectorAll('.wishlist-btn');
    if (wishlistButtons.length === 0) return;

    try {
        // Obtener toda la lista de deseos de una vez
        const response = await fetch('/ecomerce/api/lista-deseos/', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            const wishlistProductIds = new Set(
                (data.productos || []).map(item => item.producto?.id || item.id_producto)
            );

            // Actualizar todos los botones según la lista
            wishlistButtons.forEach((button) => {
                const productId = button.getAttribute('data-product-id');
                if (productId) {
                    const inWishlist = wishlistProductIds.has(productId);
                    updateWishlistButton(button, inWishlist);
                }
            });
        }
        // Si falla (401, 404, etc), simplemente no actualizar los botones
    } catch (error) {
        // Error de red - ignorar silenciosamente
    }
}

/**
 * Actualiza el estado visual del botón de wishlist
 */
function updateWishlistButton(button, inWishlist) {
    const icon = button.querySelector('i');
    
    // Agregar animación de rebote
    button.style.transition = 'transform 0.2s ease';
    button.style.transform = 'scale(1.2)';
    setTimeout(() => {
        button.style.transform = 'scale(1)';
    }, 200);
    
    if (inWishlist) {
        button.classList.add('in-wishlist');
        button.classList.remove('text-gray-600');
        button.classList.add('text-red-500');
        icon.classList.remove('far');
        icon.classList.add('fas');
        button.setAttribute('title', 'Remover de favoritos');
    } else {
        button.classList.remove('in-wishlist');
        button.classList.remove('text-red-500');
        button.classList.add('text-gray-600');
        icon.classList.remove('fas');
        icon.classList.add('far');
        button.setAttribute('title', 'Agregar a favoritos');
    }
}

/**
 * Alterna el estado de wishlist de un producto
 */
async function toggleWishlist(productId, button) {
    // Buscar token en todos los lugares posibles
    const token = sessionStorage.getItem('ecommerce_token') ||
                  localStorage.getItem('token') ||
                  localStorage.getItem('access_token');
    
    if (!token) {
        showToast('Debes iniciar sesión para agregar favoritos', 'warning');
        setTimeout(() => {
            window.location.href = '/ecomerce/login?redirect=' + encodeURIComponent(window.location.pathname);
        }, 1500);
        return;
    }

    const isInWishlist = button.classList.contains('in-wishlist');
    
    try {
        if (isInWishlist) {
            // Remover de wishlist
            const response = await fetch(`/ecomerce/api/lista-deseos/productos/${productId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                updateWishlistButton(button, false);
                showToast('Producto removido de favoritos', 'success');
                updateWishlistCount();
            } else {
                const error = await response.json();
                showToast(error.detail || 'Error al remover de favoritos', 'error');
            }
        } else {
            // Agregar a wishlist
            const response = await fetch('/ecomerce/api/lista-deseos/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ id_producto: productId })
            });

            if (response.ok) {
                updateWishlistButton(button, true);
                showToast('Producto agregado a favoritos', 'success');
                updateWishlistCount();
            } else if (response.status === 401) {
                showToast('Sesión expirada. Por favor, inicia sesión nuevamente', 'warning');
                setTimeout(() => {
                    window.location.href = '/ecomerce/login?redirect=' + encodeURIComponent(window.location.pathname);
                }, 1500);
            } else {
                const error = await response.json();
                showToast(error.detail || 'Error al agregar a favoritos', 'error');
            }
        }
    } catch (error) {
        console.error('Error al toggle wishlist:', error);
        showToast('Error de conexión. Intenta nuevamente', 'error');
    }
}

/**
 * Actualiza el contador de wishlist en la navegación
 */
async function updateWishlistCount() {
    const token = sessionStorage.getItem('ecommerce_token') ||
                 localStorage.getItem('token') ||
                 localStorage.getItem('access_token');
    if (!token) return;

    try {
        const response = await fetch('/ecomerce/api/lista-deseos/count', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            const badge = document.getElementById('wishlist-count');
            if (badge) {
                badge.textContent = data.count || 0;
                badge.classList.toggle('hidden', data.count === 0);
            }
        }
    } catch (error) {
        console.log('Error al actualizar contador de wishlist:', error);
    }
}

/**
 * Actualiza el card de descripción de categoría
 */
function updateCategoryDescription(selectedCategoryId, filteredCount, totalCount) {
    const card = document.getElementById('category-description-card');
    const title = document.getElementById('category-title');
    const description = document.getElementById('category-description');
    const count = document.getElementById('category-product-count');
    const imageContainer = document.getElementById('category-image-container');
    const image = document.getElementById('category-image');

    if (!card || !title || !description || !count || !imageContainer || !image) {
        console.error('Elementos del card de categoría no encontrados');
        return;
    }

    if (!selectedCategoryId) {
        // Sin categoría seleccionada, ocultar el card
        card.classList.remove('show');
        card.classList.add('hidden');
        return;
    }

    // Buscar la categoría seleccionada
    if (!allCategories || allCategories.length === 0) {
        console.warn('allCategories no está disponible aún');
        card.classList.remove('show');
        card.classList.add('hidden');
        return;
    }

    const category = allCategories.find(cat => String(cat.id) === selectedCategoryId);
    if (!category) {
        card.classList.remove('show');
        card.classList.add('hidden');
        return;
    }

    // Actualizar contenido
    title.textContent = category.nombre;
    description.textContent = category.descripcion || 'Descubre nuestros productos de esta categoría.';

    // Actualizar contador
    if (filteredCount !== totalCount) {
        count.textContent = `Mostrando ${filteredCount} de ${totalCount} productos`;
    } else {
        count.textContent = `Mostrando ${totalCount} productos`;
    }

    // Construir ruta de imagen basada en el nombre de la categoría
    // Normalizar el nombre: convertir a minúsculas, quitar acentos y espacios
    const categoryImageName = category.nombre
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // Remover acentos
        .replace(/\s+/g, '_') // Reemplazar espacios con guiones bajos
        .replace(/[^a-z0-9_]/g, ''); // Remover caracteres especiales
    
    const imagePath = `/static/img/categorias/${categoryImageName}.jpg`;
    
    // Actualizar imagen con fallback
    image.src = imagePath;
    image.alt = category.nombre;
    image.onerror = function() {
        // Si la imagen no existe, usar una imagen por defecto
        this.onerror = null; // Prevenir loop infinito
        this.src = '/static/img/logo.png';
    };

    // Mostrar el card
    card.classList.remove('hidden');
    card.classList.add('show');
}

/**
 * Configura los event listeners para los botones de variantes
 */
function setupVariantListeners() {
    // Usar event delegation para los botones de variantes
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('variant-btn')) {
            e.preventDefault();
            handleVariantSelection(e.target);
        }
    });
}

/**
 * Maneja la selección de variantes
 */
function handleVariantSelection(button) {
    const variantType = button.getAttribute('data-variant-type');
    const value = button.getAttribute('data-value');
    const productCard = button.closest('.product-card');

    if (!productCard) return;

    // Verificar si el botón ya está seleccionado
    const isSelected = button.classList.contains('selected');

    if (isSelected) {
        // Si ya está seleccionado, deseleccionar (toggle off)
        button.classList.remove('selected', 'bg-blue-500', 'text-white');
        button.classList.add('bg-white', 'text-gray-700');
    } else {
        // Encontrar todos los botones del mismo tipo en este producto
        const variantButtons = productCard.querySelectorAll(`.variant-btn[data-variant-type="${variantType}"]`);

        // Remover selección previa del mismo tipo
        variantButtons.forEach(btn => {
            btn.classList.remove('selected', 'bg-blue-500', 'text-white');
            btn.classList.add('bg-white', 'text-gray-700');
        });

        // Marcar el botón actual como seleccionado
        button.classList.remove('bg-white', 'text-gray-700');
        button.classList.add('selected', 'bg-blue-500', 'text-white');
    }

    // Actualizar el precio basado en las variantes seleccionadas
    updateProductPrice(productCard);
}

/**
 * Actualiza el precio del producto basado en las variantes seleccionadas
 */
function updateProductPrice(productCard) {
    const basePrice = parseFloat(productCard.querySelector('.product-price').getAttribute('data-base-price')) || 0;
    let totalAdditionalPrice = 0;

    // Encontrar todas las variantes seleccionadas en este producto
    const selectedVariants = productCard.querySelectorAll('.variant-btn.selected');

    // Buscar el producto en allData para obtener información de variantes
    const productId = productCard.querySelector('.product-btn[data-action="view"]').getAttribute('data-product-id');
    const product = allData.find(p => String(p.id) === productId);

    if (product && product.variantes) {
        selectedVariants.forEach(selectedBtn => {
            const variantType = selectedBtn.getAttribute('data-variant-type');
            const value = selectedBtn.getAttribute('data-value');

            // Encontrar la variante correspondiente
            const variant = product.variantes.find(v => v[variantType] === value);
            if (variant && variant.precio_adicional) {
                totalAdditionalPrice += parseFloat(variant.precio_adicional) || 0;
            }
        });
    }

    // Actualizar el precio mostrado
    const priceElement = productCard.querySelector('.product-price');
    const finalPrice = basePrice + totalAdditionalPrice;
    priceElement.textContent = '$' + finalPrice.toLocaleString('es-ES');

    // Actualizar el precio en el botón de agregar al carrito
    const addToCartBtn = productCard.querySelector('.product-btn[data-action="add-to-cart"]');
    if (addToCartBtn) {
        addToCartBtn.setAttribute('data-price', finalPrice);
    }
}

/**
 * Configura los event listeners para los botones de productos
 */
function setupProductButtonListeners() {
    // Usar event delegation para los botones de productos
    document.addEventListener('click', function(e) {
        const button = e.target.closest('.product-btn');
        if (button) {
            e.preventDefault();
            const action = button.getAttribute('data-action');

            if (action === 'view') {
                const productId = button.getAttribute('data-product-id');
                if (productId) {
                    window.location.href = `/ecomerce/productos/${productId}`;
                }
            } else if (action === 'add-to-cart') {
                handleAddToCart(button);
            }
            return;
        }
        
        // Manejar clics en botones de wishlist
        const wishlistBtn = e.target.closest('.wishlist-btn');
        if (wishlistBtn) {
            e.preventDefault();
            e.stopPropagation();
            const productId = wishlistBtn.getAttribute('data-product-id');
            if (productId) {
                toggleWishlist(productId, wishlistBtn);
            }
        }
    });
}

/**
 * Maneja agregar producto al carrito
 */
function handleAddToCart(button) {
    const productId = button.getAttribute('data-product-id');
    const price = parseFloat(button.getAttribute('data-price')) || 0;
    const hasVariants = button.getAttribute('data-has-variants') === 'true';
    const productCard = button.closest('.product-card');

    let variantData = null;

    if (hasVariants && productCard) {
        // Recopilar variantes seleccionadas (opcional)
        const selectedVariants = productCard.querySelectorAll('.variant-btn.selected');
        
        if (selectedVariants.length > 0) {
            variantData = {};
            selectedVariants.forEach(btn => {
                const type = btn.getAttribute('data-variant-type');
                const value = btn.getAttribute('data-value');
                variantData[type] = value;
            });
        }
        
        // Las variantes son opcionales - no requerir que todas estén seleccionadas
        // El usuario puede agregar el producto base sin seleccionar variantes
    }

    // Llamar a la función global addToCart
    if (window.addToCart) {
        console.log('🛒 Agregando producto al carrito:', { productId, quantity: 1, price, variantData });
        window.addToCart(productId, 1, price, variantData).then(success => {
            if (success) {
                console.log('✅ Producto agregado exitosamente');
                // El mensaje de éxito ya se muestra en window.addToCart
            } else {
                console.error('❌ Error al agregar producto');
                showToast('Error al agregar producto al carrito.', 'error');
            }
        }).catch(error => {
            console.error('❌ Error al agregar producto:', error);
            showToast('Error al agregar producto al carrito.', 'error');
        });
    } else {
        console.error('❌ Función addToCart no disponible');
        showToast('Error: Sistema de carrito no disponible.', 'error');
    }
}

// Inicializar event listeners para botones de productos al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    setupProductButtonListeners();
    
    // Cargar contador de wishlist inicial
    updateWishlistCount();
});
