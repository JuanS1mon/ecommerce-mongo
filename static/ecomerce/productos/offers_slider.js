/**
 * Módulo de Slider de Ofertas para la página Tienda
 * Gestiona la rotación de imágenes de ofertas en el banner hero
 */

class OffersSlider {
    constructor(containerId = 'offers-slider-container') {
        this.container = document.getElementById(containerId);
        this.currentIndex = 0;
        this.offers = []; // Array de ofertas con {image, title, description, link}
        this.autoplayInterval = null;
        this.autoplayDelay = 5000; // 5 segundos por defecto
    }

    /**
     * Inicializa el slider con un array de ofertas
     * @param {Array} offers - Array de objetos: {image, title, description, link}
     * @param {number} autoplayDelay - Milisegundos entre cambios de imagen
     */
    init(offers, autoplayDelay = 5000) {
        this.offers = offers;
        this.autoplayDelay = autoplayDelay;

        if (this.offers.length === 0) {
            console.warn('No hay ofertas para mostrar');
            return;
        }

        // Crear estructura del slider
        this.createSliderStructure();
        
        // Mostrar primer slide
        this.showSlide(0);
        
        // Iniciar autoplay si hay más de una oferta
        if (this.offers.length > 1) {
            this.startAutoplay();
        }
    }

    /**
     * Crea la estructura HTML del slider
     */
    createSliderStructure() {
        // Limpiar contenedor
        this.container.innerHTML = '';

        // Crear wrapper para las imágenes
        const slidesWrapper = document.createElement('div');
        slidesWrapper.className = 'slider-slides relative w-full h-full';

        // Agregar cada oferta como slide
        this.offers.forEach((offer, index) => {
            const slide = document.createElement('div');
            slide.className = `slider-slide absolute w-full h-full opacity-0 transition-opacity duration-500 ${index === 0 ? 'active opacity-100' : ''}`;
            slide.dataset.index = index;

            const img = document.createElement('img');
            img.src = offer.image;
            img.alt = offer.title || 'Oferta';

            slide.appendChild(img);
            slidesWrapper.appendChild(slide);
        });

        this.container.appendChild(slidesWrapper);

        // Crear controles de navegación si hay múltiples ofertas
        if (this.offers.length > 1) {
            this.createControls();
        }
    }

    /**
     * Crea los botones de navegación y dots
     */
    createControls() {
        // Botones de navegación
        const prevBtn = document.createElement('button');
        prevBtn.className = 'absolute left-4 top-1/2 transform -translate-y-1/2 z-20 bg-black/50 hover:bg-black/75 text-white rounded-full w-10 h-10 flex items-center justify-center transition-all';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.onclick = () => this.prevSlide();
        this.container.appendChild(prevBtn);

        const nextBtn = document.createElement('button');
        nextBtn.className = 'absolute right-4 top-1/2 transform -translate-y-1/2 z-20 bg-black/50 hover:bg-black/75 text-white rounded-full w-10 h-10 flex items-center justify-center transition-all';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.onclick = () => this.nextSlide();
        this.container.appendChild(nextBtn);

        // Dots de navegación
        const dotsContainer = document.createElement('div');
        dotsContainer.className = 'slider-controls absolute bottom-5 left-1/2 transform -translate-x-1/2 z-20 flex gap-2';

        this.offers.forEach((_, index) => {
            const dot = document.createElement('button');
            dot.className = `slider-dot ${index === 0 ? 'active' : ''}`;
            dot.onclick = () => this.goToSlide(index);
            dotsContainer.appendChild(dot);
        });

        this.container.appendChild(dotsContainer);
    }

    /**
     * Muestra un slide específico
     */
    showSlide(index) {
        const slides = this.container.querySelectorAll('.slider-slide');
        const dots = this.container.querySelectorAll('.slider-dot');

        slides.forEach((slide, i) => {
            slide.classList.remove('active', 'opacity-100');
            slide.classList.add('opacity-0');
            if (i === index) {
                slide.classList.add('active', 'opacity-100');
            }
        });

        dots.forEach((dot, i) => {
            dot.classList.remove('active');
            if (i === index) {
                dot.classList.add('active');
            }
        });

        this.currentIndex = index;
    }

    /**
     * Siguiente slide
     */
    nextSlide() {
        let newIndex = this.currentIndex + 1;
        if (newIndex >= this.offers.length) {
            newIndex = 0;
        }
        this.showSlide(newIndex);
        this.resetAutoplay();
    }

    /**
     * Slide anterior
     */
    prevSlide() {
        let newIndex = this.currentIndex - 1;
        if (newIndex < 0) {
            newIndex = this.offers.length - 1;
        }
        this.showSlide(newIndex);
        this.resetAutoplay();
    }

    /**
     * Ir a un slide específico
     */
    goToSlide(index) {
        this.showSlide(index);
        this.resetAutoplay();
    }

    /**
     * Inicia reproducción automática
     */
    startAutoplay() {
        this.autoplayInterval = setInterval(() => {
            this.nextSlide();
        }, this.autoplayDelay);
    }

    /**
     * Detiene la reproducción automática
     */
    stopAutoplay() {
        if (this.autoplayInterval) {
            clearInterval(this.autoplayInterval);
            this.autoplayInterval = null;
        }
    }

    /**
     * Reinicia el autoplay (útil cuando el usuario interactúa)
     */
    resetAutoplay() {
        this.stopAutoplay();
        if (this.offers.length > 1) {
            this.startAutoplay();
        }
    }

    /**
     * Pausa el autoplay al pasar el mouse
     */
    enableHoverPause() {
        this.container.addEventListener('mouseenter', () => {
            this.stopAutoplay();
        });

        this.container.addEventListener('mouseleave', () => {
            this.startAutoplay();
        });
    }
}

// Exportar para uso global
window.OffersSlider = OffersSlider;
