# utils.py
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
from io import BytesIO

def generar_pdf_comprobante(pago):
    """
    Genera un PDF con los datos del pago y lo guarda en el campo 'comprobante'.
    """
    # Renderizar HTML con los datos del pago
    html_string = render_to_string('comprobantes/comprobante_pago.html', {'pago': pago})

    # Generar PDF en memoria
    html = HTML(string=html_string)
    pdf_buffer = BytesIO()
    html.write_pdf(pdf_buffer)

    # Guardar en el campo FileField
    nombre_archivo = f"comprobante_pago_{pago.id}.pdf"
    pago.comprobante.save(
        nombre_archivo,
        ContentFile(pdf_buffer.getvalue()),
        save=True  # Guarda el modelo automáticamente
    )
    pdf_buffer.close()