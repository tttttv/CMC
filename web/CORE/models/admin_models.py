from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

import datetime

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(blank=True, null=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    first_name = models.CharField(max_length=50, blank=True, null=True, default=None)
    last_name = models.CharField(max_length=50, blank=True, null=True, default=None)
    middle_name = models.CharField(max_length=50, blank=True, null=True, default=None)

    objects = UserManager()

    def __str__(self):
        return 'Пользователь ' + self.email

    def __repr__(self):
        return self.__str__()

    def get_string(self):
        return self.__str__()


