import dash
import dash_auth
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import paramiko
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.sql import select
from sshtunnel import SSHTunnelForwarder
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, load_only
from sqlalchemy.pool import NullPool
from . import config
import plotly.express as px
import datetime


#functions

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
    
    
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
auth = dash_auth.BasicAuth(app, config.auth_pair)

app.config.suppress_callback_exceptions = True

server = app.server

#--bind 127.0.0.1:8888 app:server


app.layout = html.Div([
    dcc.Dropdown(
        id='service-col',
        options=[{'label': 'Source Type', 'value': 'VALUE'},
                {'label': 'Department', 'value': 'NAME'}],
        value='VALUE'
    ),
    dcc.Input(
        id='day-input',
        type='number',
        value=30
    ),
    dcc.Graph(id='sd-graph'),
    html.Table([
        html.Tr([html.Td(['Overall Mean Time to Completion (Minutes)']), html.Td(id='row1')]),
        html.Tr([html.Td(['Percentage of Items Completed']), html.Td(id='row2')])
    ])
    
])

@app.callback(
    [Output('sd-graph', 'figure'),
     Output('row1', 'children'),
     Output('row2', 'children')],
    [Input('day-input', 'value'),
     Input('service-col', 'value')])
def update_graph(day_val, col_val):
    l = get_order_numbers(day_val)
    df = get_service_orders(l)
    comptime = df.completiontime.mean()
    perc_complete = len(df[~df.typeCompleted.isnull()]) / len(df)
    dfg = df.groupby(col_val).mean().sort_values('completiontime').reset_index()
    fig1 = px.bar(dfg, x=col_val, y='completiontime')
    return fig1, comptime, perc_complete
    




if __name__ == '__main__':
    app.run_server(debug=True)    

