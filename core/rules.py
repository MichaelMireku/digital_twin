# Conceptual structure for a simple rule engine
def check_tank_high_level(tank_object):
    if tank_object.current_level_metres.value is not None and \
       tank_object.capacity_litres is not None: # Need capacity for this rule
       # Example Threshold: 95% (Needs proper calculation based on height/capacity)
       high_threshold = 14.5 # Placeholder - Should be dynamic per tank
       if tank_object.current_level_metres.value > high_threshold:
           print(f"ALERT: Tank {tank_object.asset_id} HIGH LEVEL detected: {tank_object.current_level_metres.value}m")
           # Add alert logging/notification logic here
           return True
    return False

def evaluate_rules(asset_object):
    """Evaluates all relevant rules for a given asset object."""
    if asset_object.asset_type == 'StorageTank':
        check_tank_high_level(asset_object)
    # Add more rules for different assets/conditions