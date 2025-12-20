// Función para actualizar el contador global del carrito
function updateGlobalCartCount(count) {
    const validCount = parseInt(count) || 0;
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
        cartCountElement.textContent = validCount.toString();
        if (validCount > 0) {
            cartCountElement.classList.add('animate-pulse');
        } else {
            cartCountElement.classList.remove('animate-pulse');
        }
    }
}

// Función global simplificada para agregar al carrito usando la clase Cart
window.addToCart = async function(productId, quantity = 1, price = 0, variantData = null) {
    console.log('🛒 window.addToCart llamada:', { productId, quantity, price, variantData });
    
    // Esperar a que window.cart esté disponible si es necesario
    let retries = 0;
    while (!window.cart && retries < 10) {
        console.log('⏳ Esperando a que window.cart esté disponible...');
        await new Promise(resolve => setTimeout(resolve, 100));
        retries++;
    }
    
    // Usar la instancia global de Cart si existe
    if (window.cart && typeof window.cart.addProduct === 'function') {
        console.log('✅ Usando window.cart.addProduct');
        const result = await window.cart.addProduct(productId, quantity, price, variantData);
        if (result) {
            showToast('Producto agregado al carrito exitosamente', 'success');
        }
        return result;
    }

    console.warn('⚠️ window.cart no disponible, usando fallback');
    
    // Fallback: implementación directa si la clase Cart no está disponible
    try {
        // Obtener token JWT
        const token = getCookie('ecommerce_token') || sessionStorage.getItem('ecommerce_token') || localStorage.getItem('token') || localStorage.getItem('access_token');

        if (!token) {
            showToast('Debes iniciar sesión para agregar productos', 'error');
            return false;
        }

        // POST directo a la ruta simplificada
        const response = await fetch(`/ecomerce/carrito_items/simple`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
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
            showToast('Producto agregado al carrito exitosamente', 'success');

            // Recargar el carrito si está disponible
            if (window.cart && typeof window.cart.loadCart === 'function') {
                await window.cart.loadCart();
            } else {
                // Si el carrito no está inicializado, actualizar contador manualmente
                const currentCount = parseInt(document.getElementById('cart-count')?.textContent || '0') || 0;
                const newCount = currentCount + quantity;
                updateGlobalCartCount(newCount);
            }

            return true;
        } else if (response.status === 401) {
            showToast('Sesión expirada. Inicia sesión nuevamente.', 'error');
            document.cookie = 'ecommerce_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            sessionStorage.removeItem('ecommerce_token');
            localStorage.removeItem('token');
            localStorage.removeItem('access_token');
            return false;
        } else {
            const error = await response.json();
            showToast(error.detail || 'Error al agregar producto', 'error');
            return false;
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        showToast('Error de conexión', 'error');
        return false;
    }
};

// Función para crear botones de carrito
window.createCartButton = function(productId, quantity = 1, price = 0, buttonText = 'Agregar al Carrito', cssClass = 'btn-cart') {
    const button = document.createElement('button');
    button.className = cssClass;
    button.innerHTML = `<i class="fas fa-cart-plus mr-1"></i> ${buttonText}`;
    button.onclick = function() {
        addToCart(productId, quantity, price);
    };
    return button;
};

// Función para agregar botón de carrito a un elemento existente
window.addCartButtonToElement = function(elementId, productId, quantity = 1, price = 0, buttonText = 'Agregar al Carrito', cssClass = 'btn-cart') {
    const element = document.getElementById(elementId);
    if (element) {
        const button = createCartButton(productId, quantity, price, buttonText, cssClass);
        element.appendChild(button);
    }
};

// Función para inicializar botones de carrito en una página
window.initCartButtons = function() {
    // Buscar todos los elementos con data-cart-button
    const cartButtons = document.querySelectorAll('[data-cart-button]');

    cartButtons.forEach(element => {
        const productId = element.dataset.productId;
        const quantity = parseInt(element.dataset.quantity) || 1;
        const price = parseFloat(element.dataset.price) || 0;

        if (productId && !element.onclick) {
            element.onclick = function() {
                addToCart(productId, quantity, price);
            };
        }
    });
};

// Función para leer cookies
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Función auxiliar para mostrar toast
function showToast(message, type = 'success') {
    // Usar la función global showToast si existe, sino crear una
    if (typeof window.showToast === 'function' && window.showToast !== showToast) {
        window.showToast(message, type);
        return;
    }
    
    // Crear contenedor si no existe
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
    }

    // Crear toast
    const toast = document.createElement('div');
    toast.className = 'px-4 py-3 rounded-lg shadow-lg text-white transform transition-all duration-300 translate-x-full';

    // Establecer color según tipo
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
    container.appendChild(toast);

    // Animar entrada
    setTimeout(() => {
        toast.classList.remove('translate-x-full');
    }, 100);

    // Auto-remover después de 3 segundos
    setTimeout(() => {
        toast.classList.add('translate-x-full');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initCartButtons();
});