# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pago
from .utils import generar_pdf_comprobante

@receiver(post_save, sender=Pago)
def crear_comprobante_automatico(sender, instance, created, **kwargs):
    if created and not instance.comprobante:  # Solo si es nuevo y no tiene comprobante
        try:
            generar_pdf_comprobante(instance)
        except Exception as e:
            # Loggear error (opcional pero recomendado)
            print(f"Error generando comprobante para pago {instance.id}: {e}")
            # En producción, usa logging en vez de print