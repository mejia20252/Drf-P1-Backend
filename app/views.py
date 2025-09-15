from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from django.db import models 
from django.shortcuts import render
from rest_framework.decorators import action
from .permissions import IsAdministrador, IsCliente,IsPersonal
from .serializers import CasaSerializer, AsignarPropietarioACasaSerializer
from rest_framework.parsers import JSONParser
from rest_framework import viewsets,status
from  django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import Group, Permission as AuthPermission

import logging
logger = logging.getLogger(__name__)
from rest_framework import viewsets
from .models import (
    Rol, Usuario, Telefono, Administrador, Personal,
    Bitacora,
)
from  .mixin import BitacoraLoggerMixin
from .serializers import (ChangePasswordSerializer,
    RolSerializer, UsuarioSerializer, TelefonoSerializer, 
    AdministradorSerializer, PersonalSerializer,LogoutSerializer,MyTokenPairSerializer,
    GroupSerializer,AuthPermissionSerializer,UsuarioMeSerializer ,AsignarResidenteACasaSerializer
)

from rest_framework.permissions import IsAuthenticated

from .permissions import RoleBasedPermission

class RolViewSet(viewsets.ModelViewSet):
    
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    # Puedes añadir permisos aquí si necesitas restringir el acceso
    # permission_classes = [IsAuthenticated]
    def create(self, request, *args, **kwargs):
        # Muestra los datos que llegan a la vista
        print("Datos de la solicitud (request.data):", request.data)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Muestra los datos validados antes de la creación
        print("Datos validados por el serializer:", serializer.validated_data)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    # Usar el permiso IsAuthenticated para requerir que el usuario esté autenticado
    # permission_classes = [IsAuthenticated]
    #permission_classes = [IsAdministrador,IsAuthenticated]
   
    @action(
        detail=False,
        methods=['get'],
        url_path='me',
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """
        Endpoint exclusivo para el usuario autenticado.
        """
        # Usa el nuevo serializador específico en lugar del serializador por defecto del ViewSet
        serializer = UsuarioMeSerializer(request.user)
        return Response(serializer.data)
    @action(
        detail=True,
        methods=['post'],
        url_path='set-password',
        permission_classes=[IsAdministrador]  # cualquiera autenticado; la lógica de permisos la hace el serializer
    )
    def set_password(self, request, pk=None):
        print("📥 Payload recibido en backend:", request.data)
        """
        Cambia la contraseña del usuario objetivo.
        Reglas:
          - Si cambias TU propia contraseña: debes enviar current_password correcto.
          - Si cambias la de OTRO: debes ser superuser (is_superuser).
          - new_password != current_password y min 6 caracteres (lo valida el serializer).
        Payload esperado:
        {
          "current_password": "opcional si admin, obligatorio si self",
          "new_password": "*****",
          "confirm_new_password": "*****"
        }
        """
        target_user = self.get_object()
        
        ser = ChangePasswordSerializer(
            data=request.data,
            context={"request": request, "user": target_user}
        )
        ser.is_valid(raise_exception=True)

        # Si pasa validación, se setea la nueva contraseña
        new_pwd = ser.validated_data["new_password"]
        target_user.set_password(new_pwd)
        target_user.save(update_fields=["password"])

        # (Opcional) registrar en bitácora esta acción específica
        try:
            self._log(request, "CAMBIAR_PASSWORD", self._tabla())
        except Exception:
            pass

        # 204 sin contenido (front solo necesita saber que fue OK)
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class TelefonoViewSet(viewsets.ModelViewSet):
    queryset = Telefono.objects.all()
    serializer_class = TelefonoSerializer
    # permission_classes = [IsAuthenticated]

class AdministradorViewSet(viewsets.ModelViewSet):
    queryset = Administrador.objects.all()
    serializer_class = AdministradorSerializer
    # permission_classes = [IsAuthenticated]

class PersonalViewSet(viewsets.ModelViewSet):
    queryset = Personal.objects.all()
    serializer_class = PersonalSerializer
    # permission_classes = [IsAuthenticated]


class MyTokenObtainPairView(TokenObtainPairView): 
    serializer_class = MyTokenPairSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user  # ← ESTE es el usuario autenticado

        # IP (X-Forwarded-For si hay proxy; si no, REMOTE_ADDR)
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None

        # User-Agent como "device" (o None si vacío)
        device = request.META.get('HTTP_USER_AGENT') or None

        # Registrar login en bitácora
        Bitacora.objects.create(
            usuario=user,
            login=timezone.now(),
            ip=ip,
            device=device
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
#vistas
"""
{
  "refresh": "...",
  "password": "..."
}

"""
class LogoutView(APIView):
    """
    Endpoint de **logout**.
    Requiere `{"refresh": "<jwt-refresh-token>"}` en el cuerpo (JSON).
    Blacklistea el refresh token mediante SimpleJWT y registra el logout en Bitacora si corresponde.
    Retorna 204 en caso de éxito.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]  # fuerza a intentar parsear JSON

    def post(self, request):
        # --- DEBUG: cuerpo crudo + datos parseados + headers ---
        raw = request.body.decode("utf-8", errors="replace")
        headers = {
            k: v for k, v in request.META.items()
            if k.startswith("HTTP_") or k in ("CONTENT_TYPE", "CONTENT_LENGTH")
        }

        logger.info("=== RAW BODY === %s", raw)
        logger.info("=== PARSED DATA === %s", request.data)
        logger.info("=== HEADERS === %s", headers)
    
        # invalidamos el refresh token
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # ——————— Registro de logout ———————
        bit = Bitacora.objects.filter(
            usuario=request.user,
            logout__isnull=True
        ).last()
        if bit:
            print('no se esta cerrando seccion ')
            bit.logout = timezone.now()
            bit.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
class AuthPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista todas las Django Permissions.
    """
    queryset = AuthPermission.objects.all()
    serializer_class = AuthPermissionSerializer
    permission_classes = [IsAdministrador]  
class GroupViewSet(viewsets.ModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupSerializer

# Importa los modelos y serializadores necesarios
from .models import (
    Mascota, Bitacora, DetalleBitacora, Propietario, Inquilino,
    Casa, AreaComun, Reserva, PagoReserva, TareaMantenimiento,
    Vehiculo, Residente
)
from .serializers import (
    MascotaSerializer, BitacoraSerializer, DetalleBitacoraSerializer,
    PropietarioSerializer, CasaSerializer,
    AreaComunSerializer, ReservaSerializer, PagoReservaSerializer,
    TareaMantenimientoSerializer, VehiculoSerializer, ResidenteSerializer
)
from rest_framework import viewsets

class PropietarioViewSet(viewsets.ModelViewSet):
    queryset = Propietario.objects.all()
    serializer_class = PropietarioSerializer
    # Opcional: añade permisos aquí
    # permission_classes = [IsAdministrador]

class InquilinoViewSet(viewsets.ModelViewSet):
    queryset = Inquilino.objects.all()

class CasaViewSet(viewsets.ModelViewSet):
    queryset = Casa.objects.select_related('propietario__usuario__rol').all()
    serializer_class = CasaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='asignar-propietario', url_name='asignar_propietario')
    def asignar_propietario(self, request, pk=None):
        casa = self.get_object()
        serializer = AsignarPropietarioACasaSerializer(data=request.data, context={'casa': casa})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Devuelve la casa actualizada
        return Response(CasaSerializer(casa).data, status=status.HTTP_200_OK)
class ResidenteViewSet(viewsets.ModelViewSet):
    queryset = Residente.objects.all()
    serializer_class = ResidenteSerializer
    # permission_classes = [IsAuthenticated]
class AreaComunViewSet(viewsets.ModelViewSet):
    queryset = AreaComun.objects.all()
    serializer_class = AreaComunSerializer
    # permission_classes = [IsAuthenticated]

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    # permission_classes = [IsAuthenticated]

class PagoReservaViewSet(viewsets.ModelViewSet):
    queryset = PagoReserva.objects.all()
    serializer_class = PagoReservaSerializer
    # permission_classes = [IsAuthenticated]

class TareaMantenimientoViewSet(viewsets.ModelViewSet):
    queryset = TareaMantenimiento.objects.all()
    serializer_class = TareaMantenimientoSerializer
    # permission_classes = [IsAuthenticated]
class BitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer
    # Usar ReadOnlyModelViewSet porque los registros no deberían ser creados, actualizados o eliminados directamente a través de la API
    # permission_classes = [IsAdministrador]

class DetalleBitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DetalleBitacora.objects.all()
    serializer_class = DetalleBitacoraSerializer
    # permission_classes = [IsAdministrador]

class MascotaViewSet(viewsets.ModelViewSet):
    queryset = Mascota.objects.all()
    serializer_class = MascotaSerializer
    # permission_classes = [IsAuthenticated]

class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.select_related('dueno', 'casa').all()
    serializer_class = VehiculoSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='asignar-casa', url_name='asignar_casa')
    def asignar_casa(self, request, pk=None):
        vehiculo = self.get_object()

        # Validar que el dueño del vehículo sea el mismo que hace la solicitud (opcional, según reglas de negocio)
        # Si quieres permitir que solo administradores o propietarios asignen:
        # if not request.user.is_superuser and request.user != vehiculo.dueno:
        #     return Response({"error": "No tienes permiso para asignar esta casa."}, status=403)

        serializer = AsignarCasaAVehiculoSerializer(data=request.data, context={'vehiculo': vehiculo})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(VehiculoSerializer(vehiculo).data, status=status.HTTP_200_OK)
    
class AsignarResidenteACasaView(APIView):
    def post(self, request, casa_id):
        casa = Casa.objects.get(id=casa_id)
        serializer = AsignarResidenteACasaSerializer(data=request.data, context={'casa': casa})
        serializer.is_valid(raise_exception=True)
        residente = serializer.save()
        return Response({
            "message": "Residente asignado correctamente",
            "residente": ResidenteSerializer(residente).data
        }, status=status.HTTP_201_CREATED)