from django.shortcuts import render
from rest_framework.decorators import action
from .permissions import IsAdministrador, IsCliente,IsPersonal

from rest_framework.parsers import JSONParser
from rest_framework import viewsets,status
from  django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

import logging
logger = logging.getLogger(__name__)
from rest_framework import viewsets
from .models import (
    Rol, Usuario, Telefono, Administrador, Personal, Cliente,
    Bitacora
)
from .serializers import (
    RolSerializer, UsuarioSerializer, TelefonoSerializer, 
    AdministradorSerializer, PersonalSerializer,LogoutSerializer, ClienteSerializer,MyTokenPairSerializer
)
from rest_framework.permissions import IsAuthenticated

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    # Puedes añadir permisos aquí si necesitas restringir el acceso
    # permission_classes = [IsAuthenticated]

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
        serializer = self.get_serializer(request.user)
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

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
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
    
