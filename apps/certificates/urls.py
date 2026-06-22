from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    path('download/<uuid:certificate_uuid>/', views.download_certificate, name='download_certificate'),
    path('verify/<uuid:certificate_uuid>/', views.verify_certificate, name='verify_certificate'),
]
