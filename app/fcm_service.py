# services/fcm_service.py
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from .models import DispositivoMovil, NotificacionPush

# Inicializa Firebase (hazlo una sola vez, ej. en apps.py o settings)
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)

initialize_firebase()

def enviar_notificacion_fcm(usuario, titulo, cuerpo, tipo='sistema', datos_adicionales=None):
    """
    Envía una notificación push a todos los dispositivos activos de un usuario.
    Retorna una lista de objetos NotificacionPush creados.
    """
    dispositivos = DispositivoMovil.objects.filter(usuario=usuario, activo=True)
    notificaciones_enviadas = []

    for dispositivo in dispositivos:
        try:
            # Construir mensaje
            message = messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo,
                ),
                data=datos_adicionales or {},
                token=dispositivo.token_fcm,
            )

            # Enviar
            response = messaging.send(message)
            print(f"Notificación enviada con éxito: {response}")

            # Registrar en DB
            notif = NotificacionPush.objects.create(
                usuario=usuario,
                dispositivo=dispositivo,
                titulo=titulo,
                cuerpo=cuerpo,
                tipo=tipo,
                estado='enviada',
                datos_adicionales=datos_adicionales,
            )
            notificaciones_enviadas.append(notif)

        except Exception as e:
            print(f"Error enviando notificación a {dispositivo.token_fcm}: {e}")
            # Registrar como fallida
            notif = NotificacionPush.objects.create(
                usuario=usuario,
                dispositivo=dispositivo,
                titulo=titulo,
                cuerpo=cuerpo,
                tipo=tipo,
                estado='fallida',
                datos_adicionales=datos_adicionales,
            )
            notificaciones_enviadas.append(notif)

    return notificaciones_enviadas