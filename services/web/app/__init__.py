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

from .queries import get_order_numbers, get_service_orders
    
    
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
auth = dash_auth.BasicAuth(app, config.auth_pair)

app.config.suppress_callback_exceptions = True

server = app.server

app.layout = html.Div([
    dcc.Tabs(id="tabs", value='tab-1', children=[
        dcc.Tab(label='Tab 1', value='tab-1'),
        dcc.Tab(label='Tab 2', value='tab-2'),
        dcc.Tab(label='Tab 3', value='tab-3')
    ]),
    html.Div(id='tabs-content')
])

@app.callback(Output('tabs-content', 'children'),
              [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
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
    
    elif tab == 'tab-2':
        return html.Div([
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

    elif tab == 'tab-3':
        return html.Div([
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

