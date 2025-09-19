from django_filters.rest_framework import DjangoFilterBackend
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
    Bitacora,Comunicado
)
from  .mixin import BitacoraLoggerMixin
from .serializers import (ChangePasswordSerializer,
    RolSerializer,PropietarioUsuarioSerializer, CasaConPropietarioDetalleSerializer,UsuarioSerializer, TelefonoSerializer, AsignarCasaAVehiculoSerializer,
    AdministradorSerializer, PersonalSerializer,LogoutSerializer,MyTokenPairSerializer,
    GroupSerializer,AuthPermissionSerializer,UsuarioMeSerializer ,AsignarResidenteACasaSerializer,ComunicadoSerializer
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
    filter_backends = [DjangoFilterBackend]  # 👈 AÑADE ESTO
    filterset_fields = ['rol__nombre']  # 👈
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
    @action(detail=False, methods=['get'], url_path='propietarios', url_name='propietarios')
    def propietarios(self, request):
        propietarios = Usuario.objects.filter(propietario__isnull=False).select_related('rol', 'propietario')

        serializer = PropietarioUsuarioSerializer(propietarios, many=True)
        return Response(serializer.data)

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
        logger.info('el usuario ingreso al perfil',)

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

        #logger.info("=== RAW BODY === %s", raw)
        #logger.info("=== PARSED DATA === %s", request.data)
        #logger.info("=== HEADERS === %s", headers)
    
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

# ======== NUEVO: Asignar propietario a una casa ========
    @action(detail=True, methods=['post'], url_path='asignar-propietario', url_name='asignar_propietario')
    def asignar_propietario(self, request, pk=None):
        casa = self.get_object()

        serializer = AsignarPropietarioACasaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_casa = serializer.save(casa=casa)

        # Devolvemos la casa actualizada con todos sus datos
        response_serializer = CasaSerializer(updated_casa)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

        # ======== NUEVO: Desasignar propietario de una casa ========
    @action(detail=True, methods=['post'], url_path='desasignar-propietario')
    def desasignar_propietario(self, request, pk=None):
    # 1. Obtener la instancia de la casa
        casa = self.get_object()

    # 2. Verificar si la casa ya tiene un propietario asignado
        if not casa.propietario:
            return Response({'detail': 'Esta casa ya no tiene un propietario asignado.'},
                        status=status.HTTP_400_BAD_REQUEST)

    # 3. Desasignar el propietario estableciendo el campo a None
        casa.propietario = None
        casa.save()

    # 4. Devolver la casa actualizada (ahora sin propietario)
        response_serializer = CasaSerializer(casa)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    @action(detail=False, methods=['get'], url_path='detalles', url_name='casas_detalles')
    def detalles(self, request):
        """
        Endpoint para listar todas las casas con detalles completos del propietario.
        """
        casas = self.get_queryset()
        serializer = CasaConPropietarioDetalleSerializer(casas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='detalle-completo', url_name='casa_detalle_completo')
    def detalle_completo(self, request, pk=None):
        casa = self.get_object()
        serializer = CasaConPropietarioDetalleSerializer(casa)
        return Response(serializer.data)
class ResidenteViewSet(viewsets.ModelViewSet):
    queryset = Residente.objects.all()
    filter_backends = [DjangoFilterBackend]  # 👈 AÑADE ESTO
    filterset_fields = ['rol_residencia'] 
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
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer  # Para GET, POST, PUT, DELETE normales

    @action(detail=True, methods=['post'], url_path='asignar-casa', url_name='asignar_casa')
    def asignar_casa(self, request, pk=None):
        vehiculo = self.get_object()  # Obtiene el vehículo por pk

        # Usamos SOLO el serializer independiente para validar la entrada
        serializer = AsignarCasaAVehiculoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Guardamos la asignación/desasignación
        updated_vehiculo = serializer.save(vehiculo=vehiculo)

        # Devolvemos el vehículo actualizado con todos sus campos (incluyendo casa)
        # Usamos VehiculoSerializer para la respuesta (porque queremos ver los detalles)
        response_serializer = VehiculoSerializer(updated_vehiculo)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
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

class ComunicadoViewSet(viewsets.ModelViewSet):
    queryset = Comunicado.objects.all().order_by('-fecha_publicacion', '-fecha_creacion')
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated]  # Solo usuarios autenticados

    def get_queryset(self):
        """
        Opcional: Filtrar comunicados visibles para el usuario actual.
        Si el usuario es residente, solo ver comunicados globales o dirigidos a su casa.
        Si es administrador, ve todos.
        """
        user = self.request.user
        queryset = Comunicado.objects.filter(estado='publicado')

        # Si es administrador, puede ver todos (incluso borradores/archivados si lo deseas)
        if hasattr(user, 'Administrador'):
            return Comunicado.objects.all().order_by('-fecha_publicacion', '-fecha_creacion')

        # Si es residente, filtrar por su casa o globales
        try:
            residente = user.residentes.first()  # Suponiendo que un usuario puede ser residente en una casa
            if residente:
                queryset = queryset.filter(
                    models.Q(casa_destino=residente.casa) | models.Q(casa_destino__isnull=True)
                )
        except:
            pass  # Si no es residente, solo ve globales

        return queryset
# views.py — Agrega al final

from .models import ConceptoPago, Cuota, Pago
from .serializers import ConceptoPagoSerializer, CuotaSerializer, PagoSerializer

class ConceptoPagoViewSet(viewsets.ModelViewSet):
    queryset = ConceptoPago.objects.all()
    serializer_class = ConceptoPagoSerializer
    permission_classes = [IsAuthenticated]  # Solo autenticados
    # Opcional: solo administradores pueden crear/editar
    # permission_classes = [IsAdministrador]


class CuotaViewSet(viewsets.ModelViewSet):
    queryset = Cuota.objects.select_related('concepto', 'casa').all()
    serializer_class = CuotaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['casa', 'estado', 'concepto', 'periodo']

    # Opcional: acción para marcar como pagada
    @action(detail=True, methods=['post'], url_path='marcar-pagada')
    def marcar_pagada(self, request, pk=None):
        cuota = self.get_object()
        if cuota.estado == 'pagada':
            return Response({'detail': 'Esta cuota ya está pagada.'}, status=status.HTTP_400_BAD_REQUEST)

        cuota.estado = 'pagada'
        cuota.fecha_pago = timezone.now()
        cuota.save()

        return Response(CuotaSerializer(cuota).data, status=status.HTTP_200_OK)


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.select_related('cuota', 'reserva', 'concepto', 'pagado_por').all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cuota', 'reserva', 'concepto', 'pagado_por', 'metodo_pago']