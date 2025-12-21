"""
Verificador SEO para la tienda online
Valida implementaciones de SEO y genera reportes
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json

class SEOChecker:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.errors = []
        self.warnings = []
        self.success = []
    
    def check_robots_txt(self):
        """Verifica que robots.txt existe y es accesible"""
        try:
            response = requests.get(f"{self.base_url}/robots.txt")
            if response.status_code == 200:
                self.success.append("✅ robots.txt es accesible")
                if "Sitemap:" in response.text:
                    self.success.append("✅ robots.txt contiene referencia a sitemap")
                else:
                    self.warnings.append("⚠️ robots.txt no contiene Sitemap:")
            else:
                self.errors.append(f"❌ robots.txt retorna código {response.status_code}")
        except Exception as e:
            self.errors.append(f"❌ Error accediendo robots.txt: {e}")
    
    def check_sitemap(self):
        """Verifica que sitemap.xml existe y es válido"""
        try:
            response = requests.get(f"{self.base_url}/sitemap.xml")
            if response.status_code == 200:
                self.success.append("✅ sitemap.xml es accesible")
                # Verificar que es XML válido
                if "<?xml" in response.text and "<urlset" in response.text:
                    self.success.append("✅ sitemap.xml tiene estructura XML correcta")
                    # Contar URLs
                    url_count = response.text.count("<url>")
                    self.success.append(f"✅ sitemap.xml contiene {url_count} URLs")
                else:
                    self.errors.append("❌ sitemap.xml no tiene estructura XML válida")
            else:
                self.errors.append(f"❌ sitemap.xml retorna código {response.status_code}")
        except Exception as e:
            self.errors.append(f"❌ Error accediendo sitemap.xml: {e}")
    
    def check_index_meta_tags(self):
        """Verifica meta tags en la página principal"""
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code != 200:
                self.errors.append(f"❌ Página principal retorna código {response.status_code}")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Verificar title
            title = soup.find('title')
            if title and len(title.text) > 0:
                self.success.append(f"✅ Página tiene título: '{title.text}'")
                if len(title.text) > 60:
                    self.warnings.append("⚠️ Título demasiado largo (>60 caracteres)")
            else:
                self.errors.append("❌ Página no tiene título")
            
            # Verificar meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                desc = meta_desc.get('content', '')
                self.success.append(f"✅ Página tiene meta description: '{desc[:60]}...'")
                if len(desc) > 160:
                    self.warnings.append("⚠️ Meta description demasiada larga (>160 caracteres)")
                elif len(desc) < 50:
                    self.warnings.append("⚠️ Meta description muy corta (<50 caracteres)")
            else:
                self.errors.append("❌ Página no tiene meta description")
            
            # Verificar H1
            h1_tags = soup.find_all('h1')
            if h1_tags:
                self.success.append(f"✅ Página contiene {len(h1_tags)} H1 tag(s)")
                if len(h1_tags) > 1:
                    self.warnings.append("⚠️ Página contiene más de un H1 (debería haber solo uno)")
            else:
                self.errors.append("❌ Página no contiene H1 tag")
            
            # Verificar Open Graph
            og_tags = soup.find_all('meta', attrs={'property': True})
            og_count = sum(1 for tag in og_tags if tag.get('property', '').startswith('og:'))
            if og_count > 0:
                self.success.append(f"✅ Página contiene {og_count} Open Graph tags")
            else:
                self.warnings.append("⚠️ Página no contiene Open Graph tags")
            
            # Verificar JSON-LD
            json_ld = soup.find_all('script', type='application/ld+json')
            if json_ld:
                self.success.append(f"✅ Página contiene {len(json_ld)} JSON-LD schema(s)")
            else:
                self.warnings.append("⚠️ Página no contiene JSON-LD schema")
            
            # Verificar canonical
            canonical = soup.find('link', rel='canonical')
            if canonical:
                self.success.append(f"✅ Página contiene canonical tag")
            else:
                self.warnings.append("⚠️ Página no contiene canonical tag")
            
        except Exception as e:
            self.errors.append(f"❌ Error analizando página principal: {e}")
    
    def check_products_schema(self):
        """Verifica schema en productos"""
        try:
            response = requests.get(f"{self.base_url}/ecomerce/api/productos/publicos?limit=1")
            if response.status_code == 200:
                products = response.json()
                if products:
                    self.success.append(f"✅ API de productos es accesible")
                    if len(products) > 0:
                        product = products[0]
                        if 'id' in product and 'nombre' in product:
                            self.success.append(f"✅ API retorna productos con estructura correcta")
                        else:
                            self.warnings.append("⚠️ Estructura de productos incompleta")
            else:
                self.warnings.append(f"⚠️ API de productos retorna código {response.status_code}")
        except Exception as e:
            self.warnings.append(f"⚠️ Error accediendo API de productos: {e}")
    
    def generate_report(self):
        """Genera reporte SEO completo"""
        print("\n" + "="*60)
        print("REPORTE DE AUDITORÍA SEO - TIENDA ONLINE")
        print("="*60 + "\n")
        
        # Realizar todas las verificaciones
        self.check_robots_txt()
        self.check_sitemap()
        self.check_index_meta_tags()
        self.check_products_schema()
        
        # Mostrar resultados
        if self.success:
            print("✅ VERIFICACIONES EXITOSAS:")
            for item in self.success:
                print(f"  {item}")
            print()
        
        if self.warnings:
            print("⚠️  ADVERTENCIAS:")
            for item in self.warnings:
                print(f"  {item}")
            print()
        
        if self.errors:
            print("❌ ERRORES:")
            for item in self.errors:
                print(f"  {item}")
            print()
        
        # Resumen
        print("="*60)
        print(f"RESUMEN: {len(self.success)} ✅ | {len(self.warnings)} ⚠️  | {len(self.errors)} ❌")
        print("="*60 + "\n")
        
        # Guardar reporte en JSON
        report = {
            "timestamp": str(__import__('datetime').datetime.now()),
            "base_url": self.base_url,
            "success": self.success,
            "warnings": self.warnings,
            "errors": self.errors,
            "summary": {
                "total_success": len(self.success),
                "total_warnings": len(self.warnings),
                "total_errors": len(self.errors)
            }
        }
        
        with open("seo_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("📊 Reporte guardado en seo_report.json\n")
        
        return report

if __name__ == "__main__":
    checker = SEOChecker()
    checker.generate_report()
