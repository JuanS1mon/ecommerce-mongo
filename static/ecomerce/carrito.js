/**
 * Clase Cart - Programación Orientada a Objetos para manejar el carrito de compras
 */
class Cart {
    constructor() {
        this.currentCart = null;
        this.cartItems = [];
        this.userId = null;
        this.isLoading = false;
        this.isInitialized = false; // Bandera para evitar inicializaciones múltiples
        this.localCartKey = 'ecommerce_local_cart'; // Clave para localStorage

        // Elementos DOM
        this.elements = {
            sidebar: null,
            overlay: null,
            cartItems: null,
            emptyCart: null,
            cartFooter: null,
            cartTotal: null,
            cartCount: null
        };

        // No llamar a init() automáticamente - se hará manualmente desde el HTML
        // this.init();
    }

    /**
     * Inicializa la clase Cart
     */
    init() {
        console.log('🛒 Iniciando Cart...');
        
        // No cachear elementos DOM aquí - esperar a que estén disponibles
        this.bindEvents();

        // Cargar carrito local si existe (para usuarios no autenticados)
        this.loadLocalCart();

        // No inicializar carrito automáticamente aquí
        // Se hará después de cachear los elementos DOM
        console.log('✅ Cart inicializado (esperando DOM)');
    }

    /**
     * Cachea los elementos del DOM para mejor rendimiento
     */
    cacheDOMElements() {
        this.elements.sidebar = document.getElementById('cart-sidebar');
        this.elements.overlay = document.getElementById('cart-overlay');
        this.elements.cartItems = document.getElementById('cart-items');
        this.elements.emptyCart = document.getElementById('empty-cart');
        this.elements.cartFooter = document.getElementById('cart-footer');
        this.elements.cartTotal = document.getElementById('cart-total');
        this.elements.cartCount = document.getElementById('cart-count');
        
        console.log('✅ Elementos DOM cacheados:', {
            sidebar: !!this.elements.sidebar,
            overlay: !!this.elements.overlay,
            cartItems: !!this.elements.cartItems,
            emptyCart: !!this.elements.emptyCart,
            cartFooter: !!this.elements.cartFooter,
            cartTotal: !!this.elements.cartTotal,
            cartCount: !!this.elements.cartCount
        });
    }

    /**
     * Vincula los eventos necesarios
     */
    bindEvents() {
        // No inicializar automáticamente - esperar a que se complete la autenticación
        // La inicialización se hará desde el script inline de la página
    }

    /**
     * Inicializa la clase Cart manualmente (llamado desde el HTML después de la autenticación)
     */
    manualInit() {
        this.init();
    }

    /**
     * Inicializa el carrito manualmente (llamado desde el script inline o automáticamente)
     */
    initCart() {
        if (this.isInitialized) {
            console.log('Carrito ya inicializado, omitiendo initCart()');
            return;
        }
        this.isInitialized = true;

        console.log('🛒 Inicializando carrito...');

        // Cachear elementos DOM ahora que deberían estar disponibles
        this.cacheDOMElements();

        // Inicializar contador en 0 después de cachear elementos DOM
        this.updateGlobalCartCount(0);

        console.log('Elementos DOM cacheados:', {
            sidebar: !!this.elements.sidebar,
            overlay: !!this.elements.overlay,
            cartItems: !!this.elements.cartItems
        });

        // Solo intentar cargar usuario y carrito si hay token disponible
        const token = this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token');
        if (token) {
            console.log('Usuario tiene token, cargando carrito del servidor');
            // Usuario podría estar autenticado, intentar cargar carrito
            this.loadUserAndCart().catch(error => {
                console.warn('Error inicializando carrito:', error);
                this.renderEmptyCart();
            });
        } else {
            console.log('Usuario no autenticado - cargando carrito local');
            // Usuario no autenticado - cargar carrito local
            this.renderLocalCart();
        }
    }

    /**
     * Carga el carrito y el carrito al inicializar
     */
    async loadUserAndCart() {
        if (this.isInitialized && this.userId) {
            // Si ya está inicializado y tenemos userId, no recargar
            return;
        }

        try {
            const currentUserId = await this.getCurrentUserId();
            if (currentUserId) {
                this.userId = currentUserId;
                // Usuario autenticado - cargar carrito del servidor
                await this.loadCart();
            } else {
                // Usuario no autenticado - mostrar carrito local
                console.log('Usuario no autenticado, mostrando carrito local');
                this.renderLocalCart();
            }
        } catch (error) {
            console.error('Error loading user and cart:', error);
            // En caso de error, mostrar carrito vacío
            this.renderEmptyCart();
        }

        // Asegurar que el contador se actualice después de cargar
        setTimeout(() => {
            this.updateGlobalCartCount(this.getItemCount());
        }, 100);
    }

    /**
     * Alterna la visibilidad del carrito
     */
    toggle() {
        console.log('🛒 Toggle del carrito llamado');

        // Asegurar que los elementos DOM estén cacheados
        if (!this.elements.sidebar || !this.elements.overlay) {
            console.log('Elementos no cacheados, intentando cachearlos...');
            this.cacheDOMElements();
        }

        if (!this.elements.sidebar || !this.elements.overlay) {
            console.error('❌ Cart elements not found after caching attempt');
            console.log('Elementos disponibles:', {
                sidebar: this.elements.sidebar,
                overlay: this.elements.overlay
            });
            return;
        }

        const isOpen = !this.elements.sidebar.classList.contains('translate-x-full');
        console.log(`Carrito está ${isOpen ? 'abierto' : 'cerrado'}`);

        if (isOpen) {
            console.log('Cerrando carrito');
            // Cerrar carrito
            this.elements.sidebar.classList.add('translate-x-full');
            this.elements.overlay.classList.add('hidden');
        } else {
            console.log('Abriendo carrito');
            // Abrir carrito - siempre recargar para asegurar datos actualizados
            this.elements.sidebar.classList.remove('translate-x-full');
            this.elements.overlay.classList.remove('hidden');

            // Forzar recarga cuando se abre el carrito para asegurar datos actualizados
            this.loadCart(true);
        }
    }

    /**
     * Carga el carrito del usuario
     */
    async loadCart(forceReload = false) {
        if (this.isLoading) return;

        // Si ya tenemos datos del carrito y no ha pasado mucho tiempo, evitar recarga
        // Pero permitir recarga forzada (útil después de agregar productos)
        if (!forceReload && this.currentCart && this.cartItems.length >= 0) {
            // Opcional: podríamos agregar un timestamp para recargar después de cierto tiempo
            // console.log('Carrito ya cargado, usando datos en caché');
            return;
        }

        // Si no hay usuario autenticado, cargar carrito local
        if (!this.userId) {
            console.log('No hay usuario autenticado, cargando carrito local');
            this.renderLocalCart();
            return;
        }

        try {
            this.isLoading = true;
            console.log(`Cargando carrito para usuario ${this.userId}...`);

            // Obtener carrito activo
            const token = this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token');
            const cartResponse = await fetch(`/ecomerce/carritos/activo`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                }
            });

            console.log(`Respuesta del carrito: ${cartResponse.status}`);

            if (cartResponse.ok) {
                this.currentCart = await cartResponse.json();
                console.log(`✅ Carrito activo cargado: ID ${this.currentCart.id} para usuario ${this.userId}`);

                // Obtener items del carrito
                const itemsResponse = await fetch(`/ecomerce/carrito_items/carrito/${this.currentCart.id}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Accept': 'application/json'
                    }
                });

                console.log(`Respuesta de items del carrito: ${itemsResponse.status}`);

                if (itemsResponse.ok) {
                    this.cartItems = await itemsResponse.json();
                    console.log(`✅ Items del carrito cargados: ${this.cartItems.length} items en carrito ${this.currentCart.id}`);

                    // Cargar información completa de los productos
                    await this.loadProductDetails();

                    this.render();
                } else {
                    const errorText = await itemsResponse.text();
                    console.error('❌ Error cargando items del carrito:', errorText);
                    throw new Error('Error al cargar los items del carrito');
                }
            } else if (cartResponse.status === 404) {
                // No hay carrito activo, crear uno nuevo
                console.log('No hay carrito activo, creando uno nuevo...');
                this.currentCart = null;
                this.cartItems = [];
                this.renderEmptyCart();
            } else if (cartResponse.status === 401) {
                // No autenticado, usar carrito local
                console.log('Usuario no autenticado (401), cargando carrito local');
                this.renderLocalCart();
                return;
            } else {
                const errorText = await cartResponse.text();
                console.error('❌ Error cargando carrito:', cartResponse.status, errorText);
                throw new Error('Error al cargar el carrito');
            }
        } catch (error) {
            console.error('❌ Error en loadCart:', error);
            // Si hay error de autenticación (401), cargar carrito local
            if (error.message.includes('401') || error.message.includes('Not authenticated')) {
                console.log('Error de autenticación detectado, cargando carrito local como fallback');
                this.renderLocalCart();
            } else {
                this.renderEmptyCart();
            }
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Renderiza el carrito completo
     */
    render() {
        console.log(`🎨 Renderizando carrito con ${this.cartItems.length} items`);

        // Verificar que al menos cartItems y emptyCart existan (mínimo requerido)
        if (!this.elements.cartItems || !this.elements.emptyCart) {
            console.warn('⚠️ Elementos esenciales del DOM del carrito no están disponibles, intentando cachearlos nuevamente');
            this.cacheDOMElements();

            // Si aún no existen los elementos esenciales, salir
            if (!this.elements.cartItems || !this.elements.emptyCart) {
                console.error('❌ No se pueden renderizar los elementos del carrito - DOM esencial no disponible');
                return;
            }
        }

        if (this.cartItems.length === 0) {
            // console.log('Carrito vacío, renderizando estado vacío');
            this.renderEmptyCart();
            return;
        }

        // Mostrar items del carrito y ocultar mensaje de vacío
        if (this.elements.emptyCart) {
            this.elements.emptyCart.style.display = 'none';
            this.elements.emptyCart.classList.add('hidden');
        }
        if (this.elements.cartItems) {
            this.elements.cartItems.style.display = 'block';
        }
        if (this.elements.cartFooter) {
            this.elements.cartFooter.style.display = 'block';
            this.elements.cartFooter.classList.remove('hidden');
        }

        let total = 0;
        let itemCount = 0;

        this.elements.cartItems.innerHTML = this.cartItems.map(item => {
            // Usar las propiedades correctas según el formato del item
            const quantity = item.cantidad || item.quantity || 1;
            const price = item.precio_unitario || item.price || 0;
            const itemTotal = quantity * price;
            total += itemTotal;
            itemCount += quantity;

            // Construir información de variante - mostrar todos los campos dinámicamente
            let variantDisplay = '';
            if (item.variant_info && typeof item.variant_info === 'object') {
                const variantParts = [];
                
                // Mapeo de nombres de campos a etiquetas legibles
                const fieldLabels = {
                    'color': 'Color',
                    'tipo': 'Tipo',
                    'talla': 'Talla',
                    'modelo': 'Modelo',
                    'tamaño': 'Tamaño',
                    'material': 'Material'
                };
                
                // Iterar sobre todos los campos de variant_info
                for (const [key, value] of Object.entries(item.variant_info)) {
                    // Ignorar campos internos o vacíos
                    if (value && key !== 'precio_adicional' && key !== 'stock' && key !== 'id') {
                        const label = fieldLabels[key] || key.charAt(0).toUpperCase() + key.slice(1);
                        variantParts.push(`${label}: ${value}`);
                    }
                }
                
                if (variantParts.length > 0) {
                    variantDisplay = `<p class="text-xs text-blue-600 font-semibold bg-blue-50 px-2 py-1 rounded-md inline-block mt-1">🎨 ${variantParts.join(' • ')}</p>`;
                }
            }

            // Usar imagen normal pero optimizada para el carrito (tamaño pequeño)
            const cartImage = item.product_image || '/static/img/logo.png';
            const productName = item.product_name || `Producto ${item.id_producto || item.product_id}`;
            const productCode = item.product_codigo || '';

            return `
                <div class="flex items-center space-x-4 bg-white p-4 rounded-lg shadow-sm mb-4" data-item-id="${item.id}">
                    <img src="${cartImage}" alt="${productName}" class="w-12 h-12 object-cover rounded" onerror="this.src='/static/img/logo.png'">
                    <div class="flex-1">
                        <h3 class="font-semibold text-gray-800 text-sm">${productName}</h3>
                        ${variantDisplay}
                        <p class="text-xs text-gray-500">${productCode}</p>
                        <p class="text-sm text-gray-600">Precio: $${this.formatPrice(price)}</p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button class="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded text-sm cart-btn" data-action="decrease" data-item-id="${item.id}">
                            <i class="fas fa-minus"></i>
                        </button>
                        <span class="font-semibold text-sm quantity-display" data-item-id="${item.id}">${quantity}</span>
                        <button class="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded text-sm cart-btn" data-action="increase" data-item-id="${item.id}">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <div class="text-right">
                        <p class="font-semibold text-sm">$${this.formatPrice(itemTotal)}</p>
                        <button class="text-red-500 hover:text-red-700 text-sm cart-btn" data-action="remove" data-item-id="${item.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Actualizar totales en sidebar (si existen)
        if (this.elements.cartTotal) {
            this.elements.cartTotal.textContent = `$${this.formatPrice(total)}`;
        }
        if (this.elements.cartCount) {
            this.elements.cartCount.textContent = itemCount;
        }

        // Actualizar totales en página de carrito completo (si existen)
        const cartSummary = document.getElementById('cart-summary');
        const totalElement = document.getElementById('total');
        const subtotalElement = document.getElementById('subtotal');
        
        if (cartSummary && this.cartItems.length > 0) {
            cartSummary.classList.remove('hidden');
            if (totalElement) totalElement.textContent = `$${this.formatPrice(total)}`;
            if (subtotalElement) subtotalElement.textContent = `$${this.formatPrice(total)}`;
        }

        // Actualizar también el contador global del carrito
        this.updateGlobalCartCount(itemCount);

        // Configurar event listeners para los botones del carrito
        this.setupCartButtonListeners();

        // console.log(`Carrito renderizado: ${itemCount} items, total $${total}`);
    }

    /**
     * Configura los event listeners para los botones del carrito
     */
    setupCartButtonListeners() {
        if (!this.elements.cartItems) return;

        // Remover event listeners anteriores para evitar duplicados
        const existingButtons = this.elements.cartItems.querySelectorAll('.cart-btn');
        existingButtons.forEach(button => {
            button.removeEventListener('click', this.handleCartButtonClick);
        });

        // Agregar event listeners a los nuevos botones
        const cartButtons = this.elements.cartItems.querySelectorAll('.cart-btn');
        cartButtons.forEach(button => {
            button.addEventListener('click', (e) => this.handleCartButtonClick(e));
        });
        console.log(`✅ Configurados ${cartButtons.length} event listeners para botones del carrito`);
    }

    /**
     * Maneja los clicks en los botones del carrito
     */
    handleCartButtonClick(event) {
        console.log('🎯 handleCartButtonClick llamado');
        event.preventDefault();
        event.stopPropagation();

        const button = event.currentTarget;
        const action = button.getAttribute('data-action');
        const itemId = button.getAttribute('data-item-id');

        console.log(`🎯 Botón clickeado: action=${action}, itemId=${itemId}`);

        if (!itemId) {
            console.error('❌ No se encontró itemId en el botón');
            return;
        }

        switch (action) {
            case 'increase':
                const currentQtyElement = this.elements.cartItems.querySelector(`.quantity-display[data-item-id="${itemId}"]`);
                if (currentQtyElement) {
                    const currentQty = parseInt(currentQtyElement.textContent) || 0;
                    console.log(`🔼 Aumentando cantidad de ${currentQty} a ${currentQty + 1}`);
                    this.updateQuantity(itemId, currentQty + 1);
                }
                break;

            case 'decrease':
                const decreaseQtyElement = this.elements.cartItems.querySelector(`.quantity-display[data-item-id="${itemId}"]`);
                if (decreaseQtyElement) {
                    const currentQty = parseInt(decreaseQtyElement.textContent) || 0;
                    console.log(`🔽 Disminuyendo cantidad de ${currentQty} a ${currentQty - 1}`);
                    this.updateQuantity(itemId, currentQty - 1);
                }
                break;

            case 'remove':
                console.log(`🗑️ Eliminando item ${itemId}`);
                this.removeItem(itemId);
                break;

            default:
                console.warn(`⚠️ Acción desconocida: ${action}`);
        }
    }

    /**
     * Renderiza el carrito vacío
     */
    renderEmptyCart() {
        console.log('📭 Renderizando carrito vacío');

        // Solo verificar elementos esenciales
        if (!this.elements.emptyCart) {
            console.warn('⚠️ Elementos del DOM para carrito vacío no disponibles, intentando cachearlos nuevamente');
            this.cacheDOMElements();

            if (!this.elements.emptyCart) {
                console.error('❌ No se puede renderizar carrito vacío - DOM no disponible');
                return;
            }
        }

        // Mostrar mensaje de carrito vacío
        if (this.elements.emptyCart) {
            this.elements.emptyCart.style.display = 'flex';
            this.elements.emptyCart.classList.remove('hidden');
        }
        
        // Ocultar footer del sidebar si existe
        if (this.elements.cartFooter) {
            this.elements.cartFooter.style.display = 'none';
            this.elements.cartFooter.classList.add('hidden');
        }
        
        // Ocultar cart-summary de la página completa si existe
        const cartSummary = document.getElementById('cart-summary');
        if (cartSummary) {
            cartSummary.classList.add('hidden');
        }
        
        if (this.elements.cartCount) {
            this.elements.cartCount.textContent = '0';
        }

        // Limpiar el contenido de items del carrito
        if (this.elements.cartItems) {
            this.elements.cartItems.innerHTML = '';
            this.elements.cartItems.style.display = 'none';
        }

        this.updateGlobalCartCount(0);
        console.log('✅ Carrito vacío renderizado correctamente');
    }

    /**
     * Agrega un producto al carrito
     */
    async addProduct(productId, quantity = 1, price = 0, variantData = null) {
        // Verificar si hay token disponible
        const token = this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token');

        if (!token) {
            // Usuario no autenticado - usar carrito local
            console.log('Usuario no autenticado, agregando al carrito local');
            const success = this.addToLocalCart(productId, quantity, price, variantData);
            if (success) {
                // Renderizar carrito local
                this.renderLocalCart();
                // Mostrar mensaje de éxito
            }
            return success;
        }

        try {
            if (!this.userId) {
                this.userId = await this.getCurrentUserId();
                if (!this.userId) {
                    // Si aún no hay userId después de intentar obtenerlo, usar carrito local como fallback
                    console.warn('No se pudo obtener userId, usando carrito local como fallback');
                    const success = this.addToLocalCart(productId, quantity, price, variantData);
                    if (success) {
                        this.renderLocalCart();
                    }
                    return success;
                }
            }

            // Usar la ruta simple que crea carrito automáticamente si no existe
            const response = await fetch(`/ecomerce/carrito_items/simple`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity,
                    price: price,
                    variant_data: variantData
                })
            });

            if (response.ok) {
                const result = await response.json();

                // Recargar el carrito para mantener la sincronización y actualizar el contador
                await this.loadCart(true);

                // Mostrar mensaje de éxito

                return true;
            } else if (response.status === 401) {
                // Token inválido, limpiar y usar carrito local como fallback
                sessionStorage.removeItem('ecommerce_token');
                sessionStorage.removeItem('ecommerce_user_id');
                this.deleteCookie('ecommerce_token');

                console.log('Token inválido, usando carrito local como fallback');
                const success = this.addToLocalCart(productId, quantity, price, variantData);
                if (success) {
                    this.renderLocalCart();
                }
                return success;
            } else {
                const error = await response.json();
                console.error('Error agregando producto al carrito:', error);
                return false;
            }
        } catch (error) {
            console.error('Error de conexión:', error);
            // En caso de error de red, usar carrito local como fallback
            console.log('Error de conexión, usando carrito local como fallback');
            const success = this.addToLocalCart(productId, quantity, price, variantData);
            if (success) {
                this.renderLocalCart();
            }
            return success;
        }
    }

    /**
     * Agrega un producto al carrito local (localStorage)
     */
    addToLocalCart(productId, quantity = 1, price = 0, variantData = null) {
        try {
            // Cargar carrito local actual
            let localCart = this.loadLocalCart();

            // Buscar si el producto ya existe
            const existingItem = localCart.find(item =>
                item.product_id === productId &&
                JSON.stringify(item.variant_data) === JSON.stringify(variantData)
            );

            if (existingItem) {
                // Incrementar cantidad si ya existe
                existingItem.quantity += quantity;
            } else {
                // Agregar nuevo item
                localCart.push({
                    product_id: productId,
                    quantity: quantity,
                    price: price,
                    variant_data: variantData,
                    added_at: new Date().toISOString()
                });
            }

            // Guardar carrito local
            this.saveLocalCart(localCart);

            // Actualizar contador global
            const totalQuantity = localCart.reduce((sum, item) => sum + item.quantity, 0);
            this.updateGlobalCartCount(totalQuantity);

            return true;
        } catch (error) {
            console.error('Error agregando al carrito local:', error);
            return false;
        }
    }

    /**
     * Actualiza la cantidad de un item del carrito
     */
    async updateQuantity(itemId, newQuantity) {
        console.log(`🔄 Cart.updateQuantity llamada: itemId=${itemId}, newQuantity=${newQuantity}`);
        if (this.isLoading) {
            console.log('⏳ Carrito está cargando, ignorando updateQuantity');
            return;
        }

        try {
            if (newQuantity <= 0) {
                await this.removeItem(itemId);
                return;
            }

            // Verificar si es un item local
            if (itemId.toString().startsWith('local_')) {
                this.updateLocalQuantity(itemId, newQuantity);
                return;
            }

            this.isLoading = true;
            console.log(`Actualizando cantidad del item ${itemId} a ${newQuantity}`);

            const token = this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token');
            const response = await fetch(`/ecomerce/carrito_items/id/${itemId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    cantidad: newQuantity
                })
            });

            if (response.ok) {
                const updatedItem = await response.json();
                console.log(`✅ Item ${itemId} actualizado a cantidad ${newQuantity}`);

                // Actualizar el item en la lista local
                const itemIndex = this.cartItems.findIndex(item => item.id === itemId);
                if (itemIndex !== -1) {
                    this.cartItems[itemIndex].cantidad = newQuantity;
                    this.render();
                }

                // Mostrar mensaje de éxito
                console.log('Cantidad actualizada exitosamente');
            } else if (response.status === 401) {
                // Token inválido, usar carrito local como fallback
                sessionStorage.removeItem('ecommerce_token');
                sessionStorage.removeItem('ecommerce_user_id');
                this.deleteCookie('ecommerce_token');

                console.log('Token inválido en updateQuantity, usando carrito local como fallback');
                // Si no hay carrito local renderizado, inicializarlo
                if (this.cartItems.length === 0 || !this.cartItems.some(item => item.id.toString().startsWith('local_'))) {
                    console.log('Inicializando carrito local para fallback');
                    this.renderLocalCart();
                    // Pequeño delay para asegurar que se renderice
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                const success = this.updateLocalQuantity(itemId, newQuantity);
                if (success) {
                    this.renderLocalCart();
                }
                return success;
            } else {
                const errorText = await response.text();
                console.error('❌ Error actualizando cantidad:', response.status, errorText);
                throw new Error('Error al actualizar la cantidad');
            }
        } catch (error) {
            console.error('❌ Error en updateQuantity:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Remueve un item del carrito
     */
    async removeItem(itemId) {
        console.log(`🗑️ Cart.removeItem llamada: itemId=${itemId}`);
        // Verificar si es un item local
        if (itemId.toString().startsWith('local_')) {
            this.removeLocalItem(itemId);
            return;
        }

        try {
            // console.log(`Intentando eliminar item ${itemId}`);

            const response = await fetch(`/ecomerce/carrito_items/id/${itemId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token')}`,
                    'Accept': 'application/json'
                }
            });

            if (response.ok) {
                // console.log(`Item ${itemId} eliminado exitosamente del backend`);

                // Remover el item de la lista local inmediatamente
                const itemIndex = this.cartItems.findIndex(item => item.id === itemId);
                if (itemIndex !== -1) {
                    this.cartItems.splice(itemIndex, 1);
                    // console.log(`Item ${itemId} removido de la lista local`);
                }

                // Re-renderizar el carrito con los items actualizados
                this.render();

                // Mensaje removido para experiencia más dinámica
                // console.log('Carrito re-renderizado después de eliminar item');
            } else if (response.status === 401) {
                // Token inválido, usar carrito local como fallback
                sessionStorage.removeItem('ecommerce_token');
                sessionStorage.removeItem('ecommerce_user_id');
                this.deleteCookie('ecommerce_token');

                console.log('Token inválido en removeItem, usando carrito local como fallback');
                // Si no hay carrito local renderizado, inicializarlo
                if (this.cartItems.length === 0 || !this.cartItems.some(item => item.id.toString().startsWith('local_'))) {
                    console.log('Inicializando carrito local para fallback');
                    this.renderLocalCart();
                    // Pequeño delay para asegurar que se renderice
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                const success = this.removeLocalItem(itemId);
                if (success) {
                    this.renderLocalCart();
                }
                return success;
            } else {
                // console.error(`Error en respuesta del servidor: ${response.status}`);
                throw new Error('Error al remover producto');
            }
        } catch (error) {
            console.error('Error removing item:', error);
        }
    }

    /**
     * Actualiza la cantidad de un item local del carrito
     */
    updateLocalQuantity(itemId, newQuantity) {
        try {
            // Cargar carrito local
            let localCart = this.loadLocalCart();

            // Encontrar el item por ID temporal
            const itemIndex = this.cartItems.findIndex(item => item.id === itemId);
            if (itemIndex !== -1) {
                const productId = this.cartItems[itemIndex].id_producto;

                // Encontrar en localCart
                const localItemIndex = localCart.findIndex(item => item.product_id === productId);
                if (localItemIndex !== -1) {
                    if (newQuantity <= 0) {
                        // Remover si cantidad es 0 o menor
                        localCart.splice(localItemIndex, 1);
                        this.cartItems.splice(itemIndex, 1);
                    } else {
                        // Actualizar cantidad
                        localCart[localItemIndex].quantity = newQuantity;
                        this.cartItems[itemIndex].cantidad = newQuantity;
                    }

                    this.saveLocalCart(localCart);
                    this.render();
                }
            }
        } catch (error) {
            console.error('Error actualizando cantidad local:', error);
        }
    }

    /**
     * Remueve un item local del carrito
     */
    removeLocalItem(itemId) {
        try {
            // Cargar carrito local
            let localCart = this.loadLocalCart();

            // Encontrar el item por ID temporal
            const itemIndex = this.cartItems.findIndex(item => item.id === itemId);
            if (itemIndex !== -1) {
                const productId = this.cartItems[itemIndex].id_producto;

                // Remover de localCart
                const localItemIndex = localCart.findIndex(item => item.product_id === productId);
                if (localItemIndex !== -1) {
                    localCart.splice(localItemIndex, 1);
                    this.saveLocalCart(localCart);

                    // Remover de cartItems
                    this.cartItems.splice(itemIndex, 1);
                    this.render();
                }
            }
        } catch (error) {
            console.error('Error removiendo item local:', error);
        }
    }

    /**
     * Obtiene el ID del usuario actual
     */
    async getCurrentUserId() {
        // Primero intentar obtener del sessionStorage (cache)
        const storedUserId = sessionStorage.getItem('ecommerce_user_id');
        if (storedUserId) {
            return parseInt(storedUserId);
        }

        // Si no está en sessionStorage, hacer petición al backend para obtener usuario actual
        const token = this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token');

        if (!token) {
            // console.log('No hay token disponible - usuario no autenticado');
            return null;
        }

        try {
            // Intentar usar el endpoint /verify primero (más eficiente)
            const verifyResponse = await fetch('/ecomerce/auth/verify', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (verifyResponse.ok) {
                const verifyData = await verifyResponse.json();
                if (verifyData.valid && verifyData.user && verifyData.user.id) {
                    // Guardar el userId en sessionStorage y cookies para futuras peticiones
                    sessionStorage.setItem('ecommerce_user_id', verifyData.user.id.toString());
                    // También guardar en cookies para consistencia cross-tab
                    document.cookie = `ecommerce_user_id=${verifyData.user.id}; path=/; max-age=86400`; // 24 horas
                    return verifyData.user.id;
                }
            }

            // Si /verify falla, intentar con /me como fallback
            const response = await fetch('/ecomerce/auth/me', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (response.ok) {
                const userData = await response.json();

                // Guardar el userId en sessionStorage y cookies para futuras peticiones
                if (userData.id) {
                    sessionStorage.setItem('ecommerce_user_id', userData.id.toString());
                    // También guardar en cookies para consistencia cross-tab
                    document.cookie = `ecommerce_user_id=${userData.id}; path=/; max-age=86400`; // 24 horas
                    return userData.id;
                } else {
                    console.error('Respuesta de /ecomerce/auth/me no contiene campo "id"');
                    return null;
                }
            } else if (response.status === 401) {
                console.warn('Token ecommerce inválido o expirado');
                // Limpiar token inválido de ambos storage
                sessionStorage.removeItem('ecommerce_token');
                sessionStorage.removeItem('ecommerce_user_id');
                this.deleteCookie('ecommerce_token');
                this.deleteCookie('ecommerce_user_id');
                return null;
            } else {
                console.error(`Error en petición a /ecomerce/auth/me: ${response.status}`);
                return null;
            }

        } catch (error) {
            console.error('Error obteniendo usuario ecommerce actual:', error);
            // En caso de error de red, limpiar tokens dudosos
            sessionStorage.removeItem('ecommerce_token');
            sessionStorage.removeItem('ecommerce_user_id');
            this.deleteCookie('ecommerce_token');
            this.deleteCookie('ecommerce_user_id');
            return null;
        }
    }

    /**
     * Actualiza el contador global del carrito
     */
    updateGlobalCartCount(count) {
        // Asegurar que count sea un número válido
        const validCount = parseInt(count) || 0;

        // Función helper para actualizar un elemento específico
        const updateElement = (element) => {
            if (element) {
                element.textContent = validCount.toString();
                // Agregar clase para animación si hay items
                if (validCount > 0) {
                    element.classList.add('animate-pulse');
                } else {
                    element.classList.remove('animate-pulse');
                }
            }
        };

        // Buscar el contador de la navbar (prioridad alta)
        const navbarCartCount = document.getElementById('cart-count');
        updateElement(navbarCartCount);

        // También actualizar el contador del sidebar si existe y es diferente
        if (this.elements.cartCount && this.elements.cartCount !== navbarCartCount) {
            updateElement(this.elements.cartCount);
        }

        // Log para debug (solo en desarrollo)
        // console.log(`Contador del carrito actualizado a: ${validCount}`);
    }

    /**
     * Formatea un precio con decimales
     */
    formatPrice(price) {
        // Formatear precio con separadores de miles y decimales
        return new Intl.NumberFormat('es-ES', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(price);
    }

    /**
     * Carga la información completa de los productos en el carrito
     */
    async loadProductDetails() {
        if (!this.cartItems || this.cartItems.length === 0) return;

        try {
            // Obtener información de todos los productos en paralelo
            const productPromises = this.cartItems.map(async (item) => {
                try {
                    console.log('🔍 Loading product details for item:', item);
                    const productId = item.product_id || item.id_producto;
                    console.log('🔍 product_id value:', productId);

                    if (!productId || productId === 'undefined') {
                        console.error('❌ No valid product ID found for item:', item);
                        item.product_name = `Producto ${item.id || 'desconocido'}`;
                        item.product_image = '/static/img/logo.png';
                        item.product_codigo = '';
                        item.variant_info = null;
                        return;
                    }

                    const response = await fetch(`/ecomerce/api/productos/${productId}`);
                    if (response.ok) {
                        const product = await response.json();
                        // Agregar información del producto al item del carrito
                        item.product_name = product.nombre || `Producto ${productId}`;
                        item.product_image = product.imagen_url || '/static/img/logo.png';
                        item.product_codigo = product.codigo || '';

                        // Cargar información de variantes si existe
                        item.variant_info = null;
                        console.log('🔍 Procesando item:', {
                            itemId: item.id,
                            productId: productId,
                            variant_data: item.variant_data,
                            variant_data_type: typeof item.variant_data
                        });
                        
                        if (item.variant_data && typeof item.variant_data === 'object') {
                            console.log('✅ Asignando variant_info desde variant_data:', item.variant_data);
                            item.variant_info = item.variant_data;
                        } else if (product.variants && product.variants.length > 0) {
                            // Si no hay variant_data pero el producto tiene variantes,
                            // intentar encontrar la variante por defecto o la primera disponible
                            console.log('⚠️ No hay variant_data, usando variante por defecto del producto');
                            const defaultVariant = product.variants.find(v => v.stock > 0) || product.variants[0];
                            if (defaultVariant) {
                                item.variant_info = {
                                    color: defaultVariant.color,
                                    tipo: defaultVariant.tipo,
                                    precio_adicional: defaultVariant.precio_adicional || 0
                                };
                            }
                        } else {
                            console.log('ℹ️ Producto sin variantes');
                        }
                    } else {
                        // Si falla la carga del producto, usar valores por defecto
                        item.product_name = `Producto ${productId}`;
                        item.product_image = '/static/img/logo.png';
                        item.product_codigo = '';
                        item.variant_info = null;
                    }
                } catch (error) {
                    console.warn(`Error cargando producto ${productId}:`, error);
                    item.product_name = `Producto ${productId}`;
                    item.product_image = '/static/img/logo.png';
                    item.product_codigo = '';
                    item.variant_info = null;
                }
            });

            await Promise.all(productPromises);
        } catch (error) {
            console.error('Error cargando detalles de productos:', error);
        }
    }

    /**
     * Obtiene el número total de items
     */
    getItemCount() {
        return this.cartItems.reduce((count, item) => {
            const quantity = item.cantidad || item.quantity || 0;
            return count + quantity;
        }, 0);
    }

    /**
     * Obtiene el total del carrito
     */
    getTotal() {
        return this.cartItems.reduce((total, item) => {
            const quantity = item.cantidad || item.quantity || 0;
            const price = item.precio_unitario || item.price || 0;
            return total + (quantity * price);
        }, 0);
    }

    /**
     * Verifica si el carrito está vacío
     */
    isEmpty() {
        return this.cartItems.length === 0;
    }

    /**
     * Sincroniza el carrito con el servidor (útil para asegurar consistencia)
     */
    async syncWithServer() {
        try {
            // console.log('Sincronizando carrito con servidor...');
            await this.loadCart();
        } catch (error) {
            console.error('Error sincronizando con servidor:', error);
        }
    }

    /**
     * Debug detallado: muestra información completa del carrito
     */
    debugDetailed() {
        console.log('=== 🛒 DETALLES COMPLETOS DEL CARRITO ===');
        console.log(`👤 User ID: ${this.userId}`);
        console.log(`🛒 Current Cart ID: ${this.currentCart ? this.currentCart.id : 'Ninguno'}`);

        if (this.currentCart) {
            console.log(`� Cart Details:`, {
                id: this.currentCart.id,
                user_id: this.currentCart.id_usuario,
                estado: this.currentCart.estado,
                created_at: this.currentCart.created_at
            });
        }

        console.log(`� Cart Items (${this.cartItems.length}):`);
        this.cartItems.forEach((item, index) => {
            console.log(`  ${index + 1}. Producto ID: ${item.id_producto}, Cantidad: ${item.cantidad}, Precio: $${this.formatPrice(item.precio_unitario)}, Subtotal: $${this.formatPrice(item.cantidad * item.precio_unitario)}`);
        });

        console.log(`💰 Total: $${this.formatPrice(this.getTotal())}`);
        console.log(`🔢 Item Count: ${this.getItemCount()}`);
        console.log(`📭 Is Empty: ${this.isEmpty()}`);
        console.log(`🔄 Is Loading: ${this.isLoading}`);
        console.log(`✅ Is Initialized: ${this.isInitialized}`);

        console.log(`🌐 DOM Elements:`, {
            sidebar: !!this.elements.sidebar,
            overlay: !!this.elements.overlay,
            cartItems: !!this.elements.cartItems,
            emptyCart: !!this.elements.emptyCart,
            cartFooter: !!this.elements.cartFooter,
            cartTotal: !!this.elements.cartTotal,
            cartCount: !!this.elements.cartCount
        });
        console.log('=======================================');
    }

    /**
     * Obtiene el valor de una cookie por nombre
     */
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Elimina una cookie
     */
    deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }

    /**
     * Guarda el carrito local en localStorage
     */
    saveLocalCart(localCartItems) {
        try {
            const localCartData = {
                items: localCartItems,
                timestamp: Date.now()
            };
            localStorage.setItem(this.localCartKey, JSON.stringify(localCartData));
        } catch (error) {
            console.error('Error guardando carrito local:', error);
        }
    }

    /**
     * Carga el carrito local desde localStorage
     */
    loadLocalCart() {
        try {
            const localCartData = localStorage.getItem(this.localCartKey);
            if (localCartData) {
                const parsed = JSON.parse(localCartData);
                // Solo cargar si no es muy antiguo (24 horas)
                if (parsed.timestamp && (Date.now() - parsed.timestamp) < 24 * 60 * 60 * 1000) {
                    return parsed.items || [];
                } else {
                    // Carrito expirado, limpiar
                    localStorage.removeItem(this.localCartKey);
                    return [];
                }
            }
            return [];
        } catch (error) {
            console.error('Error cargando carrito local:', error);
            return [];
        }
    }

    /**
     * Renderiza el carrito local (para usuarios no autenticados)
     */
    renderLocalCart() {
        const localCart = this.loadLocalCart();
        console.log(`Renderizando carrito local con ${localCart.length} items`);

        if (localCart.length > 0) {
            // Convertir items locales al formato del carrito del servidor para renderizar
            this.cartItems = localCart.map(item => ({
                id: `local_${item.product_id}_${Date.now()}`, // ID temporal para local
                id_producto: item.product_id,
                cantidad: item.quantity,
                precio_unitario: item.price,
                variant_data: item.variant_data,
                variant_info: item.variant_data,
                product_name: `Producto ${item.product_id}`, // Placeholder, se cargará después
                product_image: '/static/img/logo.png',
                product_codigo: ''
            }));

            // Calcular total de items para actualizar contador
            const totalItems = localCart.reduce((sum, item) => sum + item.quantity, 0);
            console.log(`Total de items en carrito local: ${totalItems}`);
            this.updateGlobalCartCount(totalItems);

            // Cargar detalles de productos para mostrar nombres correctos
            this.loadProductDetails().then(() => {
                this.render();
            });
        } else {
            console.log('Carrito local vacío');
            this.cartItems = [];
            this.renderEmptyCart();
            this.updateGlobalCartCount(0);
        }
    }

    /**
     * Sincroniza el carrito local con el servidor cuando el usuario se autentica
     */
    async syncLocalCartWithServer() {
        try {
            console.log('🔄 Sincronizando carrito local con servidor...');

            // Cargar items del carrito local
            const localCart = this.loadLocalCart();
            if (localCart.length === 0) {
                console.log('No hay items en carrito local para sincronizar');
                return;
            }

            console.log(`Encontrados ${localCart.length} items en carrito local`);

            // Obtener token de autenticación
            const token = this.getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token');
            if (!token) {
                console.warn('No hay token disponible para sincronización');
                return;
            }

            // Obtener userId si no está disponible
            if (!this.userId) {
                this.userId = await this.getCurrentUserId();
                if (!this.userId) {
                    console.warn('No se pudo obtener userId para sincronización');
                    return;
                }
            }

            // Agregar cada item del carrito local al servidor
            let successCount = 0;
            let errorCount = 0;

            for (const localItem of localCart) {
                try {
                    console.log(`Agregando producto ${localItem.product_id} (cantidad: ${localItem.quantity}) al servidor...`);

                    const response = await fetch(`/ecomerce/carrito_items/simple`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`,
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({
                            product_id: localItem.product_id,
                            quantity: localItem.quantity,
                            price: localItem.price,
                            variant_data: localItem.variant_data
                        })
                    });

                    if (response.ok) {
                        successCount++;
                        console.log(`✅ Producto ${localItem.product_id} agregado exitosamente`);
                    } else {
                        const errorData = await response.json();
                        console.error(`❌ Error agregando producto ${localItem.product_id}:`, errorData);
                        errorCount++;
                    }
                } catch (error) {
                    console.error(`❌ Error de conexión agregando producto ${localItem.product_id}:`, error);
                    errorCount++;
                }
            }

            console.log(`Sincronización completada: ${successCount} exitosos, ${errorCount} errores`);

            // Limpiar carrito local después de sincronizar
            if (successCount > 0) {
                console.log('🧹 Limpiando carrito local después de sincronización exitosa');
                this.saveLocalCart([]);
                localStorage.removeItem(this.localCartKey);
            }

            // Recargar carrito del servidor para mostrar los items migrados
            await this.loadCart(true);

        } catch (error) {
            console.error('❌ Error en sincronización del carrito:', error);
        }
    }
}

// Crear instancia global del carrito
const cart = new Cart();
console.log('🛒 Instancia de Cart creada:', cart);

// Asegurar que el carrito se inicialice cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('🛒 DOM listo - iniciando Cart');
        cart.init();
        cart.initCart();
    });
} else {
    // DOM ya está listo
    console.log('🛒 DOM ya listo - iniciando Cart inmediatamente');
    cart.init();
    cart.initCart();
}

// ============================================================================
// FUNCIONES DE UTILIDADES PARA TOAST
// ============================================================================

/**
 * Muestra un mensaje toast de notificación
 */

// Funciones globales para compatibilidad con HTML
function toggleCart() {
    cart.toggle();
}

function addToCart(productId, quantity = 1, price = 0, variantData = null) {
    return cart.addProduct(productId, quantity, price, variantData);
}

function updateQuantity(itemId, newQuantity) {
    console.log(`🔄 updateQuantity GLOBAL llamada: itemId=${itemId}, newQuantity=${newQuantity}`);
    console.log('window.cart disponible:', !!window.cart);
    if (window.cart && typeof window.cart.updateQuantity === 'function') {
        console.log('✅ Llamando a cart.updateQuantity');
        return window.cart.updateQuantity(itemId, newQuantity);
    } else {
        console.error('❌ Instancia de cart no disponible en updateQuantity');
        console.log('window.cart:', window.cart);
        console.log('typeof window.cart:', typeof window.cart);
        if (window.cart) {
            console.log('Métodos de window.cart:', Object.getOwnPropertyNames(window.cart.__proto__));
        }
    }
}

function removeItem(itemId) {
    console.log(`🗑️ removeItem GLOBAL llamada: itemId=${itemId}`);
    console.log('window.cart disponible:', !!window.cart);
    if (window.cart && typeof window.cart.removeItem === 'function') {
        console.log('✅ Llamando a cart.removeItem');
        return window.cart.removeItem(itemId);
    } else {
        console.error('❌ Instancia de cart no disponible en removeItem');
        console.log('window.cart:', window.cart);
        console.log('typeof window.cart:', typeof window.cart);
        if (window.cart) {
            console.log('Métodos de window.cart:', Object.getOwnPropertyNames(window.cart.__proto__));
        }
    }
}

function reloadCart() {
    cart.loadCart(true);
}

function syncCartAfterLogin() {
    if (window.cart && typeof window.cart.syncLocalCartWithServer === 'function') {
        console.log('🔄 Sincronizando carrito después del login...');
        return window.cart.syncLocalCartWithServer();
    } else {
        console.warn('Función de sincronización de carrito no disponible');
        return Promise.resolve();
    }
}

function debugCart() {
    cart.debug();
}

function debugCartDetailed() {
    cart.debugDetailed();
}

// Alias para facilitar el debug desde consola
window.debugCart = debugCart;
window.cartDebug = () => cart.debug();
window.showCartDebug = () => cart.debug();
window.debugCartDetailed = debugCartDetailed;
window.cartDetails = () => cart.debugDetailed();

// Función helper para mostrar estado del carrito de forma simple
window.cartInfo = () => {
    console.log(`🛒 Carrito Usuario ${cart.userId}: ${cart.cartItems.length} items, Total: $${cart.formatPrice(cart.getTotal())}`);
    if (cart.currentCart) {
        console.log(`📋 Carrito ID: ${cart.currentCart.id}`);
    }
    return cart;
};

// Hacer la instancia global disponible
window.cart = cart;
console.log('🌐 Cart asignado a window.cart:', window.cart);

// Función para renderizar la página del carrito completo
window.renderCartPage = function() {
    console.log('📄 Rendering full cart page');
    console.log('📦 Current cart items:', cart.cartItems);
    console.log('📊 Cart items count:', cart.cartItems ? cart.cartItems.length : 0);
    
    // Usar IDs específicos de la página del carrito
    const pageCartItems = document.getElementById('cart-items-page') || document.getElementById('cart-items');
    const emptyCartPage = document.getElementById('empty-cart-page') || document.getElementById('empty-cart');
    const cartSummary = document.getElementById('cart-summary');
    const loading = document.getElementById('loading');

    // Ocultar loading
    if (loading) {
        loading.style.display = 'none';
        console.log('✅ Loading hidden');
    }

    if (!pageCartItems) {
        console.warn('⚠️ cart-items-page element not found on page');
        return;
    }

    if (!cart.cartItems || cart.cartItems.length === 0) {
        console.log('📭 Cart is empty, showing empty message');
        // Mostrar mensaje de carrito vacío
        if (emptyCartPage) {
            emptyCartPage.style.display = 'block';
            console.log('✅ Empty cart message shown');
        }
        if (pageCartItems) pageCartItems.style.display = 'none';
        if (cartSummary) cartSummary.classList.add('hidden');
        return;
    }

    console.log(`📦 Rendering ${cart.cartItems.length} cart items...`);

    // Ocultar mensaje vacío y mostrar items
    if (emptyCartPage) {
        emptyCartPage.style.display = 'none';
        emptyCartPage.classList.add('hidden');
    }
    if (pageCartItems) {
        pageCartItems.style.display = 'flex';
        pageCartItems.style.flexDirection = 'column';
        pageCartItems.classList.remove('hidden');
        console.log('✅ Cart items container visible');
    }

    let total = 0;
    let itemCount = 0;

    // Renderizar items del carrito
    pageCartItems.innerHTML = cart.cartItems.map(item => {
        const quantity = item.cantidad || item.quantity || 1;
        const price = item.precio_unitario || item.price || 0;
        const itemTotal = quantity * price;
        total += itemTotal;
        itemCount += quantity;

        // Información de variante
        let variantDisplay = '';
        if (item.variant_info && typeof item.variant_info === 'object') {
            const variantParts = [];
            const fieldLabels = {
                'color': 'Color', 'tipo': 'Tipo', 'talla': 'Talla',
                'modelo': 'Modelo', 'tamaño': 'Tamaño', 'material': 'Material'
            };
            
            for (const [key, value] of Object.entries(item.variant_info)) {
                if (value && key !== 'precio_adicional' && key !== 'stock' && key !== 'id') {
                    const label = fieldLabels[key] || key.charAt(0).toUpperCase() + key.slice(1);
                    variantParts.push(`${label}: ${value}`);
                }
            }
            
            if (variantParts.length > 0) {
                variantDisplay = `<p class="text-sm text-purple-600 font-medium mt-1">🎨 ${variantParts.join(' • ')}</p>`;
            }
        }

        const cartImage = item.product_image || '/static/img/logo.png';
        const productName = item.product_name || `Producto ${item.id_producto || item.product_id}`;
        const productCode = item.product_codigo || '';

        return `
            <div class="cart-item" data-item-id="${item.id}" style="display: flex !important; justify-content: space-between; align-items: stretch; padding: 1.5rem; border-radius: 12px; background: white; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); gap: 1.5rem; min-height: 120px; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 1rem; flex: 1;">
                    <img src="${cartImage}" alt="${productName}" style="width: 96px; height: 96px; object-fit: cover; border-radius: 8px;" onerror="this.src='/static/img/logo.png'">
                    <div style="flex: 1;">
                        <h3 style="font-size: 1.125rem; font-weight: 600; color: #111827; margin: 0 0 0.5rem 0;">${productName}</h3>
                        ${variantDisplay}
                        <p style="font-size: 0.875rem; color: #6b7280; margin: 0.5rem 0;">${productCode}</p>
                        <p style="font-size: 1.125rem; font-weight: 700; color: #667eea; margin: 0.5rem 0;">$${cart.formatPrice(price)}</p>
                    </div>
                </div>
                
                <div style="display: flex; align-items: center; gap: 1.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <button class="cart-page-btn" data-action="decrease" data-item-id="${item.id}" style="background: #d1d5db; color: #374151; width: 32px; height: 32px; border-radius: 50%; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 0.875rem;">
                            <i class="fas fa-minus"></i>
                        </button>
                        <span style="font-weight: 600; font-size: 1.125rem; width: 48px; text-align: center; color: #111827;">${quantity}</span>
                        <button class="cart-page-btn" data-action="increase" data-item-id="${item.id}" style="background: #d1d5db; color: #374151; width: 32px; height: 32px; border-radius: 50%; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 0.875rem;">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    
                    <div style="text-align: right; min-width: 120px;">
                        <p style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.5rem 0;">$${cart.formatPrice(itemTotal)}</p>
                        <button class="cart-page-btn" data-action="remove" data-item-id="${item.id}" style="color: #ef4444; background: none; border: none; cursor: pointer; font-size: 0.875rem; padding: 0;">
                            <i class="fas fa-trash" style="margin-right: 0.25rem;"></i>Eliminar
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    console.log(`✅ HTML inserted: ${pageCartItems.innerHTML.length} characters`);
    console.log(`📦 Elements in container: ${pageCartItems.children.length}`);

    // Actualizar resumen
    if (cartSummary) {
        cartSummary.classList.remove('hidden');
        const totalElement = document.getElementById('total');
        const subtotalElement = document.getElementById('subtotal');
        if (totalElement) totalElement.textContent = `$${cart.formatPrice(total)}`;
        if (subtotalElement) subtotalElement.textContent = `$${cart.formatPrice(total)}`;
    }

    // Configurar event listeners para los botones de la página
    setupCartPageListeners();
    
    console.log(`✅ Cart page rendered: ${itemCount} items, total $${cart.formatPrice(total)}`);
};

// Event listeners para botones en la página del carrito
function setupCartPageListeners() {
    const pageButtons = document.querySelectorAll('.cart-page-btn');
    pageButtons.forEach(button => {
        button.addEventListener('click', async (e) => {
            const action = e.currentTarget.dataset.action;
            const itemId = e.currentTarget.dataset.itemId;
            
            console.log(`🎯 Cart page button: ${action} for item ${itemId}`);
            
            if (action === 'remove') {
                await cart.removeItem(itemId);
            } else if (action === 'increase' || action === 'decrease') {
                // Encontrar el item actual para obtener su cantidad
                const currentItem = cart.cartItems.find(item => item.id === itemId);
                if (currentItem) {
                    const currentQty = currentItem.cantidad || currentItem.quantity || 1;
                    const newQty = action === 'increase' ? currentQty + 1 : currentQty - 1;
                    console.log(`📊 Actualizando cantidad: ${currentQty} → ${newQty}`);
                    await cart.updateQuantity(itemId, newQty);
                } else {
                    console.error(`❌ No se encontró el item ${itemId} en el carrito`);
                }
            }
            
            // Re-renderizar la página
            window.renderCartPage();
        });
    });
    console.log(`✅ Configured ${pageButtons.length} cart page button listeners`);
}
