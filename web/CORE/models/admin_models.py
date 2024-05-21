from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from CRM_CORE.models import User, Partner
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


class PartnerSettings(models.Model):
    """
    Настройки парка
    """
    # qiwi_api_key = models.CharField(max_length=255, verbose_name='Ключ API', blank=True, null=True)  # TODO DEL
    periodic_top_up = models.BooleanField(default=False, verbose_name='Периодическое продление')
    periodic_top_up_value = models.IntegerField(default=0, blank=True, null=True, verbose_name='Сумма Периодического '
                                                                                               'продления')
    inactive_top_up = models.BooleanField(default=False, verbose_name='Автоматическое продление при не активности')
    inactive_top_up_period = models.IntegerField(default=0, blank=True, null=True, verbose_name='Период продления по '
                                                                                                'не активности')
    inactive_top_up_value = models.IntegerField(default=0, blank=True, null=True, verbose_name='Сумма продления по '
                                                                                               'не активности')
    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name='settings')


    driving_accuracy_monitoring = models.BooleanField(default=False, verbose_name='Мониторинг качества вождения')
    DAM_speed_limit = models.FloatField(default=0, blank=True, null=True, verbose_name='Ограничение скорости')
    DAM_angle_speed_limit = models.FloatField(default=0, blank=True, null=True, verbose_name='Ограничение угловой'
                                                                                             ' скорости (в градусах/c)')
    DAM_acceleration_limit = models.FloatField(default=0, blank=True, null=True, verbose_name='Ограничение ускорения')

    external_api_key = models.CharField(max_length=64, default='')

    balance_blocking = models.BooleanField(default=False)
    use_acquiring = models.BooleanField(default=False)

    use_bitrix_hooks = models.BooleanField(default=False)
    bitrix_base_url = models.URLField(default=None, blank=True, null=True)
    bitrix_list_id = models.IntegerField(default=None, blank=True, null=True)
    bitrix_fields = models.JSONField(default=dict({'car_number': None, 'location': None, 'type': None, 'mileage': None}))

    map_default_lon = models.FloatField(default=37.617617)
    map_default_lat = models.FloatField(default=55.755799)
    map_default_zoom = models.FloatField(default=8)

    aggregator_add_latest_to_car = models.BooleanField(default=False)

    geozone_phone_number = models.CharField(max_length=20, verbose_name='Номер телефона увед. геозоны', null=True,
                                            blank=True, default=None)
    geozone_engine_stop_safe = models.BooleanField(default=False)
    # TODO phone validator

    def __str__(self):
        return self.partner.name

