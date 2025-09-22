
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf.urls import handler404
from .views import  (RolViewSet, UsuarioViewSet, TelefonoViewSet,
      MyTokenObtainPairView,LogoutView,GroupViewSet,AuthPermissionViewSet,
         CasaViewSet, ResidenteViewSet,
    AreaComunViewSet, ReservaViewSet, TareaMantenimientoViewSet,PerfilTrabajadorViewSet, AsignacionTareaViewSet,
    BitacoraViewSet, DetalleBitacoraViewSet, MascotaViewSet, VehiculoViewSet,ComunicadoViewSet,ConceptoPagoViewSet,
    CuotaViewSet,PagoViewSet,PropiedadViewSet, PropiedadesDelPropietarioView,ContratoArrendamientoViewSet
        )

router = DefaultRouter()
router.register(r'contratos-arrendamiento', ContratoArrendamientoViewSet, basename='contrato-arrendamiento')
router.register(r"roles", RolViewSet)
router.register(r'perfiles-trabajador', PerfilTrabajadorViewSet)
router.register(r'asignaciones-tarea', AsignacionTareaViewSet)
router.register(r"usuarios", UsuarioViewSet)
router.register(r"telefonos", TelefonoViewSet, basename="telefono") # Add
router.register(r'grupos',        GroupViewSet,        basename='grupos')
router.register(r'auth-permisos', AuthPermissionViewSet, basename='auth-permisos')
router.register(r'casas', CasaViewSet, basename='casa')
router.register(r'residentes', ResidenteViewSet)
router.register(r'areas-comunes', AreaComunViewSet)
router.register(r'reservas', ReservaViewSet)
router.register(r'tareas-mantenimiento', TareaMantenimientoViewSet)
router.register(r'bitacoras', BitacoraViewSet)
router.register(r'detalle-bitacoras', DetalleBitacoraViewSet)
router.register(r'mascotas', MascotaViewSet)
router.register(r'vehiculos', VehiculoViewSet)
router.register(r'propiedades', PropiedadViewSet)
router.register(r'comunicados', ComunicadoViewSet, basename='comunicado')  
router.register(r'conceptos-pago', ConceptoPagoViewSet, basename='concepto-pago')
router.register(r'cuotas', CuotaViewSet, basename='cuota')
router.register(r'pagos', PagoViewSet, basename='pago')
from .views import stripe_webhook
urlpatterns = [
    path("", include(router.urls)),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('mis-propiedades/', PropiedadesDelPropietarioView.as_view(), name='mis_propiedades'),
    path('stripe-webhook/', stripe_webhook, name='stripe_webhook'),
]
    