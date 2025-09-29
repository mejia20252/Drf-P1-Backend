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
import logging
from .models import Cuota, NotificacionPush, DispositivoMovil, Propiedad, Usuario
import requests
import json
from django.conf import settings

# Configura el logger
logger = logging.getLogger(__name__)

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
        logger.debug(f"IncidenteSeguridadIA {instance.id} actualizado, no se envía notificación.")
        return

    logger.info(f"Se ha creado un nuevo incidente de seguridad IA: {instance.id} - Tipo: {instance.tipo}")

    destinatarios = set()

    # Siempre notificar a administradores
    admin_group = Group.objects.filter(name='Administrador').first()
    if admin_group:
        admin_users = Usuario.objects.filter(rol__grupo=admin_group)
        destinatarios.update(admin_users)
        logger.debug(f"Administradores encontrados: {[u.username for u in admin_users]}")
    else:
        logger.warning("No se encontró el grupo 'Administrador'.")

    # Notificar a seguridad si es incidente de acceso o persona
    if instance.tipo in ['acceso_no_autorizado', 'persona_desconocida']:
        seguridad_group = Group.objects.filter(name='Seguridad').first()
        if seguridad_group:
            seguridad_users = Usuario.objects.filter(rol__grupo=seguridad_group)
            destinatarios.update(seguridad_users)
            logger.debug(f"Usuarios de seguridad encontrados: {[u.username for u in seguridad_users]}")
        else:
            logger.warning("No se encontró el grupo 'Seguridad'.")
    else:
        logger.debug(f"Tipo de incidente '{instance.tipo}' no requiere notificación al grupo 'Seguridad'.")

    if not destinatarios:
        logger.warning(f"No hay destinatarios para notificar el incidente {instance.id}.")
        return

    for usuario in destinatarios:
        logger.info(f"Intentando enviar notificación al usuario: {usuario.username} (ID: {usuario.id})")
        try:
            notificaciones_enviadas = enviar_notificacion_fcm(
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
            
            if notificaciones_enviadas:
                logger.info(f"Notificación FCM enviada exitosamente para el incidente {instance.id} al usuario {usuario.username}. FCM ID: {notificaciones_enviadas[0]}")
                # Solo guardamos la primera notificación si se enviaron múltiples
                if not instance.notificacion_enviada: # Evitar sobreescribir si ya se envió antes por alguna razón
                    instance.notificacion_enviada = notificaciones_enviadas[0]
                    instance.save(update_fields=['notificacion_enviada'])
                    logger.debug(f"Campo 'notificacion_enviada' actualizado para el incidente {instance.id}.")
                else:
                    logger.debug(f"El incidente {instance.id} ya tiene una 'notificacion_enviada' registrada.")
            else:
                logger.warning(f"enviar_notificacion_fcm no retornó IDs de notificación para el usuario {usuario.username} en el incidente {instance.id}.")

        except Exception as e:
            logger.error(f"Error al enviar notificación FCM para el usuario {usuario.username} en el incidente {instance.id}: {e}", exc_info=True)
            # Considera marcar el incidente con un est
