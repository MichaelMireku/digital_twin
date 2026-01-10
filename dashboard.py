import os
import sys
import datetime
import requests
import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from logging.handlers import RotatingFileHandler

# --- ROBUST PATH SETUP ---
try:
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
    from utils.depot_layout import DEPOT_LAYOUT
except ImportError as e:
    print(f"CRITICAL DASHBOARD ERROR: Could not import modules: {e}")
    sys.exit(1)

import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc

# --- Configuration & Setup ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
API_KEY = os.getenv("API_KEY", settings.API_KEY if hasattr(settings, 'API_KEY') else "demo_key")
PRODUCT_PRICING = {"PMS": 18.00, "AGO": 17.25, "DPK": 16.50, "ATK": 20.25, "Default": 15.00}
PRODUCT_COLORS = {"Gasoline (PMS)": "#ef4444", "Gasoil (AGO)": "#0ea5e9", "DPK": "#8b5cf6", "ATK": "#22c55e", "Unknown": "#64748b"}
LATITUDE, LONGITUDE = 40.7128, -74.0060

# --- Electricity Costing ---
ELECTRICITY_RATE_PER_KWH = 0.12
SERVICE_CHARGE = 5.00
PUMP_POWER_KW = 30
ESTIMATED_DAILY_HOURS_PER_PUMP = 8

# --- LOGGING CONFIGURATION ---
LOG_FILE = "dashboard.log"
logger = logging.getLogger("depot_dashboard")
logger.setLevel(logging.INFO)
if not logger.handlers:
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=2)
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(log_format)
    f_handler.setFormatter(log_format)
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

# --- Custom CSS Styles ---
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #0ea5e9;
    --primary-dark: #0284c7;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --dark-bg: #0f172a;
    --card-bg: #1e293b;
    --card-border: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #0f172a !important;
    min-height: 100vh;
}

.navbar {
    background: #1e293b !important;
    border-bottom: 1px solid #334155;
    padding: 0.75rem 2rem !important;
}

.navbar-brand {
    font-weight: 600 !important;
    font-size: 1.25rem !important;
    color: #f1f5f9 !important;
}

.kpi-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.25rem;
    height: 100%;
}

.kpi-card:hover {
    border-color: #0ea5e9;
    transition: border-color 0.2s ease;
}

.kpi-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    margin-bottom: 0.75rem;
    color: #fff;
}

.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.25rem;
}

.kpi-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.glass-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.25rem;
}

.section-title {
    color: #f1f5f9;
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.section-title::before {
    content: '';
    width: 3px;
    height: 18px;
    background: #0ea5e9;
    border-radius: 2px;
}

.alert-item {
    background: #334155;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    border-left: 3px solid;
}

.alert-item:hover {
    background: #3f4f63;
}

.alert-critical { border-left-color: #ef4444; }
.alert-warning { border-left-color: #f59e0b; }
.alert-info { border-left-color: #0ea5e9; }

.weather-widget {
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
    border-radius: 12px;
    padding: 1.25rem;
    color: #fff;
    text-align: center;
}

.weather-temp {
    font-size: 2.25rem;
    font-weight: 700;
}

.weather-desc {
    font-size: 0.85rem;
    opacity: 0.9;
}

.status-badge {
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
}

.status-online { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
.status-offline { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.status-warning { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }

.nav-tabs {
    border: none !important;
    background: #1e293b !important;
    border-radius: 8px;
    padding: 0.4rem;
    margin: 1rem 2rem;
}

.nav-tabs .nav-link {
    border: none !important;
    color: #94a3b8 !important;
    border-radius: 6px !important;
    padding: 0.6rem 1.25rem !important;
    font-weight: 500;
    font-size: 0.9rem;
    background: transparent !important;
}

.nav-tabs .nav-link:hover {
    color: #f1f5f9 !important;
    background: #334155 !important;
}

.nav-tabs .nav-link.active {
    background: #0ea5e9 !important;
    color: #fff !important;
}

.tab-container {
    background: #1e293b !important;
}

.custom-tabs {
    background: #1e293b !important;
    border: none !important;
}

.custom-tabs .tab {
    background: transparent !important;
    border: none !important;
    color: #94a3b8 !important;
}

.custom-tabs .tab--selected {
    background: #0ea5e9 !important;
    color: #fff !important;
    border: none !important;
}

.dash-spreadsheet-container .dash-spreadsheet-inner th {
    background: #334155 !important;
    color: #f1f5f9 !important;
    font-weight: 600;
    border: none !important;
    padding: 0.75rem !important;
}

.dash-spreadsheet-container .dash-spreadsheet-inner td {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: none !important;
    border-bottom: 1px solid #334155 !important;
    padding: 0.6rem 0.75rem !important;
}

.dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td {
    background: #334155 !important;
}

.btn-primary-gradient {
    background: #0ea5e9;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.25rem;
    font-weight: 600;
    color: #fff;
}

.btn-primary-gradient:hover {
    background: #0284c7;
}

.pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.6); }
    70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
    100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

.tank-legend {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    color: #94a3b8;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}

.Select-control {
    background: #334155 !important;
    border: 1px solid #475569 !important;
    border-radius: 6px !important;
}

.Select-value-label, .Select-placeholder {
    color: #e2e8f0 !important;
}

/* Dash Tabs Specific Styling */
.tab-parent {
    background: #1e293b !important;
    border-radius: 8px;
    margin: 1rem 2rem;
    padding: 0.4rem;
}

.tab {
    background: transparent !important;
    border: none !important;
    color: #94a3b8 !important;
    padding: 0.6rem 1.25rem !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    border-radius: 6px !important;
}

.tab:hover {
    background: #334155 !important;
    color: #f1f5f9 !important;
}

.tab--selected {
    background: #0ea5e9 !important;
    color: #fff !important;
    border: none !important;
    border-bottom: none !important;
}

.tab-content {
    border: none !important;
    background: transparent !important;
}
"""

# --- Dash App Initialization ---
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True
)
app.title = "Fuel Depot Digital Twin"

# --- API & Data Helper Functions ---
def get_api_data(endpoint: str, payload: dict = None, method: str = 'GET') -> dict:
    if not API_KEY:
        logger.error("API Key not configured for dashboard.")
        return {}
    try:
        headers = {'x-api-key': API_KEY, 'Content-Type': 'application/json'}
        url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Making API call: {method} {url}")
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=payload, timeout=15)
        else:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"API call successful for {endpoint}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API call to {endpoint} failed: {e}")
        return {}

def fetch_weather_data():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get('current', {})
        description = get_weather_description(data.get('weather_code'))
        icon = get_weather_icon(data.get('weather_code'))
        return {
            "description": description,
            "temp": f"{data.get('temperature_2m', ''):.1f}",
            "wind_speed": f"{data.get('wind_speed_10m', ''):.1f}",
            "humidity": f"{data.get('relative_humidity_2m', '')}",
            "icon": icon
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Public weather API call failed: {e}")
        return {"description": "Unavailable", "temp": "--", "wind_speed": "--", "humidity": "--", "icon": "fa-cloud-question"}

def get_weather_description(code):
    wmo_codes = {0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast", 45: "Foggy", 61: "Light Rain", 80: "Showers", 95: "Thunderstorm"}
    return wmo_codes.get(code, "Unknown")

def get_weather_icon(code):
    icons = {0: "fa-sun", 1: "fa-sun", 2: "fa-cloud-sun", 3: "fa-cloud", 45: "fa-smog", 61: "fa-cloud-rain", 80: "fa-cloud-showers-heavy", 95: "fa-bolt"}
    return icons.get(code, "fa-cloud")


# --- UI Component Builders ---
def build_kpi_card(title, value, unit, icon, bg_color, trend=None, trend_value=None):
    """Build a modern KPI card with icon and optional trend indicator."""
    trend_element = None
    if trend and trend_value:
        trend_class = "trend-up" if trend == "up" else "trend-down"
        trend_icon = "fa-arrow-up" if trend == "up" else "fa-arrow-down"
        trend_element = html.Div([
            html.I(className=f"fas {trend_icon} me-1"),
            html.Span(trend_value)
        ], className=f"kpi-trend {trend_class}")
    
    return html.Div([
        html.Div([
            html.I(className=f"fas {icon}")
        ], className=f"kpi-icon", style={"background": bg_color}),
        html.Div(f"{value} {unit}", className="kpi-value"),
        html.Div(title, className="kpi-label"),
        trend_element
    ], className="kpi-card")


def build_weather_widget(weather_data):
    """Build an attractive weather widget."""
    return html.Div([
        html.Div([
            html.I(className=f"fas {weather_data.get('icon', 'fa-cloud')} fa-3x mb-3"),
            html.Div(f"{weather_data.get('temp', '--')}°C", className="weather-temp"),
            html.Div(weather_data.get('description', 'Unknown'), className="weather-desc mb-2"),
        ]),
        html.Hr(style={"opacity": "0.3"}),
        html.Div([
            html.Div([
                html.I(className="fas fa-wind me-2"),
                html.Span(f"{weather_data.get('wind_speed', '--')} km/h")
            ], className="d-flex align-items-center justify-content-center mb-1"),
            html.Div([
                html.I(className="fas fa-droplet me-2"),
                html.Span(f"{weather_data.get('humidity', '--')}%")
            ], className="d-flex align-items-center justify-content-center"),
        ], style={"fontSize": "0.85rem"})
    ], className="weather-widget")


def build_alert_item(alert):
    """Build a styled alert item."""
    severity = alert.get('severity', 'warning').lower()
    severity_class = f"alert-{severity}" if severity in ['critical', 'warning', 'info'] else 'alert-warning'
    icon = "fa-circle-exclamation" if severity == 'critical' else "fa-triangle-exclamation" if severity == 'warning' else "fa-circle-info"
    
    return html.Div([
        html.Div([
            html.I(className=f"fas {icon} me-2", style={"color": "#f39c12" if severity == 'warning' else "#e74c3c"}),
            html.Span(alert.get('alert_name', 'Alert'), style={"fontWeight": "600", "color": "#fff"})
        ], className="d-flex align-items-center mb-1"),
        html.P(alert.get('message', ''), className="mb-0", style={"fontSize": "0.85rem", "color": "#a0a0a0"})
    ], className=f"alert-item {severity_class}")


def build_alerts_section(alerts: list):
    """Build the alerts section with styled items."""
    if not alerts:
        return html.Div([
            html.Div([
                html.I(className="fas fa-check-circle fa-2x mb-2", style={"color": "#38ef7d"}),
                html.P("All systems operational", className="mb-0", style={"color": "#a0a0a0"})
            ], className="text-center py-4")
        ])
    return html.Div([build_alert_item(a) for a in alerts[:5]])


def build_depot_hmi_view(assets_data: list, fire_sim_results: dict = None) -> dcc.Graph:
    """Build the depot HMI visualization with improved styling."""
    fig = go.Figure()
    
    # Draw Buildings with better styling
    for name, b in DEPOT_LAYOUT.get('buildings', {}).items():
        fig.add_shape(
            type="rect",
            x0=b['x']-b['width']/2, y0=b['y']-b['height']/2,
            x1=b['x']+b['width']/2, y1=b['y']+b['height']/2,
            line=dict(color="#334155", width=2),
            fillcolor="#1e293b",
            layer="below"
        )
        fig.add_annotation(
            x=b['x'], y=b['y'], text=name, showarrow=False,
            font=dict(size=b.get('size', 8), color="#94a3b8", family="Inter")
        )

    # Draw Features
    for name, f in DEPOT_LAYOUT.get('features', {}).items():
        fig.add_shape(
            type="rect",
            x0=f['x']-f['width']/2, y0=f['y']-f['height']/2,
            x1=f['x']+f['width']/2, y1=f['y']+f['height']/2,
            line=dict(color=f['color']), fillcolor=f['color'], layer="below"
        )
        if "Assembly" in name:
            fig.add_annotation(x=f['x'], y=f['y'], text="<b>+</b>", showarrow=False, font=dict(size=16, color="white"))
        elif "Water" in name:
            fig.add_annotation(x=f['x'], y=f['y'], text="W", showarrow=False, font=dict(size=10, color="white"))

    # Draw Gantries
    for gantry in DEPOT_LAYOUT.get('gantries', []):
        x, y, w, h = gantry['x'], gantry['y'], gantry['width'], gantry['height']
        fig.add_shape(
            type="rect", x0=x-w/2, y0=y-h/2, x1=x+w/2, y1=y+h/2,
            line=dict(color="#475569", width=2), fillcolor="#334155", layer="below"
        )
        fig.add_annotation(x=x, y=y, text=gantry['id'], showarrow=False, font=dict(size=9, color="#f1f5f9"))

    # Draw Pump Stations
    for name, p_coords in DEPOT_LAYOUT.get('pump_stations', {}).items():
        fig.add_trace(go.Scatter(
            x=[p_coords['x']], y=[p_coords['y']], mode='markers',
            marker=dict(symbol='diamond', color='#f59e0b', size=18, line=dict(width=2, color='#fff')),
            hoverinfo="text", hovertext=f"<b>{name}</b>", name=name
        ))

    # Draw Tanks with gradient colors based on level
    tanks = [a for a in assets_data if a.get('asset_type') == 'StorageTank']
    tank_coords = DEPOT_LAYOUT.get('tanks', {})
    
    for tank in tanks:
        asset_id = tank['asset_id']
        coords = tank_coords.get(asset_id)
        if not coords:
            continue
        
        level_pct = tank.get('latest_dynamic_state', {}).get('level_percentage', {}).get('value', 0)
        product = tank.get('product_service', 'Unknown')
        
        # Color based on level status
        if level_pct > 90:
            fill_color = "#e74c3c"  # Critical high
            status = "HIGH"
        elif level_pct > 80:
            fill_color = "#f39c12"  # Warning
            status = "WARN"
        elif level_pct > 20:
            fill_color = "#27ae60"  # Normal
            status = "OK"
        elif level_pct > 10:
            fill_color = "#3498db"  # Low
            status = "LOW"
        else:
            fill_color = "#9b59b6"  # Critical low
            status = "CRIT"
        
        radius = coords.get('radius', 5.0)
        marker_size = 20 + (radius * 2.5)
        
        fig.add_trace(go.Scatter(
            x=[coords['x']], y=[coords['y']], mode='markers+text',
            marker=dict(
                size=marker_size, color=fill_color, opacity=0.9,
                line=dict(width=3, color='rgba(255,255,255,0.3)'),
                symbol='circle'
            ),
            text=f"<b>{asset_id.replace('TANK_','T-')}</b>",
            textposition="middle center",
            hoverinfo="text",
            hovertext=f"<b>{asset_id}</b><br>Product: {product}<br>Level: {level_pct:.1f}%<br>Status: {status}",
            name=asset_id,
            customdata=[asset_id],
            textfont=dict(color='white', size=10, family="Inter")
        ))

    # Draw Area Labels
    for name, l in DEPOT_LAYOUT.get('labels', {}).items():
        fig.add_annotation(
            x=l['x'], y=l['y'], text=f"<b>{name}</b>", showarrow=False,
            font=dict(size=l.get('size', 12), color="#0ea5e9", family="Inter")
        )

    # Fire Simulation Radii
    if fire_sim_results and 'source_asset_id' in fire_sim_results:
        source_id = fire_sim_results.get('source_asset_id')
        source_coords = tank_coords.get(source_id)
        if source_coords:
            radii = fire_sim_results.get('impact_radii_meters', {})
            scale_factor = (source_coords.get('radius', 5.0) * 2) / 20.0
            colors = {
                "equipment_damage": "rgba(231,76,60,0.3)",
                "second_degree_burns": "rgba(243,156,18,0.3)",
                "pain_threshold": "rgba(241,196,15,0.3)"
            }
            for effect, radius_m in sorted(radii.items(), key=lambda item: item[1], reverse=True):
                fig.add_shape(
                    type="circle", xref="x", yref="y",
                    x0=source_coords['x']-radius_m*scale_factor,
                    y0=source_coords['y']-radius_m*scale_factor,
                    x1=source_coords['x']+radius_m*scale_factor,
                    y1=source_coords['y']+radius_m*scale_factor,
                    line=dict(color=colors.get(effect, "rgba(255,255,255,0.3)"), width=2, dash="dot"),
                    fillcolor=colors.get(effect, "rgba(255,255,255,0.1)"),
                    layer="below"
                )

    fig.update_layout(
        title=None,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 125]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 115]),
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        height=650,
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(
            bgcolor="#1e293b",
            font_size=12,
            font_family="Inter",
            bordercolor="#0ea5e9"
        )
    )
    
    return dcc.Graph(id='depot-hmi-graph', figure=fig, config={'displayModeBar': False})


def build_inventory_chart(tanks_data):
    """Build a donut chart showing inventory by product."""
    inventory_by_product = {}
    for tank in tanks_data:
        product = tank.get('product_service', 'Unknown')
        volume = float(tank.get('latest_dynamic_state', {}).get('volume_gsv', {}).get('value', 0))
        inventory_by_product[product] = inventory_by_product.get(product, 0) + volume
    
    if not inventory_by_product:
        return html.Div("No inventory data", className="text-center text-muted py-4")
    
    labels = list(inventory_by_product.keys())
    values = [v/1e6 for v in inventory_by_product.values()]
    colors = [PRODUCT_COLORS.get(p, "#95a5a6") for p in labels]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color='#1a1a2e', width=2)),
        textinfo='percent',
        textfont=dict(size=11, color='#fff'),
        hovertemplate="<b>%{label}</b><br>%{value:.2f}M Litres<br>%{percent}<extra></extra>"
    )])
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5,
            font=dict(size=10, color="#a0a0a0")
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=60),
        height=280,
        annotations=[dict(
            text=f"<b>{sum(values):.1f}M</b><br>Total",
            x=0.5, y=0.5, font_size=14, font_color="#fff", showarrow=False
        )]
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


# --- Page Layout Builders ---
def build_overview_layout():
    """Build the main command center overview layout."""
    return html.Div([
        # KPI Row
        dbc.Row([
            dbc.Col([
                html.Div(id='kpi-total-inventory')
            ], lg=3, md=6, className="mb-3"),
            dbc.Col([
                html.Div(id='kpi-usable-ullage')
            ], lg=3, md=6, className="mb-3"),
            dbc.Col([
                html.Div(id='kpi-active-pumps')
            ], lg=3, md=6, className="mb-3"),
            dbc.Col([
                html.Div(id='kpi-daily-throughput')
            ], lg=3, md=6, className="mb-3"),
        ], className="mb-4"),
        
        # Main Content Row
        dbc.Row([
            # Left Column - HMI View
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("Live Depot View", className="section-title"),
                        html.Div([
                            html.Div(className="pulse-dot me-2"),
                            html.Span("LIVE", style={"color": "#38ef7d", "fontSize": "0.75rem", "fontWeight": "600"})
                        ], className="d-flex align-items-center")
                    ], className="d-flex justify-content-between align-items-center mb-3"),
                    dcc.Loading(
                        type="circle",
                        color="#667eea",
                        children=html.Div(id='depot-hmi-view-container')
                    ),
                    # Legend
                    html.Div([
                        html.Div([html.Div(className="legend-dot", style={"background": "#27ae60"}), "Normal"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#f39c12"}), "Warning"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#e74c3c"}), "Critical"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#3498db"}), "Low"], className="legend-item"),
                        html.Div([
                        html.Div(className="legend-dot", style={"background": "#f59e0b"}), "Pump Station"
                    ], className="legend-item"),
                    ], className="tank-legend")
                ], className="glass-card h-100")
            ], lg=8, className="mb-4"),
            
            # Right Column - Sidebar
            dbc.Col([
                # Weather Widget
                html.Div(id='weather-widget-container', className="mb-4"),
                
                # Inventory Breakdown
                html.Div([
                    html.Span("Inventory by Product", className="section-title"),
                    html.Div(id='inventory-chart-container')
                ], className="glass-card mb-4"),
                
                # Active Alerts
                html.Div([
                    html.Div([
                        html.Span("Active Alerts", className="section-title"),
                        html.Span(id='alert-count-badge', className="status-badge status-warning")
                    ], className="d-flex justify-content-between align-items-center"),
                    html.Div(id='active-alerts-list', style={'maxHeight': '250px', 'overflowY': 'auto'})
                ], className="glass-card")
            ], lg=4, className="mb-4"),
        ]),
        
        # Bottom Row - Financial KPIs & Recent Operations
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span("Financial Overview", className="section-title"),
                    dbc.Row([
                        dbc.Col([html.Div(id='kpi-inventory-value')], md=4),
                        dbc.Col([html.Div(id='kpi-daily-cost')], md=4),
                        dbc.Col([html.Div(id='kpi-efficiency')], md=4),
                    ])
                ], className="glass-card")
            ], lg=6, className="mb-4"),
            dbc.Col([
                html.Div([
                    html.Span("Recent Operations", className="section-title"),
                    dcc.Loading(
                        type="circle",
                        color="#667eea",
                        children=html.Div(id='operation-logs-list', style={'maxHeight': '200px', 'overflowY': 'auto'})
                    )
                ], className="glass-card")
            ], lg=6, className="mb-4"),
        ]),
        
        # Last Updated
        html.Div([
            html.I(className="fas fa-sync-alt me-2"),
            html.Span(id='last-updated-time')
        ], className="text-center", style={"color": "#a0a0a0", "fontSize": "0.8rem"})
    ], className="p-4")


def build_historical_analysis_layout():
    """Build the historical data analysis page."""
    return html.Div([
        html.Div([
            html.Span("Historical Data Analysis", className="section-title"),
            html.P("Analyze trends and patterns in your depot data", style={"color": "#a0a0a0", "marginBottom": "1.5rem"})
        ]),
        
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Asset", style={"color": "#a0a0a0", "fontSize": "0.85rem", "marginBottom": "0.5rem"}),
                    dcc.Dropdown(id='history-asset-dropdown', placeholder="Choose an asset...", className="mb-3")
                ], md=3),
                dbc.Col([
                    html.Label("Select Metric", style={"color": "#a0a0a0", "fontSize": "0.85rem", "marginBottom": "0.5rem"}),
                    dcc.Dropdown(id='history-metric-dropdown', placeholder="Choose a metric...", className="mb-3")
                ], md=3),
                dbc.Col([
                    html.Label("Date Range", style={"color": "#a0a0a0", "fontSize": "0.85rem", "marginBottom": "0.5rem"}),
                    dcc.DatePickerRange(
                        id='history-date-picker',
                        start_date=datetime.date.today() - datetime.timedelta(days=7),
                        end_date=datetime.date.today(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    )
                ], md=4),
                dbc.Col([
                    html.Label(" ", style={"display": "block", "marginBottom": "0.5rem"}),
                    dbc.Button([
                        html.I(className="fas fa-chart-line me-2"),
                        "Load Data"
                    ], id="history-load-button", className="btn-primary-gradient w-100")
                ], md=2),
            ])
        ], className="glass-card mb-4"),
        
        dcc.Loading(
            type="circle",
            color="#667eea",
            children=html.Div(id="history-output-container")
        )
    ], className="p-4")


def build_asset_info_layout():
    """Build the asset information page."""
    return html.Div([
        html.Div([
            html.Span("Asset Registry", className="section-title"),
            html.P("Complete inventory of all depot assets", style={"color": "#a0a0a0", "marginBottom": "1.5rem"})
        ]),
        html.Div([
            dcc.Loading(
                type="circle",
                color="#667eea",
                children=html.Div(id="asset-info-table-container")
            )
        ], className="glass-card")
    ], className="p-4")


def build_logbook_layout():
    """Build the manual logbook entry page."""
    return html.Div([
        html.Div([
            html.Span("Operations Logbook", className="section-title"),
            html.P("Record operational events and activities", style={"color": "#a0a0a0", "marginBottom": "1.5rem"})
        ]),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5([html.I(className="fas fa-pen-to-square me-2"), "New Entry"], style={"color": "#fff", "marginBottom": "1.5rem"}),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Your Name", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                            dbc.Input(id='log-user-name', type='text', placeholder="Enter your name...", className="mb-3")
                        ], md=6),
                        dbc.Col([
                            html.Label("Event Type", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                            dcc.Dropdown(
                                id='log-event-type',
                                options=[
                                    {'label': '📋 General', 'value': 'General'},
                                    {'label': '🛡️ Safety Check', 'value': 'Safety Check'},
                                    {'label': '🔧 Maintenance', 'value': 'Maintenance'},
                                    {'label': '🚛 Product Transfer', 'value': 'Product Transfer'},
                                    {'label': '⚠️ Incident', 'value': 'Incident'}
                                ],
                                value='General',
                                className="mb-3"
                            )
                        ], md=6)
                    ]),
                    html.Label("Related Asset (Optional)", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                    dcc.Dropdown(id='log-asset-dropdown', placeholder="Select asset...", className="mb-3"),
                    html.Label("Description", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                    dbc.Textarea(id='log-description', placeholder="Describe the event...", style={'height': '120px'}, className="mb-3"),
                    dbc.Button([
                        html.I(className="fas fa-paper-plane me-2"),
                        "Submit Entry"
                    ], id="log-submit-button", className="btn-primary-gradient"),
                    html.Div(id='log-submission-status', className="mt-3")
                ], className="glass-card")
            ], lg=6),
            dbc.Col([
                html.Div([
                    html.H5([html.I(className="fas fa-clock-rotate-left me-2"), "Recent Entries"], style={"color": "#fff", "marginBottom": "1.5rem"}),
                    html.Div(id='recent-log-entries', style={'maxHeight': '400px', 'overflowY': 'auto'})
                ], className="glass-card")
            ], lg=6)
        ])
    ], className="p-4")


def build_simulation_sandbox_layout():
    """Build the simulation sandbox page."""
    return html.Div([
        html.Div([
            html.Span("Simulation Sandbox", className="section-title"),
            html.P("Run what-if scenarios and predictive simulations", style={"color": "#a0a0a0", "marginBottom": "1.5rem"})
        ]),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5([html.I(className="fas fa-flask me-2"), "Tank Transfer Simulation"], style={"color": "#fff", "marginBottom": "1.5rem"}),
                    html.Label("Source Tank", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                    dcc.Dropdown(id='sim-source-tank-dropdown', placeholder="Select source...", className="mb-3"),
                    html.Label("Destination Tank", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                    dcc.Dropdown(id='sim-dest-tank-dropdown', placeholder="Select destination...", className="mb-3"),
                    html.Label("Transfer Pump", style={"color": "#a0a0a0", "fontSize": "0.85rem"}),
                    dcc.Dropdown(id='sim-pump-dropdown', placeholder="Select pump...", className="mb-3"),
                    dbc.Button([
                        html.I(className="fas fa-play me-2"),
                        "Run Simulation"
                    ], id="run-tank-sim-button", className="btn-primary-gradient w-100 mt-2")
                ], className="glass-card")
            ], lg=4),
            dbc.Col([
                html.Div([
                    html.H5([html.I(className="fas fa-chart-area me-2"), "Simulation Results"], style={"color": "#fff", "marginBottom": "1.5rem"}),
                    dcc.Loading(
                        type="circle",
                        color="#667eea",
                        children=html.Div(id="sim-results-output")
                    )
                ], className="glass-card h-100")
            ], lg=8)
        ])
    ], className="p-4")


def build_log_viewer_layout():
    """Build the system log viewer page."""
    return html.Div([
        html.Div([
            html.Span("System Logs", className="section-title"),
            html.P("Real-time dashboard activity logs", style={"color": "#a0a0a0", "marginBottom": "1.5rem"})
        ]),
        html.Div([
            dcc.Textarea(
                id='log-viewer-textarea',
                style={
                    'width': '100%', 'height': '600px',
                    'fontFamily': 'JetBrains Mono, monospace',
                    'fontSize': '12px',
                    'backgroundColor': '#0d1b2a',
                    'color': '#38ef7d',
                    'border': '1px solid rgba(255,255,255,0.1)',
                    'borderRadius': '8px',
                    'padding': '1rem'
                },
                readOnly=True
            )
        ], className="glass-card")
    ], className="p-4")


# --- Main App Layout ---
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>''' + CUSTOM_CSS + '''</style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
    
    # Data stores
    dcc.Store(id='api-data-store'),
    dcc.Store(id='fire-sim-results-store'),
    dcc.Interval(id='api-update-interval', interval=15 * 1000, n_intervals=0),
    dcc.Interval(id='log-update-interval', interval=5 * 1000, n_intervals=0),
    
    # Navbar
    dbc.Navbar([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-industry me-3", style={"fontSize": "1.5rem", "color": "#667eea"}),
                        html.Span("Fuel Depot Digital Twin", className="navbar-brand mb-0")
                    ], className="d-flex align-items-center")
                ]),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Div(className="pulse-dot"),
                        ], className="me-2"),
                        html.Span("System Online", style={"color": "#38ef7d", "fontSize": "0.85rem"})
                    ], className="d-flex align-items-center justify-content-end")
                ])
            ], className="w-100", align="center")
        ], fluid=True)
    ], className="navbar", dark=True),
    
    # Navigation Tabs
    dcc.Tabs(
        id="app-tabs",
        value='tab-overview',
        parent_className='tab-parent',
        className='custom-tabs',
        children=[
            dcc.Tab(label='Command Center', value='tab-overview', className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Simulations', value='tab-sandbox', className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Logbook', value='tab-logbook', className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Analytics', value='tab-history', className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Assets', value='tab-assets', className='tab', selected_className='tab--selected'),
            dcc.Tab(label='System Logs', value='tab-logs', className='tab', selected_className='tab--selected'),
        ]
    ),
    
    # Main Content
    html.Div(id='app-content'),
    
    # Safety Simulation Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle([
            html.I(className="fas fa-fire-flame-curved me-2", style={"color": "#e74c3c"}),
            "Safety Simulation"
        ]), close_button=True),
        dbc.ModalBody(id="safety-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-fire-sim", className="me-2", outline=True, color="secondary"),
            dbc.Button([
                html.I(className="fas fa-fire me-2"),
                "Run Fire Simulation"
            ], id="run-fire-sim-button", color="danger")
        ]),
    ], id="safety-modal", is_open=False, centered=True),
])


# --- Callbacks ---
@app.callback(Output('app-content', 'children'), Input('app-tabs', 'value'))
def render_tab_content(tab):
    if tab == 'tab-overview':
        return build_overview_layout()
    elif tab == 'tab-history':
        return build_historical_analysis_layout()
    elif tab == 'tab-assets':
        return build_asset_info_layout()
    elif tab == 'tab-logs':
        return build_log_viewer_layout()
    elif tab == 'tab-logbook':
        return build_logbook_layout()
    elif tab == 'tab-sandbox':
        return build_simulation_sandbox_layout()
    return html.P("Page not found.", className="text-center text-muted p-5")


@app.callback(Output('api-data-store', 'data'), Input('api-update-interval', 'n_intervals'))
def update_api_data(n):
    logger.info("Fetching latest data from API...")
    assets_data = get_api_data('/api/v1/assets', payload={'per_page': 500})
    alerts_data = get_api_data('/api/v1/alerts/active')
    logs_data = get_api_data('/api/v1/logs')
    weather_data = fetch_weather_data()
    logger.info("API data fetch complete.")
    return {
        'assets': assets_data.get('assets', []) if isinstance(assets_data, dict) else [],
        'alerts': alerts_data if isinstance(alerts_data, list) else [],
        'logs': logs_data if isinstance(logs_data, list) else [],
        'weather': weather_data,
        'last_updated': datetime.datetime.now().isoformat()
    }


@app.callback(
    [Output('kpi-total-inventory', 'children'),
     Output('kpi-usable-ullage', 'children'),
     Output('kpi-active-pumps', 'children'),
     Output('kpi-daily-throughput', 'children'),
     Output('kpi-inventory-value', 'children'),
     Output('kpi-daily-cost', 'children'),
     Output('kpi-efficiency', 'children'),
     Output('depot-hmi-view-container', 'children'),
     Output('active-alerts-list', 'children'),
     Output('alert-count-badge', 'children'),
     Output('operation-logs-list', 'children'),
     Output('weather-widget-container', 'children'),
     Output('inventory-chart-container', 'children'),
     Output('last-updated-time', 'children')],
    [Input('api-data-store', 'data'), Input('fire-sim-results-store', 'data')]
)
def update_all_components(data, fire_sim_results):
    try:
        if not data or not data.get('assets'):
            loading = html.Div([
                dbc.Spinner(color="primary", size="sm"),
                html.Span(" Loading...", className="ms-2")
            ], className="text-center py-3")
            return (loading,) * 13 + ("Connecting...",)
        
        assets = data.get('assets', [])
        tanks = [a for a in assets if a.get('asset_type') == 'StorageTank']
        
        # Calculate KPIs
        total_inv = sum(float(t.get('latest_dynamic_state', {}).get('volume_gsv', {}).get('value', 0)) for t in tanks)
        total_cap = sum(float(t.get('capacity_litres', 0)) for t in tanks)
        usable_ullage = total_cap - total_inv
        
        inventory_by_product = {}
        for tank in tanks:
            product = tank.get('product_service', 'Unknown')
            volume = float(tank.get('latest_dynamic_state', {}).get('volume_gsv', {}).get('value', 0))
            inventory_by_product[product] = inventory_by_product.get(product, 0) + volume
        
        inv_value = sum(vol * PRODUCT_PRICING.get(prod.split()[0] if prod else 'Default', PRODUCT_PRICING['Default']) for prod, vol in inventory_by_product.items())
        active_pumps = sum(1 for a in assets if a.get('asset_type') == 'Pump' and a.get('is_active'))
        total_pumps = sum(1 for a in assets if a.get('asset_type') == 'Pump')
        
        daily_kwh = active_pumps * PUMP_POWER_KW * ESTIMATED_DAILY_HOURS_PER_PUMP
        daily_electricity_cost = (daily_kwh * ELECTRICITY_RATE_PER_KWH) + SERVICE_CHARGE
        
        # Build KPI cards
        kpi_inventory = build_kpi_card("Total Inventory", f"{total_inv/1e6:.2f}", "M Litres", "fa-oil-can", "#0ea5e9")
        kpi_ullage = build_kpi_card("Usable Ullage", f"{usable_ullage/1e6:.2f}", "M Litres", "fa-arrow-up-from-bracket", "#22c55e")
        kpi_pumps = build_kpi_card("Active Pumps", f"{active_pumps}/{total_pumps}", "", "fa-gauge-high", "#f59e0b")
        kpi_throughput = build_kpi_card("Daily Throughput", "10.1", "M Litres", "fa-truck-fast", "#8b5cf6")
        
        kpi_value = build_kpi_card("Inventory Value", f"${inv_value/1e6:.2f}M", "", "fa-dollar-sign", "#22c55e")
        kpi_cost = build_kpi_card("Daily Op. Cost", f"${daily_electricity_cost:,.0f}", "", "fa-bolt", "#f59e0b")
        kpi_efficiency = build_kpi_card("Efficiency", "94.2%", "", "fa-chart-line", "#0ea5e9")
        
        # Alerts
        alerts = data.get('alerts', [])
        alert_count = f"{len(alerts)} Active" if alerts else "0 Active"
        
        # Logs
        logs = data.get('logs', [])
        if logs:
            log_items = []
            for log in logs[:5]:
                log_items.append(html.Div([
                    html.Div([
                        html.Span(log.get('event_type', 'Event'), className="status-badge status-online me-2"),
                        html.Span(log.get('user_name', 'System'), style={"color": "#fff", "fontWeight": "500"})
                    ], className="d-flex align-items-center mb-1"),
                    html.P(log.get('description', '')[:80] + "..." if len(log.get('description', '')) > 80 else log.get('description', ''), 
                           className="mb-0", style={"fontSize": "0.8rem", "color": "#a0a0a0"})
                ], className="alert-item alert-info"))
            log_list = html.Div(log_items)
        else:
            log_list = html.Div("No recent operations", className="text-center text-muted py-3")
        
        # Weather
        weather = data.get('weather', {})
        weather_widget = build_weather_widget(weather)
        
        # Inventory chart
        inventory_chart = build_inventory_chart(tanks)
        
        # Last updated
        last_updated = f"Last updated: {pd.to_datetime(data.get('last_updated')).strftime('%H:%M:%S')}"
        
        return (
            kpi_inventory, kpi_ullage, kpi_pumps, kpi_throughput,
            kpi_value, kpi_cost, kpi_efficiency,
            build_depot_hmi_view(assets, fire_sim_results),
            build_alerts_section(alerts),
            alert_count,
            log_list,
            weather_widget,
            inventory_chart,
            last_updated
        )
    except Exception as e:
        logger.error(f"Error in main update callback: {e}", exc_info=True)
        error_msg = html.Div([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error: {str(e)}"
        ], className="text-danger")
        return (error_msg,) * 13 + ("Error",)


@app.callback(
    [Output("safety-modal", "is_open"), Output("safety-modal-body", "children")],
    Input("depot-hmi-graph", "clickData"),
    prevent_initial_call=True
)
def open_safety_modal(click_data):
    if not click_data:
        return False, ""
    try:
        asset_id = click_data['points'][0]['customdata']
        return True, html.Div([
            html.P([
                "Run fire consequence simulation for ",
                html.Strong(asset_id, style={"color": "#667eea"}),
                "?"
            ]),
            html.P("This will calculate thermal radiation zones for emergency planning.", 
                   style={"color": "#a0a0a0", "fontSize": "0.9rem"}),
            dcc.Store(id='selected-tank-for-sim', data=asset_id)
        ])
    except:
        return False, ""


@app.callback(
    [Output('fire-sim-results-store', 'data'), Output("safety-modal", "is_open", allow_duplicate=True)],
    Input('run-fire-sim-button', 'n_clicks'),
    State('selected-tank-for-sim', 'data'),
    prevent_initial_call=True
)
def run_fire_simulation(n_clicks, asset_id):
    if not n_clicks:
        return dash.no_update, True
    results = get_api_data('/api/v1/simulations/fire-consequence', payload={'asset_id': asset_id}, method='POST')
    return results, False


# --- Historical Analysis Callbacks ---
@app.callback(Output('history-asset-dropdown', 'options'), Input('app-tabs', 'value'), State('api-data-store', 'data'))
def populate_history_asset_dropdown(tab, data):
    if tab != 'tab-history' or not data or not data.get('assets'):
        return []
    return [{'label': f"🛢️ {a['asset_id']}" if a.get('asset_type') == 'StorageTank' else f"⚙️ {a['asset_id']}", 'value': a['asset_id']} for a in data['assets']]


@app.callback(Output('history-metric-dropdown', 'options'), Input('history-asset-dropdown', 'value'))
def populate_history_metric_dropdown(asset_id):
    if not asset_id:
        return []
    asset_details = get_api_data(f'/api/v1/assets/{asset_id}')
    if not asset_details or 'latest_dynamic_state' not in asset_details:
        return []
    return [{'label': m.replace('_', ' ').title(), 'value': m} for m in asset_details['latest_dynamic_state'].keys()]


@app.callback(
    Output('history-output-container', 'children'),
    Input('history-load-button', 'n_clicks'),
    [State('history-asset-dropdown', 'value'), State('history-metric-dropdown', 'value'),
     State('history-date-picker', 'start_date'), State('history-date-picker', 'end_date')],
    prevent_initial_call=True
)
def load_historical_data(n_clicks, asset_id, metric, start_date, end_date):
    if not all([asset_id, metric, start_date, end_date]):
        return html.Div([
            html.I(className="fas fa-info-circle me-2"),
            "Please select all fields to load data."
        ], className="glass-card text-center py-4", style={"color": "#f39c12"})
    
    params = {'start_time': start_date, 'end_time': end_date, 'limit': 5000}
    history_data = get_api_data(f'/api/v1/assets/{asset_id}/metrics/{metric}/history', payload=params)
    
    if not history_data:
        return html.Div([
            html.I(className="fas fa-database me-2"),
            f"No historical data found for {asset_id} - {metric}."
        ], className="glass-card text-center py-4", style={"color": "#a0a0a0"})
    
    df = pd.DataFrame(history_data)
    df['time'] = pd.to_datetime(df['time'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['value'],
        mode='lines',
        line=dict(color='#667eea', width=2),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)',
        name=metric
    ))
    
    fig.update_layout(
        title=None,
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title=None),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title=df.iloc[0]['unit'] if not df.empty and 'unit' in df.columns else ''),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a0a0a0'),
        height=400,
        margin=dict(l=50, r=20, t=20, b=50),
        hovermode='x unified'
    )
    
    return html.Div([
        html.Div([
            html.H5([
                html.I(className="fas fa-chart-line me-2"),
                f"{asset_id} - {metric.replace('_', ' ').title()}"
            ], style={"color": "#fff"}),
            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ], className="glass-card mb-4"),
        html.Div([
            html.H5([html.I(className="fas fa-table me-2"), "Raw Data"], style={"color": "#fff", "marginBottom": "1rem"}),
            dash_table.DataTable(
                data=history_data[:100],
                columns=[{'name': c.replace('_', ' ').title(), 'id': c} for c in ['time', 'value', 'unit']],
                page_size=10,
                style_header={'backgroundColor': '#1e2a4a', 'color': '#fff', 'fontWeight': '600', 'border': 'none'},
                style_cell={'backgroundColor': '#16213e', 'color': '#eaeaea', 'border': 'none', 'padding': '12px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#1a2744'}]
            )
        ], className="glass-card")
    ])


# --- Asset Info Callback ---
@app.callback(Output('asset-info-table-container', 'children'), Input('app-tabs', 'value'), State('api-data-store', 'data'))
def load_asset_info_table(tab, data):
    if tab != 'tab-assets' or not data or not data.get('assets'):
        return html.Div("Loading asset data...", className="text-center text-muted py-4")
    
    datasheet_data = [{k: v for k, v in asset.items() if k != 'latest_dynamic_state'} for asset in data['assets']]
    if not datasheet_data:
        return html.Div("No asset data available.", className="text-center text-muted py-4")
    
    return dash_table.DataTable(
        data=datasheet_data,
        columns=[{'name': c.replace('_', ' ').title(), 'id': c} for c in datasheet_data[0].keys()],
        page_size=15,
        sort_action="native",
        filter_action="native",
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': '#1e2a4a', 'color': '#fff', 'fontWeight': '600', 'border': 'none', 'padding': '12px'},
        style_cell={'backgroundColor': '#16213e', 'color': '#eaeaea', 'border': 'none', 'padding': '10px', 'textAlign': 'left', 'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#1a2744'}],
        style_filter={'backgroundColor': '#1e2a4a', 'color': '#fff'}
    )


# --- Log Viewer Callback ---
@app.callback(Output('log-viewer-textarea', 'value'), Input('log-update-interval', 'n_intervals'))
def update_log_viewer(n):
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()[-100:]
            return "".join(lines)
    except FileNotFoundError:
        return f"# Log file not found at: {LOG_FILE}\n# Logs will appear here once the system starts logging."
    except Exception as e:
        return f"# Error reading log file: {e}"


# --- Logbook Callbacks ---
@app.callback(Output('log-asset-dropdown', 'options'), Input('app-tabs', 'value'), State('api-data-store', 'data'))
def populate_logbook_asset_dropdown(tab, data):
    if tab != 'tab-logbook' or not data or not data.get('assets'):
        return []
    return [{'label': a['asset_id'], 'value': a['asset_id']} for a in data['assets']]


@app.callback(
    Output('log-submission-status', 'children'),
    Input('log-submit-button', 'n_clicks'),
    [State('log-user-name', 'value'), State('log-event-type', 'value'),
     State('log-description', 'value'), State('log-asset-dropdown', 'value')],
    prevent_initial_call=True
)
def submit_log_entry(n_clicks, user, event_type, desc, asset_id):
    if not all([user, event_type, desc]):
        return html.Div([
            html.I(className="fas fa-exclamation-circle me-2"),
            "Please fill in all required fields."
        ], style={"color": "#f39c12"})
    
    payload = {"user_name": user, "event_type": event_type.upper(), "description": desc, "related_asset_id": asset_id}
    response = get_api_data('/api/v1/logs', payload=payload, method='POST')
    
    if response and response.get('message'):
        return html.Div([
            html.I(className="fas fa-check-circle me-2"),
            "Log entry submitted successfully!"
        ], style={"color": "#38ef7d"})
    else:
        return html.Div([
            html.I(className="fas fa-times-circle me-2"),
            "Failed to submit log entry."
        ], style={"color": "#e74c3c"})


# --- Simulation Callbacks ---
@app.callback(
    [Output('sim-source-tank-dropdown', 'options'), Output('sim-dest-tank-dropdown', 'options'), Output('sim-pump-dropdown', 'options')],
    Input('app-tabs', 'value'),
    State('api-data-store', 'data')
)
def populate_sim_dropdowns(tab, data):
    if tab != 'tab-sandbox' or not data or not data.get('assets'):
        return [], [], []
    tanks = [{'label': f"🛢️ {a['asset_id']}", 'value': a['asset_id']} for a in data['assets'] if a.get('asset_type') == 'StorageTank']
    pumps = [{'label': f"⚙️ {a['asset_id']}", 'value': a['asset_id']} for a in data['assets'] if a.get('asset_type') == 'Pump']
    return tanks, tanks, pumps


@app.callback(
    Output('sim-results-output', 'children'),
    Input('run-tank-sim-button', 'n_clicks'),
    [State('sim-source-tank-dropdown', 'value'), State('sim-dest-tank-dropdown', 'value'), State('sim-pump-dropdown', 'value')],
    prevent_initial_call=True
)
def run_tank_transfer_simulation(n_clicks, source_tank, dest_tank, pump_id):
    if not all([source_tank, dest_tank, pump_id]):
        return html.Div([
            html.I(className="fas fa-info-circle me-2"),
            "Please select source, destination, and pump."
        ], style={"color": "#f39c12"})
    
    payload = {"source_tank_id": source_tank, "destination_tank_id": dest_tank, "pump_id": pump_id}
    results = get_api_data('/api/v1/simulations/tank-transfer', payload, 'POST')
    
    if not results or 'results' not in results:
        return html.Div([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Simulation failed. Check API server logs."
        ], style={"color": "#e74c3c"})
    
    sim_results = results.get('results', {})
    timestamps = sim_results.get('timestamps', [])
    source_vol = sim_results.get('source_tank_volume', [])
    dest_vol = sim_results.get('dest_tank_volume', [])
    
    fig = go.Figure()
    if timestamps:
        fig.add_trace(go.Scatter(
            x=timestamps, y=source_vol,
            name=f'{source_tank}',
            mode='lines',
            line=dict(color='#e74c3c', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=timestamps, y=dest_vol,
            name=f'{dest_tank}',
            mode='lines',
            line=dict(color='#27ae60', width=2)
        ))
        
        fig.update_layout(
            title=None,
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Time"),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Volume (Litres)"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#a0a0a0'),
            height=350,
            margin=dict(l=50, r=20, t=20, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )

    return html.Div([
        html.Div([
            html.I(className="fas fa-check-circle me-2", style={"color": "#38ef7d"}),
            html.Span("Simulation Complete", style={"color": "#38ef7d", "fontWeight": "600"})
        ], className="mb-3"),
        dcc.Graph(figure=fig, config={'displayModeBar': False})
    ])


# --- Main Execution Block ---
# Expose server for gunicorn (Render deployment)
server = app.server

if __name__ == '__main__':
    print("\n🚀 Dashboard running at: http://127.0.0.1:8050\n")
    app.run(debug=True, port=8050)
