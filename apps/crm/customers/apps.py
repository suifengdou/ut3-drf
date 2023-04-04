from django.apps import AppConfig


class CustomersConfig(AppConfig):
    defualt_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.crm.customers'

