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
def send_fcm_notification(device_tokens, title, body, data=None):
    """
    Envía una notificación a través de Firebase Cloud Messaging.
    """
    if not settings.FCM_SERVER_KEY:
        logger.error("FCM_SERVER_KEY no está configurada en settings.py")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"key={settings.FCM_SERVER_KEY}",
    }

    payload = {
        "notification": {
            "title": title,
            "body": body,
        },
        "data": data if data is not None else {},
        "registration_ids": device_tokens, # Usar registration_ids para múltiples tokens
    }

    try:
        response = requests.post("https://fcm.googleapis.com/fcm/send", headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx
        result = response.json()
        logger.info(f"FCM Response: {result}")

        # Aquí puedes procesar el resultado si necesitas actualizar el estado de NotificacionPush
        # Por ejemplo, si un token falló, podrías desactivar el DispositivoMovil.
        if result.get('failure') > 0 or result.get('canonical_ids') > 0:
            for i, res in enumerate(result.get('results', [])):
                if 'error' in res:
                    logger.warning(f"Error en FCM para token {device_tokens[i]}: {res['error']}")
                    # Considerar desactivar o eliminar el token si es 'NotRegistered' o 'InvalidRegistration'
                    if res['error'] in ['NotRegistered', 'InvalidRegistration']:
                        DispositivoMovil.objects.filter(token_fcm=device_tokens[i]).update(activo=False)
                if 'registration_id' in res:
                    # El token ha sido actualizado (canonical_id), deberías actualizarlo en tu DB
                    old_token = device_tokens[i]
                    new_token = res['registration_id']
                    if old_token != new_token:
                        logger.info(f"FCM token actualizado de {old_token} a {new_token}")
                        DispositivoMovil.objects.filter(token_fcm=old_token).update(token_fcm=new_token)
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al enviar notificación FCM: {e}", exc_info=True)
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar JSON de respuesta FCM: {e}", exc_info=True)
        return False


@receiver(post_save, sender=Cuota)
def cuota_creada_o_actualizada(sender, instance, created, **kwargs):
    """
    Señal que se dispara después de que una Cuota es guardada (creada o actualizada).
    """
    if created: # Solo queremos actuar cuando una cuota es creada
        logger.info(f"Señal 'post_save' para Cuota ID {instance.id} (CREADA)")
        
        try:
            # 1. Encontrar al propietario de la casa de la cuota
            # Asumimos que una casa solo tiene un propietario activo.
            propiedad = Propiedad.objects.filter(casa=instance.casa, activa=True).first()
            
            if not propiedad:
                logger.warning(f"No se encontró un propietario activo para la Casa ID {instance.casa.id} de la Cuota ID {instance.id}. No se enviará notificación.")
                return

            propietario = propiedad.propietario
            logger.info(f"Propietario de la casa {instance.casa.numero_casa}: {propietario.username} (ID: {propietario.id})")

            # 2. Obtener todos los dispositivos activos del propietario
            dispositivos_activos = DispositivoMovil.objects.filter(usuario=propietario, activo=True)
            
            if not dispositivos_activos.exists():
                logger.info(f"El propietario {propietario.username} no tiene dispositivos activos registrados. No se enviará notificación push.")
                return

            tokens_fcm = [d.token_fcm for d in dispositivos_activos]
            
            # 3. Preparar los datos de la notificación
            titulo = f"Nueva Cuota Generada para Casa {instance.casa.numero_casa}"
            cuerpo = f"Se ha generado una nueva cuota de {instance.monto} {instance.concepto.nombre} para el periodo {instance.periodo.strftime('%B %Y')}. Fecha de vencimiento: {instance.fecha_vencimiento.strftime('%d/%m/%Y')}."
            
            # Datos adicionales para la aplicación móvil (opcional, útil para navegar a la cuota)
            datos_adicionales = {
                "cuota_id": str(instance.id),
                "casa_id": str(instance.casa.id),
                "tipo_notificacion": "finanzas", # Para que la app sepa cómo manejarla
                "ruta_app": "/mis-cuotas" # Ejemplo de ruta en la app
            }

            # 4. Enviar la notificación a través de FCM
            success = send_fcm_notification(tokens_fcm, titulo, cuerpo, datos_adicionales)

            # 5. Registrar las notificaciones enviadas en tu modelo NotificacionPush
            for dispositivo in dispositivos_activos:
                NotificacionPush.objects.create(
                    usuario=propietario,
                    dispositivo=dispositivo,
                    titulo=titulo,
                    cuerpo=cuerpo,
                    tipo='finanzas', # O el tipo que consideres más apropiado
                    estado='enviada',
                    datos_adicionales=datos_adicionales
                )
            if success:
                logger.info(f"Notificaciones push enviadas exitosamente a {len(tokens_fcm)} dispositivos del propietario {propietario.username}.")
            else:
                logger.error(f"Falló el envío de notificaciones push para la Cuota ID {instance.id}.")

        except Exception as e:
            logger.error(f"Error en la señal 'cuota_creada_o_actualizada' para Cuota ID {instance.id}: {e}", exc_info=True)