from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import api_view
from rest_framework import generics
from django.shortcuts import get_object_or_404
from django.db import models 
from django.shortcuts import render
from rest_framework.decorators import action
from .permissions import IsAdministrador, IsPropietario
from .serializers import CasaSerializer
from rest_framework.parsers import JSONParser
from rest_framework import viewsets,status
from  django.utils import timezone
from django.core.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import Group, Permission as AuthPermission
from rest_framework import serializers
import logging
from django.conf import settings

import stripe

from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Casa, Propiedad
from .serializers import CasaSerializer

logger = logging.getLogger(__name__)

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
import logging
from rest_framework.response import Response
from rest_framework import status

stripe.api_key = settings.STRIPE_SECRET_KEY




from rest_framework import viewsets
from .models import (
    Rol, Usuario, Telefono ,
    Bitacora,Comunicado,Residente,Propiedad,ContratoArrendamiento
)
from  .mixin import BitacoraLoggerMixin
from .serializers import (ChangePasswordSerializer,
    RolSerializer,UsuarioSerializer, TelefonoSerializer, 
     LogoutSerializer,MyTokenPairSerializer,
    UsuarioMeSerializer ,ComunicadoSerializer,GroupSerializer,ResidenteSerializer,ContratoArrendamientoSerializer
)
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

from rest_framework.permissions import IsAuthenticated



class RolViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    
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

class UsuarioViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
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
        permission_classes=[IsAuthenticated]  # cualquiera autenticado; la lógica de permisos la hace el serializer
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
        pass

class TelefonoViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    serializer_class = TelefonoSerializer

    def get_queryset(self):
        # Administrador ve todos
        if self.request.user.rol and self.request.user.rol.nombre == 'Administrador':
            return Telefono.objects.all()
        # Usuario normal solo ve los suyos
        return Telefono.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        # Si es admin y envía un 'usuario', lo respeta
        if self.request.user.rol and self.request.user.rol.nombre == 'Administrador':
            # Permitir que el admin asigne cualquier usuario
            serializer.save()
        else:
            # Usuario normal: fuerza que sea él mismo
            serializer.save(usuario=self.request.user)

    def perform_update(self, serializer):
        # Validación extra: si no es admin, no puede cambiar el propietario
        if not (self.request.user.rol and self.request.user.rol.nombre == 'Administrador'):
            if 'usuario' in serializer.validated_data and serializer.instance.usuario != self.request.user:
                raise PermissionDenied("No puedes asignar este teléfono a otro usuario.")
        serializer.save()

    def perform_destroy(self, instance):
        # Ya está cubierto por IsOwnerOrAdmin, pero puedes dejarlo explícito si quieres
        if not (self.request.user.rol and self.request.user.rol.nombre == 'Administrador'):
            if instance.usuario != self.request.user:
                raise PermissionDenied("No puedes eliminar teléfonos de otros usuarios.")
        instance.delete()





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
class AuthPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthPermission
        fields = ['id', 'codename', 'name']  
class AuthPermissionViewSet(BitacoraLoggerMixin,viewsets.ReadOnlyModelViewSet):
    """
    Lista todas las Django Permissions.
    """
    queryset = AuthPermission.objects.all()
    serializer_class = AuthPermissionSerializer
    permission_classes = [IsAdministrador]  
class GroupViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupSerializer

# Importa los modelos y serializadores necesarios
from .models import (
    Mascota, Bitacora, DetalleBitacora,
    Casa, AreaComun, Reserva , TareaMantenimiento,
    Vehiculo, Residente
)
from .serializers import (
    MascotaSerializer, BitacoraSerializer, DetalleBitacoraSerializer,
    CasaSerializer,
    AreaComunSerializer, ReservaSerializer,PropiedadSerializer,
    TareaMantenimientoSerializer, VehiculoSerializer,AsignarCasaAVehiculoSerializer
)
from rest_framework import viewsets





class CasaViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    serializer_class = CasaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Casa.objects.prefetch_related(
            Prefetch(
                'propiedad',  # <--- CORRECTED: Use 'propiedad' (singular)
                queryset=Propiedad.objects.select_related('propietario__rol').filter(activa=True),
                to_attr='_prefetched_propiedad_activa' # Optional: a custom attribute to store the prefetched object
            )
        ).all()
class ResidenteViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Residente.objects.all()
    filter_backends = [DjangoFilterBackend]  # 👈 AÑADE ESTO
    filterset_fields = ['rol_residencia'] 
    serializer_class = ResidenteSerializer

    # permission_classes = [IsAuthenticated]
class AreaComunViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = AreaComun.objects.all()
    serializer_class = AreaComunSerializer
    # permission_classes = [IsAuthenticated]

class ReservaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    # permission_classes = [IsAuthenticated]

class ContratoArrendamientoViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    # Usamos select_related para traer los datos de arrendatario, unidad y propietario
    # en una sola consulta cuando se cargan los contratos.
    queryset = ContratoArrendamiento.objects.select_related(
        'arrendatario__rol', # Para el rol del arrendatario si se necesitara
        'unidad',
        'propietario__rol' # Para el rol del propietario si se necesitara
    ).all()
    serializer_class = ContratoArrendamientoSerializer
    permission_classes = [IsAuthenticated] # Ajusta según tus necesidades de permisos
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['arrendatario', 'unidad', 'propietario', 'esta_activo']

    # Opcional: Si quieres que los propietarios/inquilinos solo vean sus propios contratos
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'rol'):
            # Los administradores pueden ver todos los contratos
            if user.rol.nombre == 'Administrador':
                return super().get_queryset()
            # Los propietarios solo ven los contratos donde son propietarios
            if user.rol.nombre == 'Propietario':
                return super().get_queryset().filter(propietario=user)
            # Los inquilinos solo ven los contratos donde son arrendatarios
            if user.rol.nombre == 'Inquilino':
                return super().get_queryset().filter(arrendatario=user)
        # Para cualquier otro caso, o si no hay rol, devuelve un queryset vacío
        return ContratoArrendamiento.objects.none()

    # Opcional: Restringir la creación/actualización/eliminación si es necesario
    def perform_create(self, serializer):
        # Aquí puedes añadir lógica si, por ejemplo, solo los administradores
        # pueden crear contratos o si un propietario puede crear contratos para sus unidades.
        user = self.request.user
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            serializer.save()
        else:
            raise PermissionDenied("Solo los administradores pueden crear contratos de arrendamiento.")

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            serializer.save()
        else:
            raise PermissionDenied("Solo los administradores pueden actualizar contratos de arrendamiento.")

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            instance.delete()
        else:
            raise PermissionDenied("Solo los administradores pueden eliminar contratos de arrendamiento.")

class PropiedadViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Propiedad.objects.all()
    serializer_class = PropiedadSerializer
    permission_classes = [IsAuthenticated]

class TareaMantenimientoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = TareaMantenimiento.objects.all()
    serializer_class = TareaMantenimientoSerializer
    # permission_classes = [IsAuthenticated]
class BitacoraViewSet(BitacoraLoggerMixin,viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer
    # Usar ReadOnlyModelViewSet porque los registros no deberían ser creados, actualizados o eliminados directamente a través de la API
    # permission_classes = [IsAdministrador]

class DetalleBitacoraViewSet(BitacoraLoggerMixin,viewsets.ReadOnlyModelViewSet):
    queryset = DetalleBitacora.objects.all()
    serializer_class = DetalleBitacoraSerializer
    permission_classes = [IsAdministrador]

class MascotaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Mascota.objects.all()
    serializer_class = MascotaSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user

        # Si el usuario es Administrador, puede ver todas las mascotas.
        # Asegúrate de que 'rol' existe en el usuario y tiene un 'nombre'.
        if user.is_authenticated and hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Administrador':
            return Mascota.objects.all()

        # Si el usuario es Propietario o Inquilino (Residente), solo puede ver sus propias mascotas.
        # Las mascotas están asociadas a un Residente, y un Residente está asociado a un Usuario.
        if user.is_authenticated and hasattr(user, 'rol') and user.rol and user.rol.nombre in ['Propietario', 'Inquilino']:
            # Filtra las mascotas que pertenecen a Residentes cuyo campo 'usuario' es el usuario actual.
            return Mascota.objects.filter(dueno__usuario=user)
        
        # Para cualquier otro rol o si el usuario no tiene un rol relevante, no mostramos mascotas.
        return Mascota.objects.none() # Devuelve un queryset vacío si no se cumplen las condiciones

class VehiculoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer  # Para GET, POST, PUT, DELETE normales
    permission_classes = [IsAuthenticated] # Ensures only logged-in users can access

    def get_queryset(self):
        user = self.request.user

        # Administrators can view all vehicles
        if user.is_authenticated and hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Administrador':
            return Vehiculo.objects.all()

        # Owners can only view vehicles associated with their houses
        if user.is_authenticated and hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Propietario':
            # Get IDs of houses owned by the current user
            owned_house_ids = Propiedad.objects.filter(propietario=user, activa=True).values_list('casa__id', flat=True)
            # Filter vehicles that are associated with these houses
            return Vehiculo.objects.filter(casa__id__in=owned_house_ids)
        
        # If the user is neither Admin nor Owner, or doesn't have a role, return an empty queryset
        return Vehiculo.objects.none()

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

class ComunicadoViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    queryset = Comunicado.objects.all().order_by('-fecha_publicacion', '-fecha_creacion')
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Administradores siempre ven todos los comunicados, independientemente del estado.
        if user.is_authenticated and hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Administrador':
            return Comunicado.objects.all().order_by('-fecha_publicacion', '-fecha_creacion')

        # Para usuarios no administradores:
        # 1. Filtramos los comunicados que están 'publicado' y que no han expirado.
        base_queryset = Comunicado.objects.filter(
            estado='publicado',
            fecha_publicacion__isnull=False # Asegura que esté publicado
        ).filter( # <---  Moved Q objects to a separate .filter() call
            models.Q(fecha_expiracion__isnull=True) | models.Q(fecha_expiracion__gte=timezone.now())
        )

        # 2. Comunicados generales (casa_destino es nulo)
        # Estos deben ser visibles para TODOS los propietarios.
        # Identificamos si el usuario actual es un 'Propietario'.
        if user.is_authenticated and hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Propietario':
            general_comunicados = base_queryset.filter(casa_destino__isnull=True)
        else:
            # Otros roles (inquilinos, personal, etc.) no ven comunicados generales
            # a menos que estén asociados a una casa específica.
            general_comunicados = Comunicado.objects.none() # Vacío para otros roles

        # 3. Comunicados específicos para las casas del usuario.
        #    a) Casas donde el usuario es un propietario activo.
        casas_propietario_ids = Propiedad.objects.filter(
            propietario=user,
            activa=True
        ).values_list('casa__id', flat=True)

        #    b) Casas donde el usuario es un residente.
        casas_residente_ids = Residente.objects.filter(
            usuario=user
        ).values_list('casa__id', flat=True)

        # Combina los IDs de todas las casas relevantes y elimina duplicados
        todas_las_casas_ids = list(set(list(casas_propietario_ids) + list(casas_residente_ids)))

        # Filtrar comunicados dirigidos a estas casas específicas
        if todas_las_casas_ids:
            specific_comunicados = base_queryset.filter(
                casa_destino__id__in=todas_las_casas_ids
            )
        else:
            specific_comunicados = Comunicado.objects.none()

        # Combina ambos querysets y elimina duplicados
        # El operador '|' entre querysets realiza un UNION.
        final_queryset = (general_comunicados | specific_comunicados).distinct()

        return final_queryset.order_by('-fecha_publicacion', '-fecha_creacion')

from .models import ConceptoPago, Cuota, Pago
from .serializers import ConceptoPagoSerializer, CuotaSerializer, PagoSerializer

class ConceptoPagoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = ConceptoPago.objects.all()
    serializer_class = ConceptoPagoSerializer
    permission_classes = [IsAuthenticated]  # Solo autenticados
    # Opcional: solo administradores pueden crear/editar
    # permission_classes = [IsAdministrador]


class CuotaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Cuota.objects.select_related('concepto', 'casa').all()
    serializer_class = CuotaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['casa', 'estado', 'concepto', 'periodo']

   
    @action(detail=False, methods=['get'], url_path='mis-cuotas', permission_classes=[IsAuthenticated])
    def mis_cuotas(self, request):
        """
        Permite a un usuario (propietario o residente) ver las cuotas asignadas a sus casas.
        """
        user = request.user

    # Obtener las casas de las que el usuario es propietario activo
        casas_propietario_ids = Propiedad.objects.filter(propietario=user, activa=True).values_list('casa__id', flat=True)

    # Obtener las casas en las que el usuario es residente
        casas_residente_ids = Residente.objects.filter(usuario=user).values_list('casa__id', flat=True)
    
    # Combinar ambas listas de IDs de casas y eliminar duplicados
        todas_las_casas_ids = list(set(list(casas_propietario_ids) + list(casas_residente_ids)))

        if not todas_las_casas_ids:
        # 👇 RETORNAMOS 200 CON MENSAJE Y LISTA VACÍA
            return Response({
                "message": "No tienes casas asociadas para ver cuotas.",
                "results": []
            }, status=status.HTTP_200_OK)

    # Filtrar cuotas que estén relacionadas con cualquiera de las casas del usuario
        queryset = self.filter_queryset(self.get_queryset().filter(casa__id__in=todas_las_casas_ids))
    
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
 
    

class PagoViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    queryset = Pago.objects.select_related('usuario').all() # Optimized queryset
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def crear_sesion_stripe(self, request):
        """
        Crea una sesión de Stripe Checkout para pagar una cuota o reserva.
        Espera: tipo_objeto (cuota/reserva), objeto_id, success_url, cancel_url
        """
        tipo_objeto = request.data.get('tipo_objeto')  # 'cuota' o 'reserva'
        objeto_id = request.data.get('objeto_id')
        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')

        if not all([tipo_objeto, objeto_id, success_url, cancel_url]):
            return Response({"error": "Faltan parámetros."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Obtener el objeto relacionado
            if tipo_objeto == 'cuota':
                objeto = Cuota.objects.get(id=objeto_id)
                nombre_producto = f"Cuota {objeto.concepto.nombre} - {objeto.periodo.strftime('%Y-%m')}"
                monto = int(objeto.monto * 100)  # Stripe usa centavos
            elif tipo_objeto == 'reserva':
                objeto = Reserva.objects.get(id=objeto_id)
                nombre_producto = f"Reserva {objeto.area_comun.nombre} - {objeto.fecha}"
                monto = int(objeto.area_comun.costo_alquiler * 100)
            else:
                return Response({"error": "Tipo de objeto no soportado."}, status=status.HTTP_400_BAD_REQUEST)

            # Crear sesión de Stripe
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',  # o tu moneda local, ej: 'mxn', 'pen', 'cop'
                        'product_data': {
                            'name': nombre_producto,
                        },
                        'unit_amount': monto,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'tipo_objeto': tipo_objeto,
                    'objeto_id': str(objeto_id),
                    'usuario_id': str(request.user.id),
                }
            )

            return Response({
                'id': session.id,
                'url': session.url
            })

        except (Cuota.DoesNotExist, Reserva.DoesNotExist):
            return Response({"error": "Objeto no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# views.py (añade esta vista)


# views.py (dentro de tu archivo de vistas)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    if not sig_header:
        logger.warning("Webhook de Stripe recibido sin firma. Payload: %s", payload.decode())
        return HttpResponse(status=400)

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        logger.error("Error de ValueError en Stripe Webhook: %s", e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error("Error de SignatureVerificationError en Stripe Webhook: %s", e)
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error desconocido al construir evento de Stripe: {e}")
        return HttpResponse(status=500)


    # Manejar el evento
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        logger.info(f"Stripe Checkout Session Completed: {session.id}")

        # Obtener metadata
        metadata = session.get('metadata', {})
        tipo_objeto = metadata.get('tipo_objeto')
        objeto_id = metadata.get('objeto_id')
        usuario_id = metadata.get('usuario_id')

        if not all([tipo_objeto, objeto_id, usuario_id]):
            logger.warning("Metadata incompleta en webhook de Stripe para session %s: %s", session.id, metadata)
            return HttpResponse(status=400)

        try:
            usuario = Usuario.objects.get(id=usuario_id)
            monto = session['amount_total'] / 100  # convertir de centavos a unidades
            stripe_payment_id = session.get('payment_intent', session['id'])

            # Intentamos encontrar un Pago existente con esta referencia para evitar duplicados
            # Esto es una capa de seguridad adicional por si un webhook se envía dos veces
            existing_pago = Pago.objects.filter(referencia=stripe_payment_id, usuario=usuario).first()

            if existing_pago:
                logger.info(f"Pago duplicado detectado para referencia {stripe_payment_id}. Ignorando.")
                # Si ya existe, nos aseguramos de que el estado del objeto relacionado sea correcto
                if tipo_objeto == 'cuota' and existing_pago.content_object and existing_pago.content_object.estado != 'pagada':
                    existing_pago.content_object.estado = 'pagada'
                    existing_pago.content_object.save()
                elif tipo_objeto == 'reserva' and existing_pago.content_object and existing_pago.content_object.estado != 'confirmada':
                    existing_pago.content_object.estado = 'confirmada'
                    existing_pago.content_object.save()
                return HttpResponse(status=200) # Ya procesado


            # Crear el Pago
            pago = Pago.objects.create(
                usuario=usuario,
                tipo_pago=tipo_objeto,
                monto=monto,
                metodo_pago='tarjeta',
                referencia=stripe_payment_id,
                fecha_pago=timezone.now(),
            )

            # Asociar el objeto relacionado y actualizar su estado
            if tipo_objeto == 'cuota':
                cuota = Cuota.objects.get(id=objeto_id)
                pago.content_object = cuota
                cuota.estado = 'pagada'  # ¡Actualizar el estado de la cuota!
                cuota.save() # ¡Guardar la cuota con el nuevo estado!
            elif tipo_objeto == 'reserva':
                reserva = Reserva.objects.get(id=objeto_id)
                pago.content_object = reserva
                reserva.estado = 'confirmada' # ¡Actualizar el estado de la reserva!
                reserva.save() # ¡Guardar la reserva con el nuevo estado!
            else:
                logger.warning(f"Tipo de objeto no soportado en webhook: {tipo_objeto} para session {session.id}")
                # Si el tipo no es soportado, podríamos eliminar el pago creado o marcarlo para revisión
                pago.delete() # Eliminar el pago si el tipo de objeto no es válido
                return HttpResponse(status=400)
            
            # ¡Guardar el pago después de asignar content_object!
            pago.save() 

            logger.info(f"Pago registrado correctamente: ID {pago.id} para {tipo_objeto} {objeto_id}")

        except Usuario.DoesNotExist:
            logger.error(f"Usuario no encontrado para session {session.id}: ID {usuario_id}")
            return HttpResponse(status=404)
        except (Cuota.DoesNotExist, Reserva.DoesNotExist) as e:
            logger.error(f"Objeto relacionado no encontrado para session {session.id}: {tipo_objeto} ID {objeto_id}. Error: {e}")
            # Si el pago ya se creó, podrías querer borrarlo o marcarlo para revisión
            if 'pago' in locals() and pago.pk: # Check if pago was created before error
                pago.delete()
            return HttpResponse(status=404)
        except Exception as e:
            logger.error(f"Error al procesar webhook de Stripe para session {session.id}: {e}", exc_info=True)
            # Asegurarse de que el pago no quede huérfano si el content_object falla
            if 'pago' in locals() and pago.pk:
                pago.delete()
            return HttpResponse(status=500)

    # Si el evento no es de checkout.session.completed, o si es un evento que no manejamos
    # aún así respondemos 200 para que Stripe sepa que lo recibimos.
    return HttpResponse(status=200)

class PropiedadesDelPropietarioView(generics.ListAPIView):
    serializer_class = PropiedadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtrar propiedades donde el propietario es el usuario autenticado
        return Propiedad.objects.filter(propietario=self.request.user, activa=True)
        # Opcional: agregar "activa=True" si solo quieres las propiedades actuales




# ... (tus imports existentes)
from .models import PerfilTrabajador, AsignacionTarea, TareaMantenimiento, Usuario # Asegúrate de importar PerfilTrabajador y AsignacionTarea
from .serializers import PerfilTrabajadorSerializer, AsignacionTareaSerializer
from rest_framework.permissions import IsAdminUser # Podrías usar IsAdministrador que ya tienes
from rest_framework.exceptions import PermissionDenied


# --- ViewSet para PerfilTrabajador ---
class PerfilTrabajadorViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    # Optimizado para evitar N+1 queries al traer el usuario y su rol, y el supervisor y su rol
    queryset = PerfilTrabajador.objects.select_related('usuario__rol', 'supervisor__rol').all()
    serializer_class = PerfilTrabajadorSerializer
    permission_classes = [IsAuthenticated] # Solo usuarios autenticados pueden acceder

    # Filtros opcionales si necesitas buscar por campos específicos
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        user = self.request.user
        # Si es Administrador, puede ver todos los perfiles de trabajador
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            return super().get_queryset()
        
        # Un trabajador solo puede ver su propio perfil
        if user.is_authenticated and PerfilTrabajador.objects.filter(usuario=user).exists():
            return super().get_queryset().filter(usuario=user)
        
        # Otros roles no ven perfiles de trabajador (o se podría permitir ver perfiles activos públicos)
        return PerfilTrabajador.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        # Solo administradores pueden crear perfiles de trabajador
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            serializer.save()
        else:
            raise PermissionDenied("Solo los administradores pueden crear perfiles de trabajador.")

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        # Los administradores pueden actualizar cualquier perfil
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            serializer.save()
        # Un trabajador solo puede actualizar su propio perfil y solo ciertos campos
        elif user.is_authenticated and instance.usuario == user:
            # Aquí podrías limitar qué campos puede actualizar un trabajador.
            # Por ejemplo, no permitir que cambie su 'activo' o 'salario'.
            # Para simplificar, le dejamos actualizar todos los campos permitidos por el serializer,
            # pero es una buena práctica ser más restrictivo.
            if 'activo' in serializer.validated_data and serializer.validated_data['activo'] != instance.activo:
                raise PermissionDenied("Un trabajador no puede cambiar su propio estado de activo.")
            if 'salario' in serializer.validated_data and serializer.validated_data['salario'] != instance.salario:
                raise PermissionDenied("Un trabajador no puede cambiar su propio salario.")
            serializer.save()
        else:
            raise PermissionDenied("No tienes permiso para actualizar este perfil de trabajador.")

    def perform_destroy(self, instance):
        user = self.request.user
        # Solo administradores pueden eliminar perfiles de trabajador
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            instance.delete()
        else:
            raise PermissionDenied("Solo los administradores pueden eliminar perfiles de trabajador.")


# --- ViewSet para AsignacionTarea ---
class AsignacionTareaViewSet(BitacoraLoggerMixin, viewsets.ModelViewSet):
    # Optimizado para evitar N+1 queries al traer tarea, trabajador (y su usuario) y asignado_por (y su usuario)
    queryset = AsignacionTarea.objects.select_related(
        'tarea', 'trabajador__usuario', 'asignado_por'
    ).all()
    serializer_class = AsignacionTareaSerializer
    permission_classes = [IsAuthenticated] # Ajusta según tus necesidades de permisos

    # Filtros para facilitar la búsqueda
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tarea', 'trabajador', 'estado_asignacion', 'fecha_asignacion']

    def get_queryset(self):
        user = self.request.user
        # Los administradores ven todas las asignaciones
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            return super().get_queryset()
        
        # Un trabajador ve las tareas que le han sido asignadas
        if user.is_authenticated and PerfilTrabajador.objects.filter(usuario=user).exists():
            trabajador_perfil = PerfilTrabajador.objects.get(usuario=user)
            return super().get_queryset().filter(trabajador=trabajador_perfil)
        
        # Otros roles no ven asignaciones o podrías dar acceso limitado
        return AsignacionTarea.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        # Solo los administradores pueden crear asignaciones
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            serializer.save(asignado_por=user) # Asegura que el usuario autenticado es quien asigna
        else:
            raise PermissionDenied("Solo los administradores pueden crear asignaciones de tareas.")

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        
        # Los administradores pueden actualizar cualquier asignación
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            serializer.save()
        # Un trabajador asignado solo puede cambiar el estado a 'completada'
        elif user.is_authenticated and instance.trabajador.usuario == user:
            if 'estado_asignacion' in serializer.validated_data and serializer.validated_data['estado_asignacion'] == 'completada':
                # Permitir la actualización del estado a 'completada'
                serializer.save()
            else:
                raise PermissionDenied("Solo puedes marcar tu propia asignación como 'completada'.")
        else:
            raise PermissionDenied("No tienes permiso para actualizar esta asignación de tarea.")

    def perform_destroy(self, instance):
        user = self.request.user
        # Solo administradores pueden eliminar asignaciones
        if user.is_authenticated and user.rol and user.rol.nombre == 'Administrador':
            instance.delete()
        else:
            raise PermissionDenied("Solo los administradores pueden eliminar asignaciones de tareas.")