"""
Academic Management System — Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Django Admin (superuser interface)
    path('admin/', admin.site.urls),

    # Redirect root to dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),

    # Application URLs
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.core.urls', namespace='core')),
    path('courses/', include('apps.courses.urls', namespace='courses')),
    path('grades/', include('apps.grades.urls', namespace='grades')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('assignments/', include('apps.assignments.urls', namespace='assignments')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = 'Academic Management System'
admin.site.site_title = 'AMS Admin'
admin.site.index_title = 'Welcome to AMS Administration'