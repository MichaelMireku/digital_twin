import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TankTransferSimulator:
    def __init__(self, source_tank: Dict[str, Any], dest_tank: Dict[str, Any], pump: Dict[str, Any]):
        self.source_tank = source_tank
        self.dest_tank = dest_tank
        self.pump = pump
        
        # Using a typical pump flow rate for this type of service
        self.pump_flow_rate_lpm = float(pump.get('flow_rate_lpm', 2500)) # Litres per minute
        self.time_step_minutes = 5
        
        logger.info(f"TankTransferSimulator initialized for {source_tank['asset_id']} -> {dest_tank['asset_id']} via {pump['asset_id']}")

    def run(self) -> Dict[str, Any]:
        """Runs the tank transfer simulation."""
        
        source_vol = self.source_tank['current_volume_litres']
        dest_vol = self.dest_tank['current_volume_litres']
        
        source_capacity = self.source_tank['capacity_litres']
        dest_capacity = self.dest_tank['capacity_litres']
        
        # Safety thresholds (95% for high, 5% for low)
        dest_high_level = dest_capacity * 0.95
        source_low_level = source_capacity * 0.05
        
        timestamps = [0]
        source_vols = [source_vol]
        dest_vols = [dest_vol]
        
        alerts = []
        
        elapsed_time_minutes = 0
        volume_per_step = self.pump_flow_rate_lpm * self.time_step_minutes

        while source_vol > source_low_level and dest_vol < dest_high_level:
            transfer_vol = min(volume_per_step, source_vol - source_low_level, dest_high_level - dest_vol)
            
            source_vol -= transfer_vol
            dest_vol += transfer_vol
            elapsed_time_minutes += self.time_step_minutes
            
            timestamps.append(elapsed_time_minutes)
            source_vols.append(source_vol)
            dest_vols.append(dest_vol)

            if dest_vol >= dest_high_level:
                alerts.append(f"Destination tank {self.dest_tank['asset_id']} will reach High Level Alarm.")
            if source_vol <= source_low_level:
                alerts.append(f"Source tank {self.source_tank['asset_id']} will reach Low Level Alarm.")
        
        total_time_hours = elapsed_time_minutes / 60
        
        return {
            "summary": {
                "total_time_hours": round(total_time_hours, 2),
                "total_volume_transferred": round(dest_vols[-1] - self.dest_tank['current_volume_litres'], 0),
                "predicted_alerts": alerts if alerts else ["No alarms predicted."]
            },
            "results": {
                "timestamps": timestamps,
                "source_tank_volume": source_vols,
                "dest_tank_volume": dest_vols
            }
        }
