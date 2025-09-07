
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf.urls import handler404
from .views import  (RolViewSet, UsuarioViewSet, TelefonoViewSet, AdministradorViewSet,
        PersonalViewSet, ClienteViewSet,MyTokenObtainPairView,LogoutView
        )

router = DefaultRouter()
router.register(r"roles", RolViewSet)
router.register(r"usuarios", UsuarioViewSet)
router.register(r"administradores", AdministradorViewSet)
router.register(r"personal", PersonalViewSet)
router.register(r"clientes", ClienteViewSet)
router.register(r"telefonos", TelefonoViewSet)
urlpatterns = [
    path("", include(router.urls)),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]
    