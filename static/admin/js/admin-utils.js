/**
 * Utilidades comunes para el panel de administración
 * Incluye manejo de autenticación, sesiones y redirecciones
 */

// Manejador global de errores de autenticación (401)
function manejarErrorAutenticacion(response) {
    if (response.status === 401) {
        console.warn('⚠️ Token expirado o inválido. Redirigiendo al login...');
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_user');
        
        // Mostrar mensaje breve antes de redirigir
        const mensaje = document.createElement('div');
        mensaje.id = 'session-expired-message';
        mensaje.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(231, 76, 60, 0.95);
            color: white;
            padding: 20px 40px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            z-index: 10001;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            text-align: center;
        `;
        mensaje.innerHTML = '<i class="fas fa-lock"></i> Sesión expirada. Redirigiendo al login...';
        document.body.appendChild(mensaje);
        
        // Redirigir después de 1.5 segundos
        setTimeout(() => {
            window.location.href = '/admin/login';
        }, 1500);
        
        return true;
    }
    return false;
}

// Verificar autenticación al cargar la página
function verificarAutenticacionAdmin() {
    const token = localStorage.getItem('admin_token');
    const userStr = localStorage.getItem('admin_user');
    
    if (!token || !userStr) {
        console.warn('No hay sesión activa. Redirigiendo al login...');
        window.location.href = '/admin/login';
        return false;
    }
    
    return true;
}

// Logout global
function logoutAdmin() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = '/admin/login';
}

// Wrapper para fetch que maneja automáticamente errores 401
async function fetchConAutenticacion(url, options = {}) {
    const token = localStorage.getItem('admin_token');
    
    if (!token) {
        console.error('No hay token de autenticación');
        window.location.href = '/admin/login';
        return null;
    }
    
    // Agregar token a los headers
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...(options.headers || {})
    };
    
    try {
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // Manejar error 401
        if (manejarErrorAutenticacion(response)) {
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('Error en la petición:', error);
        throw error;
    }
}

// Interceptor global para fetch (opcional, más avanzado)
function instalarInterceptorFetch() {
    const originalFetch = window.fetch;
    
    window.fetch = async function(...args) {
        try {
            const response = await originalFetch.apply(this, args);
            
            // Verificar si es una petición al API del admin y si hay error 401
            const url = args[0];
            if (typeof url === 'string' && url.includes('/admin/') && response.status === 401) {
                manejarErrorAutenticacion(response);
            }
            
            return response;
        } catch (error) {
            console.error('Error en fetch interceptado:', error);
            throw error;
        }
    };
}

// Mostrar notificación toast
function mostrarNotificacion(mensaje, tipo = 'info') {
    const colores = {
        'success': '#27ae60',
        'error': '#e74c3c',
        'warning': '#f39c12',
        'info': '#3498db'
    };
    
    const iconos = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colores[tipo] || colores.info};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        animation: slideInRight 0.3s ease-out;
        max-width: 350px;
    `;
    toast.innerHTML = `<i class="fas fa-${iconos[tipo] || iconos.info}"></i> ${mensaje}`;
    
    // Agregar animación
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    if (!document.getElementById('toast-animations')) {
        style.id = 'toast-animations';
        document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    // Remover después de 3 segundos
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Exportar funciones si se usa como módulo
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        manejarErrorAutenticacion,
        verificarAutenticacionAdmin,
        logoutAdmin,
        fetchConAutenticacion,
        instalarInterceptorFetch,
        mostrarNotificacion
    };
}
