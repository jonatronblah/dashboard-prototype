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
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import pmdarima as pm
from pmdarima.model_selection import train_test_split
import numpy as np

from .queries import get_order_numbers, get_service_orders, get_bill_details, year_over_year, plot_yoy, get_budget, train_model_graph
    
    
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
    dcc.Graph(id='sd-graph-2'),
    html.Table([
        html.Tr([html.Td(['Overall Mean Time to Completion (Minutes)']), html.Td(id='row1')]),
        html.Tr([html.Td(['Percentage of Items Completed']), html.Td(id='row2')])
    ])    
])
    
    elif tab == 'tab-2':
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthnums = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        optionsmonths = []
        for e, i in enumerate(months):
            optionsmonths.append({'label': i, 'value': monthnums[e]})
        years = ['2020', '2019', '2018', '2017', '2016', '2015']
        yearnums = ['20', '19', '18', '17', '16', '15']
        optionsyears = []
        for e, i in enumerate(years):
            optionsyears.append({'label': i, 'value': yearnums[e]})
        return html.Div([
    dcc.Dropdown(
        id='year-input',
        options = optionsyears,
        value='20'
    ),
    dcc.Dropdown(
        id='month-input',
        options = optionsmonths,
        value='05'
    ),
    dcc.Graph(id='yoy-graph')
])

    elif tab == 'tab-3':
        ts_df = get_budget()
        bill_dates = train_model_graph(ts_df)
        y = ts_df['TOTAL'].values
        model = pm.auto_arima(y)
        forecasts = model.predict(12)
        
        
        ts_fig = px.line()
        ts_fig.add_scatter(x=bill_dates, y=ts_df['TOTAL'].values, name='Historical Bills')
        ts_fig.add_scatter(x=bill_dates[len(ts_df['BILL_DATE'].values):], y=forecasts, mode='lines', name = 'Predicted Bills')
        return html.Div([
        dcc.Graph(id='ts-graph', figure=ts_fig)  
])







#order completion callback
@app.callback(
    [Output('sd-graph', 'figure'),
     Output('sd-graph-2', 'figure'),
     Output('row1', 'children'),
     Output('row2', 'children')],
    [Input('day-input', 'value'),
     Input('service-col', 'value')])
def update_graph_orders(day_val, col_val):
    l = get_order_numbers(day_val)
    df = get_service_orders(l)
    comptime = df.completiontime.mean()
    perc_complete = len(df[~df.typeCompleted.isnull()]) / len(df)
    dfg = df.groupby(col_val).mean().sort_values('completiontime').reset_index()
    fig1 = px.bar(dfg, x=col_val, y='completiontime', labels={col_val: 'Ticket Source', 'completiontime': 'Avg Ticket Completion Time'})
    
    df_t = df[~df.completiontime.isnull()]
    df_t = df_t.set_index('typeCompleted').resample('1W').mean().reset_index()
    fig2 = px.line(df_t, x='typeCompleted', y='completiontime', labels={'typeCompleted': 'Week Of', 'completiontime': 'Avg Ticket Completion Time'})
    
    
    return fig1, fig2, comptime, perc_complete

#yoy budget callback
@app.callback(
    Output('yoy-graph', 'figure'),
    [Input('year-input', 'value'),
     Input('month-input', 'value')])
def update_graph_yoy(year_val, month_val):
    ty, ly = get_bill_details(year_val, month_val)
    ty_cost, ly_cost = year_over_year(ty, ly)
    fig = plot_yoy(ty_cost, ly_cost)
    return fig




if __name__ == '__main__':
    app.run_server(debug=True)    

