from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

# processing
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
# from pandas.core import SettingWithCopyWarning
pd.options.mode.chained_assignment = None
# files processing
import os

## User Login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import  csrf_protect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Permission
from django.contrib import messages
from django.contrib.auth.models import Group
from django.conf import settings as django_settings

# py data plots
from plotly import express as px
from plotly.utils import PlotlyJSONEncoder as enc_pltjson
from plotly import graph_objs as go
from plotly.subplots import make_subplots

# Database Connections
from django.db import connections
from django.http import JsonResponse
from django.conf import settings

# Getting Models
from .models import Clients
# Clients Form
from .forms import ClientsForm

# tokens = settings.mapbox_token
User = get_user_model()
token = settings.MAPBOX_TOKEN
px.set_mapbox_access_token(token)
# data_file_path = os.path.join(django_settings.STATICFILES_DIRS[0],'data')
data_file_path = 'static/data'
date_format = '%Y-%m-%d %H:%M:%S'
# Create your views here.


# Get the Connection
def get_connection():
    connection1 = connections['dashboarding'].cursor()
    return connection1


# get the json response through Pandas dataframe
def get_json_response(df: pd.DataFrame):
    json_records = df.reset_index().to_json(orient='records')
    data = json.loads(json_records)
    return data


# query Executor
def get_sql_data(query):
    connection1 = get_connection()
    with connection1 as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
        columns = cursor.description
        column = []
        for col in columns:
            column.append(col.name)
        df = pd.DataFrame(result, columns=column)
        # print(df)
        cursor.close()
        return df


def get_site_client(client_name=None, type=None):
    # client_name = client_name.title()

    if client_name == None:
        df = get_sql_data(
            "select sc.site_name,sc.client_name from configs.site_config sc WHERE sc.type='Solar' and sc.site_status='Active'")
        return df
    else:
        df = get_sql_data(
            f"select sc.site_name,sc.client_name from configs.site_config sc where client_name= '{client_name}' "
            f"AND sc.type='{type}' and sc.site_status='Active' order by sc.site_name  ")
        return df


def convert_data_to_json(df: pd.DataFrame):
    json_records = df.reset_index().to_json(orient='records')
    data = json.loads(json_records)
    return data

@csrf_protect
def admin_login(request):
    form = AuthenticationForm()
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect("admin_home")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    context = {'admin_form': form}
    return render(request, template_name='website/admin_login.html', context=context)


def client_login(request):
    form = AuthenticationForm()
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect("homepage")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    context = {'client_form': form}
    return render(request, template_name='website/client_login.html', context=context)


def admin_logout(request):
    logout(request)
    messages.warning(request, "You have successfully logged out.")
    return redirect('admin_login')


def client_logout(request):
    username = request.user.username
    
    if check_data_store(request):
        os.remove(f'{settings.MEDIA_ROOT}/data/{username}.csv')
    logout(request)
    messages.warning(request, "You have successfully logged out.")
    return redirect('client_login')


def admin_home(request):
    return render(request=request, template_name='website/admin_home.html')


@login_required(login_url='admin_login')
def create_client(request):
    form = ClientsForm()
    if request.method == "POST":
        form = ClientsForm(request.POST, request.FILES)
        if form.is_valid():
            group_data = form.cleaned_data['role_type']
            # print(form.cleaned_data['role_type'])
            user = form.save()
            # Save admins to admin group
            client_group = Group.objects.get(name='Client')
            admin_group = Group.objects.get(name='Admin')
            if group_data == "CLIENT":
                user.groups.add(client_group)
            elif client_group == "ADMIN":
                user.groups.add(admin_group)
                list_perms = ['Can add user', 'Can change user', 'Can delete user', 'Can view user']
                for x in list_perms:
                    permission = Permission.objects.get(name=x)
                    user.user_permissions.add(permission)
            messages.success(request, "Client Successfully Added")
            return redirect('create_client')
        else:
            messages.warning(request, "There was an error in the Form")
    context = {'form': form}
    return render(request=request, template_name='website/create_client.html', context=context)


def get_data_store(username):
    date = datetime.now().date() - timedelta(days=10)
    print("Date is")
    print(date)
    date = datetime.strftime(date,'%Y-%m-%d 00:00:00')
    sites = get_site_client(client_name=username, type='Solar')
    sites = tuple(sites)
    # print(data_file_path)
    query = f"""SELECT vda.site_name,
                                vda.timestamp,
                               vda.wind_speed_10m_mps AS wind_speed_forecast,
                               vda.wind_direction_in_deg AS wind_direction_forecast,
                               vda.temp_c  AS temp_forecast,
                               vda.nowcast_ghi_wpm2   AS ghi_forecast,
                               vda.ct_flag_data AS "Cloud Description",
                               vda.ci_data AS "forecast_cloud_index",
                               vda.ct_data AS "forecast_cloud_type",
                               vda.forecast_method,
                               conf.client_name AS site_client_name,
                               conf.site_status AS site_status,
                               conf.latitude as site_lat,
                               conf.longitude as site_lon,
                               sa."ghi(w/m2)" AS ghi_actual,
                               sa."temp(c)"   AS temp_actual,
                               sa.ws          AS wind_speed_actual,
                               sa.wd          AS wind_direction_actual,
                               conf.type
                        FROM forecast.v_db_api vda
                                 JOIN configs.site_config conf ON vda.site_name = conf.site_name
                                 LEFT JOIN site_actual.site_actual sa on (vda.timestamp,vda.site_name) = (sa.timestamp,sa.site_name)
                        WHERE vda.timestamp >= '{date}' AND conf.client_name = '{username}' 
                        AND conf.type='Solar'  ORDER BY vda.timestamp desc"""

    df = get_sql_data(query)
    df.to_csv(f"{settings.MEDIA_ROOT}/data/{username}.csv",index=False)

    
    return f"Data Store created for {username} for date {date}"

def check_data_store(request):
    username = request.user.username
    # return os.path.exists(os.path.join(data_file_path,f'{username}.csv'))
    return os.path.exists(f'{settings.MEDIA_ROOT}/data/{username}.csv')


@login_required(login_url='client_login')
def homepage(request):
    context = {}
    if not check_data_store(request):
        print(get_data_store(request.user.username))
    print(check_data_store(request))
    return render(request, template_name='website/homepage.html', context=context)


@login_required(login_url='client_login')
def overview(request):
    context = {}
    if not check_data_store(request):
        print(get_data_store(request.user.username))
    return render(request, template_name='website/overview.html', context=context)

@login_required(login_url='client_login')
def get_overview_data(request):
    if request.method == "GET":
        username = request.GET['username']
        group = request.GET['group']
        type = request.GET['type']
        if group == "Client":
            sites_df = get_site_client(client_name=username, type=type)
            sites_tuple = tuple(sites_df['site_name'])
            df_act = get_sql_data(f"""SELECT max(timestamp) timestamp_actual,site_name from site_actual.site_actual 
                where site_name in {sites_tuple} group by site_name order by timestamp_actual desc""")
            df_fcst = get_sql_data(f"""SELECT max(timestamp) timestamp_forecast,site_name from forecast.v_db_api where 
                site_name in {sites_tuple} group by site_name order by timestamp_forecast desc""")
            df_config = get_sql_data(f"""select site_name,client_name,state,capacity,site_status from 
            configs.site_config where site_name in {sites_tuple}""")


        else:
            df_act = get_sql_data(f"""SELECT max(timestamp) timestamp_actual,site_name from site_actual.site_actual 
                             group by site_name order by timestamp_actual desc""")
            df_fcst = get_sql_data(f"""SELECT max(timestamp) timestamp_forecast,site_name from forecast.v_db_api 
            group by site_name order by timestamp_forecast desc""")
            df_config = get_sql_data(f"""select site_name,client_name,state,capacity,site_status from 
                        configs.site_config""")

        df_act_fct = pd.merge(df_act, df_fcst, how='outer', on=['site_name'])
        df_c = pd.merge(df_act_fct, df_config, on=['site_name'])

        df_c['client_name'] = df_c['client_name'].fillna('In-House Development')

        df_c['today'] = pd.to_datetime(datetime.today().strftime("%Y-%m-%d %H:%M:%S"))

        df_c['days_till'] = df_c['timestamp_actual'].map(lambda x: datetime.today() - x if pd.notna(x) else None)
        df_c['days_till'] = df_c['days_till'].map(lambda x: x.days if pd.notna(x) else None)

        df_c['timestamp_forecast'] = df_c['timestamp_forecast'].dt.strftime('%d/%m/%Y %H:%M:%S')
        df_c['timestamp_actual'] = df_c['timestamp_actual'].map(
            lambda x: datetime.strftime(x, '%d/%m/%Y %H:%M:%S') if pd.notna(x) else None)
        if group == "Admin":
            send_list = ['site_name', 'client_name', 'site_status', 'state', 'capacity', 'max_date_wrf',
                         'max_actual', 'days_till']
        else:
            send_list = ['site_name', 'site_status', 'state', 'capacity', 'timestamp_forecast',
                         'timestamp_actual', 'days_till']
        df_c.fillna("Not Available", inplace=True)

        df_c = df_c.loc[:, send_list]
        df_c['capacity'] = df_c['capacity'].fillna("None")
        df_c = df_c.loc[df_c['site_status'] == 'Active', :]
        # print(df_c)
        return JsonResponse({'data': df_c.to_dict('records')}, status=200, safe=False)


@login_required(login_url='client_login')
def get_sites(request):
    if request.method == "GET":
        username = request.GET['username']
        # username = username.title()
        group = request.GET['group']
        type = request.GET['type']
        df = get_site_client(client_name=username, type=type)
        # sites = ""
        if group == "Admin":
            sites = pd.DataFrame(df['site_name'])
            sites.sort_values('site_name', ascending=True, inplace=True)
        else:
            sites = pd.DataFrame(df.loc[df['client_name'] == username, 'site_name'])
            sites.sort_values('site_name', ascending=True, inplace=True)
        return JsonResponse({'data': sites.to_dict('records')}, status=200)


@login_required(login_url='client_login')
def get_homepage_data(request):
    if request.method == "GET":
        client = request.GET['username']
        # client = client.title()
        client_name = client
        group = request.GET['group']
        type = request.GET['type']
        site_name = request.GET['site_name']
        date_yesterday = datetime.now() -timedelta(days=1)
        yesterday = date_yesterday.date()
        time_string = datetime.strftime(yesterday, '%m-%d-%y %H:%M:%S')
        if group == "Admin":
            query = ""
        else:
        #     query = f"""SELECT vda.site_name, vda.timestamp, vda.wind_speed_10m_mps AS wind_speed_forecast,
        #     vda.wind_direction_in_deg AS wind_direction_forecast, vda.temp_c AS wind_direction_forecast,
        #     vda.nowcast_ghi_wpm2 AS ghi_forecast, vda.swdown2,vda.ci_data AS forecast_cloud_index, vda.tz, vda.ct_data, vda.ct_flag_data,
        #     vda.forecast_method, vda.log_ts, conf.client_name, conf.latitude AS site_lat,
        #     conf.longitude AS site_lon, sa."ghi(w/m2)" AS ghi_actual,
        #     sa."temp(c)" AS temp_actual, sa.ws AS wind_speed_actual, sa.wd AS wind_direction_actual
        #     FROM forecast.v_db_api vda JOIN configs.site_config conf ON vda.site_name = conf.site_name
        #     LEFT JOIN site_actual.site_actual sa on (vda.timestamp,vda.site_name) = (sa.timestamp,sa.site_name)
        #     WHERE conf.client_name = '{client}' AND vda.ci_data IS NOT NULL  AND vda.timestamp > '{time_string}'
        # ORDER BY timestamp DESC"""

            ci_index = 0.1
            # df = get_sql_data(query)
            # df = pd.read_csv(os.path.join(data_file_path,f'{client_name}.csv'))
            df = pd.read_csv(f'{settings.MEDIA_ROOT}/data/{client_name}.csv')

            df = df.rename({'site_client_name':'client_name'},axis='columns')
            # print(df.columns)
            df = df.groupby(['timestamp', 'site_name', 'client_name']).aggregate(
                {'ghi_forecast': 'mean', 'ghi_actual': 'mean', 'forecast_cloud_index': 'mean', 'site_lat': 'mean',
                 'site_lon': 'mean'}).reset_index()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.loc[df['timestamp']>=date_yesterday,:]
            df['C_I_R'] = df['forecast_cloud_index'] * 125
            df['Warning Description'] = None
            df['Warning Category'] = None
            df['Graph Index'] = None
            df.loc[
                (df['forecast_cloud_index'] > 0.1) & (
                        df['forecast_cloud_index'] <= 0.25), "Warning Category"] = "Orange"
            df.loc[df['forecast_cloud_index'] <= 0.1, "Warning Category"] = "Green"
            df.loc[df['forecast_cloud_index'] > 0.25, "Warning Category"] = "Red"
            df.loc[df['forecast_cloud_index'] > 0.1, "Warning Description"] = "Cloud Warning"
            df.loc[df['forecast_cloud_index'] <= 0.1, "Warning Description"] = "No Warning"
            fn1 = df.copy()
            for x in df.loc[:, 'forecast_cloud_index'].index:
                if df['forecast_cloud_index'][x] > ci_index:
                    df['Graph Index'][x] = df[f'ghi_forecast'][x]
            # color_list = ['lightgreen', 'green', 'orange', 'red', 'red', 'red', 'red', 'red', 'crimson', 'crimson',
            #               'crimson']
            color_list = fn1['Warning Category'].str.lower().unique()
            fig = px.scatter_mapbox(fn1, lat='site_lat', lon='site_lon',
                                    size='C_I_R',
                                    hover_name='site_name',
                                    hover_data={'C_I_R': False,
                                                'Warning Category': False,
                                                'forecast_cloud_index': True,
                                                'timestamp': True},
                                    height=350,
                                    size_max=20,
                                    color='Warning Category',
                                    opacity=0.3, zoom=3,
                                    color_discrete_sequence=color_list
                                    )
            fig.add_trace(
                go.Scattermapbox(
                    lat=fn1['site_lat'],
                    lon=fn1['site_lon'],
                    mode='markers+text',
                    text=fn1['site_name'],
                    textposition='bottom center',
                    marker=dict(size=9, color="green"),
                    textfont=dict(size=16, color='blue'),
                    # template='plotly_dark'
                )
            )
            fig.update_layout(showlegend=False)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)',
                              margin={'l': 0, 't': 0, 'b': 0, 'r': 0})
            graphJSON = json.dumps(fig, cls=enc_pltjson)

            variable = 'ghi'

            df_sites = get_site_client(client_name= client_name)
            sites = list(df_sites.loc[df_sites['client_name'] == client, 'site_name'])
            df = df.loc[df['site_name'] == site_name, :]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df[f'{variable}_actual'],
                name=f"{variable.title()} Actual"
            ))
            fig2.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df[f'{variable}_forecast'],
                name=f"{variable.title()} Forecast"
            ))
            fig2.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['Graph Index'],
                    name='Cloud Warning',
                    mode='markers',
                    marker_color='orange',
                    marker_size=10
                )
            )
            fig2.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='grey',color='white')
            fig2.update_xaxes(showgrid=True, gridwidth=0.4, gridcolor='grey',color='white')
            fig2.update_layout(legend_font_color='grey')
            fig2.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                xaxis_title="Timestamp",
                yaxis_title="GHI (W/m2)",
                # legend_title="Legends",

                font=dict(
                    family="Arial",
                    size=15,
                ),
                margin=dict(
                    l=10,
                    r=10,
                    b=10,
                    t=10,
                    pad=1
                ),
            )
            graphJSON2 = json.dumps(fig2, cls=enc_pltjson)
            return JsonResponse({'maps_data': graphJSON, 'graphs_data': graphJSON2}, status=200, safe=False)


@login_required(login_url='client_login')
def forecast_tabular(request):
    if not check_data_store(request):
        print(get_data_store(request.user.username))
    return render(request=request, template_name='website/forecast.html')

@login_required(login_url='client_login')
def get_forecast_table(request):
    if request.method == 'GET':
        username = request.GET['username']
        user_group = request.GET['group']
        # username = username.title()
        # print(request.GET['group'])
        # print(user_group)
        yesterday = datetime.now()
        time_string = datetime.strftime(yesterday, '%m-%d-%y %H:%M:%S')
        if user_group == "Admin":
            query = "SELECT site_client_name, forecast_cloud_index , timestamp, site_name,temp_actual,temp_forecast,ghi_actual" \
                    ",ghi_forecast,wind_speed_actual,wind_speed_forecast,forecast_cloud_type FROM dashboarding.v_final_dashboarding_view WHERE timestamp >= '{time_string}' " \
                    "ORDER BY timestamp DESC LIMIT 10000"
        else:
            query = f"""SELECT vda.site_name,
                                vda.timestamp,
                               vda.wind_speed_10m_mps AS wind_speed_forecast,
                               vda.wind_direction_in_deg AS wind_direction_forecast,
                               vda.temp_c  AS temp_forecast,
                               vda.nowcast_ghi_wpm2   AS ghi_forecast,
                               vda.ct_flag_data AS "Cloud Description",
                               vda.ci_data AS "forecast_cloud_index",
                               vda.ct_data AS "forecast_cloud_type",
                               vda.forecast_method,
                               conf.client_name AS site_client_name,
                               conf.site_status AS site_status,
                               sa."ghi(w/m2)" AS ghi_actual,
                               sa."temp(c)"   AS temp_actual,
                               sa.ws          AS wind_speed_actual,
                               sa.wd          AS wind_direction_actual,
                               conf.type
                        FROM forecast.v_db_api vda
                                 JOIN configs.site_config conf ON vda.site_name = conf.site_name
                                 LEFT JOIN site_actual.site_actual sa on (vda.timestamp,vda.site_name) = (sa.timestamp,sa.site_name)
                        WHERE vda.timestamp >= '{time_string}' AND conf.client_name = '{username}'
                        AND conf.type='Solar'  ORDER BY vda.timestamp desc LIMIT 10000;"""

        # df_4 = get_sql_data(query)
        df_4 = pd.read_csv(f'{settings.MEDIA_ROOT}/data/{username}.csv')
        ci_index = 0.1
        df_4 = df_4.loc[df_4['site_status']=='Active',:]
        df_4['forecast_cloud_type'] = df_4['forecast_cloud_type'].fillna('No Cloud')  ## Old Query
        df_4['Cloud Description'] = df_4['Cloud Description'].str.replace("_", " ").str.title()
        df_4['ghi_actual'] = df_4['ghi_actual'].fillna('None')
        df_4['Warning Description'] = None
        df_4.loc[df_4['forecast_cloud_index'] > 0.1, "Warning Description"] = "Cloud Warning"
        df_4.loc[df_4['forecast_cloud_index'] <= 0.1, "Warning Description"] = "No Warning"


        df_4.fillna("None", inplace=True)
        if user_group == "Admin":
            send_list = ['site_client_name', 'timestamp', 'site_name', 'Cloud Description',
                         'Warning Description', 'temp_forecast', 'temp_actual', 'ghi_forecast',
                         'ghi_actual', 'wind_speed_forecast']
        else:
            send_list = ['timestamp', 'site_name', 'Cloud Description',
                         'Warning Description', 'temp_forecast', 'temp_actual', 'ghi_forecast',
                         'ghi_actual', 'wind_speed_forecast']
        df_4 = df_4.loc[:, send_list]
        return JsonResponse({'data': df_4.to_dict('records')}, status=200, safe=False)

@login_required(login_url='client_login')
def forecast_warning(request):
    if not check_data_store(request):
        print(get_data_store(request.user.username))
    return render(request=request,template_name='website/forecast_warning.html',context={})
@login_required(login_url='client_login')
def get_fw_data(request):
    if request.method == 'GET':
        username = request.GET['username']
        site_name = request.GET['site_name']
        start_date = request.GET['start_date']
        end_date = request.GET['end_date']
        variable = request.GET['variable']

        if len(start_date) > 1:
            start_date = start_date + " 00:00:00"
        if len(end_date) > 1:
            end_date = end_date + " 23:59:59"

        pd_start_date = datetime.strptime(start_date,date_format)
        pd_end_date = datetime.strptime(end_date,date_format)

        query = f"""SELECT vda.site_name, vda.timestamp, vda.wind_speed_10m_mps AS wind_speed_forecast, 
            vda.wind_direction_in_deg AS wind_direction_forecast, vda.temp_c AS temp_forecast, 
            vda.nowcast_ghi_wpm2 AS ghi_forecast, vda.swdown2,vda.ci_data AS forecast_cloud_index, vda.tz, vda.ct_data, vda.ct_flag_data, 
            vda.forecast_method, vda.log_ts, conf.client_name, conf.latitude AS site_lat,
            conf.longitude AS site_lon, sa."ghi(w/m2)" AS ghi_actual, 
            sa."temp(c)" AS temp_actual, sa.ws AS wind_speed_actual, sa.wd AS wind_direction_actual 
            FROM forecast.v_db_api vda JOIN configs.site_config conf ON vda.site_name = conf.site_name 
            LEFT JOIN site_actual.site_actual sa on (vda.timestamp,vda.site_name) = (sa.timestamp,sa.site_name) 
            WHERE conf.site_name = '{site_name}' AND vda.ci_data IS NOT NULL  AND vda.timestamp > '{start_date}' AND vda.timestamp <= '{end_date}'  ORDER BY timestamp DESC"""
        df = pd.read_csv(f'{settings.MEDIA_ROOT}/data/{username}.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'],format=date_format)
        min_date = df.loc[:,'timestamp'].min()
        max_date = df.loc[:,'timestamp'].max()

        ## Do this Later
        # print(pd_start_date < min_date)
        if pd_start_date < min_date or pd_start_date > max_date:
            df = get_sql_data(query)
            print("start date is not in range")
        elif pd_end_date > max_date or pd_end_date < min_date:
            df = get_sql_data(query)
            print("End date is not in range")
        else:
            print("Date in data-stores")
        ci_index = 0.1
        # df = get_sql_data(query)
        df = df.loc[df['site_name']==site_name,:]
        df = df.loc[(df['timestamp']>= pd_start_date) & (df['timestamp']<=pd_end_date),:]

        df = df.groupby(['timestamp']).aggregate(
            {f'{variable}_actual': 'mean', f'{variable}_forecast': 'mean',
             'forecast_cloud_index': 'mean'}).reset_index()
        max_variable =  df[f'{variable}_actual'].max()
        df['Deviation'] = (df[f'{variable}_actual'] - df[f'{variable}_forecast']).abs().div(
            max_variable) * 100
        
        mn = df.loc[df[f'{variable}_actual'] > 0, 'Deviation'].mean()
        # print(f"Mean is {df['Deviation'].mean()}")
        df['color'] = df['Deviation'].map(lambda x: "Green" if x <= mn else "Red")
        df['Graph Index'] = None
        df['Warning Description'] = None
        df['Warning Category'] = None
        df.loc[df['forecast_cloud_index'] > 0.1, "Warning Category"] = "Red"
        df.loc[df['forecast_cloud_index'] <= 0.1, "Warning Category"] = "Green"
        df.loc[df['forecast_cloud_index'] > 0.1, "Warning Description"] = "Cloud Warning"
        df.loc[df['forecast_cloud_index'] <= 0.1, "Warning Description"] = "No Warning"
        for x in df.loc[:, ['forecast_cloud_index', f'{variable}_forecast', 'Warning Description']].index:
            if df['forecast_cloud_index'][x] > ci_index:
                df['Graph Index'][x] = df[f'{variable}_forecast'][x]

        readings = {'ghi': "W/m2", "temp": f"{chr(176)} C", 'wind_speed': "m/s"}
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f'{variable}_actual'],
            name=f"{variable.title()} Actual"
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f'{variable}_forecast'],
            name=f"{variable.title()} Forecast"
        ))
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['Graph Index'],
                name='Cloud Warning',
                mode='markers',
                marker_color='orange',
                marker_size=10
            )
        )
        fig.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='LightGrey')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                          plot_bgcolor='rgba(0,0,0,0)',
                          height=500,
                          xaxis_title="Timestamp",
                          yaxis_title=f"{readings[variable]}",
                          legend_title="Legends",
                          font=dict(
                              family="Arial",
                              size=15,
                          ),
                          margin=dict(
                              l=10,
                              r=10,
                              b=10,
                              t=10,
                              pad=1
                          ),
                          )

        # print(df)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df.loc[df['color'] == 'Green', 'timestamp'],
            y=df.loc[df['color'] == 'Green', 'Deviation'],
            marker_color='green',
            name='Below'
        ))

        fig2.add_trace(go.Bar(
            x=df.loc[df['color'] == 'Red', 'timestamp'],
            y=df.loc[df['color'] == 'Red', 'Deviation'],
            name="Above",
            marker_color="red"

        ))
        fig2.add_hline(y=mn,name='MAE',line_color='LightGrey',line_dash="dot",
              annotation_text=" MAE", 
              annotation_font_size=15,
              annotation_font_color="LightGrey",
              annotation_position="top left")
        fig2.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='LightGrey')
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                           plot_bgcolor='rgba(0,0,0,0)',
                           height=500 / 2,

                           xaxis_title="Timestamp",
                           yaxis_title="Deviation",
                           legend_title="%Deviation",
                           font=dict(
                               family="Arial",
                               size=15,
                           ),
                           margin=dict(
                               l=10,
                               r=10,
                               b=10,
                               t=10,
                               pad=1
                           ),
                           )

        fig.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig.update_xaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig.update_layout(legend_font_color='grey')
        fig2.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig2.update_xaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig2.update_layout(legend_font_color='grey')
        graphJSON = json.dumps(fig, cls=enc_pltjson)
        graphJson2 = json.dumps(fig2, cls=enc_pltjson)
        return JsonResponse({'data': graphJSON, 'deviation': graphJson2}, status=200)


@login_required(login_url='client_login')
def warnings(request):
    if not check_data_store(request):
        print(get_data_store(request.user.username))
    return render(request=request,template_name='website/warnings.html',context={})


@login_required(login_url='client_login')
def get_warnings_data(request):
    if request.method == 'GET':
        username = request.GET['username']
        group = request.GET['username']
        ci_index = 0.1
        # Get the Data Frame
        df = pd.read_csv(f'{settings.MEDIA_ROOT}/data/{username}.csv')
        
        now_timestamp = datetime.now()
        three_hours_plus = now_timestamp + timedelta(hours=3)

        now_string = datetime.strftime(now_timestamp,date_format)
        three_hours_plus_string = datetime.strftime(three_hours_plus,date_format)

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.loc[(df['timestamp']>=now_timestamp)&(df['timestamp']<=three_hours_plus),:]
        
        fnl = df.copy()
        fnl['Warning Description'] = None
        fnl['Warning Category'] = None
        fnl.loc[
            (fnl['forecast_cloud_index'] > 0.1) & (fnl['forecast_cloud_index'] <= 0.25), "Warning Category"] = "Orange"
        fnl.loc[fnl['forecast_cloud_index'] <= 0.1, "Warning Category"] = "Green"
        fnl.loc[fnl['forecast_cloud_index'] > 0.25, "Warning Category"] = "Red"
        fnl.loc[fnl['forecast_cloud_index'] > 0.1, "Warning Description"] = "Cloud Warning"
        fnl.loc[fnl['forecast_cloud_index'] <= 0.1, "Warning Description"] = "No Warning"
        sites_list = list(fnl['site_name'].unique())
        print(sites_list)
        sites_list.sort()
        fnl['timestamp'] = pd.to_datetime(fnl.timestamp)
        fnl['timestamp2'] = fnl['timestamp'].dt.strftime('%d %b %Y %H:%M')
        fnl['C_I_R'] = fnl['forecast_cloud_index'] * 100
        fn1 = fnl.groupby(['site_name', 'timestamp', 'Warning Description', 'Warning Category']).aggregate(
            {'site_lat': 'mean', 'site_lon': 'mean', 'forecast_cloud_index': 'mean', 'C_I_R': 'mean'}).reset_index()
        color_list = ['lightgreen', 'green', 'red', 'red', 'red', 'red', 'red', 'crimson', 'crimson', 'crimson']
        if ci_index > 0.1:
            replace_list = ['green'] * int(ci_index * 10)
            color_list[1:(int(ci_index * 10))] = replace_list
        color_list = fn1['Warning Category'].str.lower().unique()
        fig = px.scatter_mapbox(fn1, lat='site_lat', lon='site_lon',
                                size='C_I_R',
                                hover_name='site_name',
                                hover_data={'C_I_R': False,
                                            'Warning Category': False,
                                            'forecast_cloud_index': True,
                                            'timestamp': True},
                                height=700,
                                size_max=20,

                                color='Warning Category',
                                opacity=0.3, zoom=4,
                                color_discrete_sequence=color_list)
        fig.add_trace(
            go.Scattermapbox(
                lat=fn1['site_lat'],
                lon=fn1['site_lon'],
                mode='markers+text',
                text=fn1['site_name'],
                textposition='bottom center',
                marker=dict(size=5, color="green"),
                textfont=dict(size=16, color='blue')
            )
        )
        fig.update_layout(showlegend=False)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                          plot_bgcolor='rgba(0,0,0,0)',
                          margin={'l': 0, 't': 0, 'b': 0, 'r': 0})
        # fig.update_layout(hovermode=False)
        graphJSON = json.dumps(fig, cls=enc_pltjson)
        three_plus = datetime.now() + timedelta(hours=3)
        fn1 = fn1.loc[fn1['timestamp'] <= three_plus, :]
        fig2 = make_subplots(rows=len(sites_list), cols=1, subplot_titles=sites_list)
        for idx in range(len(sites_list)):
            fig2.add_trace(go.Bar(
                x=fn1.loc[(fn1['site_name'] == sites_list[idx]) & (fn1['Warning Category'] == 'Green'), 'timestamp'],
                y=fn1.loc[(fn1['site_name'] == sites_list[idx]) & (
                        fn1['Warning Category'] == 'Green'), 'forecast_cloud_index'], name=sites_list[idx]
                , marker_color='green'),
                row=idx + 1, col=1)
            fig2.add_trace(go.Bar(
                x=fn1.loc[(fn1['site_name'] == sites_list[idx]) & (fn1['Warning Category'] == 'Orange'), 'timestamp'],
                y=fn1.loc[(fn1['site_name'] == sites_list[idx]) & (
                        fn1['Warning Category'] == 'Orange'), 'forecast_cloud_index'], name=sites_list[idx]
                , marker_color='orange'),
                row=idx + 1, col=1)
            fig2.add_trace(go.Bar(
                x=fn1.loc[(fn1['site_name'] == sites_list[idx]) & (fn1['Warning Category'] == 'Red'), 'timestamp'],
                y=fn1.loc[
                    (fn1['site_name'] == sites_list[idx]) & (fn1['Warning Category'] == 'Red'), 'forecast_cloud_index'],
                name=sites_list[idx]
                , marker_color='red'),
                row=idx + 1, col=1)
            fig2.add_hline(y=0.1, line_width=1, line_dash="dash", line_color="grey", opacity=0.7, annotation_text="0.1 CI",)
            fig2.update_layout(font ={'color':'white'},margin={'l': 0, 't': 30, 'b': 0, 'r': 0})
            fig2.update_yaxes(visible=False)

        # print(fn1)
        fig.update_layout(height=700, title_text="Forecast Cloud Index")
        fig.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig.update_xaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig.update_layout(legend_font_color='grey')
        fig2.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig2.update_xaxes(showgrid=True, gridwidth=0.4, gridcolor='grey', color='white')
        fig2.update_layout(legend_font_color='grey')
        fig2.update_layout(height=700, showlegend=False, )
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                           plot_bgcolor='rgba(0,0,0,0)',
                           margin={'l': 0, 't': 30, 'b': 0, 'r': 0})
        graphJSON2 = json.dumps(fig2, cls=enc_pltjson)
        return JsonResponse({'data': graphJSON, 'histos': graphJSON2}, status=200, safe=False)


def update_on_site_change(request):
    if request.method == "GET":
        group = request.GET['group']
        client = request.GET['client_name']
        site_name = request.GET['site_name']
        # yesterday = datetime.now().date()
        date_yesterday = datetime.now() -timedelta(days=1)
        yesterday = date_yesterday.date()
        variable = 'ghi'
        time_string = datetime.strftime(yesterday, '%m-%d-%y %H:%M:%S')
        if group == "Admin":
            query = ""
        else:
            df = pd.read_csv(f'{settings.MEDIA_ROOT}/data/{client}.csv')
            df = df.rename({'site_client_name':'client_name'},axis='columns')
        ci_index = 0.1
        # df = get_sql_data(query)

        # print(query)
        df = df.loc[df['site_name'] == site_name, :]
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.loc[df['timestamp']>=date_yesterday,:]
        df = df.groupby(['timestamp', 'site_name', 'client_name']).aggregate(
            {'ghi_forecast': 'mean', 'ghi_actual': 'mean', 'forecast_cloud_index': 'mean', 'site_lat': 'mean',
             'site_lon': 'mean'}).reset_index()

        df['C_I_R'] = df['forecast_cloud_index'] * 100
        df['Warning Description'] = None
        df['Warning Category'] = None
        df['Graph Index'] = None
        df.loc[df['forecast_cloud_index'] > 0.1, "Warning Category"] = "Red"
        df.loc[df['forecast_cloud_index'] <= 0.1, "Warning Category"] = "Green"
        df.loc[df['forecast_cloud_index'] > 0.1, "Warning Description"] = "Cloud Warning"
        df.loc[df['forecast_cloud_index'] <= 0.1, "Warning Description"] = "No Warning"

        for x in df.loc[:, 'forecast_cloud_index'].index:
            if df['forecast_cloud_index'][x] > ci_index:
                df['Graph Index'][x] = df[f'ghi_forecast'][x]
        color_list = ['lightgreen', 'green', 'red', 'red', 'red', 'red', 'red', 'crimson', 'crimson', 'crimson']
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f'{variable}_actual'],
            name=f"{variable.title()} Actual"
        ))
        fig2.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f'{variable}_forecast'],
            name=f"{variable.title()} Forecast"
        ))
        fig2.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['Graph Index'],
                name='Cloud Warning',
                mode='markers',
                marker_color='orange',
                marker_size=10
            )
        )

        fig2.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='LightGrey')
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',

            height=500,
            xaxis_title="Timestamp",
            yaxis_title="GHI (W/m2)",
            # legend_title="Legends",

            font=dict(
                family="Arial",
                size=15,
            ),
            margin=dict(
                l=10,
                r=10,
                b=10,
                t=10,
                pad=1
            ),
        )
        fig2.update_yaxes(showgrid=True, gridwidth=0.4, gridcolor='grey',color='white')
        fig2.update_xaxes(showgrid=True, gridwidth=0.4, gridcolor='grey',color='white')
        fig2.update_layout(legend_font_color='grey')
        fig2.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                xaxis_title="Timestamp",
                yaxis_title="GHI (W/m2)",
                # legend_title="Legends",

                font=dict(
                    family="Arial",
                    size=15,
                ),
                margin=dict(
                    l=10,
                    r=10,
                    b=10,
                    t=10,
                    pad=1
                ),
            )
        graphJSON2 = json.dumps(fig2, cls=enc_pltjson)
        return JsonResponse({'graphs_data': graphJSON2}, status=200, safe=False)
