
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf.urls import handler404
from .views import  (RolViewSet, UsuarioViewSet, TelefonoViewSet, AdministradorViewSet,
        PersonalViewSet,MyTokenObtainPairView,LogoutView,GroupViewSet,AuthPermissionViewSet,
        PropietarioViewSet, InquilinoViewSet, CasaViewSet, ResidenteViewSet,
    AreaComunViewSet, ReservaViewSet, PagoReservaViewSet, TareaMantenimientoViewSet,
    BitacoraViewSet, DetalleBitacoraViewSet, MascotaViewSet, VehiculoViewSet,ComunicadoViewSet,ConceptoPagoViewSet,
    CuotaViewSet,PagoViewSet
        )

router = DefaultRouter()
router.register(r"roles", RolViewSet)
router.register(r"usuarios", UsuarioViewSet)
router.register(r"administradores", AdministradorViewSet)
router.register(r"personal", PersonalViewSet)
router.register(r"telefonos", TelefonoViewSet)
router.register(r'grupos',        GroupViewSet,        basename='grupos')
router.register(r'auth-permisos', AuthPermissionViewSet, basename='auth-permisos')
router.register(r'propietarios', PropietarioViewSet)
router.register(r'inquilinos', InquilinoViewSet)
router.register(r'casas', CasaViewSet, basename='casa')
router.register(r'residentes', ResidenteViewSet)
router.register(r'areas-comunes', AreaComunViewSet)
router.register(r'reservas', ReservaViewSet)
router.register(r'pagos-reservas', PagoReservaViewSet)
router.register(r'tareas-mantenimiento', TareaMantenimientoViewSet)
router.register(r'bitacoras', BitacoraViewSet)
router.register(r'detalle-bitacoras', DetalleBitacoraViewSet)
router.register(r'mascotas', MascotaViewSet)
router.register(r'vehiculos', VehiculoViewSet)
router.register(r'comunicados', ComunicadoViewSet, basename='comunicado')  # 👈 AGREGA ESTO
# urls.py — Dentro de la sección del router

router.register(r'conceptos-pago', ConceptoPagoViewSet, basename='concepto-pago')
router.register(r'cuotas', CuotaViewSet, basename='cuota')
router.register(r'pagos', PagoViewSet, basename='pago')
urlpatterns = [
    path("", include(router.urls)),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]
    