# utils/depot_layout.py 
# Fictional depot layout for demonstration purposes
# All positions and dimensions are randomized

DEPOT_LAYOUT = { 
    "tanks": { 
        # Zone A - Northwest cluster
        "TK-A01": {"x": 18, "y": 85, "radius": 6.5}, 
        "TK-A02": {"x": 32, "y": 85, "radius": 6.5}, 
        "TK-A03": {"x": 18, "y": 70, "radius": 7.0}, 
        "TK-A04": {"x": 32, "y": 70, "radius": 7.0}, 

        # Zone B - Northeast cluster
        "TK-B01": {"x": 55, "y": 90, "radius": 4.5}, 
        "TK-B02": {"x": 68, "y": 90, "radius": 5.0}, 
        "TK-B03": {"x": 62, "y": 75, "radius": 5.5}, 

        # Zone C - Central-East cluster
        "TK-C01": {"x": 85, "y": 65, "radius": 5.5}, 
        "TK-C02": {"x": 98, "y": 65, "radius": 5.5}, 
        "TK-C03": {"x": 85, "y": 50, "radius": 5.5}, 
        "TK-C04": {"x": 98, "y": 50, "radius": 5.5}, 

        # Zone D - South cluster
        "TK-D01": {"x": 25, "y": 35, "radius": 7.0}, 
        "TK-D02": {"x": 42, "y": 35, "radius": 7.0}, 
        "TK-D03": {"x": 25, "y": 18, "radius": 7.0}, 
        "TK-D04": {"x": 42, "y": 18, "radius": 5.5}, 
    }, 
    "gantries": [ 
        {"id": "Loading Bay", "x": 75, "y": 25, "width": 20, "height": 8}, 
    ], 
    "buildings": { 
        "Admin Block": {"x": 108, "y": 90, "width": 12, "height": 8, "size": 9}, 
        "Control Room": {"x": 60, "y": 45, "width": 10, "height": 6, "size": 9}, 
        "Operations": {"x": 95, "y": 85, "width": 8, "height": 5, "size": 8}, 
        "Maintenance": {"x": 108, "y": 25, "width": 10, "height": 6, "size": 8}, 
    }, 
    "features": { 
        "ACCESS ROAD": {"x": 60, "y": 100, "width": 100, "height": 6, "color": "#636363"}, 
        "Fire Water 1": {"x": 50, "y": 58, "width": 4, "height": 4, "color": "#add8e6"}, 
        "Fire Water 2": {"x": 75, "y": 78, "width": 4, "height": 4, "color": "#add8e6"}, 
        "Muster Point 1": {"x": 8, "y": 55, "width": 3, "height": 3, "color": "green"}, 
        "Muster Point 2": {"x": 115, "y": 55, "width": 3, "height": 3, "color": "green"}, 
        "Muster Point 3": {"x": 60, "y": 8, "width": 3, "height": 3, "color": "green"}, 
    }, 
    "pump_stations": { 
        "Pump House A": {"x": 25, "y": 55}, 
        "Pump House B": {"x": 62, "y": 82}, 
        "Pump House C": {"x": 92, "y": 75}, 
        "Transfer Station": {"x": 55, "y": 30}, 
    }, 
    "labels": { 
        "Zone A": {"x": 25, "y": 93, "size": 12}, 
        "Zone B": {"x": 62, "y": 98, "size": 12}, 
        "Zone C": {"x": 92, "y": 73, "size": 12}, 
        "Zone D": {"x": 33, "y": 42, "size": 12}, 
    } 
}
