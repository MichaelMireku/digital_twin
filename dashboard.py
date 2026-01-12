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
LATITUDE, LONGITUDE = 5.7194, -0.0847  # Oyibi, Ghana (near Dodowa)

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --primary: #000000;
    --primary-light: #333333;
    --primary-dark: #000000;
    --accent: #555555;
    --success: #22c55e;
    --success-light: #4ade80;
    --warning: #f59e0b;
    --warning-light: #fbbf24;
    --danger: #ef4444;
    --danger-light: #f87171;
    --bg-primary: #ffffff;
    --bg-secondary: #f8f9fa;
    --card-bg: #ffffff;
    --card-bg-hover: #f8f9fa;
    --card-border: #e5e7eb;
    --card-border-hover: #d1d5db;
    --text-primary: #111827;
    --text-secondary: #4b5563;
    --text-muted: #9ca3af;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

* {
    scrollbar-width: thin;
    scrollbar-color: #d1d5db #f3f4f6;
}

*::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

*::-webkit-scrollbar-track {
    background: #f3f4f6;
    border-radius: 3px;
}

*::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 3px;
}

*::-webkit-scrollbar-thumb:hover {
    background: #9ca3af;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background: var(--bg-secondary) !important;
    min-height: 100vh;
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow-x: hidden;
}

/* Clean Navbar */
.navbar {
    background: #ffffff !important;
    border-bottom: 1px solid var(--card-border);
    padding: 0.875rem 2rem !important;
    box-shadow: var(--shadow-sm);
    position: sticky;
    top: 0;
    z-index: 1000;
    max-width: 100%;
}

.navbar-brand {
    font-weight: 700 !important;
    font-size: 1.35rem !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.025em;
}

.navbar-brand i {
    color: #000000;
}

/* Clean KPI Cards */
.kpi-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 1.5rem;
    height: 100%;
    position: relative;
    transition: all 0.2s ease;
}

.kpi-card:hover {
    border-color: var(--card-border-hover);
    box-shadow: var(--shadow-md);
}

.kpi-icon {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    margin-bottom: 1rem;
    color: #fff;
}

.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
    letter-spacing: -0.025em;
    line-height: 1.2;
}

.kpi-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 500;
}

.kpi-trend {
    display: inline-flex;
    align-items: center;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    margin-top: 0.75rem;
}

.kpi-trend.trend-up {
    background: rgba(34, 197, 94, 0.1);
    color: var(--success);
}

.kpi-trend.trend-down {
    background: rgba(239, 68, 68, 0.1);
    color: var(--danger);
}

/* Glass Card Effect */
.glass-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 1.5rem;
    transition: all 0.2s ease;
}

.glass-card:hover {
    border-color: var(--card-border-hover);
}

/* Section Titles */
.section-title {
    color: var(--text-primary);
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    letter-spacing: -0.01em;
}

.section-title::before {
    content: '';
    width: 4px;
    height: 20px;
    background: #000000;
    border-radius: 2px;
}

/* Alert Items */
.alert-item {
    background: var(--bg-secondary);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    border-left: 4px solid;
    transition: all 0.2s ease;
}

.alert-item:hover {
    background: #f3f4f6;
}

.alert-critical { border-left-color: var(--danger); }
.alert-warning { border-left-color: var(--warning); }
.alert-info { border-left-color: #000000; }

/* Weather Widget */
.weather-widget {
    background: #000000;
    border-radius: 12px;
    padding: 1.5rem;
    color: #fff;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.weather-temp {
    font-size: 2.5rem;
    font-weight: 700;
    letter-spacing: -0.025em;
}

.weather-desc {
    font-size: 0.9rem;
    opacity: 0.9;
    font-weight: 500;
}

/* Status Badges */
.status-badge {
    padding: 0.3rem 0.75rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.status-online { 
    background: rgba(34, 197, 94, 0.1); 
    color: var(--success);
    border: 1px solid rgba(34, 197, 94, 0.2);
}

.status-offline { 
    background: rgba(239, 68, 68, 0.1); 
    color: var(--danger);
    border: 1px solid rgba(239, 68, 68, 0.2);
}

.status-warning { 
    background: rgba(245, 158, 11, 0.1); 
    color: var(--warning);
    border: 1px solid rgba(245, 158, 11, 0.2);
}

/* Clean Tabs */
.tab-parent {
    background: var(--card-bg) !important;
    border-radius: 10px;
    margin: 1.25rem 2rem;
    padding: 0.375rem;
    border: 1px solid var(--card-border);
    max-width: calc(100% - 4rem);
    overflow-x: auto;
}

.tab {
    background: transparent !important;
    border: none !important;
    color: var(--text-secondary) !important;
    padding: 0.625rem 1.25rem !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}

.tab:hover {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}

.tab--selected {
    background: #000000 !important;
    color: #fff !important;
    border: none !important;
}

/* Data Tables */
.dash-spreadsheet-container .dash-spreadsheet-inner th {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    font-weight: 600;
    border: none !important;
    border-bottom: 2px solid var(--card-border) !important;
    padding: 1rem !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.dash-spreadsheet-container .dash-spreadsheet-inner td {
    background: var(--card-bg) !important;
    color: var(--text-secondary) !important;
    border: none !important;
    border-bottom: 1px solid var(--card-border) !important;
    padding: 0.875rem 1rem !important;
    font-size: 0.875rem;
}

.dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}

/* Buttons */
.btn-primary-gradient {
    background: #000000;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    color: #fff;
    font-size: 0.875rem;
    transition: all 0.2s ease;
}

.btn-primary-gradient:hover {
    background: #333333;
}

/* Pulse Animation */
.pulse-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--success);
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%, 100% { 
        box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.5);
        transform: scale(1);
    }
    50% { 
        box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
        transform: scale(1.05);
    }
}

/* Tank Legend */
.tank-legend {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--card-border);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
}

.legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 4px;
}

/* Dropdown Styling */
.Select-control {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 8px !important;
    min-height: 42px !important;
}

.Select-control:hover {
    border-color: #000000 !important;
}

.Select-value-label, .Select-placeholder {
    color: var(--text-secondary) !important;
}

.Select-menu-outer {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 8px !important;
    box-shadow: var(--shadow-lg) !important;
    margin-top: 4px !important;
}

.Select-option {
    background: transparent !important;
    color: var(--text-secondary) !important;
    padding: 0.75rem 1rem !important;
}

.Select-option:hover, .Select-option.is-focused {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}

.Select-option.is-selected {
    background: #f3f4f6 !important;
    color: #000000 !important;
}

/* Input Fields */
.form-control, input[type="text"], textarea {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    padding: 0.75rem 1rem !important;
    transition: all 0.2s ease;
}

.form-control:focus, input[type="text"]:focus, textarea:focus {
    border-color: #000000 !important;
    box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1) !important;
    outline: none !important;
}

/* Date Picker */
.DateInput_input {
    background: var(--card-bg) !important;
    color: var(--text-primary) !important;
    border-radius: 6px !important;
    font-size: 0.875rem !important;
}

.DateRangePickerInput {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 8px !important;
}

/* Loading Spinner */
._dash-loading {
    background: transparent !important;
}

.dash-spinner {
    border-color: #000000 !important;
    border-top-color: transparent !important;
}

/* Modal Styling */
.modal-content {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-lg) !important;
}

.modal-header {
    border-bottom: 1px solid var(--card-border) !important;
    padding: 1.25rem 1.5rem !important;
}

.modal-body {
    padding: 1.5rem !important;
    color: var(--text-secondary);
}

.modal-footer {
    border-top: 1px solid var(--card-border) !important;
    padding: 1rem 1.5rem !important;
}

.modal-title {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

/* Fade In Animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.3s ease-out forwards;
}

/* Responsive Adjustments */
@media (max-width: 768px) {
    .navbar {
        padding: 0.75rem 1rem !important;
    }
    
    .tab-parent {
        margin: 1rem;
        max-width: calc(100% - 2rem);
        overflow-x: auto;
    }
    
    .kpi-value {
        font-size: 1.5rem;
    }
    
    .glass-card {
        padding: 1rem;
    }
    
    .p-4 {
        padding: 1rem !important;
    }
}

/* Custom Scrollbar for specific containers */
.alert-scroll, .log-scroll {
    max-height: 300px;
    overflow-y: auto;
    padding-right: 0.5rem;
}

/* Hover Effects for Interactive Elements */
.interactive-element {
    cursor: pointer;
    transition: all 0.2s ease;
}

.interactive-element:hover {
    transform: scale(1.02);
}
"""

# --- Dash App Initialization ---
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True,
    serve_locally=False  # Use CDN for Plotly.js - faster loading on free tier
)
app.title = "Fuel Depot Digital Twin"

# --- API & Data Helper Functions ---
def get_api_data(endpoint: str, payload: dict = None, method: str = 'GET') -> dict:
    if not API_KEY:
        logger.error("API Key not configured for dashboard.")
        return {"error": "API Key not configured"}
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
    except requests.exceptions.HTTPError as e:
        # Capture the error message from API response
        error_msg = "Request failed"
        try:
            error_data = e.response.json()
            error_msg = error_data.get('description') or error_data.get('message') or error_data.get('error') or str(e)
        except:
            error_msg = str(e)
        logger.error(f"API call to {endpoint} failed: {error_msg}")
        return {"error": error_msg}
    except requests.exceptions.RequestException as e:
        logger.error(f"API call to {endpoint} failed: {e}")
        return {"error": f"Connection error: {str(e)}"}

# Weather cache to avoid rate limiting
_weather_cache = {"data": None, "timestamp": 0}
WEATHER_CACHE_TTL = 300  # 5 minutes
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

def fetch_weather_data():
    import time
    current_time = time.time()
    
    # Return cached data if still valid
    if _weather_cache["data"] and (current_time - _weather_cache["timestamp"]) < WEATHER_CACHE_TTL:
        return _weather_cache["data"]
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LATITUDE}&lon={LONGITUDE}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        weather_main = data.get('weather', [{}])[0]
        main_data = data.get('main', {})
        wind_data = data.get('wind', {})
        
        description = weather_main.get('description', 'Unknown').title()
        icon = get_weather_icon(weather_main.get('icon', ''))
        
        result = {
            "description": description,
            "temp": f"{main_data.get('temp', 0):.1f}",
            "wind_speed": f"{wind_data.get('speed', 0) * 3.6:.1f}",  # Convert m/s to km/h
            "humidity": f"{main_data.get('humidity', 0)}",
            "icon": icon
        }
        # Update cache
        _weather_cache["data"] = result
        _weather_cache["timestamp"] = current_time
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenWeather API call failed: {e}")
        # Return cached data if available, otherwise fallback
        if _weather_cache["data"]:
            return _weather_cache["data"]
        return {"description": "Unavailable", "temp": "--", "wind_speed": "--", "humidity": "--", "icon": "fa-cloud-question"}

def get_weather_icon(icon_code):
    """Map OpenWeather icon codes to Font Awesome icons."""
    icon_map = {
        '01d': 'fa-sun', '01n': 'fa-moon',
        '02d': 'fa-cloud-sun', '02n': 'fa-cloud-moon',
        '03d': 'fa-cloud', '03n': 'fa-cloud',
        '04d': 'fa-cloud', '04n': 'fa-cloud',
        '09d': 'fa-cloud-showers-heavy', '09n': 'fa-cloud-showers-heavy',
        '10d': 'fa-cloud-rain', '10n': 'fa-cloud-rain',
        '11d': 'fa-bolt', '11n': 'fa-bolt',
        '13d': 'fa-snowflake', '13n': 'fa-snowflake',
        '50d': 'fa-smog', '50n': 'fa-smog',
    }
    return icon_map.get(icon_code, 'fa-cloud')


def format_large_number(value, prefix="", suffix=""):
    """Format large numbers with K, M, B suffixes."""
    if value >= 1e9:
        return f"{prefix}{value/1e9:.2f}B{suffix}"
    elif value >= 1e6:
        return f"{prefix}{value/1e6:.2f}M{suffix}"
    elif value >= 1e3:
        return f"{prefix}{value/1e3:.2f}K{suffix}"
    else:
        return f"{prefix}{value:.2f}{suffix}"


# --- UI Component Builders ---
def build_kpi_card(title, value, unit, icon, bg_color, trend=None, trend_value=None, subtitle=None):
    """Build a professional KPI card with icon, trend indicator, and optional subtitle."""
    trend_element = None
    if trend and trend_value:
        trend_class = "trend-up" if trend == "up" else "trend-down"
        trend_icon = "fa-trending-up" if trend == "up" else "fa-trending-down"
        trend_element = html.Div([
            html.I(className=f"fas {trend_icon} me-1"),
            html.Span(trend_value)
        ], className=f"kpi-trend {trend_class}")
    
    # Create gradient background based on color
    gradient_map = {
        "#0ea5e9": "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
        "#3b82f6": "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
        "#22c55e": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        "#10b981": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        "#f59e0b": "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
        "#8b5cf6": "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)",
        "#ef4444": "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
    }
    gradient = gradient_map.get(bg_color, f"linear-gradient(135deg, {bg_color} 0%, {bg_color} 100%)")
    
    return html.Div([
        html.Div([
            html.Div([
                html.I(className=f"fas {icon}")
            ], className="kpi-icon", style={"background": gradient}),
            html.Div([
                html.Div([
                    html.Span(value, style={"fontSize": "2rem", "fontWeight": "800", "letterSpacing": "-0.025em"}),
                    html.Span(f" {unit}" if unit else "", style={"fontSize": "1rem", "fontWeight": "500", "color": "#9ca3af", "marginLeft": "0.25rem"})
                ], className="kpi-value", style={"marginBottom": "0.25rem"}),
                html.Div(title, className="kpi-label"),
                html.Div(subtitle, style={"fontSize": "0.7rem", "color": "#6b7280", "marginTop": "0.25rem"}) if subtitle else None,
            ], style={"flex": "1"})
        ], className="d-flex align-items-start gap-3"),
        trend_element
    ], className="kpi-card")


def build_weather_widget(weather_data):
    """Build a professional weather widget with glassmorphism effect."""
    return html.Div([
        html.Div([
            html.Div([
                html.I(className=f"fas {weather_data.get('icon', 'fa-cloud')} fa-3x", 
                       style={"filter": "drop-shadow(0 4px 6px rgba(0,0,0,0.3))"}),
            ], className="mb-3"),
            html.Div(f"{weather_data.get('temp', '--')}°C", className="weather-temp"),
            html.Div(weather_data.get('description', 'Unknown'), className="weather-desc mb-3"),
        ]),
        html.Div(style={"height": "1px", "background": "rgba(255,255,255,0.2)", "margin": "0.75rem 0"}),
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-wind", style={"fontSize": "1rem", "opacity": "0.8"}),
                ], style={"marginBottom": "0.25rem"}),
                html.Div(f"{weather_data.get('wind_speed', '--')}", style={"fontWeight": "700", "fontSize": "1.1rem"}),
                html.Div("km/h", style={"fontSize": "0.7rem", "opacity": "0.7"})
            ], className="text-center", style={"flex": "1"}),
            html.Div(style={"width": "1px", "background": "rgba(255,255,255,0.2)"}),
            html.Div([
                html.Div([
                    html.I(className="fas fa-droplet", style={"fontSize": "1rem", "opacity": "0.8"}),
                ], style={"marginBottom": "0.25rem"}),
                html.Div(f"{weather_data.get('humidity', '--')}", style={"fontWeight": "700", "fontSize": "1.1rem"}),
                html.Div("%", style={"fontSize": "0.7rem", "opacity": "0.7"})
            ], className="text-center", style={"flex": "1"}),
        ], className="d-flex align-items-center", style={"padding": "0.5rem 0"})
    ], className="weather-widget")


def build_alert_item(alert):
    """Build a professional styled alert item."""
    severity = alert.get('severity', 'warning').lower()
    severity_class = f"alert-{severity}" if severity in ['critical', 'warning', 'info'] else 'alert-warning'
    
    icon_map = {
        'critical': ('fa-circle-exclamation', '#ef4444'),
        'warning': ('fa-triangle-exclamation', '#f59e0b'),
        'info': ('fa-circle-info', '#3b82f6')
    }
    icon, color = icon_map.get(severity, ('fa-triangle-exclamation', '#f59e0b'))
    
    time_ago = alert.get('created_at', '')
    if time_ago:
        try:
            from datetime import datetime
            created = datetime.fromisoformat(time_ago.replace('Z', '+00:00'))
            diff = datetime.now(created.tzinfo) - created if created.tzinfo else datetime.now() - created
            if diff.days > 0:
                time_ago = f"{diff.days}d ago"
            elif diff.seconds > 3600:
                time_ago = f"{diff.seconds // 3600}h ago"
            else:
                time_ago = f"{diff.seconds // 60}m ago"
        except:
            time_ago = ""
    
    return html.Div([
        html.Div([
            html.Div([
                html.I(className=f"fas {icon}", style={"color": color, "fontSize": "1rem"}),
            ], style={
                "width": "32px", "height": "32px", "borderRadius": "8px",
                "background": f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)",
                "display": "flex", "alignItems": "center", "justifyContent": "center", "flexShrink": "0"
            }),
            html.Div([
                html.Div([
                    html.Span(alert.get('alert_name', 'Alert'), style={"fontWeight": "600", "color": "#111827", "fontSize": "0.875rem"}),
                    html.Span(time_ago, style={"fontSize": "0.7rem", "color": "#6b7280", "marginLeft": "auto"}) if time_ago else None
                ], className="d-flex align-items-center justify-content-between"),
                html.P(alert.get('message', ''), className="mb-0", style={"fontSize": "0.8rem", "color": "#4b5563", "marginTop": "0.25rem", "lineHeight": "1.4"})
            ], style={"flex": "1", "minWidth": "0"})
        ], className="d-flex align-items-start gap-3")
    ], className=f"alert-item {severity_class}")


def build_alerts_section(alerts: list):
    """Build the alerts section with professional styled items."""
    if not alerts:
        return html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-shield-check", style={"fontSize": "2.5rem", "color": "#10b981"})
                ], style={
                    "width": "72px", "height": "72px", "borderRadius": "50%",
                    "background": "rgba(16, 185, 129, 0.1)", "display": "flex",
                    "alignItems": "center", "justifyContent": "center", "margin": "0 auto 1rem"
                }),
                html.P("All Systems Operational", style={"color": "#111827", "fontWeight": "600", "marginBottom": "0.25rem"}),
                html.P("No active alerts at this time", style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "0"})
            ], className="text-center py-4")
        ])
    return html.Div([build_alert_item(a) for a in alerts[:5]], className="alert-scroll")


def build_depot_hmi_view(assets_data: list, fire_sim_results: dict = None) -> dcc.Graph:
    """Build the professional depot HMI visualization."""
    fig = go.Figure()
    
    # Draw Buildings with better styling
    for name, b in DEPOT_LAYOUT.get('buildings', {}).items():
        fig.add_shape(
            type="rect",
            x0=b['x']-b['width']/2, y0=b['y']-b['height']/2,
            x1=b['x']+b['width']/2, y1=b['y']+b['height']/2,
            line=dict(color="#374151", width=2),
            fillcolor="#1f2937",
            layer="below"
        )
        fig.add_annotation(
            x=b['x'], y=b['y'], text=name, showarrow=False,
            font=dict(size=b.get('size', 8), color="#9ca3af", family="Inter")
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
            line=dict(color="#4b5563", width=2), fillcolor="#374151", layer="below"
        )
        fig.add_annotation(x=x, y=y, text=gantry['id'], showarrow=False, font=dict(size=9, color="#111827"))

    # Draw Pump Stations
    for name, p_coords in DEPOT_LAYOUT.get('pump_stations', {}).items():
        fig.add_trace(go.Scatter(
            x=[p_coords['x']], y=[p_coords['y']], mode='markers',
            marker=dict(symbol='diamond', color='#f59e0b', size=20, line=dict(width=2, color='rgba(255,255,255,0.3)')),
            hoverinfo="text", hovertext=f"<b>{name}</b>", name=name
        ))

    # Draw Tanks with professional gradient colors based on level
    tanks = [a for a in assets_data if a.get('asset_type') == 'StorageTank']
    tank_coords = DEPOT_LAYOUT.get('tanks', {})
    
    for tank in tanks:
        asset_id = tank['asset_id']
        coords = tank_coords.get(asset_id)
        if not coords:
            continue
        
        level_pct = tank.get('latest_dynamic_state', {}).get('level_percentage', {}).get('value', 0)
        product = tank.get('product_service', 'Unknown')
        
        # Professional color scheme based on level status
        if level_pct > 90:
            fill_color = "#ef4444"  # Critical high - red
            status = "HIGH"
            status_color = "#fecaca"
        elif level_pct > 80:
            fill_color = "#f59e0b"  # Warning - amber
            status = "WARN"
            status_color = "#fde68a"
        elif level_pct > 20:
            fill_color = "#10b981"  # Normal - emerald
            status = "OK"
            status_color = "#a7f3d0"
        elif level_pct > 10:
            fill_color = "#3b82f6"  # Low - blue
            status = "LOW"
            status_color = "#bfdbfe"
        else:
            fill_color = "#8b5cf6"  # Critical low - purple
            status = "CRIT"
            status_color = "#ddd6fe"
        
        radius = coords.get('radius', 5.0)
        marker_size = 22 + (radius * 2.5)
        
        fig.add_trace(go.Scatter(
            x=[coords['x']], y=[coords['y']], mode='markers+text',
            marker=dict(
                size=marker_size, color=fill_color, opacity=0.95,
                line=dict(width=3, color='rgba(255,255,255,0.2)'),
                symbol='circle'
            ),
            text=f"<b>{asset_id.replace('TK-','')}</b>",
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
            font=dict(size=l.get('size', 12), color="#3b82f6", family="Inter")
        )

    # Fire Simulation Radii
    if fire_sim_results and 'source_asset_id' in fire_sim_results:
        source_id = fire_sim_results.get('source_asset_id')
        source_coords = tank_coords.get(source_id)
        if source_coords:
            radii = fire_sim_results.get('impact_radii_meters', {})
            scale_factor = (source_coords.get('radius', 5.0) * 2) / 20.0
            colors = {
                "equipment_damage": "rgba(239,68,68,0.25)",
                "second_degree_burns": "rgba(245,158,11,0.25)",
                "pain_threshold": "rgba(251,191,36,0.25)"
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
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 145]),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 145]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 120], scaleanchor="x", scaleratio=1),
        plot_bgcolor='#0a0f1a',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        height=650,
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(
            bgcolor="#1f2937",
            font_size=12,
            font_family="Inter",
            bordercolor="#3b82f6"
        )
    )
    
    return dcc.Graph(id='depot-hmi-graph', figure=fig, config={'displayModeBar': False}, style={'minWidth': '500px', 'margin': '0 auto'})


def build_inventory_chart(tanks_data):
    """Build a professional donut chart showing inventory by product."""
    inventory_by_product = {}
    for tank in tanks_data:
        product = tank.get('product_service', 'Unknown')
        volume = float(tank.get('latest_dynamic_state', {}).get('volume_gsv', {}).get('value', 0))
        inventory_by_product[product] = inventory_by_product.get(product, 0) + volume
    
    if not inventory_by_product:
        return html.Div([
            html.I(className="fas fa-database", style={"fontSize": "2rem", "color": "#374151"}),
            html.P("No inventory data", style={"color": "#6b7280", "marginTop": "0.5rem"})
        ], className="text-center py-4")
    
    labels = list(inventory_by_product.keys())
    values = [v/1e6 for v in inventory_by_product.values()]
    
    # Professional color palette
    color_palette = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']
    colors = [color_palette[i % len(color_palette)] for i in range(len(labels))]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker=dict(
            colors=colors, 
            line=dict(color='#ffffff', width=3)
        ),
        textinfo='percent',
        textfont=dict(size=11, color='#111827', family='Inter'),
        hovertemplate="<b>%{label}</b><br>%{value:.2f}M Litres<br>%{percent}<extra></extra>",
        direction='clockwise',
        sort=False
    )])
    
    total = sum(values)
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=-0.25, 
            xanchor="center", 
            x=0.5,
            font=dict(size=10, color="#4b5563", family='Inter'),
            itemsizing='constant'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=70),
        height=280,
        annotations=[
            dict(
                text=f"<b>{total:.1f}M</b>",
                x=0.5, y=0.55, 
                font_size=20, 
                font_color="#111827",
                font_family='Inter',
                showarrow=False
            ),
            dict(
                text="Litres",
                x=0.5, y=0.4, 
                font_size=11, 
                font_color="#6b7280",
                font_family='Inter',
                showarrow=False
            )
        ],
        hoverlabel=dict(
            bgcolor="#ffffff",
            font_size=12,
            font_family="Inter",
            bordercolor="#e5e7eb"
        )
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


# --- Page Layout Builders ---
def build_overview_layout():
    """Build the professional command center overview layout."""
    return html.Div([
        # KPI Row
        dbc.Row([
            dbc.Col([
                html.Div(id='kpi-total-inventory')
            ], xl=3, lg=6, md=6, className="mb-4"),
            dbc.Col([
                html.Div(id='kpi-usable-ullage')
            ], xl=3, lg=6, md=6, className="mb-4"),
            dbc.Col([
                html.Div(id='kpi-active-pumps')
            ], xl=3, lg=6, md=6, className="mb-4"),
            dbc.Col([
                html.Div(id='kpi-daily-throughput')
            ], xl=3, lg=6, md=6, className="mb-4"),
        ]),
        
        # Main Content Row
        dbc.Row([
            # Left Column - HMI View
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("Live Depot View", className="section-title", style={"marginBottom": "0"}),
                        ]),
                        html.Div([
                            html.Div([
                                html.Div(className="pulse-dot me-2"),
                                html.Span("LIVE", style={"color": "#10b981", "fontSize": "0.7rem", "fontWeight": "700", "letterSpacing": "0.1em"})
                            ], className="d-flex align-items-center", style={
                                "background": "rgba(16, 185, 129, 0.1)",
                                "padding": "0.35rem 0.75rem",
                                "borderRadius": "20px",
                                "border": "1px solid rgba(16, 185, 129, 0.2)"
                            })
                        ])
                    ], className="d-flex justify-content-between align-items-center mb-4"),
                    html.Div([
                        dcc.Loading(
                            type="circle",
                            color="#3b82f6",
                            children=html.Div(id='depot-hmi-view-container')
                        )
                    ], style={'overflowX': 'auto', 'width': '100%'}, className="hmi-scroll-container"),
                    # Legend
                    html.Div([
                        html.Div([html.Div(className="legend-dot", style={"background": "#10b981"}), "Normal"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#f59e0b"}), "Warning"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#ef4444"}), "Critical"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#3b82f6"}), "Low"], className="legend-item"),
                        html.Div([html.Div(className="legend-dot", style={"background": "#f59e0b", "transform": "rotate(45deg)", "borderRadius": "2px"}), "Pump Station"], className="legend-item"),
                    ], className="tank-legend")
                ], className="glass-card h-100")
            ], xl=8, lg=12, className="mb-4"),
            
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
                        html.Span("Active Alerts", className="section-title", style={"marginBottom": "0"}),
                        html.Span(id='alert-count-badge', className="status-badge status-warning")
                    ], className="d-flex justify-content-between align-items-center mb-3"),
                    html.Div(id='active-alerts-list', style={'maxHeight': '280px', 'overflowY': 'auto'})
                ], className="glass-card")
            ], xl=4, lg=12, className="mb-4"),
        ]),
        
        # Bottom Row - Financial KPIs & Recent Operations
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span("Financial Overview", className="section-title"),
                    dbc.Row([
                        dbc.Col([html.Div(id='kpi-inventory-value')], lg=4, md=12, className="mb-3 mb-lg-0"),
                        dbc.Col([html.Div(id='kpi-daily-cost')], lg=4, md=12, className="mb-3 mb-lg-0"),
                        dbc.Col([html.Div(id='kpi-efficiency')], lg=4, md=12),
                    ])
                ], className="glass-card")
            ], xl=6, lg=12, className="mb-4"),
            dbc.Col([
                html.Div([
                    html.Span("Recent Operations", className="section-title"),
                    dcc.Loading(
                        type="circle",
                        color="#3b82f6",
                        children=html.Div(id='operation-logs-list', className="log-scroll", style={'maxHeight': '220px', 'overflowY': 'auto'})
                    )
                ], className="glass-card")
            ], xl=6, lg=12, className="mb-4"),
        ]),
        
        # Last Updated Footer
        html.Div([
            html.Div([
                html.I(className="fas fa-sync-alt me-2", style={"fontSize": "0.75rem"}),
                html.Span(id='last-updated-time')
            ], style={
                "display": "inline-flex", "alignItems": "center",
                "background": "#f3f4f6", "padding": "0.5rem 1rem",
                "borderRadius": "20px", "border": "1px solid #e5e7eb"
            })
        ], className="text-center", style={"color": "#4b5563", "fontSize": "0.75rem"})
    ], className="p-4", style={"maxWidth": "1800px", "margin": "0 auto"})


def build_historical_analysis_layout():
    """Build the professional historical data analysis page."""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-chart-line", style={"fontSize": "1.5rem", "color": "#3b82f6"})
                ], style={
                    "width": "48px", "height": "48px", "borderRadius": "12px",
                    "background": "rgba(59, 130, 246, 0.15)", "display": "flex",
                    "alignItems": "center", "justifyContent": "center", "marginRight": "1rem"
                }),
                html.Div([
                    html.H4("Historical Data Analysis", style={"color": "#111827", "marginBottom": "0.25rem", "fontWeight": "700"}),
                    html.P("Analyze trends and patterns in your depot data", style={"color": "#6b7280", "marginBottom": "0", "fontSize": "0.9rem"})
                ])
            ], className="d-flex align-items-center")
        ], className="mb-4"),
        
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Asset", style={"color": "#4b5563", "fontSize": "0.8rem", "marginBottom": "0.5rem", "fontWeight": "500"}),
                    dcc.Dropdown(id='history-asset-dropdown', placeholder="Choose an asset...", className="mb-3")
                ], lg=3, md=6),
                dbc.Col([
                    html.Label("Select Metric", style={"color": "#4b5563", "fontSize": "0.8rem", "marginBottom": "0.5rem", "fontWeight": "500"}),
                    dcc.Dropdown(id='history-metric-dropdown', placeholder="Choose a metric...", className="mb-3")
                ], lg=3, md=6),
                dbc.Col([
                    html.Label("Date Range", style={"color": "#4b5563", "fontSize": "0.8rem", "marginBottom": "0.5rem", "fontWeight": "500"}),
                    dcc.DatePickerRange(
                        id='history-date-picker',
                        start_date=datetime.date.today() - datetime.timedelta(days=7),
                        end_date=datetime.date.today(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    )
                ], lg=4, md=8),
                dbc.Col([
                    html.Label(" ", style={"display": "block", "marginBottom": "0.5rem"}),
                    dbc.Button([
                        html.I(className="fas fa-chart-line me-2"),
                        "Load Data"
                    ], id="history-load-button", className="btn-primary-gradient w-100")
                ], lg=2, md=4),
            ])
        ], className="glass-card mb-4"),
        
        dcc.Loading(
            type="circle",
            color="#3b82f6",
            children=html.Div(id="history-output-container")
        )
    ], className="p-4", style={"maxWidth": "1800px", "margin": "0 auto"})


def build_asset_info_layout():
    """Build the professional asset information page."""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-database", style={"fontSize": "1.5rem", "color": "#8b5cf6"})
                ], style={
                    "width": "48px", "height": "48px", "borderRadius": "12px",
                    "background": "rgba(139, 92, 246, 0.15)", "display": "flex",
                    "alignItems": "center", "justifyContent": "center", "marginRight": "1rem"
                }),
                html.Div([
                    html.H4("Asset Registry", style={"color": "#111827", "marginBottom": "0.25rem", "fontWeight": "700"}),
                    html.P("Complete inventory of all depot assets", style={"color": "#6b7280", "marginBottom": "0", "fontSize": "0.9rem"})
                ])
            ], className="d-flex align-items-center")
        ], className="mb-4"),
        html.Div([
            dcc.Loading(
                type="circle",
                color="#8b5cf6",
                children=html.Div(id="asset-info-table-container")
            )
        ], className="glass-card")
    ], className="p-4", style={"maxWidth": "1800px", "margin": "0 auto"})


def build_logbook_layout():
    """Build the professional manual logbook entry page."""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-book", style={"fontSize": "1.5rem", "color": "#10b981"})
                ], style={
                    "width": "48px", "height": "48px", "borderRadius": "12px",
                    "background": "rgba(16, 185, 129, 0.15)", "display": "flex",
                    "alignItems": "center", "justifyContent": "center", "marginRight": "1rem"
                }),
                html.Div([
                    html.H4("Operations Logbook", style={"color": "#111827", "marginBottom": "0.25rem", "fontWeight": "700"}),
                    html.P("Record operational events and activities", style={"color": "#6b7280", "marginBottom": "0", "fontSize": "0.9rem"})
                ])
            ], className="d-flex align-items-center")
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-pen-to-square me-2", style={"color": "#10b981"}),
                        html.Span("New Entry", style={"fontWeight": "600"})
                    ], style={"color": "#111827", "marginBottom": "1.5rem", "fontSize": "1.1rem"}),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Your Name", style={"color": "#4b5563", "fontSize": "0.8rem", "fontWeight": "500"}),
                            dbc.Input(id='log-user-name', type='text', placeholder="Enter your name...", className="mb-3")
                        ], md=6),
                        dbc.Col([
                            html.Label("Event Type", style={"color": "#4b5563", "fontSize": "0.8rem", "fontWeight": "500"}),
                            dcc.Dropdown(
                                id='log-event-type',
                                options=[
                                    {'label': 'General', 'value': 'General'},
                                    {'label': 'Safety Check', 'value': 'Safety Check'},
                                    {'label': 'Maintenance', 'value': 'Maintenance'},
                                    {'label': 'Product Transfer', 'value': 'Product Transfer'},
                                    {'label': 'Incident', 'value': 'Incident'}
                                ],
                                value='General',
                                className="mb-3"
                            )
                        ], md=6)
                    ]),
                    html.Label("Related Asset (Optional)", style={"color": "#4b5563", "fontSize": "0.8rem", "fontWeight": "500"}),
                    dcc.Dropdown(id='log-asset-dropdown', placeholder="Select asset...", className="mb-3"),
                    html.Label("Description", style={"color": "#4b5563", "fontSize": "0.8rem", "fontWeight": "500"}),
                    dbc.Textarea(id='log-description', placeholder="Describe the event...", style={'height': '120px'}, className="mb-4"),
                    dbc.Button([
                        html.I(className="fas fa-paper-plane me-2"),
                        "Submit Entry"
                    ], id="log-submit-button", className="btn-primary-gradient"),
                    html.Div(id='log-submission-status', className="mt-3")
                ], className="glass-card h-100")
            ], lg=6, className="mb-4"),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-clock-rotate-left me-2", style={"color": "#3b82f6"}),
                        html.Span("Recent Entries", style={"fontWeight": "600"})
                    ], style={"color": "#111827", "marginBottom": "1.5rem", "fontSize": "1.1rem"}),
                    html.Div(id='recent-log-entries', className="log-scroll", style={'maxHeight': '400px', 'overflowY': 'auto'})
                ], className="glass-card h-100")
            ], lg=6, className="mb-4")
        ])
    ], className="p-4", style={"maxWidth": "1800px", "margin": "0 auto"})


def build_simulation_sandbox_layout():
    """Build the professional simulation sandbox page with tank transfer simulation."""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-flask", style={"fontSize": "1.5rem", "color": "#f59e0b"})
                ], style={
                    "width": "48px", "height": "48px", "borderRadius": "12px",
                    "background": "rgba(245, 158, 11, 0.15)", "display": "flex",
                    "alignItems": "center", "justifyContent": "center", "marginRight": "1rem"
                }),
                html.Div([
                    html.H4("Simulation Sandbox", style={"color": "#111827", "marginBottom": "0.25rem", "fontWeight": "700"}),
                    html.P("Run what-if scenarios and predictive simulations for operational planning", style={"color": "#6b7280", "marginBottom": "0", "fontSize": "0.9rem"})
                ])
            ], className="d-flex align-items-center")
        ], className="mb-4"),
        
        dbc.Row([
            # Left Panel - Configuration
            dbc.Col([
                html.Div([
                    # Header
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-exchange-alt", 
                                   style={"fontSize": "1.25rem", "color": "#3b82f6"}),
                        ], style={
                            "width": "44px", "height": "44px", "borderRadius": "10px",
                            "background": "rgba(59, 130, 246, 0.15)", "display": "flex",
                            "alignItems": "center", "justifyContent": "center", "marginRight": "1rem"
                        }),
                        html.Div([
                            html.H5("Tank Transfer Simulation", 
                                    style={"color": "#111827", "marginBottom": "0.25rem", "fontWeight": "600"}),
                            html.Span("Predict transfer times and volume changes", 
                                      style={"color": "#6b7280", "fontSize": "0.8rem"})
                        ])
                    ], className="d-flex align-items-center mb-4"),
                    
                    # Source Tank Selection
                    html.Div([
                        html.Label([
                            html.I(className="fas fa-arrow-right-from-bracket me-2", style={"color": "#ef4444"}),
                            "Source Tank"
                        ], style={"color": "#111827", "fontSize": "0.8rem", "fontWeight": "500", "marginBottom": "0.5rem"}),
                        dcc.Dropdown(
                            id='sim-source-tank-dropdown', 
                            placeholder="Select source tank...", 
                            className="mb-2"
                        ),
                        html.Div(id='source-tank-info', className="mb-3")
                    ]),
                    
                    # Destination Tank Selection
                    html.Div([
                        html.Label([
                            html.I(className="fas fa-arrow-right-to-bracket me-2", style={"color": "#10b981"}),
                            "Destination Tank"
                        ], style={"color": "#111827", "fontSize": "0.8rem", "fontWeight": "500", "marginBottom": "0.5rem"}),
                        dcc.Dropdown(
                            id='sim-dest-tank-dropdown', 
                            placeholder="Select destination tank...", 
                            className="mb-2"
                        ),
                        html.Div(id='dest-tank-info', className="mb-3")
                    ]),
                    
                    # Pump Selection
                    html.Div([
                        html.Label([
                            html.I(className="fas fa-gauge-high me-2", style={"color": "#f59e0b"}),
                            "Transfer Pump"
                        ], style={"color": "#111827", "fontSize": "0.8rem", "fontWeight": "500", "marginBottom": "0.5rem"}),
                        dcc.Dropdown(
                            id='sim-pump-dropdown', 
                            placeholder="Select pump...", 
                            className="mb-2"
                        ),
                        html.Div(id='pump-info', className="mb-4")
                    ]),
                    
                    # Run Button
                    dbc.Button([
                        html.I(className="fas fa-play me-2"),
                        "Run Simulation"
                    ], id="run-tank-sim-button", className="btn-primary-gradient w-100", 
                       style={"padding": "0.875rem", "fontSize": "0.95rem", "fontWeight": "600"})
                    
                ], className="glass-card h-100")
            ], lg=4, className="mb-4"),
            
            # Right Panel - Results
            dbc.Col([
                html.Div([
                    dcc.Loading(
                        type="circle",
                        color="#3b82f6",
                        children=html.Div(id="sim-results-output", children=[
                            # Default state
                            html.Div([
                                html.Div([
                                    html.Div([
                                        html.I(className="fas fa-flask", style={"fontSize": "2.5rem", "color": "#9ca3af"})
                                    ], style={
                                        "width": "80px", "height": "80px", "borderRadius": "50%",
                                        "background": "#f3f4f6", "display": "flex",
                                        "alignItems": "center", "justifyContent": "center", "margin": "0 auto 1.5rem"
                                    }),
                                    html.H5("Ready to Simulate", style={"color": "#4b5563", "fontWeight": "600", "marginBottom": "0.5rem"}),
                                    html.P("Select source tank, destination tank, and pump to run a transfer simulation.",
                                           style={"color": "#6b7280", "fontSize": "0.9rem", "maxWidth": "400px", "margin": "0 auto", "lineHeight": "1.6"})
                                ], className="text-center py-5")
                            ])
                        ])
                    )
                ], className="glass-card h-100", style={"minHeight": "500px"})
            ], lg=8, className="mb-4")
        ]),
        
        # Info Cards Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-info-circle me-2", style={"color": "#3b82f6"}),
                        html.Span("How It Works", style={"fontWeight": "600", "color": "#111827"})
                    ], className="mb-2"),
                    html.P([
                        "The simulation calculates transfer time based on pump flow rate, tank capacities, ",
                        "and current fill levels. It predicts when high/low level alarms will trigger."
                    ], style={"color": "#4b5563", "fontSize": "0.85rem", "marginBottom": "0", "lineHeight": "1.5"})
                ], className="glass-card h-100")
            ], lg=4, className="mb-3"),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-shield-halved me-2", style={"color": "#10b981"}),
                        html.Span("Safety Thresholds", style={"fontWeight": "600", "color": "#111827"})
                    ], className="mb-2"),
                    html.P([
                        "Transfer stops automatically at 95% destination capacity (high level) ",
                        "or 5% source capacity (low level) to prevent overflow and pump cavitation."
                    ], style={"color": "#4b5563", "fontSize": "0.85rem", "marginBottom": "0", "lineHeight": "1.5"})
                ], className="glass-card h-100")
            ], lg=4, className="mb-3"),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-gauge-high me-2", style={"color": "#f59e0b"}),
                        html.Span("Pump Specifications", style={"fontWeight": "600", "color": "#111827"})
                    ], className="mb-2"),
                    html.P([
                        "Flow rates vary by pump: Zone A (2500-3000 LPM), Zone B (2000 LPM), ",
                        "Zone C (1500-2200 LPM). Select appropriate pump for product compatibility."
                    ], style={"color": "#4b5563", "fontSize": "0.85rem", "marginBottom": "0", "lineHeight": "1.5"})
                ], className="glass-card h-100")
            ], lg=4, className="mb-3"),
        ])
    ], className="p-4", style={"maxWidth": "1800px", "margin": "0 auto"})


def build_log_viewer_layout():
    """Build the professional system log viewer page."""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-terminal", style={"fontSize": "1.5rem", "color": "#10b981"})
                ], style={
                    "width": "48px", "height": "48px", "borderRadius": "12px",
                    "background": "rgba(16, 185, 129, 0.15)", "display": "flex",
                    "alignItems": "center", "justifyContent": "center", "marginRight": "1rem"
                }),
                html.Div([
                    html.H4("System Logs", style={"color": "#111827", "marginBottom": "0.25rem", "fontWeight": "700"}),
                    html.P("Real-time dashboard activity logs", style={"color": "#6b7280", "marginBottom": "0", "fontSize": "0.9rem"})
                ])
            ], className="d-flex align-items-center")
        ], className="mb-4"),
        html.Div([
            dcc.Textarea(
                id='log-viewer-textarea',
                style={
                    'width': '100%', 'height': '600px',
                    'fontFamily': '"JetBrains Mono", "Fira Code", "Consolas", monospace',
                    'fontSize': '12px',
                    'backgroundColor': '#1f2937',
                    'color': '#10b981',
                    'border': '1px solid #e5e7eb',
                    'borderRadius': '12px',
                    'padding': '1.25rem',
                    'lineHeight': '1.6'
                },
                readOnly=True
            )
        ], className="glass-card")
    ], className="p-4", style={"maxWidth": "1800px", "margin": "0 auto"})


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
    
    # Professional Navbar
    dbc.Navbar([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-industry", style={"fontSize": "1.25rem"})
                        ], style={
                            "width": "40px", "height": "40px", "borderRadius": "10px",
                            "background": "#000000",
                            "display": "flex", "alignItems": "center", "justifyContent": "center",
                            "color": "#fff", "marginRight": "0.875rem"
                        }),
                        html.Div([
                            html.Span("Fuel Depot", style={"fontWeight": "700", "fontSize": "1.15rem", "color": "#111827", "letterSpacing": "-0.025em"}),
                            html.Span(" Digital Twin", style={"fontWeight": "400", "fontSize": "1.15rem", "color": "#6b7280", "letterSpacing": "-0.025em"})
                        ])
                    ], className="d-flex align-items-center")
                ]),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Div(className="pulse-dot"),
                        ], className="me-2"),
                        html.Span("System Online", style={"color": "#10b981", "fontSize": "0.8rem", "fontWeight": "600", "letterSpacing": "0.025em"})
                    ], className="d-flex align-items-center justify-content-end")
                ])
            ], className="w-100", align="center")
        ], fluid=True)
    ], className="navbar", dark=False),
    
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
            html.I(className="fas fa-fire-flame-curved me-2", style={"color": "#ef4444"}),
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
    pump_costs_data = get_api_data('/api/v1/pumps/costs')  # Fetch real pump operating costs
    weather_data = fetch_weather_data()
    logger.info("API data fetch complete.")
    return {
        'assets': assets_data.get('assets', []) if isinstance(assets_data, dict) else [],
        'alerts': alerts_data if isinstance(alerts_data, list) else [],
        'logs': logs_data if isinstance(logs_data, list) else [],
        'pump_costs': pump_costs_data if isinstance(pump_costs_data, dict) and 'error' not in pump_costs_data else {},
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
        active_pumps = sum(1 for a in assets if a.get('asset_type') == 'Pump' and a.get('is_active', True) is not False)
        total_pumps = sum(1 for a in assets if a.get('asset_type') == 'Pump')
        
        # Get real pump costs and runtime data from API
        pump_costs = data.get('pump_costs', {})
        pump_summary = pump_costs.get('summary', {})
        pumps_data = pump_costs.get('pumps', [])
        
        # Calculate actual daily operating cost from real data
        if pump_summary.get('total_cost_ghs'):
            daily_electricity_cost = pump_summary['total_cost_ghs']
        else:
            # Fallback to estimate if no real data
            daily_kwh = active_pumps * PUMP_POWER_KW * ESTIMATED_DAILY_HOURS_PER_PUMP
            daily_electricity_cost = (daily_kwh * ELECTRICITY_RATE_PER_KWH) + SERVICE_CHARGE
        
        # Calculate average pump runtime percentage from real data
        if pumps_data:
            running_pumps = sum(1 for p in pumps_data if p.get('runtime_percentage', 0) > 0)
            avg_runtime = sum(p.get('runtime_percentage', 0) for p in pumps_data) / len(pumps_data)
            pump_display = f"{running_pumps}/{total_pumps}"
            pump_subtitle = f"{avg_runtime:.0f}% avg uptime"
        else:
            pump_display = f"{active_pumps}/{total_pumps}"
            pump_subtitle = ""
        
        # Build KPI cards with professional styling
        kpi_inventory = build_kpi_card("Total Inventory", f"{total_inv/1e6:.2f}", "M Litres", "fa-oil-can", "#3b82f6")
        kpi_ullage = build_kpi_card("Usable Ullage", f"{usable_ullage/1e6:.2f}", "M Litres", "fa-arrow-up-from-bracket", "#10b981")
        kpi_pumps = build_kpi_card("Active Pumps", pump_display, pump_subtitle, "fa-gauge-high", "#f59e0b")
        kpi_throughput = build_kpi_card("Daily Throughput", "10.1", "M Litres", "fa-truck-fast", "#8b5cf6")
        
        # Show actual energy consumption if available
        total_energy_kwh = pump_summary.get('total_energy_kwh', 0)
        cost_subtitle = f"{total_energy_kwh:.1f} kWh" if total_energy_kwh else ""
        
        kpi_value = build_kpi_card("Inventory Value", format_large_number(inv_value, prefix="₵"), "", "fa-cedi-sign", "#10b981")
        kpi_cost = build_kpi_card("Daily Op. Cost", f"₵{daily_electricity_cost:,.2f}", cost_subtitle, "fa-bolt", "#f59e0b")
        kpi_efficiency = build_kpi_card("Efficiency", "94.2%", "", "fa-chart-line", "#3b82f6")
        
        # Alerts
        alerts = data.get('alerts', [])
        alert_count = f"{len(alerts)} Active" if alerts else "0 Active"
        
        # Logs with professional styling
        logs = data.get('logs', [])
        if logs:
            log_items = []
            for log in logs[:5]:
                event_type = log.get('event_type', 'Event')
                badge_colors = {
                    'GENERAL': ('#3b82f6', 'rgba(59, 130, 246, 0.15)'),
                    'SAFETY CHECK': ('#10b981', 'rgba(16, 185, 129, 0.15)'),
                    'MAINTENANCE': ('#f59e0b', 'rgba(245, 158, 11, 0.15)'),
                    'PRODUCT TRANSFER': ('#8b5cf6', 'rgba(139, 92, 246, 0.15)'),
                    'INCIDENT': ('#ef4444', 'rgba(239, 68, 68, 0.15)')
                }
                color, bg = badge_colors.get(event_type.upper(), ('#3b82f6', 'rgba(59, 130, 246, 0.15)'))
                
                log_items.append(html.Div([
                    html.Div([
                        html.Span(event_type, style={
                            "fontSize": "0.65rem", "fontWeight": "600", "textTransform": "uppercase",
                            "letterSpacing": "0.5px", "color": color, "background": bg,
                            "padding": "0.25rem 0.5rem", "borderRadius": "4px", "marginRight": "0.75rem"
                        }),
                        html.Span(log.get('user_name', 'System'), style={"color": "#111827", "fontWeight": "500", "fontSize": "0.875rem"})
                    ], className="d-flex align-items-center mb-1"),
                    html.P(log.get('description', '')[:100] + "..." if len(log.get('description', '')) > 100 else log.get('description', ''), 
                           className="mb-0", style={"fontSize": "0.8rem", "color": "#4b5563", "lineHeight": "1.4"})
                ], style={
                    "background": "#f8f9fa", "borderRadius": "10px",
                    "padding": "0.875rem 1rem", "marginBottom": "0.75rem",
                    "borderLeft": f"3px solid {color}"
                }))
            log_list = html.Div(log_items)
        else:
            log_list = html.Div([
                html.I(className="fas fa-inbox", style={"fontSize": "1.5rem", "color": "#9ca3af"}),
                html.P("No recent operations", style={"color": "#6b7280", "marginTop": "0.5rem", "marginBottom": "0"})
            ], className="text-center py-4")
        
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
    return [{'label': f"[Tank] {a['asset_id']}" if a.get('asset_type') == 'StorageTank' else f"[Equip] {a['asset_id']}", 'value': a['asset_id']} for a in data['assets']]


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
    tanks = [{'label': f"[Tank] {a['asset_id']}", 'value': a['asset_id']} for a in data['assets'] if a.get('asset_type') == 'StorageTank']
    pumps = [{'label': f"[Pump] {a['asset_id']}", 'value': a['asset_id']} for a in data['assets'] if a.get('asset_type') == 'Pump']
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
    
    # Check for error response (product mismatch, invalid assets, etc.)
    if 'error' in results:
        error_msg = results['error']
        # Determine icon based on error type
        if 'mismatch' in error_msg.lower() or 'different products' in error_msg.lower():
            icon = "fa-flask"
            title = "Product Mismatch"
        elif 'not found' in error_msg.lower():
            icon = "fa-search"
            title = "Asset Not Found"
        elif 'not a' in error_msg.lower():
            icon = "fa-ban"
            title = "Invalid Asset Type"
        else:
            icon = "fa-exclamation-triangle"
            title = "Simulation Error"
        
        return html.Div([
            html.Div([
                html.I(className=f"fas {icon}", style={"fontSize": "2rem", "color": "#ef4444"}),
            ], style={
                "width": "64px", "height": "64px", "borderRadius": "50%",
                "background": "rgba(239, 68, 68, 0.1)", "display": "flex",
                "alignItems": "center", "justifyContent": "center", "margin": "0 auto 1rem"
            }),
            html.Div(title, style={"color": "#ef4444", "fontWeight": "600", "fontSize": "1.1rem", "marginBottom": "0.5rem"}),
            html.Div(error_msg, style={"color": "#6b7280", "fontSize": "0.9rem", "lineHeight": "1.5"})
        ], className="text-center py-4")
    
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
    print("\nDashboard running at: http://127.0.0.1:8050\n")
    app.run(debug=True, port=8050)
