# pdf_generator.py
"""
Generador de PDFs para contratos profesionales
"""
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ContractPDFGenerator:
    """Generador de PDFs para contratos profesionales"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Configurar estilos personalizados para el PDF"""
        # Estilo para el título principal
        self.styles.add(ParagraphStyle(
            name='ContractTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        ))

        # Estilo para subtítulos
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            alignment=TA_LEFT,
            spaceAfter=15,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        ))

        # Estilo para texto normal
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_LEFT,
            spaceAfter=10,
            leading=14
        ))

        # Estilo para términos legales
        self.styles.add(ParagraphStyle(
            name='LegalText',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=8,
            leading=12,
            textColor=colors.darkslategray
        ))

        # Estilo para firma
        self.styles.add(ParagraphStyle(
            name='Signature',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=5
        ))

    def generate_contract_pdf(self, contract_data: Dict[str, Any], user_data: Dict[str, Any]) -> BytesIO:
        """
        Genera un PDF profesional del contrato

        Args:
            contract_data: Datos del contrato
            user_data: Datos del usuario

        Returns:
            BytesIO: Buffer con el PDF generado
        """
        buffer = BytesIO()

        # Crear documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Construir el contenido del PDF
        story = self._build_contract_content(contract_data, user_data)

        # Generar PDF
        doc.build(story)

        # Resetear posición del buffer
        buffer.seek(0)
        return buffer

    def _build_contract_content(self, contract_data: Dict[str, Any], user_data: Dict[str, Any]) -> list:
        """Construye el contenido del contrato"""
        story = []

        # Título del contrato
        story.append(Paragraph("CONTRATO DE SERVICIOS SAAS", self.styles['ContractTitle']))
        story.append(Spacer(1, 0.5*cm))

        # Información básica
        info_data = [
            ['Número de Contrato:', contract_data.get('id', 'N/A')],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y')]
        ]
        info_table = Table(info_data, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 1*cm))

        # 1. PARTES
        story.append(Paragraph("1. PARTES", self.styles['SectionTitle']))
        partes_text = f"""
        Entre <b>{contract_data.get('proveedor_razon_social', 'SysNeg S.A.')}</b>, CUIT {contract_data.get('proveedor_cuit', 'XX-XXXXXXXX-X')}, 
        con domicilio en {contract_data.get('proveedor_domicilio', 'Ciudad Autónoma de Buenos Aires, Argentina')}, en adelante <b>EL PROVEEDOR</b>, 
        y <b>{user_data.get('razon_social', user_data.get('email', 'Cliente'))}</b>, CUIT {user_data.get('cuit', 'XX-XXXXXXXX-X')}, 
        con domicilio en {user_data.get('domicilio', 'Domicilio del Cliente')}, en adelante <b>EL CLIENTE</b>, 
        se celebra el presente Contrato de Servicios SaaS.
        """
        story.append(Paragraph(partes_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 2. OBJETO
        story.append(Paragraph("2. OBJETO", self.styles['SectionTitle']))
        objeto_text = """
        El presente contrato regula la prestación de servicios <b>Software as a Service (SaaS)</b> provistos por EL PROVEEDOR, 
        consistentes en el acceso y uso de plataformas, sistemas informáticos y/o soluciones tecnológicas alojadas en infraestructura del PROVEEDOR o de terceros.<br/>
        El alcance específico del servicio será el correspondiente al plan o producto contratado por EL CLIENTE.
        """
        story.append(Paragraph(objeto_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 3. ALCANCE DEL SERVICIO
        story.append(Paragraph("3. ALCANCE DEL SERVICIO", self.styles['SectionTitle']))
        alcance_text = f"""
        El servicio SaaS incluye exclusivamente:<br/>
        • Acceso remoto a la plataforma durante la vigencia del contrato.<br/>
        • Uso de las funcionalidades habilitadas según el plan contratado ({contract_data.get('servicio', {}).get('nombre', 'Plan Contratado')}).<br/>
        • Puesta en marcha inicial, si correspondiera (2 semanas bonificadas).<br/>
        <br/>
        <b>3.1 Exclusiones</b><br/>
        Salvo acuerdo expreso por escrito, <b>no están incluidos</b>:<br/>
        • Desarrollos a medida.<br/>
        • Soporte técnico continuo.<br/>
        • Mantenimiento evolutivo.<br/>
        • Integraciones con sistemas externos.<br/>
        • Capacitación.<br/>
        • Costos de terceros (APIs, servicios cloud, licencias, modelos de IA).
        """
        story.append(Paragraph(alcance_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 4. OBLIGACIONES DEL PROVEEDOR
        story.append(Paragraph("4. OBLIGACIONES DEL PROVEEDOR", self.styles['SectionTitle']))
        obligaciones_proveedor = """
        EL PROVEEDOR se compromete a:<br/>
        • Mantener la disponibilidad del servicio conforme a estándares razonables.<br/>
        • Proteger la confidencialidad de los datos del CLIENTE.<br/>
        • No divulgar información sensible bajo ninguna circunstancia.<br/>
        <br/>
        EL PROVEEDOR <b>no garantiza</b> que el servicio esté libre de errores ni que produzca resultados específicos.
        """
        story.append(Paragraph(obligaciones_proveedor, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 5. OBLIGACIONES DEL CLIENTE
        story.append(Paragraph("5. OBLIGACIONES DEL CLIENTE", self.styles['SectionTitle']))
        obligaciones_cliente = """
        EL CLIENTE se compromete a:<br/>
        • Utilizar el servicio conforme a su finalidad.<br/>
        • Proporcionar información veraz y completa.<br/>
        • Mantener la confidencialidad de sus credenciales.<br/>
        • Abonar el precio del servicio en tiempo y forma.
        """
        story.append(Paragraph(obligaciones_cliente, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 6. PRECIO Y FORMA DE PAGO
        story.append(Paragraph("6. PRECIO Y FORMA DE PAGO", self.styles['SectionTitle']))
        precio_text = f"""
        El precio del servicio será el correspondiente al plan contratado, expresado en {contract_data.get('moneda', 'ARS')}.<br/>
        • La facturación será {contract_data.get('periodicidad', 'mensual')}.<br/>
        • Los importes no incluyen impuestos.<br/>
        • El vencimiento opera a los {contract_data.get('dias_vencimiento', 30)} días.<br/>
        <br/>
        La falta de pago habilita la suspensión automática del servicio.
        """
        story.append(Paragraph(precio_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 7. DURACIÓN Y RENOVACIÓN
        story.append(Paragraph("7. DURACIÓN Y RENOVACIÓN", self.styles['SectionTitle']))
        duracion_text = f"""
        El contrato tendrá una duración inicial de {contract_data.get('duracion_meses', 1)} mes(es).<br/>
        La renovación será automática por períodos iguales, salvo notificación fehaciente con {contract_data.get('dias_preaviso', 30)} días de antelación.
        """
        story.append(Paragraph(duracion_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 8. SUSPENSIÓN Y TERMINACIÓN
        story.append(Paragraph("8. SUSPENSIÓN Y TERMINACIÓN", self.styles['SectionTitle']))
        suspension_text = f"""
        EL PROVEEDOR podrá suspender el servicio por:<br/>
        • Falta de pago.<br/>
        • Uso indebido.<br/>
        • Incumplimiento contractual.<br/>
        <br/>
        Transcurridos {contract_data.get('dias_retencion', 30)} días de suspensión, los datos podrán ser eliminados de forma permanente.<br/>
        Cualquiera de las partes podrá rescindir el contrato con preaviso de 30 días.
        """
        story.append(Paragraph(suspension_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 9. DATOS Y CONFIDENCIALIDAD
        story.append(Paragraph("9. DATOS Y CONFIDENCIALIDAD", self.styles['SectionTitle']))
        datos_text = """
        Los datos cargados por EL CLIENTE son de su exclusiva propiedad.<br/>
        EL CLIENTE acepta que el servicio puede utilizar infraestructura y servicios de terceros, sujetos a sus propios términos.<br/>
        EL PROVEEDOR no será responsable por pérdidas de datos derivadas de causas externas, fuerza mayor o fallas de terceros.
        """
        story.append(Paragraph(datos_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 10. LIMITACIÓN DE RESPONSABILIDAD
        story.append(Paragraph("10. LIMITACIÓN DE RESPONSABILIDAD", self.styles['SectionTitle']))
        responsabilidad_text = """
        La responsabilidad total de EL PROVEEDOR se limita, en todos los casos, al monto efectivamente abonado por EL CLIENTE en los últimos <b>3 meses</b>.
        """
        story.append(Paragraph(responsabilidad_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 11. PROPIEDAD INTELECTUAL
        story.append(Paragraph("11. PROPIEDAD INTELECTUAL", self.styles['SectionTitle']))
        propiedad_text = """
        EL PROVEEDOR conserva la titularidad total del software, código fuente, arquitectura y documentación.<br/>
        El presente contrato no otorga derechos de propiedad intelectual al CLIENTE.
        """
        story.append(Paragraph(propiedad_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 12. MODIFICACIONES
        story.append(Paragraph("12. MODIFICACIONES", self.styles['SectionTitle']))
        modificaciones_text = """
        Cualquier modificación deberá realizarse por escrito y aceptada por ambas partes.
        """
        story.append(Paragraph(modificaciones_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 13. LEY APLICABLE Y JURISDICCIÓN
        story.append(Paragraph("13. LEY APLICABLE Y JURISDICCIÓN", self.styles['SectionTitle']))
        ley_text = """
        El presente contrato se rige por las leyes de la República Argentina.<br/>
        Las partes se someten a la jurisdicción exclusiva de los tribunales de la Ciudad Autónoma de Buenos Aires.
        """
        story.append(Paragraph(ley_text, self.styles['NormalText']))
        story.append(Spacer(1, 0.5*cm))

        # 14. ACEPTACIÓN DIGITAL
        story.append(Paragraph("14. ACEPTACIÓN DIGITAL", self.styles['SectionTitle']))
        aceptacion_text = """
        El presente contrato se considera aceptado mediante confirmación electrónica, reconociendo ambas partes plena validez legal.
        """
        story.append(Paragraph(aceptacion_text, self.styles['NormalText']))
        story.append(Spacer(1, 1*cm))

        # Firmas
        signatures = self._create_signatures_section(user_data)
        story.append(signatures)

        return story

    def _create_contract_info_table(self, contract_data: Dict[str, Any], user_data: Dict[str, Any]) -> Table:
        """Crea tabla con información del contrato"""
        data = [
            ['Número de Contrato:', contract_data.get('id', 'N/A')],
            ['Fecha de Emisión:', datetime.now().strftime('%d/%m/%Y')],
            ['Cliente:', user_data.get('email', 'N/A')],
            ['Servicio:', contract_data.get('servicio', {}).get('nombre', 'Servicio Profesional')],
            ['Precio Acordado:', f"${contract_data.get('precio_acordado', contract_data.get('servicio', {}).get('precio_base', 'N/A'))}"],
            ['Duración:', f"{contract_data.get('duracion_meses', 1)} mes(es)"],
            ['Fecha de Inicio:', contract_data.get('fecha_contrato', datetime.now()).strftime('%d/%m/%Y')],
            ['Estado:', contract_data.get('estado', 'Pendiente').upper()]
        ]

        table = Table(data, colWidths=[4*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        return table

    def _get_contract_terms(self) -> list:
        """Obtiene los términos y condiciones del contrato"""
        return [
            "1. <b>OBJETO DEL CONTRATO</b><br/>"
            "El presente contrato tiene por objeto regular la prestación de servicios profesionales "
            "de desarrollo e implementación de sistemas informáticos por parte del PROVEEDOR al CLIENTE, "
            "conforme a las condiciones aquí establecidas. El tipo de servicio se determina por el producto "
            "seleccionado por el CLIENTE, pudiendo incluir servicios de consultoría, desarrollo web, "
            "mantenimiento de sistemas u otros servicios tecnológicos.",

            "2. <b>OBLIGACIONES DEL PROVEEDOR</b><br/>"
            "El PROVEEDOR se compromete a:<br/>"
            "• Prestar los servicios contratados con la diligencia y profesionalismo requeridos<br/>"
            "• Cumplir con los plazos de instalación (2 semanas bonificadas) y estándares de calidad acordados<br/>"
            "• Garantizar que todos los datos e información del CLIENTE son de su exclusiva propiedad<br/>"
            "• Mantener la confidencialidad de toda información sensible y datos de clientes<br/>"
            "• No publicar ni divulgar información del CLIENTE ni de sus usuarios bajo ninguna circunstancia",

            "3. <b>OBLIGACIONES DEL CLIENTE</b><br/>"
            "El CLIENTE se compromete a:<br/>"
            "• Proporcionar toda la información necesaria para la prestación del servicio<br/>"
            "• Realizar los pagos conforme a lo establecido y acordado<br/>"
            "• Cumplir con las condiciones de uso del servicio<br/>"
            "• Aceptar la renovación automática del contrato salvo cancelación expresa",

            "4. <b>PRECIO Y FORMA DE PAGO</b><br/>"
            "El precio del servicio es el establecido en la información del contrato. "
            "Los pagos se realizarán conforme a las condiciones acordadas entre las partes, "
            "aceptándose cualquier método de pago válido que ambas partes convengan.",

            "5. <b>DURACIÓN, INSTALACIÓN Y RENOVACIÓN</b><br/>"
            "El presente contrato tendrá una duración de los meses establecidos por el CLIENTE. "
            "Se otorgarán 2 semanas bonificadas para la instalación y puesta en producción del sistema. "
            "Una vez en producción, comenzará el cómputo del período contractual. "
            "La renovación será automática. En caso de vencimiento sin renovación, el CLIENTE no podrá "
            "acceder al panel de administración hasta que se realice la renovación correspondiente.",

            "6. <b>TERMINACIÓN Y SUSPENSIÓN DEL SERVICIO</b><br/>"
            "En caso de incumplimiento por falta de pago, el servicio será suspendido sin eliminación de datos "
            "por un período de 30 días. Transcurrido dicho plazo, los registros serán eliminados permanentemente. "
            "En caso de requerimiento del CLIENTE, los datos podrán ser proporcionados en el formato original "
            "del sistema, sujeto a acuerdos adicionales.",

            "7. <b>ACEPTACIÓN DE TÉRMINOS</b><br/>"
            "Al aceptar este contrato, el CLIENTE declara haber leído, comprendido y aceptado "
            "todos los términos y condiciones aquí establecidos. Este contrato se rige por las leyes "
            "de la República Argentina, con jurisdicción en la Ciudad Autónoma de Buenos Aires, 2024."
        ]

    def _create_services_section(self, contract_data: Dict[str, Any]) -> Paragraph:
        """Crea la sección de servicios contratados"""
        servicio = contract_data.get('servicio', {})
        detalles = contract_data.get('detalles', 'Sin detalles adicionales')
        tipo_servicio = servicio.get('tipo_servicio', 'Servicio Tecnológico Profesional')

        content = f"""
        <b>Servicio Contratado:</b> {servicio.get('nombre', 'Servicio Profesional')}<br/>
        <b>Tipo de Servicio:</b> {tipo_servicio} (determinado por el producto seleccionado)<br/>
        <b>Descripción:</b> {servicio.get('descripcion', 'Servicio profesional personalizado de desarrollo e implementación de sistemas informáticos')}<br/>
        <b>Instalación:</b> 2 semanas bonificadas para instalación y puesta en producción<br/>
        <b>Detalles Adicionales:</b> {detalles}
        """

        return Paragraph(content, self.styles['NormalText'])

    def _get_special_conditions(self) -> list:
        """Obtiene las condiciones especiales del contrato"""
        return [
            "• <b>PROPIEDAD DE LOS DATOS:</b> Todos los datos e información proporcionados por el CLIENTE "
            "son de su exclusiva propiedad. El PROVEEDOR garantiza la integridad y propiedad de dichos datos.",

            "• <b>CONFIDENCIALIDAD Y PROTECCIÓN DE DATOS:</b> El manejo de datos e información sensible "
            "se realizará conforme a los servicios de hosting contratados. El PROVEEDOR no publicará ni divulgará "
            "información del CLIENTE ni de sus usuarios bajo ninguna circunstancia.",

            "• <b>SOPORTE TÉCNICO:</b> El soporte técnico no está incluido en el contrato, salvo en casos críticos "
            "que comprometan la funcionalidad esencial del servicio o bugs reportados. En estos casos, no se aplicarán cargos adicionales.",

            "• <b>ACTUALIZACIONES Y MEJORAS:</b> Las actualizaciones y mejoras del sistema se realizarán cada 6 meses, "
            "salvo casos extremos que requieran intervención inmediata. El PROVEEDOR no está obligado a realizar "
            "actualizaciones. Cualquier desarrollo adicional requerido por el CLIENTE será objeto de un contrato separado.",

            "• <b>ACCESO AL SISTEMA:</b> En caso de vencimiento del contrato sin renovación, el CLIENTE perderá "
            "el acceso al panel de administración hasta que se realice la renovación correspondiente.",

            "• <b>MODIFICACIONES:</b> Cualquier modificación al contrato deberá ser acordada por escrito entre ambas partes.",

            "• <b>TERMINACIÓN:</b> Cualquiera de las partes podrá terminar el contrato con un preaviso de 30 días, "
            "o inmediatamente en caso de incumplimiento grave.",

            "• <b>LEY APLICABLE:</b> Este contrato se rige por las leyes de la República Argentina, "
            "con jurisdicción exclusiva en la Ciudad Autónoma de Buenos Aires, 2024."
        ]

    def _create_signatures_section(self, user_data: Dict[str, Any]) -> Table:
        """Crea la sección de firmas"""
        data = [
            ['_______________________________', '_______________________________'],
            ['EL PROVEEDOR', 'EL CLIENTE'],
            ['', ''],
            ['Aceptación Digital', 'Aceptación Digital'],
            [f'Fecha: {datetime.now().strftime("%d/%m/%Y")}', f'Cliente: {user_data.get("email", "N/A")}']
        ]

        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        return table


# Función de conveniencia para generar PDFs
def generate_contract_pdf(contract_data: Dict[str, Any], user_data: Dict[str, Any]) -> BytesIO:
    """
    Función de conveniencia para generar PDFs de contratos

    Args:
        contract_data: Datos del contrato
        user_data: Datos del usuario

    Returns:
        BytesIO: Buffer con el PDF generado
    """
    generator = ContractPDFGenerator()
    return generator.generate_contract_pdf(contract_data, user_data)