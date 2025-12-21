/**
 * ANIMACIONES Y EFECTOS DE VARIANTES
 * ====================================
 * Este archivo proporciona efectos visuales mejorados para la selección de variantes
 */

// Función para animar el cambio de variante
function animateVariantChange(element) {
    if (!element) return;
    
    // Remover la clase de animación anterior
    element.classList.remove('variant-change-highlight');
    
    // Forzar reflow para reiniciar la animación
    void element.offsetWidth;
    
    // Agregar la clase de animación
    element.classList.add('variant-change-highlight');
}

// Función para animar el cambio de precio
function animatePriceChange(priceElement) {
    if (!priceElement) return;
    
    // Remover animación anterior
    priceElement.classList.remove('price-update');
    
    // Forzar reflow
    void priceElement.offsetWidth;
    
    // Agregar animación
    priceElement.classList.add('price-update');
}

// Función para crear efecto de ripple en botones
function createRippleEffect(button, event) {
    const ripple = document.createElement('span');
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('ripple');
    
    button.appendChild(ripple);
    
    // Remover el ripple después de la animación
    setTimeout(() => ripple.remove(), 600);
}

// Función para animar la carga de secciones
function fadeInSection(section, delay = 0) {
    section.style.opacity = '0';
    section.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        section.style.transition = 'all 0.4s ease-in-out';
        section.style.opacity = '1';
        section.style.transform = 'translateY(0)';
    }, delay);
}

// Función para animar cambios de imagen
function animateImageChange(imgElement, newSrc) {
    if (!imgElement) return;
    
    imgElement.style.transition = 'opacity 0.3s ease';
    imgElement.style.opacity = '0';
    
    setTimeout(() => {
        imgElement.src = newSrc;
        imgElement.style.opacity = '1';
    }, 150);
}

// Función para highlight de selects cuando cambian
function setupVariantSelectAnimations() {
    const selects = document.querySelectorAll('.variant-select');
    
    selects.forEach(select => {
        select.addEventListener('change', function() {
            // Animar el select que cambió
            this.classList.remove('variant-change-highlight');
            void this.offsetWidth;
            this.classList.add('variant-change-highlight');
            
            // Animar el contenedor principal
            const container = document.querySelector('.variant-selection-container') || 
                              document.querySelector('#product-details');
            if (container) {
                animateVariantChange(container);
            }
        });
        
        // Efecto hover con transición suave
        select.addEventListener('focus', function() {
            this.style.boxShadow = '0 0 0 3px rgba(0, 191, 255, 0.1)';
        });
        
        select.addEventListener('blur', function() {
            this.style.boxShadow = '';
        });
    });
}

// Inicializar animaciones cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
    setupVariantSelectAnimations();
});

// Exportar funciones para uso global
window.AnimationUtils = {
    animateVariantChange,
    animatePriceChange,
    createRippleEffect,
    fadeInSection,
    animateImageChange,
    setupVariantSelectAnimations
};
