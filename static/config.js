// Configuración global para la aplicación ecommerce
window.ECOMMERCE_CONFIG = {
    API_BASE_URL: '/ecomerce/api',
    FRONTEND_URL: window.location.origin,
    DEBUG: true,

    // Endpoints de API
    ENDPOINTS: {
        PRODUCTS_PUBLIC: '/ecomerce/api/productos/publicos',
        PRODUCTS_TIENDA: '/ecomerce/api/productos/tienda',
        PRODUCT_DETAIL: '/ecomerce/api/productos',
        CATEGORIES_PUBLIC: '/ecomerce/api/categorias/publicas',
        CART: '/ecomerce/api/carrito',
        AUTH: '/ecomerce/auth'
    },

    // Configuración de UI
    UI: {
        ITEMS_PER_PAGE: 12,
        MAX_PRODUCTS_DISPLAY: 50,
        LOADING_TIMEOUT: 10000
    },

    // Configuración de autenticación
    AUTH: {
        TOKEN_KEY: 'token',
        REFRESH_TOKEN_KEY: 'refresh_token'
    }
};

// **FUNCIÓN HELPER CENTRALIZADA PARA OBTENER TOKEN**
// Busca el token en el orden correcto: Cookies > localStorage
window.getAuthToken = function() {
    // Helper para obtener cookie
    const getCookie = function(name) {
        const value = '; ' + document.cookie;
        const parts = value.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    
    return getCookie('access_token') ||
           getCookie('token') ||
           localStorage.getItem('access_token') ||
           localStorage.getItem('token');
};

// Configuración de la tienda (compatibilidad con código existente)
const STORE_CONFIG = {
    name: 'Ecommerce Store',
    description: 'Tu tienda online de confianza',
    logo: '/static/logo.svg',
    primaryColor: '#3B82F6',
    secondaryColor: '#1E40AF'
};

// Función de utilidad para logging
window.log = function(message, level = 'info') {
    if (window.ECOMMERCE_CONFIG.DEBUG) {
        const timestamp = new Date().toISOString();
        const prefix = '[' + timestamp + '] [' + level.toUpperCase() + ']';
        console.log(prefix + ' ' + message);
    }
};

// Función para obtener headers de autenticación
window.getAuthHeaders = function() {
    const token = window.getAuthToken();
    return token ? { 'Authorization': 'Bearer ' + token } : {};
};

// Función para hacer peticiones API con manejo de errores
window.apiRequest = async function(url, options) {
    if (typeof options === 'undefined') {
        options = {};
    }
    
    var defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    // Agregar headers de autenticación
    var authHeaders = window.getAuthHeaders();
    for (var key in authHeaders) {
        if (authHeaders.hasOwnProperty(key)) {
            defaultOptions.headers[key] = authHeaders[key];
        }
    }

    var finalOptions = {};
    for (var key in defaultOptions) {
        if (defaultOptions.hasOwnProperty(key)) {
            finalOptions[key] = defaultOptions[key];
        }
    }
    for (var key in options) {
        if (options.hasOwnProperty(key)) {
            finalOptions[key] = options[key];
        }
    }
    
    if (finalOptions.body && typeof finalOptions.body === 'object') {
        finalOptions.body = JSON.stringify(finalOptions.body);
    }

    try {
        window.log('API Request: ' + (options.method || 'GET') + ' ' + url);
        var response = await fetch(url, finalOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(function() {
                return { detail: 'Error desconocido' };
            });
            throw new Error(errorData.detail || 'HTTP ' + response.status + ': ' + response.statusText);
        }

        const data = await response.json();
        window.log('API Response: ' + url + ' - Success');
        return data;
    } catch (error) {
        window.log('API Error: ' + url + ' - ' + error.message, 'error');
        throw error;
    }
};

// Función para obtener el nombre de la tienda (compatibilidad)
function getStoreName() {
    return STORE_CONFIG.name;
}

// Función para actualizar el nombre de la tienda (compatibilidad)
function setStoreName(newName) {
    STORE_CONFIG.name = newName;
    updateStoreNameInDOM();
}

// Función para actualizar elementos DOM con el nombre de la tienda
function updateStoreNameInDOM() {
    const storeNameElements = document.querySelectorAll('[data-store-name]');
    storeNameElements.forEach(function(element) {
        element.textContent = getStoreName();
    });

    const titleElements = document.querySelectorAll('[data-store-title]');
    titleElements.forEach(function(element) {
        const baseTitle = element.getAttribute('data-store-title');
        document.title = baseTitle + ' - ' + getStoreName();
    });
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    updateStoreNameInDOM();
    window.log('Configuración ecommerce cargada');
});