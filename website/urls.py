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
    path('forecast_tabular/',view=forecast_tabular,name='forecast_tabular'),
    path('forecast_warning',view=forecast_warning,name='forecast_warning'),
    path('warning',view=warnings,name='warning'),
    path('overview',view=overview,name='overview'),



    # ajax data
    path('get_overview_data',get_overview_data,name='get_overview_data'),
    path('get_sites',get_sites,name='get_sites'),
    path('get_homepage_data',get_homepage_data,name='get_homepage_data'),
    path('get_forecast_table',get_forecast_table,name='get_forecast_table'),
    path('get_fw_data',get_fw_data,name='get_fw_data'),
    path('get_warnings_data',get_warnings_data,name='get_warnings_data'),
    path('get_homepage_graph_data/',update_on_site_change,name='get_homepage_graph_data')

]