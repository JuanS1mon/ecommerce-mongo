// company_config.js
// =============================
// Configuración de constantes de empresa para el frontend
// =============================

const COMPANY_CONFIG = {
    // Nombre de la empresa
    name: 'Sysne',

    // Información de contacto
    email: 'info@sysne.com',
    domain: 'sysne.com',

    // Descripciones
    description: 'Transformamos datos en decisiones inteligentes con servicios tecnológicos avanzados',
    tagline: 'Consultoría IA, ecommerce inteligente, desarrollo web',

    // URLs
    website: 'https://sysne.com',
    logo: '/static/img/logo.png',

    // Redes sociales (opcional)
    social: {
        linkedin: 'https://linkedin.com/company/sysne',
        twitter: 'https://twitter.com/sysne'
    }
};

// Función helper para obtener valores
function getCompanyInfo(key) {
    return COMPANY_CONFIG[key] || '';
}

// Exportar para uso en módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { COMPANY_CONFIG, getCompanyInfo };
}