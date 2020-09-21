import paramiko
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.sql import select
from sshtunnel import SSHTunnelForwarder
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, load_only
from sqlalchemy.pool import NullPool
from . import config
import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pmdarima as pm
from pmdarima.model_selection import train_test_split
import numpy as np

###order completion###
def get_order_numbers(n):
    server = SSHTunnelForwarder(
    (config.pcr_ssh_url, 0),
    ssh_username=config.pcr_ssh_user,
    ssh_password=config.pcr_ssh_pass,
    remote_bind_address=(config.pcr_db_name, 3306))
    server.start()
    localport = str(server.local_bind_port)
    engine = create_engine(config.pcr_db_conn_str+localport+'/pcr360_prod', poolclass=NullPool)
    metadata = MetaData()
    
    service_desk = Table('SERVICE_DESK', metadata, autoload=True, autoload_with=engine)
    desk_activity = Table('SERVICE_DESK_ACTIVITY', metadata, autoload=True, autoload_with=engine)
    
    session = Session(engine)
    
    days = datetime.datetime.now() - datetime.timedelta(days=n)
    
    r = session.query(service_desk.c.SD_NUMBER).join(desk_activity, service_desk.c.RECID==desk_activity.c.SERVICE_DESK_RECID).filter(desk_activity.c.ACTIVITY_TYPE=='typeCreated').filter(desk_activity.c.MODIFIED_DATE >= days).all()
    session.close()
    server.stop()
    l = [i[0] for i in r]
    return l

def get_service_orders(l):
    server = SSHTunnelForwarder(
    (config.pcr_ssh_url, 0),
    ssh_username=config.pcr_ssh_user,
    ssh_password=config.pcr_ssh_pass,
    remote_bind_address=(config.pcr_db_name, 3306))
    server.start()
    localport = str(server.local_bind_port)
    engine = create_engine(config.pcr_db_conn_str+localport+'/pcr360_prod', poolclass=NullPool)
    metadata = MetaData()
    
    service_desk = Table('SERVICE_DESK', metadata, autoload=True, autoload_with=engine)
    lists = Table('LISTS', metadata, autoload=True, autoload_with=engine)
    contacts = Table('CONTACTS', metadata, autoload=True, autoload_with=engine)
    dept = Table('DEPT_HIERARCHY', metadata, autoload=True, autoload_with=engine)
    desk_activity = Table('SERVICE_DESK_ACTIVITY', metadata, autoload=True, autoload_with=engine)
    
    session = Session(engine)
    
    
    r = session.query(service_desk.c.SD_NUMBER, desk_activity.c.ACTIVITY_TYPE, desk_activity.c.MODIFIED_DATE, lists.c.VALUE, contacts.c.LAST_NAME, dept.c.NAME).join(desk_activity, service_desk.c.RECID==desk_activity.c.SERVICE_DESK_RECID).join(lists, service_desk.c.SD_SOURCE_LISTS_RECID==lists.c.RECID).join(contacts, service_desk.c.REQUESTOR_CONTACTS_RECID==contacts.c.RECID).join(dept, contacts.c.DEPT_HIERARCHY_RECID==dept.c.RECID).filter(service_desk.c.SD_NUMBER.in_(l)).all()
    cols = session.query(service_desk.c.SD_NUMBER, desk_activity.c.ACTIVITY_TYPE, desk_activity.c.MODIFIED_DATE, lists.c.VALUE, contacts.c.LAST_NAME, dept.c.NAME).join(desk_activity, service_desk.c.RECID==desk_activity.c.SERVICE_DESK_RECID).join(lists, service_desk.c.SD_SOURCE_LISTS_RECID==lists.c.RECID).join(contacts, service_desk.c.REQUESTOR_CONTACTS_RECID==contacts.c.RECID).join(dept, contacts.c.DEPT_HIERARCHY_RECID==dept.c.RECID).column_descriptions
    cols = [i['name'] for i in cols]
    df = pd.DataFrame(r, columns=cols)
    
    dfp = df.pivot_table(index='SD_NUMBER', columns='ACTIVITY_TYPE', values='MODIFIED_DATE', aggfunc='first')
    dfg = df.groupby('SD_NUMBER').first()[['VALUE', 'LAST_NAME', 'NAME']]
    df = dfp.merge(dfg, left_on='SD_NUMBER', right_on='SD_NUMBER')
    df['completiontime'] = df['typeCompleted'] - df['typeCreated']
    df['completiontime'] = df['completiontime'] / pd.Timedelta(minutes=1)
    
    
    session.close()
    server.stop()
    return df
    
    
    
    
###budget - year over year###
def get_bill_details(year, month):
    server = SSHTunnelForwarder(
    (config.pcr_ssh_url, 0),
    ssh_username=config.pcr_ssh_user,
    ssh_password=config.pcr_ssh_pass,
    remote_bind_address=(config.pcr_db_name, 3306))
    server.start()
    localport = str(server.local_bind_port)
    engine = create_engine(config.pcr_db_conn_str+localport+'/pcr360_prod', poolclass=NullPool)
    metadata = MetaData()
    
    bill_details = Table('BILL_DETAILS_' + year + month, metadata, autoload=True, autoload_with=engine)
    session = Session(engine)
    
    r = session.query(bill_details).all()
    cols = session.query(bill_details).column_descriptions
    cols = [i['name'] for i in cols]
    df1 = pd.DataFrame(r, columns=cols)
    
    last_year = str(int(year) - 1)
    bill_details = Table('BILL_DETAILS_' + last_year + month, metadata, autoload=True, autoload_with=engine)
    session = Session(engine)
    
    r = session.query(bill_details).all()
    cols = session.query(bill_details).column_descriptions
    cols = [i['name'] for i in cols]
    df2 = pd.DataFrame(r, columns=cols)
    
    
    
    
    session.close()
    server.stop()
    return df1, df2
    
def year_over_year(ty, ly):
    ty = ty[ty.COST >0]
    ly = ly[ly.COST >0]
    ty['COST'] = ty['COST'].astype('float')
    ly['COST'] = ly['COST'].astype('float')
    ty_cost = ty.groupby('REVENUE_OBJECT_CODE_DESC').sum()['COST']
    ly_cost = ly.groupby('REVENUE_OBJECT_CODE_DESC').sum()['COST']
    
    
    return ty_cost, ly_cost
    
def plot_yoy(ty_cost, ly_cost):
    service_cat = []
    perc_chng = []

    for i in ty_cost.index:
        if i in ly_cost:
            change = ty_cost[i] / ly_cost[i]
            service_cat.append(i)
            perc_chng.append(change*100)
            
            
    fig = make_subplots(1, 3, specs=[[{'type':'table'}, {'type':'domain'}, {'type':'domain'}]],
                        subplot_titles=['Service Type', 'Previous Year', 'Selected Year'])
    
    
    fig.add_trace(go.Pie(labels=ly_cost.index, values=ly_cost.values, scalegroup='one',
                         name="2019"), 1, 2)
    fig.add_trace(go.Pie(labels=ty_cost.index, values=ty_cost.values, scalegroup='one',
                         name="2020"), 1, 3)
    
    fig.add_trace(
        go.Table(
            header=dict(
                values=["Category", "Percent Change"],
                font=dict(size=10),
                align="left"
            ),
            cells=dict(
                values=[service_cat, perc_chng],
                align = "left"),
            name="Service Type"
        ),
        row=1, col=1
    )
    
    
    fig.update_layout(title_text='Total YoY Growth: ' + str((sum(ty_cost.values) / sum(ly_cost.values)) - 1))
    return fig
    
    
    
###budget time series prediction###
def get_budget():
    server = SSHTunnelForwarder(
    (config.pcr_ssh_url, 0),
    ssh_username=config.pcr_ssh_user,
    ssh_password=config.pcr_ssh_pass,
    remote_bind_address=(config.pcr_db_name, 3306))
    server.start()
    localport = str(server.local_bind_port)
    engine = create_engine(config.pcr_db_conn_str+localport+'/pcr360_prod', poolclass=NullPool)
    metadata = MetaData()
    
    bills = Table('BILLS', metadata, autoload=True, autoload_with=engine)
    
    session = Session(engine)
    
    r = session.query(bills).all()
    cols = session.query(bills).column_descriptions
    cols = [i['name'] for i in cols]
    df = pd.DataFrame(r, columns=cols)
    session.close()
    server.stop()
    df = df[df.TEST_BILL == 0]
    df = df[['BILL_DATE', 'CALL_COUNT', 'TOTAL']]
    df['TOTAL'] = df['TOTAL'].astype('int32')
    df = df[df['TOTAL'] > 0] 
    return df
    
def train_model_graph(df):
    current_dates = [pd.Timestamp(i) for i in df['BILL_DATE'].values] 
    last_bill = current_dates[-1]
    future_dates = []
    for i in range(1, 13):
        bill = pd.Timestamp(last_bill) + pd.DateOffset(months=i)
        future_dates.append(bill)
    bill_dates = np.append(current_dates, future_dates)
    
    
    '''
    y = df['TOTAL'].values
    model = pm.auto_arima(y)
    forecasts = model.predict(12)
    
    
    fig = px.line()
    fig.add_scatter(x=bill_dates, y=df['TOTAL'].values, name='Historical Bills')
    fig.add_scatter(x=bill_dates[len(df['BILL_DATE'].values):], y=forecasts, mode='lines', name = 'Predicted Bills')
    '''
    return bill_dates
    
def train_model_test(df):
    current_dates = [pd.Timestamp(i) for i in df['BILL_DATE'].values] 
    last_bill = current_dates[-1]
    future_dates = []
    for i in range(1, 13):
        bill = pd.Timestamp(last_bill) + pd.DateOffset(months=i)
        future_dates.append(bill)
    bill_dates = np.append(current_dates, future_dates)
    
    y = df['TOTAL'].values
    model = pm.auto_arima(y, seasonal=True, m=1)
    forecasts = model.predict(12)
    
   
    return forecasts
    
    
    
    
    
    