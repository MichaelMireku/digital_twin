# utils/depot_layout.py 
# Fictional depot layout for demonstration purposes
# Optimized spatial layout - no overlaps, proper safety clearances
# Grid: 140m x 120m depot footprint

DEPOT_LAYOUT = { 
    "tanks": { 
        # Zone A - Northwest (AGO/PMS) - 2x2 grid with proper spacing
        "TK-A01": {"x": 18, "y": 95, "radius": 6.5}, 
        "TK-A02": {"x": 35, "y": 95, "radius": 6.5}, 
        "TK-A03": {"x": 18, "y": 78, "radius": 7.0}, 
        "TK-A04": {"x": 35, "y": 78, "radius": 7.0}, 

        # Zone B - Northeast (smaller AGO) - triangle formation
        "TK-B01": {"x": 58, "y": 100, "radius": 4.5}, 
        "TK-B02": {"x": 72, "y": 100, "radius": 5.0}, 
        "TK-B03": {"x": 65, "y": 85, "radius": 5.5}, 

        # Zone C - East (AGO/PMS) - 2x2 grid
        "TK-C01": {"x": 100, "y": 75, "radius": 5.5}, 
        "TK-C02": {"x": 115, "y": 75, "radius": 5.5}, 
        "TK-C03": {"x": 100, "y": 60, "radius": 5.5}, 
        "TK-C04": {"x": 115, "y": 60, "radius": 5.5}, 

        # Zone D - South (large AGO) - 2x2 grid
        "TK-D01": {"x": 20, "y": 38, "radius": 7.0}, 
        "TK-D02": {"x": 40, "y": 38, "radius": 7.0}, 
        "TK-D03": {"x": 20, "y": 18, "radius": 7.0}, 
        "TK-D04": {"x": 40, "y": 18, "radius": 5.5}, 
    }, 
    "gantries": [ 
        {"id": "Loading Bay", "x": 85, "y": 25, "width": 24, "height": 10}, 
    ], 
    "buildings": { 
        "Admin Block": {"x": 125, "y": 20, "width": 14, "height": 10, "size": 9},
        "Control Room": {"x": 70, "y": 50, "width": 10, "height": 7, "size": 9}, 
        "Operations": {"x": 90, "y": 95, "width": 8, "height": 6, "size": 8}, 
        "Maintenance": {"x": 125, "y": 35, "width": 12, "height": 8, "size": 8},
        "Gate House": {"x": 70, "y": 115, "width": 6, "height": 4, "size": 6},
    }, 
    "features": { 
        "ACCESS ROAD": {"x": 70, "y": 110, "width": 140, "height": 8, "color": "#636363"}, 
        "Fire Water 1": {"x": 55, "y": 58, "width": 6, "height": 6, "color": "#add8e6"}, 
        "Fire Water 2": {"x": 80, "y": 45, "width": 6, "height": 6, "color": "#add8e6"},
        "Muster Point 1": {"x": 5, "y": 55, "width": 4, "height": 4, "color": "green"}, 
        "Muster Point 2": {"x": 135, "y": 55, "width": 4, "height": 4, "color": "green"}, 
        "Muster Point 3": {"x": 70, "y": 5, "width": 4, "height": 4, "color": "green"}, 
    }, 
    "pump_stations": { 
        "Pump House A": {"x": 26, "y": 62},
        "Pump House B": {"x": 65, "y": 75}, 
        "Pump House C": {"x": 88, "y": 67}, 
        "Transfer Station": {"x": 58, "y": 30}, 
    }, 
    "bund_walls": {
        "Zone A": {"x1": 8, "y1": 68, "x2": 48, "y2": 108},
        "Zone B": {"x1": 50, "y1": 77, "x2": 82, "y2": 110},
        "Zone C": {"x1": 90, "y1": 50, "x2": 128, "y2": 85},
        "Zone D": {"x1": 8, "y1": 6, "x2": 55, "y2": 50},
    },
    "labels": { 
        "Zone A": {"x": 26, "y": 102, "size": 12}, 
        "Zone B": {"x": 65, "y": 107, "size": 12}, 
        "Zone C": {"x": 107, "y": 82, "size": 12}, 
        "Zone D": {"x": 30, "y": 45, "size": 12}, 
    } 
}
