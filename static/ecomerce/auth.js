/**
 * Módulo de Autenticación Centralizado para E-commerce
 * Maneja la autenticación, navbar y estado del usuario de forma consistente
 * en todas las páginas de la aplicación.
 */

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.isAuthenticated = false;
        this.token = null;
        this.initialized = false;
    }

    /**
     * Inicializa el módulo de autenticación
     * Debe llamarse cuando el DOM esté listo
     */
    async init() {
        if (this.initialized) return;

        console.log('🚀 AuthManager.init() - Iniciando...');

        try {
            // Obtener token de storage
            this.token = this.getToken();
            console.log('🔑 Token encontrado en init():', this.token ? 'SÍ' : 'NO');

            // Verificar autenticación si hay token
            if (this.token) {
                console.log('🔍 Verificando autenticación con token...');
                await this.verifyAuthentication();
            } else {
                console.log('ℹ️ No hay token, mostrando UI no autenticada');
                this.showUnauthenticatedUI();
            }

            this.initialized = true;
            console.log('✅ AuthManager inicializado correctamente');
        } catch (error) {
            console.error('❌ Error inicializando AuthManager:', error);
            this.showUnauthenticatedUI();
        }
    }

    /**
     * Obtiene el token de autenticación desde storage
     * Prioridad: Cookies > localStorage
     */
    getToken() {
        const cookieToken = this.getCookie('access_token') || this.getCookie('token');
        const localToken = localStorage.getItem('access_token') || localStorage.getItem('token');

        console.log('🍪 Cookie access_token:', this.getCookie('access_token'));
        console.log('🍪 Cookie token:', this.getCookie('token'));
        console.log('💾 localStorage access_token:', localStorage.getItem('access_token'));
        console.log('💾 localStorage token:', localStorage.getItem('token'));
        console.log('🎯 Token seleccionado:', cookieToken || localToken || 'NINGUNO');

        return cookieToken || localToken;
    }

    /**
     * Obtiene el valor de una cookie
     */
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Verifica la autenticación con el backend
     */
    async verifyAuthentication() {
        if (!this.token) {
            console.log('❌ verifyAuthentication: No hay token');
            this.showUnauthenticatedUI();
            return;
        }

        console.log('🔍 verifyAuthentication: Verificando token con servidor...');

        try {
            const response = await fetch('/ecomerce/auth/verify', {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Accept': 'application/json'
                }
            });

            console.log('📡 Respuesta del servidor:', response.status);

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Respuesta OK:', data);
                if (data.success && data.user) {
                    this.currentUser = data.user;
                    this.isAuthenticated = true;

                    // Guardar usuario en localStorage para persistencia
                    localStorage.setItem('user', JSON.stringify(data.user));
                    console.log('💾 Usuario guardado en localStorage');

                    this.showAuthenticatedUI(data.user);
                } else {
                    console.log('❌ Token inválido según servidor - respuesta:', data);
                    this.handleInvalidToken();
                }
            } else if (response.status === 401) {
                console.log('🚫 Token rechazado (401)');
                this.handleInvalidToken();
            } else {
                console.error('💥 Error verificando autenticación:', response.status);
                this.showUnauthenticatedUI();
            }
        } catch (error) {
            console.error('💥 Error en verifyAuthentication:', error);
            this.showUnauthenticatedUI();
        }
    }

    /**
     * Maneja tokens inválidos o expirados
     */
    handleInvalidToken() {
        this.clearAuthentication();
        this.showUnauthenticatedUI();
    }

    /**
     * Limpia toda la información de autenticación
     */
    clearAuthentication() {
        this.currentUser = null;
        this.isAuthenticated = false;
        this.token = null;

        // Limpiar localStorage
        localStorage.removeItem('token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        localStorage.removeItem('token_type');

        // Limpiar cookies
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        document.cookie = 'token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    }

    /**
     * Muestra la UI para usuario no autenticado
     */
    showUnauthenticatedUI() {
        const authButtons = document.getElementById('auth-buttons');
        const userInfo = document.getElementById('user-info');
        const cartButton = document.getElementById('cart-button');
        const wishlistButton = document.getElementById('wishlist-nav-button');

        if (authButtons) authButtons.classList.remove('hidden');
        if (userInfo) userInfo.classList.add('hidden');
        
        // Ocultar carrito si usuario no está autenticado
        if (cartButton) cartButton.classList.add('hidden');
        if (wishlistButton) wishlistButton.classList.add('hidden');
    }

    /**
     * Muestra la UI para usuario autenticado
     */
    showAuthenticatedUI(user) {
        const authButtons = document.getElementById('auth-buttons');
        const userInfo = document.getElementById('user-info');
        const userGreeting = document.getElementById('user-greeting');
        const cartButton = document.getElementById('cart-button');
        const wishlistButton = document.getElementById('wishlist-nav-button');

        if (authButtons) authButtons.classList.add('hidden');
        if (userInfo) userInfo.classList.remove('hidden');
        
        // Mostrar carrito y favoritos si usuario está autenticado
        if (cartButton) cartButton.classList.remove('hidden');
        if (wishlistButton) wishlistButton.classList.remove('hidden');
        
        if (userGreeting) {
            const displayName = user.nombre || user.name || 'Usuario';
            userGreeting.textContent = `Hola, ${displayName}`;
        }

        // Configurar dropdown
        this.setupDropdown();
    }

    /**
     * Configura el dropdown del usuario
     */
    setupDropdown() {
        const dropdownBtn = document.getElementById('user-dropdown-btn');
        const dropdown = document.getElementById('user-dropdown');

        if (dropdownBtn && dropdown) {
            // Remover listeners previos
            const newBtn = dropdownBtn.cloneNode(true);
            dropdownBtn.parentNode.replaceChild(newBtn, dropdownBtn);

            // Agregar nuevo listener
            newBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                dropdown.classList.toggle('hidden');
            });

            // Cerrar dropdown al hacer clic fuera
            document.addEventListener('click', function(e) {
                if (!dropdown.contains(e.target) && !newBtn.contains(e.target)) {
                    dropdown.classList.add('hidden');
                }
            });
        }
    }

    /**
     * Obtiene el ID del usuario actual
     * Primero intenta obtenerlo del cache, luego del backend
     */
    async getCurrentUserId() {
        // Primero intentar obtener del sessionStorage (cache)
        const storedUserId = sessionStorage.getItem('ecommerce_user_id');
        if (storedUserId) {
            return parseInt(storedUserId);
        }

        // Si no está en cache y estamos autenticados, hacer petición
        if (!this.isAuthenticated || !this.token) {
            return null;
        }

        try {
            const response = await fetch('/ecomerce/auth/me', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (response.ok) {
                const userData = await response.json();

                if (userData.id) {
                    // Guardar en cache
                    sessionStorage.setItem('ecommerce_user_id', userData.id.toString());
                    document.cookie = `ecommerce_user_id=${userData.id}; path=/; max-age=86400`;
                    return userData.id;
                }
            } else if (response.status === 401) {
                this.handleInvalidToken();
            }
        } catch (error) {
            console.error('Error obteniendo usuario actual:', error);
        }

        return null;
    }

    /**
     * Función de logout
     */
    logout() {
        this.clearAuthentication();
        this.showUnauthenticatedUI();

        // Limpiar carrito si existe
        if (window.cart) {
            window.cart.userId = null;
            window.cart.cartItems = [];
            if (typeof window.cart.renderEmptyCart === 'function') {
                window.cart.renderEmptyCart();
            }
        }

        // Mostrar mensaje
        if (typeof showToast === 'function') {
            showToast('Sesión cerrada exitosamente', 'success');
        }

        // Redirigir a login si estamos en una página que requiere autenticación
        const currentPath = window.location.pathname;
        if (currentPath.includes('/carrito') || currentPath.includes('/checkout')) {
            window.location.href = '/login';
        }
    }

    /**
     * Verifica si el usuario está autenticado
     */
    isUserAuthenticated() {
        return this.isAuthenticated && this.token !== null;
    }

    /**
     * Obtiene la información del usuario actual
     */
    getCurrentUser() {
        return this.currentUser;
    }

    /**
     * Fuerza una recarga de la autenticación
     */
    async refreshAuthentication() {
        this.token = this.getToken();
        if (this.token) {
            await this.verifyAuthentication();
        } else {
            this.showUnauthenticatedUI();
        }
    }
}

// Crear instancia global
window.authManager = new AuthManager();

// Función global para logout (para compatibilidad con código existente)
window.logout = function() {
    if (window.authManager) {
        window.authManager.logout();
    }
};

// Función global para obtener user ID (para compatibilidad con código existente)
window.getCurrentUserId = async function() {
    if (window.authManager) {
        return await window.authManager.getCurrentUserId();
    }
    return null;
};

// Función global para obtener token (para compatibilidad con código existente)
window.getAuthToken = function() {
    if (window.authManager) {
        return window.authManager.getToken();
    }
    // Función helper para obtener cookie
    const getCookie = function(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    
    return getCookie('access_token') ||
           getCookie('token') ||
           localStorage.getItem('access_token') ||
           localStorage.getItem('token');
};

// Función global para obtener headers de autenticación
window.getAuthHeaders = function() {
    const token = window.getAuthToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Función global para obtener token de autenticación
window.getAuthToken = function() {
    if (window.authManager && window.authManager.token) {
        return window.authManager.token;
    }
    
    // Fallback: buscar en cookies y localStorage
    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    
    return getCookie('access_token') ||
           getCookie('token') ||
           localStorage.getItem('access_token') ||
           localStorage.getItem('token');
};

// Crear instancia global del AuthManager
window.authManager = new AuthManager();

// Inicializar automáticamente cuando el DOM esté listo (solo si no hay inicialización específica)
document.addEventListener('DOMContentLoaded', function() {
    // No inicializar automáticamente si la página ya maneja su propia inicialización
    // (detectado por la presencia de una inicialización específica en el DOMContentLoaded)
    const hasSpecificInit = document.querySelector('script[src*="auth.js"]') &&
                           (window.location.pathname.includes('/servicios') ||
                            window.location.pathname.includes('/servicio/') ||
                            window.location.pathname.includes('/contrato/') ||
                            window.location.pathname.includes('/perfil') ||
                            window.location.pathname.includes('/tienda') ||
                            window.location.pathname.includes('/checkout'));

    if (!hasSpecificInit && window.authManager && !window.authManager.initialized) {
        console.log('🔄 Inicialización automática del AuthManager...');
        window.authManager.init();
    }
});

// Exportar para uso en módulos ES6 si es necesario
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}