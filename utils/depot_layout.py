# utils/depot_layout.py 

# This file defines the static 2D coordinates for assets in the depot layout. 
# UPDATED: Added a dedicated 'pump_stations' dictionary for visual symbols. 
# The layout uses a 120x105 grid, where (0,0) is the bottom-left corner. 

DEPOT_LAYOUT = { 
    "tanks": { 
        # --- Area A --- 
        "TANK_121": {"x": 22, "y": 80, "radius": 7.2}, 
        "TANK_122": {"x": 22, "y": 68, "radius": 7.2}, 
        "TANK_123": {"x": 13, "y": 80, "radius": 7.2}, 
        "TANK_124": {"x": 13, "y": 68, "radius": 7.2}, 

        # --- Area B --- 
        "TANK_101": {"x": 32, "y": 80, "radius": 4}, 
        "TANK_102": {"x": 42, "y": 80, "radius": 5}, 
        "TANK_103": {"x": 32, "y": 68, "radius": 6}, 

        # --- Area C --- 
        "TANK_143": {"x": 80, "y": 80, "radius": 6}, 
        "TANK_141": {"x": 90, "y": 80, "radius": 6}, 
        "TANK_144": {"x": 80, "y": 68, "radius": 6}, 
        "TANK_142": {"x": 90, "y": 68, "radius": 6}, 

        # --- Area AT&V --- 
        "TANK_5801": {"x": 102.5, "y": 90, "radius": 7.5}, 
        "TANK_5802": {"x": 114, "y": 95, "radius": 7.5}, 
        "TANK_5803": {"x": 114, "y": 83, "radius": 7.5}, 
        "TANK_5804": {"x": 102.5, "y": 78, "radius": 6}, 
    }, 
    "gantries": [ 
        {"id": "Loading Gantry", "x": 53, "y": 50, "width": 18, "height": 6}, 
    ], 
    "buildings": { 
        "Admin Area": {"x": 15, "y": 15, "width": 15, "height": 10, "size": 10}, 
        "Control Room": {"x": 45, "y": 30, "width": 15, "height": 8, "size": 10}, 
        "Ullage Area": {"x": 65, "y": 80, "width": 8, "height": 6, "size": 9}, 
        "PL Receipt Area": {"x": 103, "y": 68, "width": 12, "height": 6, "size": 9}, 
    }, 
    "features": { 
        "MAIN HIGHWAY": {"x": 55, "y": 5, "width": 110, "height": 8, "color": "#636363"}, 
        "Water Tank 1": {"x": 40, "y": 40, "width": 5, "height": 5, "color": "#add8e6"}, 
        "Water Tank 2": {"x": 109, "y": 77, "width": 4, "height": 4, "color": "#add8e6"}, 
    
        "Assembly Point 1": {"x": 5, "y": 85, "width": 4, "height": 4, "color": "green"}, 
        "Assembly Point 2": {"x": 40, "y": 50, "width": 4, "height": 4, "color": "green"}, 
        "Assembly Point 3": {"x": 70, "y": 90, "width": 4, "height": 4, "color": "green"}, 
        "Assembly Point 4": {"x": 70, "y": 40, "width": 4, "height": 4, "color": "green"}, 
    }, 
    "pump_stations": { 
        "Pump - A": {"x": 22, "y": 74}, 
        "Pump-B": {"x": 41, "y": 68}, 
        "TAPP Pumps": {"x": 32, "y": 61}, 
        "Pump - C": {"x": 85, "y": 85}, 
        "Pump-AT&V": {"x": 97, "y": 76}, 
    }, 
    "labels": { 
        "Area A": {"x": 17.5, "y": 88, "size": 14}, 
        "Area B": {"x": 53, "y": 98, "size": 14}, 
        "Area C": {"x": 85, "y": 85, "size": 14}, 
        "Area AT&V": {"x": 95, "y": 100, "size": 14}, 
    } 
} 
