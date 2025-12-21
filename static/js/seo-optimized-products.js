// Optimización de imágenes con alt text descriptivo
function createProductCard(product) {
  const price = product.precio ? `$${product.precio.toLocaleString('es-ES')}` : 'Consultar';
  const image = product.imagen_url || '/static/img/no-image.png';
  const description = product.descripcion ? 
    (product.descripcion.length > 80 ? product.descripcion.substring(0, 80) + '...' : product.descripcion) 
    : 'Sin descripción';
  
  // Crear alt text descriptivo para SEO
  const altText = `${product.nombre} - ${description} - ${price} - Tienda Online`;
  
  return `
    <div class="product-card bg-white rounded-lg overflow-hidden cursor-pointer" onclick="goToProduct('${product.id}')" itemscope itemtype="https://schema.org/Product">
      <meta itemprop="name" content="${product.nombre}">
      <meta itemprop="description" content="${description}">
      ${product.precio ? `<meta itemprop="price" content="${product.precio}">` : ''}
      <meta itemprop="priceCurrency" content="ARS">
      <img src="${image}" alt="${altText}" class="product-image" loading="lazy"
           onerror="this.src='/static/img/no-image.png'">
      <div class="p-4">
        <h3 class="font-semibold text-gray-800 mb-2 line-clamp-2">${product.nombre}</h3>
        <p class="text-sm text-gray-600 mb-3 line-clamp-2">${description}</p>
        <div class="flex justify-between items-center">
          <span class="text-lg font-bold text-purple-600" itemprop="price">${price}</span>
          <button class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm transition-colors" aria-label="Ver detalles de ${product.nombre}">
            <i class="fas fa-eye"></i> Ver
          </button>
        </div>
        ${product.variantes && product.variantes.length > 0 ? 
          `<div class="mt-2 text-xs text-gray-500">
            <i class="fas fa-palette"></i> ${product.variantes.length} variante${product.variantes.length !== 1 ? 's' : ''}
          </div>` : ''}
      </div>
    </div>
  `;
}
