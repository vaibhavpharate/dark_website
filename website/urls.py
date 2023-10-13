from django.urls import path
from .views import *

urlpatterns = [
    path("admin_home",view=admin_home,name='admin_home'),
    path('create_client',view=create_client,name='create_client'),

    path('client_login',view=client_login,name='client_login'),
    path('admin_login',view = admin_login,name='admin_login'),
    path('admin_logout',view=admin_logout,name='admin_logout'),
    path('client_logout',view=client_logout,name='client_logout'),
    path('homepage',view=homepage,name='homepage'),
    path('forecast_tabular',view=forecast_tabular,name='forecast_tabular'),



    # ajax data
    path('get_overview_data',get_overview_data,name='get_overview_data'),
    path('get_sites',get_sites,name='get_sites'),
    path('get_homepage_data',get_homepage_data,name='get_homepage_data'),
    path('get_forecast_table',get_forecast_table,name='get_forecast_table')

]