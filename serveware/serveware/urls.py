from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from accounts import views as account_views
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', views.healthz, name='healthz'),
    path('debug/fail/', views.simulate_error, name='simulate_error'),
    path('', include('django_prometheus.urls')),  # exposes /metrics
    path('', account_views.home, name='home'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('restaurant/', include('restaurant.urls', namespace='restaurant')),
    path('customer/', include('customer.urls', namespace='customer')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}, name='media'),
]
