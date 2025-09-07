# === Auditoría de acciones en Bitácora ===
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import (
    Bitacora, DetalleBitacora
)
class BitacoraLoggerMixin:
    """
    Mixin para registrar automáticamente acciones del actor (request.user)
    en DetalleBitacora, reusando (o creando) su Bitacora abierta.
    """

    def _current_bitacora(self, request):
        bit = Bitacora.objects.filter(
            usuario=request.user,
            logout__isnull=True
        ).last()
        if bit is None:
            # Abrimos una bitácora mínima para el ACTOR
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None
            device = request.META.get('HTTP_USER_AGENT') or None
            bit = Bitacora.objects.create(
                usuario=request.user,   # ACTOR
                login=timezone.now(),
                ip=ip,
                device=device
            )
        return bit

    def _log(self, request, accion: str, tabla: str):
        bit = self._current_bitacora(request)
        DetalleBitacora.objects.create(
            bitacora=bit,
            accion=accion,
            fecha=timezone.now(),
            tabla=tabla
        )

    def _tabla(self):
        # Usa el nombre de tabla real del modelo (db_table) para consistencia
        try:
            return self.get_queryset().model._meta.db_table
        except Exception:
            return self.__class__.__name__.lower()

    # Hooks para operaciones DRF comunes
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        self._log(request, "LISTAR", self._tabla())
        return resp

    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        self._log(request, "VER_DETALLE", self._tabla())
        return resp

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        self._log(request, "CREAR", self._tabla())
        return resp

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        self._log(request, "EDITAR", self._tabla())
        return resp

    def partial_update(self, request, *args, **kwargs):
        resp = super().partial_update(request, *args, **kwargs)
        self._log(request, "EDITAR_PARCIAL", self._tabla())
        return resp

    def destroy(self, request, *args, **kwargs):
        resp = super().destroy(request, *args, **kwargs)
        self._log(request, "ELIMINAR", self._tabla())
        return resp
# === fin mixin ===