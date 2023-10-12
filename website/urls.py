from django.urls import path
from .views import *

urlpatterns = [
    path("admin_home",view=admin_home,name='admin_home')
]