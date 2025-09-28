"""
URL configuration for drf_p1_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from rest_framework.exceptions import NotFound  # ← excepción DRF
from django.conf.urls import handler404
from django.http import JsonResponse

from django.contrib import admin
from django.urls import path,include


urlpatterns = [
        path('admin/', admin.site.urls),
        path("api/", include("app.urls")),

        

]
def api_handler_404(request, exception=None):
    if request.path.startswith("/api/"):
        exc = NotFound()  # detail="Not found.", default_code="not_found"
        return JsonResponse(
            {
                "error": {
                    "message": "Endpoint no encontrado",
                    "code": exc.default_code.upper(),  # usa mismo formato que exceptions.py
                    "fields": {}
                }
            },
            status=404
        )

    from django.views.defaults import page_not_found
    return page_not_found(request, exception, template_name="404.html")

handler404 = "drf_p1_backend.urls.api_handler_404"
