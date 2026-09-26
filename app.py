import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import base64
import io
from scipy.interpolate import griddata

# Initialize Dash application
app = dash.Dash(__name__, title="Waferplot Interactive")
server = app.server

def empty_figure():
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title=dict(text="Please upload a CSV file to begin", font=dict(family="Inter", size=16, color="#A3AED0")),
        xaxis=dict(visible=False), yaxis=dict(visible=False)
    )
    return fig

app.layout = html.Div(className='app-container', children=[
    html.Div(className='header-section', children=[
        html.H1("Waferplot Pro", className='header-title'),
        html.P("Precision Measurement Analytics", className='header-subtitle')
    ]),
    
    html.Div(className='dashboard-grid', children=[
        html.Div(className='card chart-card', children=[
            html.H3("Measurement Map", className='card-title', id='plot-title'),
            dcc.Graph(id='wafer-map', figure=empty_figure(), config={'displayModeBar': False}, style={'height': '700px'})
        ]),
        
        html.Div(className='side-panel', children=[
            html.Div(className='card', style={'zIndex': 100}, children=[
                html.H4("Data Import", className='card-title', style={'marginBottom': '15px', 'fontSize': '16px'}),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        html.Span("Drag and Drop or ", className='upload-text'),
                        html.Span("Select CSV File", className='upload-link')
                    ]),
                    className='upload-area',
                    multiple=False
                ),
                html.Div(id='upload-status', style={'color': 'var(--success)', 'fontSize': '12px', 'marginTop': '8px', 'fontWeight': '500'})
            ]),
            
            html.Div(className='card', style={'zIndex': 99}, children=[
                html.H4("Plot Settings", className='card-title', style={'marginBottom': '15px', 'fontSize': '16px'}),
                
                html.Label("Z-Axis Parameter", className='control-label'),
                dcc.Dropdown(
                    id='parameter-dropdown',
                    options=[],
                    className='custom-dropdown',
                    placeholder="Select parameter..."
                ),
                
                html.Label("Plot Type", className='control-label'),
                dcc.Dropdown(
                    id='plot-type-dropdown',
                    options=[
                        {'label': '2D Contour Map', 'value': 'contour'},
                        {'label': '3D Surface Topology', 'value': 'surface'},
                        {'label': 'Raw Scatter Points', 'value': 'scatter'}
                    ],
                    value='contour',
                    clearable=False,
                    className='custom-dropdown'
                ),

                html.Label("Color Theme", className='control-label'),
                dcc.Dropdown(
                    id='colorscale-dropdown',
                    options=[
                        {'label': 'Turbo (High Contrast)', 'value': 'Turbo'},
                        {'label': 'RdYlBu (Reversed)', 'value': 'RdYlBu_r'},
                        {'label': 'Plasma (Modern)', 'value': 'Plasma'},
                        {'label': 'Viridis (Scientific)', 'value': 'Viridis'},
                        {'label': 'Spectral', 'value': 'Spectral'}
                    ],
                    value='Turbo',
                    clearable=False,
                    className='custom-dropdown'
                ),
                
                html.Br(),
                dcc.Checklist(
                    id='show-axes-checkbox',
                    options=[{'label': ' Show Axis Grid', 'value': 'show'}],
                    value=['show'],
                    style={'marginTop': '10px', 'color': 'var(--text-main)', 'fontWeight': '600', 'fontSize': '14px', 'cursor': 'pointer'}
                )
            ]),

            html.Div(className='card', style={'textAlign': 'center', 'padding': '20px'}, children=[
                html.H4("MEAN VALUE", className='stat-title'),
                html.H2(id='stat-mean', className='stat-value success', children="-")
            ]),
            html.Div(className='card', style={'textAlign': 'center', 'padding': '20px'}, children=[
                html.H4("STANDARD DEVIATION", className='stat-title'),
                html.H2(id='stat-std', className='stat-value', children="-")
            ]),
        ])
    ]),
    dcc.Store(id='stored-data')
])

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            return df.to_json(date_format='iso', orient='split')
    except Exception as e:
        print(e)
    return None

@app.callback(
    [Output('stored-data', 'data'),
     Output('parameter-dropdown', 'options'),
     Output('parameter-dropdown', 'value'),
     Output('upload-status', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_data(contents, filename):
    if contents is None:
        try:
            df = pd.read_csv('sample_wafer_data.csv')
            json_data = df.to_json(date_format='iso', orient='split')
            excluded = ['diex', 'diey', 'x', 'y', 'x_coord', 'y_coord']
            cols = [{'label': col, 'value': col} for col in df.columns if col.lower() not in excluded]
            val = cols[0]['value'] if cols else None
            return json_data, cols, val, "Loaded default sample"
        except:
            return dash.no_update, [], None, ""

    json_data = parse_contents(contents, filename)
    if json_data:
        df = pd.read_json(io.StringIO(json_data), orient='split')
        excluded = ['diex', 'diey', 'x', 'y', 'x_coord', 'y_coord']
        options = [{'label': col, 'value': col} for col in df.columns if col.lower() not in excluded]
        default_val = options[0]['value'] if options else None
        return json_data, options, default_val, f"File: {filename}"
    
    return dash.no_update, [], None, "Error parsing file"

@app.callback(
    [Output('wafer-map', 'figure'),
     Output('plot-title', 'children'),
     Output('stat-mean', 'children'),
     Output('stat-std', 'children')],
    [Input('stored-data', 'data'),
     Input('parameter-dropdown', 'value'),
     Input('plot-type-dropdown', 'value'),
     Input('colorscale-dropdown', 'value'),
     Input('show-axes-checkbox', 'value')]
)
def update_graph(json_data, parameter, plot_type, colorscale, show_axes):
    if not json_data or not parameter:
        return empty_figure(), "Measurement Map", "-", "-"

    df = pd.read_json(io.StringIO(json_data), orient='split')
    
    x_col = next((col for col in df.columns if col.lower() in ['x', 'diex', 'x_coord']), df.columns[0])
    y_col = next((col for col in df.columns if col.lower() in ['y', 'diey', 'y_coord']), df.columns[1])
    
    x = df[x_col].values
    y = df[y_col].values
    z = df[parameter].values

    mean_val = f"{np.nanmean(z):.2f}"
    std_val = f"{np.nanstd(z):.2f}"
    
    fig = go.Figure()

    # Shared colorbar settings for a cleaner look
    cbar_dict = dict(
        title=dict(text=parameter, font=dict(family="Inter", size=12, color="#A3AED0")),
        tickfont=dict(family="Inter", size=11, color="#A3AED0"),
        thickness=12,
        len=0.7,
        outlinewidth=0,
        bgcolor='rgba(0,0,0,0)'
    )

    if plot_type == 'scatter':
        fig.add_trace(go.Scatter(
            x=x, y=y, mode='markers',
            marker=dict(
                size=14, color=z, colorscale=colorscale, showscale=True, symbol='square',
                colorbar=cbar_dict
            ),
            text=np.round(z, 2),
            hovertemplate=f"X: %{{x}}<br>Y: %{{y}}<br>{parameter}: %{{text}}<extra></extra>"
        ))
        
    else:
        grid_x, grid_y = np.mgrid[min(x):max(x):200j, min(y):max(y):200j]
        grid_z = griddata((x, y), z, (grid_x, grid_y), method='cubic')
        
        radius = max(max(abs(x)), max(abs(y)))
        mask = (grid_x**2 + grid_y**2) > (radius * 1.05)**2
        grid_z[mask] = np.nan

        if plot_type == 'contour':
            fig.add_trace(go.Contour(
                z=grid_z.T, x=grid_x[:,0], y=grid_y[0,:],
                colorscale=colorscale,
                colorbar=cbar_dict,
                hovertemplate=f"X: %{{x:.2f}}<br>Y: %{{y:.2f}}<br>{parameter}: %{{z:.2f}}<extra></extra>",
                contours=dict(showlines=False)
            ))
            
            fig.add_shape(
                type="circle",
                x0=-radius, y0=-radius, x1=radius, y1=radius,
                line_color="#E0E5F2", line_width=1
            )

        elif plot_type == 'surface':
            fig.add_trace(go.Surface(
                z=grid_z.T, x=grid_x[:,0], y=grid_y[0,:],
                colorscale=colorscale,
                colorbar=cbar_dict,
                hovertemplate=f"X: %{{x:.2f}}<br>Y: %{{y:.2f}}<br>{parameter}: %{{z:.2f}}<extra></extra>"
            ))
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title="", showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(title="", showgrid=False, zeroline=False, showticklabels=False),
                    zaxis=dict(title=parameter, gridcolor="#E0E5F2", tickfont=dict(color="#A3AED0")),
                    bgcolor='rgba(0,0,0,0)'
                )
            )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=20, b=10),
        hovermode='closest'
    )

    if plot_type in ['scatter', 'contour']:
        # Elegant axis lines and labels for clean aesthetics
        show_axis_flag = bool(show_axes and 'show' in show_axes)
        axis_style = dict(
            showgrid=show_axis_flag, gridcolor="rgba(163, 174, 208, 0.2)",
            zeroline=show_axis_flag, zerolinecolor="rgba(163, 174, 208, 0.5)", zerolinewidth=1,
            showticklabels=show_axis_flag, tickfont=dict(family="Inter", size=11, color="#A3AED0"),
            showline=False,
            scaleanchor="x", scaleratio=1
        )
        title_dict = dict(text="X Coordinate", font=dict(family="Inter", size=12, color="#A3AED0")) if show_axis_flag else None
        title_dict_y = dict(text="Y Coordinate", font=dict(family="Inter", size=12, color="#A3AED0")) if show_axis_flag else None
        fig.update_layout(
            xaxis=dict(title=title_dict, **axis_style),
            yaxis=dict(title=title_dict_y, **axis_style)
        )

    return fig, f"Analysis: {parameter}", mean_val, std_val

if __name__ == '__main__':
    app.run(debug=True, port=8050)
