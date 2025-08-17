"""
URL configuration for edustream project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="EduStream API",
        default_version='v1',
        description="API documentation for EduStream VR Learning Platform",
        terms_of_service="https://www.edustream.com/terms/",
        contact=openapi.Contact(email="support@edustream.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/', include('accounts.urls', namespace='accounts')),
    path('api/courses/', include('courses.urls', namespace='courses')),
    path('api/classes/', include('classes.urls', namespace='classes')),
    path('api/payments/', include('payments.urls', namespace='payments')),
    path('api/recordings/', include('recordings.urls', namespace='recordings')),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
