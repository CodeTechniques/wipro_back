from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/properties/', include('properties.urls')),
    path("api/", include("wallet.urls")),
    path('api/investments/', include('investments.urls')),
    path('api/loans/', include('loans.urls')),
    path('api/', include('notifications.urls')),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/", include("committees.urls")),



    # Add other API routes here
]


# Serve media files in development
