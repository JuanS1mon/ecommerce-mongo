/**
 * Script global para actualizar el contador de wishlist en toda la aplicación
 */

(function() {
    'use strict';

    // Función para actualizar el contador de wishlist
    async function updateGlobalWishlistCount() {
        const token = window.getAuthToken && window.getAuthToken() || 
                     sessionStorage.getItem('ecommerce_token') ||
                     localStorage.getItem('token') ||
                     localStorage.getItem('access_token');
        if (!token) {
            hideWishlistBadge();
            hideWishlistNavButton();
            return;
        }

        // Mostrar el botón de favoritos en la navegación
        showWishlistNavButton();

        try {
            const response = await fetch('/ecomerce/api/lista-deseos/count', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                const count = data.count || 0;
                updateWishlistBadge(count);
            } else {
                hideWishlistBadge();
            }
        } catch (error) {
            console.log('Error al actualizar contador de wishlist:', error);
            hideWishlistBadge();
        }
    }

    // Actualizar el badge del contador
    function updateWishlistBadge(count) {
        const badge = document.getElementById('wishlist-count');
        if (badge) {
            badge.textContent = count;
            if (count > 0) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    // Ocultar el badge
    function hideWishlistBadge() {
        const badge = document.getElementById('wishlist-count');
        if (badge) {
            badge.classList.add('hidden');
        }
    }

    // Mostrar el botón de favoritos en la navegación
    function showWishlistNavButton() {
        const navButton = document.getElementById('wishlist-nav-button');
        if (navButton) {
            navButton.classList.remove('hidden');
        }
    }

    // Ocultar el botón de favoritos en la navegación
    function hideWishlistNavButton() {
        const navButton = document.getElementById('wishlist-nav-button');
        if (navButton) {
            navButton.classList.add('hidden');
        }
    }

    // Actualizar al cargar la página
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateGlobalWishlistCount);
    } else {
        updateGlobalWishlistCount();
    }

    // Exponer función globalmente para que otros scripts la puedan llamar
    window.updateWishlistCount = updateGlobalWishlistCount;

    // Actualizar cada 30 segundos si el usuario está autenticado
    setInterval(function() {
        const token = window.getAuthToken && window.getAuthToken() || 
                     sessionStorage.getItem('ecommerce_token') ||
                     localStorage.getItem('token') ||
                     localStorage.getItem('access_token');
        if (token) {
            updateGlobalWishlistCount();
        }
    }, 30000);

})();
