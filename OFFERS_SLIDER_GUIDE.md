# Slider de Ofertas - Guía de Uso

## Descripción

El slider de ofertas es un componente interactivo que muestra un carrusel de imágenes con ofertas y promociones especiales. Está ubicado en el banner hero de la página tienda (`/ecomerce/productos/tienda`).

## Características

- ✅ Rotación automática de imágenes (configurable)
- ✅ Navegación con botones "Anterior/Siguiente"
- ✅ Indicadores (dots) para seleccionar slide
- ✅ Pausa automática al pasar el mouse
- ✅ Transiciones suaves con animaciones CSS
- ✅ Responsive (funciona en móvil, tablet, desktop)

## Estructura

### HTML
La estructura base ya está creada en `Projects/ecomerce/templates/productos_tienda.html`:

```html
<section class="mb-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg shadow-xl overflow-hidden">
    <!-- ... contenido ... -->
    <div class="w-full md:w-2/3 h-72 md:h-80 bg-gray-800 relative flex items-center justify-center overflow-hidden" id="offers-slider-container">
        <!-- El slider se genera aquí dinámicamente -->
    </div>
    <!-- ... -->
</section>
```

### Archivo JavaScript
El módulo está en: `static/ecomerce/productos/offers_slider.js`

## Cómo Usar

### Paso 1: Obtener los datos de ofertas

Puedes obtener las ofertas desde tu API o una base de datos:

```javascript
// Ejemplo 1: Desde un array estático
const offers = [
    {
        image: '/static/images/oferta1.jpg',
        title: 'Oferta Verano',
        description: '50% en ropa',
        link: '/tienda?categoria=ropa'
    },
    {
        image: '/static/images/oferta2.jpg',
        title: 'Electrónica',
        description: 'Hasta 30% off',
        link: '/tienda?categoria=electronicos'
    }
];

// Ejemplo 2: Desde tu API
async function getOffers() {
    const response = await fetch('/api/offers');
    return await response.json();
}
```

### Paso 2: Inicializar el slider

En el archivo `Projects/ecomerce/templates/productos_tienda.html`, descomenta el código en la sección `extra_scripts`:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const offersSlider = new OffersSlider('offers-slider-container');
    
    // Tus ofertas aquí
    const offers = [
        {
            image: '/static/images/oferta1.jpg',
            title: 'Oferta 1',
            description: 'Descripción',
            link: '/oferta1'
        }
    ];
    
    // Inicializar con autoplay cada 5 segundos
    offersSlider.init(offers, 5000);
    
    // Opcional: pausar al pasar el mouse
    offersSlider.enableHoverPause();
});
```

## API de la Clase OffersSlider

### Constructor
```javascript
const slider = new OffersSlider(containerId);
// containerId por defecto es 'offers-slider-container'
```

### Métodos principales

| Método | Parámetros | Descripción |
|--------|-----------|-------------|
| `init(offers, autoplayDelay)` | `offers`: Array de objetos, `autoplayDelay`: ms | Inicializa el slider |
| `nextSlide()` | - | Ir al siguiente slide |
| `prevSlide()` | - | Ir al slide anterior |
| `goToSlide(index)` | `index`: número | Ir a un slide específico |
| `startAutoplay()` | - | Inicia rotación automática |
| `stopAutoplay()` | - | Detiene rotación automática |
| `enableHoverPause()` | - | Pausa al pasar el mouse |

## Ejemplo completo con API

```javascript
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Cargar ofertas desde la API
        const response = await fetch('/api/ecomerce/offers');
        const offers = await response.json();
        
        // Inicializar slider
        const offersSlider = new OffersSlider('offers-slider-container');
        offersSlider.init(offers, 4000); // 4 segundos entre cambios
        offersSlider.enableHoverPause();
        
        console.log('Slider de ofertas inicializado');
    } catch (error) {
        console.error('Error cargando ofertas:', error);
    }
});
```

## Estructura de datos de ofertas

Cada oferta debe tener la siguiente estructura:

```javascript
{
    image: String,      // URL de la imagen (requerido)
    title: String,      // Título de la oferta
    description: String, // Descripción corta
    link: String        // Enlace cuando se hace click
}
```

## Estilos CSS Personalizados

Puedes personalizar los estilos editando las variables CSS en `productos_tienda.html`:

```css
/* Cambiar duración de transición */
.slider-slide {
    transition-duration: 800ms; /* Por defecto 500ms */
}

/* Cambiar velocidad de autoplay */
offersSlider.autoplayDelay = 3000; // 3 segundos
```

## Próximas mejoras sugeridas

1. **Fetch dinámico de ofertas**: Conectar con tu API de ofertas
2. **Links funcionando**: Agregar onclick a los slides para redirigir
3. **Indicadores de oferta**: Mostrar "HOT DEAL", "LIMITED TIME" badges
4. **Swipe gestures**: Soporte para swipe en móviles
5. **Ofertas por categoría**: Diferentes ofertas según la categoría seleccionada

## Debugging

Si el slider no aparece:

1. Verifica que el container `offers-slider-container` existe en el HTML
2. Abre la consola del navegador (F12) y busca errores
3. Verifica que `offers_slider.js` esté cargado
4. Verifica que `offers` no esté vacío

```javascript
// En la consola del navegador:
console.log(window.OffersSlider); // Debe mostrar la clase
console.log(document.getElementById('offers-slider-container')); // Debe mostrar el elemento
```
