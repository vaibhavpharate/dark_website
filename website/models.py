from django.db import models
from django.contrib.auth.models import AbstractUser

# Importing the manager
from .manager import UserManager


# Create your models here.
class Clients(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CLIENT = "CLIENT", "Client"

    username = models.CharField(max_length=14, unique=True)
    email = models.EmailField(max_length=200,unique=True)
    client_short = models.CharField(max_length=10)
    role_type = models.CharField(max_length=10,choices=Roles.choices,default=Roles.CLIENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    date_updated = models.DateTimeField(auto_now=True)
    logos = models.ImageField(upload_to='client_logos/',default="None")
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

