# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pago,Usuario
from .utils import generar_pdf_comprobante
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import IncidenteSeguridadIA
from .fcm_service import enviar_notificacion_fcm 
@receiver(post_save, sender=Pago)
def crear_comprobante_automatico(sender, instance, created, **kwargs):
    if created and not instance.comprobante:  # Solo si es nuevo y no tiene comprobante
        try:
            generar_pdf_comprobante(instance)
        except Exception as e:
            # Loggear error (opcional pero recomendado)
            print(f"Error generando comprobante para pago {instance.id}: {e}")
            # En producción, usa logging en vez de print
@receiver(post_save, sender=IncidenteSeguridadIA)
def notificar_incidente(sender, instance, created, **kwargs):
    if not created:
        return

    destinatarios = set()

    # Siempre notificar a administradores
    admin_group = Group.objects.filter(name='Administrador').first()
    if admin_group:
        destinatarios.update(Usuario.objects.filter(rol__grupo=admin_group))

    # Notificar a seguridad si es incidente de acceso o persona
    if instance.tipo in ['acceso_no_autorizado', 'persona_desconocida']:
        seguridad_group = Group.objects.filter(name='Seguridad').first()
        if seguridad_group:
            destinatarios.update(Usuario.objects.filter(rol__grupo=seguridad_group))

    # Aquí puedes agregar más lógica según el tipo (vehículo → dueño, perro → dueño mascota, etc.)

    for usuario in destinatarios:
        notificaciones = enviar_notificacion_fcm(
            usuario=usuario,
            titulo=f"🚨 Incidente: {instance.get_tipo_display()}",
            cuerpo=f"📍 {instance.ubicacion}\n📝 {instance.descripcion[:100]}...",
            tipo='seguridad',
            datos_adicionales={
                'incidente_id': str(instance.id),
                'tipo': instance.tipo,
                'accion': 'ver_incidente'
            }
        )
        if notificaciones and not instance.notificacion_enviada:
            instance.notificacion_enviada = notificaciones[0]
            instance.save(update_fields=['notificacion_enviada'])