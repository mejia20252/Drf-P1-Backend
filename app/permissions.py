# permissions.py

# permissions.py
from rest_framework.permissions import DjangoModelPermissions
from rest_framework import permissions
class RoleBasedPermission(DjangoModelPermissions):
    """
    Extiende DjangoModelPermissions para verificar permisos CRUD:
    - view_model
    - add_model
    - change_model
    - delete_model
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

class IsAdministrador(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

class IsPropietario(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Propietario'

class IsPersonal(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Personal'        