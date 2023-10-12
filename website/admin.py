from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import ClientsForm
from django.contrib.auth import get_user_model

from .models import Clients
admin.site.register(get_user_model())