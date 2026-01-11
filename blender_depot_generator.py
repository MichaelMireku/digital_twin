# ============================================================================
# FUEL DEPOT 3D GENERATOR FOR BLENDER
# ============================================================================
# Run in Blender 3.0+ via Scripting tab
# Creates accurate 3D model of petroleum storage depot
# ============================================================================

import bpy
import math

# ============================================================================
# CONFIGURATION - Depot Layout (matches utils/depot_layout.py)
# ============================================================================

SCALE = 1.0
CENTER_X, CENTER_Y = 60, 55  # Center offset for scene

TANKS = {
    # Zone A - Northwest
    "TK-A01": {"x": 18, "y": 85, "r": 6.5, "h": 12, "type": "AGO"},
    "TK-A02": {"x": 32, "y": 85, "r": 6.5, "h": 12, "type": "AGO"},
    "TK-A03": {"x": 18, "y": 70, "r": 7.0, "h": 14, "type": "PMS"},
    "TK-A04": {"x": 32, "y": 70, "r": 7.0, "h": 14, "type": "PMS"},
    # Zone B - Northeast
    "TK-B01": {"x": 55, "y": 90, "r": 4.5, "h": 8, "type": "AGO"},
    "TK-B02": {"x": 68, "y": 90, "r": 5.0, "h": 10, "type": "AGO"},
    "TK-B03": {"x": 62, "y": 75, "r": 5.5, "h": 10, "type": "AGO"},
    # Zone C - East
    "TK-C01": {"x": 85, "y": 65, "r": 5.5, "h": 12, "type": "AGO"},
    "TK-C02": {"x": 98, "y": 65, "r": 5.5, "h": 12, "type": "AGO"},
    "TK-C03": {"x": 85, "y": 50, "r": 5.5, "h": 12, "type": "PMS"},
    "TK-C04": {"x": 98, "y": 50, "r": 5.5, "h": 12, "type": "PMS"},
    # Zone D - South
    "TK-D01": {"x": 25, "y": 35, "r": 7.0, "h": 14, "type": "AGO"},
    "TK-D02": {"x": 42, "y": 35, "r": 7.0, "h": 14, "type": "AGO"},
    "TK-D03": {"x": 25, "y": 18, "r": 7.0, "h": 14, "type": "AGO"},
    "TK-D04": {"x": 42, "y": 18, "r": 5.5, "h": 10, "type": "AGO"},
}

BUILDINGS = {
    "Admin_Block": {"x": 108, "y": 90, "w": 15, "d": 10, "h": 8},
    "Control_Room": {"x": 60, "y": 45, "w": 12, "d": 8, "h": 5},
    "Operations": {"x": 95, "y": 85, "w": 10, "d": 6, "h": 4},
    "Maintenance": {"x": 108, "y": 25, "w": 12, "d": 8, "h": 5},
    "Gate_House": {"x": 60, "y": 105, "w": 6, "d": 4, "h": 3},
}

PUMP_HOUSES = {
    "PH-A01": {"x": 25, "y": 55, "w": 6, "d": 4},
    "PH-B01": {"x": 62, "y": 82, "w": 5, "d": 4},
    "PH-C01": {"x": 92, "y": 75, "w": 5, "d": 4},
}

BUND_WALLS = {
    "Zone_A": {"x1": 5, "y1": 60, "x2": 45, "y2": 95},
    "Zone_B": {"x1": 48, "y1": 65, "x2": 78, "y2": 98},
    "Zone_C": {"x1": 75, "y1": 40, "x2": 110, "y2": 75},
    "Zone_D": {"x1": 12, "y1": 8, "x2": 55, "y2": 45},
}

GANTRY = {"x": 75, "y": 25, "w": 24, "d": 10, "lanes": 6}

FIRE_TANKS = {
    "Fire_Water_1": {"x": 50, "y": 58, "r": 3, "h": 6},
    "Fire_Water_2": {"x": 75, "y": 78, "r": 3, "h": 6},
}

MUSTER_POINTS = {
    "Muster_A": {"x": 8, "y": 55},
    "Muster_B": {"x": 115, "y": 55},
    "Muster_C": {"x": 60, "y": 8},
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def loc(x, y, z=0):
    """Convert layout coords to Blender coords (centered)."""
    return ((x - CENTER_X) * SCALE, (y - CENTER_Y) * SCALE, z * SCALE)

def clear_scene():
    """Clear all objects and data."""
    # Deselect all first
    if bpy.context.active_object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Clean orphan data
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)

def get_collection(name):
    """Get or create a collection."""
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

def link_to_collection(obj, col_name):
    """Link object to collection and unlink from default."""
    col = get_collection(col_name)
    if obj.name not in col.objects:
        col.objects.link(obj)
    if obj.name in bpy.context.collection.objects:
        bpy.context.collection.objects.unlink(obj)

# ============================================================================
# MATERIALS
# ============================================================================

MATERIALS = {}

def create_material(name, color, metallic=0, roughness=0.5):
    """Create a simple PBR material with viewport color."""
    if name in MATERIALS:
        return MATERIALS[name]
    
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    
    # Set viewport display color (important for solid/material preview)
    mat.diffuse_color = (*color, 1)
    
    MATERIALS[name] = mat
    return mat

def setup_materials():
    """Create all depot materials with distinct colors."""
    # Tanks - distinct colors for product types
    create_material("Tank_AGO", (0.3, 0.5, 0.8), metallic=0.8, roughness=0.3)      # Blue for AGO
    create_material("Tank_PMS", (0.9, 0.3, 0.3), metallic=0.8, roughness=0.3)      # Red for PMS
    create_material("Tank_Roof", (0.85, 0.85, 0.9), metallic=0.95, roughness=0.15) # Silver roof
    
    # Buildings
    create_material("Concrete", (0.7, 0.68, 0.65), metallic=0, roughness=0.9)      # Light gray
    
    # Gantry - safety yellow
    create_material("Gantry", (1.0, 0.8, 0.0), metallic=0.7, roughness=0.4)        # Bright yellow
    
    # Ground & Roads
    create_material("Asphalt", (0.15, 0.15, 0.15), metallic=0, roughness=0.95)     # Dark gray
    create_material("Ground", (0.45, 0.4, 0.3), metallic=0, roughness=0.95)        # Brown/tan
    
    # Bund walls
    create_material("Bund", (0.6, 0.55, 0.5), metallic=0, roughness=0.9)           # Concrete tan
    
    # Safety colors
    create_material("Fire_Red", (0.9, 0.1, 0.1), metallic=0.5, roughness=0.4)      # Bright red
    create_material("Safety_Green", (0.0, 0.8, 0.2), metallic=0, roughness=0.5)    # Bright green
    
    # Infrastructure
    create_material("Pump_Blue", (0.2, 0.4, 0.7), metallic=0.3, roughness=0.6)     # Industrial blue
    create_material("Steel", (0.5, 0.5, 0.55), metallic=0.9, roughness=0.4)        # Steel gray

# ============================================================================
# OBJECT CREATION FUNCTIONS
# ============================================================================

def create_tank(name, x, y, radius, height, tank_type):
    """Create storage tank with roof and details."""
    position = loc(x, y, height/2)
    mat_name = "Tank_PMS" if tank_type == "PMS" else "Tank_AGO"
    
    # Tank shell
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, vertices=48,
        location=position
    )
    tank = bpy.context.active_object
    tank.name = name
    tank.data.materials.append(MATERIALS[mat_name])
    link_to_collection(tank, "Tanks")
    
    # Floating roof - LOCAL position relative to tank center (which is at height/2)
    # So roof at 75% height means: (0.75 * height) - (height/2) = 0.25 * height above center
    roof_local_z = height * 0.25
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius - 0.2, depth=0.25, vertices=48,
        location=(position[0], position[1], position[2] + roof_local_z)
    )
    roof = bpy.context.active_object
    roof.name = f"{name}_Roof"
    roof.data.materials.append(MATERIALS["Tank_Roof"])
    roof.parent = tank
    roof.matrix_parent_inverse = tank.matrix_world.inverted()
    link_to_collection(roof, "Tanks")
    
    # Wind girder ring - at top of tank
    # Top of tank is at height, tank center is at height/2, so girder is (height/2 - 0.3) above center
    girder_local_z = height/2 - 0.3
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius, minor_radius=0.12,
        location=(position[0], position[1], position[2] + girder_local_z)
    )
    girder = bpy.context.active_object
    girder.name = f"{name}_Girder"
    girder.data.materials.append(MATERIALS[mat_name])
    girder.parent = tank
    girder.matrix_parent_inverse = tank.matrix_world.inverted()
    link_to_collection(girder, "Tanks")
    
    return tank

def create_building(name, x, y, width, depth, height):
    """Create a building."""
    position = loc(x, y, height/2)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    bldg = bpy.context.active_object
    bldg.name = name
    bldg.scale = (width/2, depth/2, height/2)
    bldg.data.materials.append(MATERIALS["Concrete"])
    link_to_collection(bldg, "Buildings")
    
    # Roof overhang - at top of building
    roof_z = position[2] + height/2 + 0.1
    bpy.ops.mesh.primitive_cube_add(size=1, location=(position[0], position[1], roof_z))
    roof = bpy.context.active_object
    roof.name = f"{name}_Roof"
    roof.scale = ((width+0.6)/2, (depth+0.6)/2, 0.1)
    roof.data.materials.append(MATERIALS["Concrete"])
    roof.parent = bldg
    roof.matrix_parent_inverse = bldg.matrix_world.inverted()
    link_to_collection(roof, "Buildings")
    
    return bldg

def create_pump_house(name, x, y, width, depth):
    """Create pump house."""
    height = 4
    position = loc(x, y, height/2)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    pump = bpy.context.active_object
    pump.name = name
    pump.scale = (width/2, depth/2, height/2)
    pump.data.materials.append(MATERIALS["Pump_Blue"])
    link_to_collection(pump, "Infrastructure")
    
    # Vent pipe - on top of pump house
    vent_z = position[2] + height/2 + 0.5
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=1, location=(position[0], position[1], vent_z))
    vent = bpy.context.active_object
    vent.name = f"{name}_Vent"
    vent.data.materials.append(MATERIALS["Steel"])
    vent.parent = pump
    vent.matrix_parent_inverse = pump.matrix_world.inverted()
    link_to_collection(vent, "Infrastructure")
    
    return pump

def create_bund_wall(name, x1, y1, x2, y2):
    """Create containment bund walls."""
    wall_h = 1.8
    wall_t = 0.5
    
    walls = []
    segments = [
        ((x1+x2)/2, y1, x2-x1+wall_t, wall_t),  # Bottom
        ((x1+x2)/2, y2, x2-x1+wall_t, wall_t),  # Top
        (x1, (y1+y2)/2, wall_t, y2-y1),          # Left
        (x2, (y1+y2)/2, wall_t, y2-y1),          # Right
    ]
    
    for i, (wx, wy, ww, wd) in enumerate(segments):
        position = loc(wx, wy, wall_h/2)
        bpy.ops.mesh.primitive_cube_add(size=1, location=position)
        wall = bpy.context.active_object
        wall.name = f"{name}_Wall_{i}"
        wall.scale = (ww/2, wd/2, wall_h/2)
        wall.data.materials.append(MATERIALS["Bund"])
        link_to_collection(wall, "Infrastructure")
        walls.append(wall)
    
    return walls

def create_gantry(x, y, width, depth, lanes):
    """Create loading gantry structure."""
    platform_h = 6
    canopy_h = platform_h + 2
    
    # Get base position
    base_x, base_y, _ = loc(x, y, 0)
    
    # Canopy (roof)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(base_x, base_y, canopy_h))
    canopy = bpy.context.active_object
    canopy.name = "Loading_Gantry"
    canopy.scale = (width/2, depth/2, 0.15)
    canopy.data.materials.append(MATERIALS["Gantry"])
    link_to_collection(canopy, "Infrastructure")
    
    # Support columns (6 columns) - absolute positions, not parented
    col_positions = [
        (-width/2+2, -depth/2+1), (0, -depth/2+1), (width/2-2, -depth/2+1),
        (-width/2+2, depth/2-1), (0, depth/2-1), (width/2-2, depth/2-1),
    ]
    for i, (cx, cy) in enumerate(col_positions):
        col_z = canopy_h / 2
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.2, depth=canopy_h, vertices=12,
            location=(base_x + cx, base_y + cy, col_z)
        )
        col = bpy.context.active_object
        col.name = f"Gantry_Column_{i}"
        col.data.materials.append(MATERIALS["Gantry"])
        link_to_collection(col, "Infrastructure")
    
    # Loading platform walkway
    bpy.ops.mesh.primitive_cube_add(size=1, location=(base_x, base_y, platform_h))
    walk = bpy.context.active_object
    walk.name = "Gantry_Walkway"
    walk.scale = (width/2, 1.2, 0.08)
    walk.data.materials.append(MATERIALS["Gantry"])
    link_to_collection(walk, "Infrastructure")
    
    # Loading arms - one per lane
    lane_w = width / lanes
    for i in range(lanes):
        arm_x = base_x - width/2 + lane_w * (i + 0.5)
        arm_z = platform_h + 1
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.06, depth=2.5, vertices=8,
            location=(arm_x, base_y, arm_z),
            rotation=(math.radians(50), 0, 0)
        )
        arm = bpy.context.active_object
        arm.name = f"Loading_Arm_{i+1}"
        arm.data.materials.append(MATERIALS["Steel"])
        link_to_collection(arm, "Infrastructure")
    
    return canopy

def create_fire_tank(name, x, y, radius, height):
    """Create fire water tank."""
    position = loc(x, y, height/2)
    
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, vertices=32,
        location=position
    )
    tank = bpy.context.active_object
    tank.name = name
    tank.data.materials.append(MATERIALS["Fire_Red"])
    link_to_collection(tank, "Safety")
    
    return tank

def create_muster_point(name, x, y):
    """Create muster point marker."""
    base_x, base_y, _ = loc(x, y, 0)
    
    # Ground circle
    bpy.ops.mesh.primitive_cylinder_add(
        radius=2, depth=0.1, vertices=32,
        location=(base_x, base_y, 0.05)
    )
    marker = bpy.context.active_object
    marker.name = name
    marker.data.materials.append(MATERIALS["Safety_Green"])
    link_to_collection(marker, "Safety")
    
    # Sign post
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.06, depth=3, vertices=8,
        location=(base_x, base_y, 1.5)
    )
    post = bpy.context.active_object
    post.name = f"{name}_Post"
    post.data.materials.append(MATERIALS["Steel"])
    link_to_collection(post, "Safety")
    
    return marker

def create_ground():
    """Create ground plane."""
    bpy.ops.mesh.primitive_plane_add(size=180, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(MATERIALS["Ground"])
    link_to_collection(ground, "Environment")
    return ground

def create_roads():
    """Create main roads."""
    roads = [
        {"s": (0, 100), "e": (120, 100), "w": 8, "n": "Main_Road"},
        {"s": (60, 100), "e": (60, 0), "w": 6, "n": "Central_Road"},
        {"s": (0, 55), "e": (120, 55), "w": 5, "n": "Service_Road"},
    ]
    
    for r in roads:
        sx, sy = r["s"]
        ex, ey = r["e"]
        ls = loc(sx, sy, 0.02)
        le = loc(ex, ey, 0.02)
        
        length = math.sqrt((le[0]-ls[0])**2 + (le[1]-ls[1])**2)
        angle = math.atan2(le[1]-ls[1], le[0]-ls[0])
        mid = ((ls[0]+le[0])/2, (ls[1]+le[1])/2, 0.02)
        
        bpy.ops.mesh.primitive_cube_add(size=1, location=mid)
        road = bpy.context.active_object
        road.name = r["n"]
        road.scale = (length/2, r["w"]/2, 0.02)
        road.rotation_euler = (0, 0, angle)
        road.data.materials.append(MATERIALS["Asphalt"])
        link_to_collection(road, "Environment")

# ============================================================================
# LIGHTING & CAMERA
# ============================================================================

def setup_lighting():
    """Create sun and fill lights."""
    # Main sun
    bpy.ops.object.light_add(type='SUN', location=(30, 30, 50))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), math.radians(15), math.radians(45))
    
    # Fill light
    bpy.ops.object.light_add(type='SUN', location=(-30, -30, 40))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 1.5
    fill.rotation_euler = (math.radians(70), 0, math.radians(-135))

def setup_camera():
    """Create overview camera."""
    bpy.ops.object.camera_add(
        location=(80, -80, 60),
        rotation=(math.radians(55), 0, math.radians(45))
    )
    cam = bpy.context.active_object
    cam.name = "Camera_Main"
    cam.data.lens = 28
    cam.data.clip_end = 500
    bpy.context.scene.camera = cam
    
    # Frame camera to view
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            override = bpy.context.copy()
            override['area'] = area
            override['region'] = area.regions[-1]
            with bpy.context.temp_override(**override):
                bpy.ops.view3d.camera_to_view_selected()
            break

def setup_world():
    """Configure world/sky."""
    world = bpy.data.worlds.get("World")
    if world and world.use_nodes:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Color"].default_value = (0.5, 0.6, 0.75, 1)
            bg.inputs["Strength"].default_value = 0.8

def setup_render():
    """Configure render settings."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    
    # Set viewport to Material Preview for colors
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = False
                    space.shading.studio_light = 'studio.exr'
                    space.shading.color_type = 'MATERIAL'
                    break

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Generate the complete fuel depot."""
    print("\n" + "="*60)
    print("  FUEL DEPOT 3D GENERATOR")
    print("="*60)
    
    # Setup
    print("\n[1/8] Clearing scene...")
    clear_scene()
    
    print("[2/8] Creating materials...")
    setup_materials()
    
    # Create collections
    for col_name in ["Tanks", "Buildings", "Infrastructure", "Safety", "Environment"]:
        get_collection(col_name)
    
    # Environment
    print("[3/8] Creating environment...")
    create_ground()
    create_roads()
    
    # Storage Tanks
    print("[4/8] Creating storage tanks...")
    for name, t in TANKS.items():
        create_tank(name, t["x"], t["y"], t["r"], t["h"], t["type"])
    print(f"       -> {len(TANKS)} tanks created")
    
    # Buildings
    print("[5/8] Creating buildings...")
    for name, b in BUILDINGS.items():
        create_building(name, b["x"], b["y"], b["w"], b["d"], b["h"])
    print(f"       -> {len(BUILDINGS)} buildings created")
    
    # Infrastructure
    print("[6/8] Creating infrastructure...")
    for name, p in PUMP_HOUSES.items():
        create_pump_house(name, p["x"], p["y"], p["w"], p["d"])
    for name, bund in BUND_WALLS.items():
        create_bund_wall(name, bund["x1"], bund["y1"], bund["x2"], bund["y2"])
    create_gantry(GANTRY["x"], GANTRY["y"], GANTRY["w"], GANTRY["d"], GANTRY["lanes"])
    
    # Safety systems
    print("[7/8] Creating safety systems...")
    for name, f in FIRE_TANKS.items():
        create_fire_tank(name, f["x"], f["y"], f["r"], f["h"])
    for name, m in MUSTER_POINTS.items():
        create_muster_point(name, m["x"], m["y"])
    
    # Lighting & Camera
    print("[8/8] Setting up lighting and camera...")
    setup_lighting()
    setup_world()
    setup_render()
    
    # Select all depot objects for camera framing
    bpy.ops.object.select_all(action='DESELECT')
    for col_name in ["Tanks", "Buildings", "Infrastructure", "Safety"]:
        col = bpy.data.collections.get(col_name)
        if col:
            for obj in col.objects:
                obj.select_set(True)
    
    setup_camera()
    
    # Done
    print("\n" + "="*60)
    print("  DEPOT GENERATION COMPLETE!")
    print("="*60)
    print(f"\n  Tanks:        {len(TANKS)}")
    print(f"  Buildings:    {len(BUILDINGS)}")
    print(f"  Pump Houses:  {len(PUMP_HOUSES)}")
    print(f"  Bund Zones:   {len(BUND_WALLS)}")
    print(f"  Fire Tanks:   {len(FIRE_TANKS)}")
    print(f"  Muster Pts:   {len(MUSTER_POINTS)}")
    print("\n  -> Press F12 to render")
    print("  -> Use 'Z' key for viewport shading modes")
    print("  -> Check Outliner for organized collections\n")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()
