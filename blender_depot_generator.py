# ============================================================================
# REALISTIC FUEL DEPOT GENERATOR V2.3 (ALL FIXES APPLIED)
# ============================================================================
# Run in Blender 3.0+ via Scripting tab
# Fixes: Roof positioning, staircase positioning, building windows, pipe connections
# ============================================================================

import bpy
import math
import mathutils

# ============================================================================
# CONFIGURATION
# ============================================================================

SCALE = 1.0
CENTER_X, CENTER_Y = 70, 60

TANKS = {
    # Zone A - Northwest (AGO/PMS)
    "TK-A01": {"x": 18, "y": 95, "r": 6.5, "h": 12, "type": "AGO"},
    "TK-A02": {"x": 35, "y": 95, "r": 6.5, "h": 12, "type": "AGO"},
    "TK-A03": {"x": 18, "y": 78, "r": 7.0, "h": 14, "type": "PMS"},
    "TK-A04": {"x": 35, "y": 78, "r": 7.0, "h": 14, "type": "PMS"},
    # Zone B - Northeast (Smaller tanks)
    "TK-B01": {"x": 58, "y": 100, "r": 4.5, "h": 8, "type": "AGO"},
    "TK-B02": {"x": 72, "y": 100, "r": 5.0, "h": 10, "type": "AGO"},
    "TK-B03": {"x": 65, "y": 88, "r": 5.5, "h": 10, "type": "AGO"},
    # Zone C - East
    "TK-C01": {"x": 105, "y": 75, "r": 5.5, "h": 12, "type": "AGO"},
    "TK-C02": {"x": 120, "y": 75, "r": 5.5, "h": 12, "type": "AGO"},
    "TK-C03": {"x": 105, "y": 60, "r": 5.5, "h": 12, "type": "PMS"},
    "TK-C04": {"x": 120, "y": 60, "r": 5.5, "h": 12, "type": "PMS"},
    # Zone D - South
    "TK-D01": {"x": 20, "y": 38, "r": 7.0, "h": 14, "type": "AGO"},
    "TK-D02": {"x": 40, "y": 38, "r": 7.0, "h": 14, "type": "AGO"},
    "TK-D03": {"x": 20, "y": 18, "r": 7.0, "h": 14, "type": "AGO"},
    "TK-D04": {"x": 40, "y": 18, "r": 5.5, "h": 10, "type": "AGO"},
}

BUILDINGS = {
    "Admin_Block": {"x": 125, "y": 25, "w": 14, "d": 10, "h": 8},
    "Maintenance": {"x": 125, "y": 40, "w": 12, "d": 8, "h": 5},
    "Control_Room": {"x": 88, "y": 50, "w": 10, "d": 7, "h": 5},
    "Operations": {"x": 92, "y": 95, "w": 8, "d": 6, "h": 4},
    "Gate_House": {"x": 70, "y": 116, "w": 6, "d": 4, "h": 3},
}

PUMP_HOUSES = {
    "PH-A": {"x": 26, "y": 62, "w": 6, "d": 4},
    "PH-B": {"x": 65, "y": 76, "w": 5, "d": 4},
    "PH-C": {"x": 90, "y": 67, "w": 5, "d": 4},
    "Transfer": {"x": 60, "y": 30, "w": 6, "d": 4},
}

BUND_WALLS = {
    "Zone_A": {"x1": 8, "y1": 68, "x2": 48, "y2": 108},
    "Zone_B": {"x1": 50, "y1": 80, "x2": 82, "y2": 110},
    "Zone_C": {"x1": 95, "y1": 50, "x2": 130, "y2": 85},
    "Zone_D": {"x1": 8, "y1": 6, "x2": 50, "y2": 50},
}

GANTRY = {"x": 85, "y": 25, "w": 24, "d": 10, "lanes": 6}

FIRE_TANKS = {
    "Fire_Water_1": {"x": 62, "y": 65, "r": 3, "h": 6},
    "Fire_Water_2": {"x": 80, "y": 45, "r": 3, "h": 6},
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def loc(x, y, z=0):
    """Convert depot coordinates to Blender world coordinates."""
    return ((x - CENTER_X) * SCALE, (y - CENTER_Y) * SCALE, z * SCALE)

def clear_scene():
    """Clear all objects, meshes, materials, and collections."""
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.collections:
        bpy.data.collections.remove(block)

def get_collection(name):
    """Get or create a collection by name."""
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

def link_to_collection(obj, col_name):
    """Link object to specified collection and unlink from default."""
    col = get_collection(col_name)
    if obj.name not in col.objects:
        col.objects.link(obj)
    if obj.name in bpy.context.collection.objects:
        bpy.context.collection.objects.unlink(obj)

def add_bevel(obj, width=0.05):
    """Add bevel modifier for realistic edges."""
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = 2
    mod.limit_method = 'ANGLE'

# ============================================================================
# MATERIALS
# ============================================================================

MATERIALS = {}

def create_pbr_material(name, color, roughness=0.5, metallic=0.0, bump_strength=0.0):
    """Create a PBR material with optional noise texture."""
    if name in MATERIALS:
        return MATERIALS[name]
    
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    
    if bump_strength > 0:
        noise = nodes.new(type='ShaderNodeTexNoise')
        noise.inputs["Scale"].default_value = 50.0
        noise.inputs["Detail"].default_value = 5.0
        noise.location = (-400, 200)
        
        bump = nodes.new(type='ShaderNodeBump')
        bump.inputs["Strength"].default_value = bump_strength
        bump.location = (-100, -100)
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    mat.diffuse_color = (*color, 1)
    MATERIALS[name] = mat
    return mat

def setup_materials():
    """Initialize all materials used in the scene."""
    create_pbr_material("Tank_AGO", (0.2, 0.4, 0.7), metallic=0.3, roughness=0.4, bump_strength=0.02)
    create_pbr_material("Tank_PMS", (0.8, 0.2, 0.2), metallic=0.3, roughness=0.4, bump_strength=0.02)
    create_pbr_material("Tank_Roof", (0.8, 0.8, 0.85), metallic=0.7, roughness=0.3, bump_strength=0.05)
    create_pbr_material("Fire_Tank", (0.9, 0.1, 0.1), metallic=0.3, roughness=0.4, bump_strength=0.02)
    create_pbr_material("Concrete", (0.7, 0.7, 0.65), roughness=0.9, bump_strength=0.2)
    create_pbr_material("Concrete_Bund", (0.6, 0.55, 0.5), roughness=0.95, bump_strength=0.3)
    create_pbr_material("Asphalt", (0.1, 0.1, 0.12), roughness=0.8, bump_strength=0.1)
    create_pbr_material("Grass", (0.2, 0.4, 0.1), roughness=0.9, bump_strength=0.4)
    create_pbr_material("Steel", (0.5, 0.5, 0.55), metallic=0.9, roughness=0.3)
    create_pbr_material("Pipe_Silver", (0.7, 0.7, 0.7), metallic=0.8, roughness=0.3)
    create_pbr_material("Safety_Yellow", (1.0, 0.7, 0.0), roughness=0.4)
    create_pbr_material("Glass", (0.4, 0.5, 0.6), metallic=0.0, roughness=0.1)

# ============================================================================
# OBJECT CREATION FUNCTIONS
# ============================================================================

def create_tank(name, x, y, radius, height, tank_type, is_fire_tank=False):
    """Create a storage tank with roof and optional staircase."""
    # Calculate world position - tank base at ground level (z=0)
    world_x, world_y, _ = loc(x, y, 0)
    tank_center_z = height / 2  # Center of cylinder
    
    # Main cylinder body
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, 
        depth=height, 
        vertices=64, 
        location=(world_x, world_y, tank_center_z)
    )
    tank = bpy.context.active_object
    tank.name = name
    
    if is_fire_tank:
        tank.data.materials.append(MATERIALS["Fire_Tank"])
    else:
        mat_name = "Tank_PMS" if tank_type == "PMS" else "Tank_AGO"
        tank.data.materials.append(MATERIALS[mat_name])
    link_to_collection(tank, "Tanks")
    
    # Conical roof - sits on top of tank
    roof_depth = 1.5
    roof_z = height + (roof_depth / 2)  # Top of tank + half roof height
    bpy.ops.mesh.primitive_cone_add(
        radius1=radius + 0.1, 
        radius2=0.5,  # Small top for cone
        depth=roof_depth, 
        vertices=64, 
        location=(world_x, world_y, roof_z)
    )
    roof = bpy.context.active_object
    roof.name = f"{name}_Roof"
    roof.data.materials.append(MATERIALS["Tank_Roof"])
    link_to_collection(roof, "Tanks")
    
    # Spiral staircase for larger tanks
    if height > 8 and not is_fire_tank:
        create_spiral_staircase(world_x, world_y, radius, height)
    
    return tank

def create_spiral_staircase(tank_x, tank_y, radius, height):
    """Create a spiral staircase around a tank."""
    steps = int(height * 2)
    stair_radius = radius + 0.8
    
    for i in range(steps):
        angle = (i / steps) * math.pi * 1.5  # 270 degrees wrap
        step_z = (i / steps) * height + 0.5  # Start slightly above ground
        
        step_x = tank_x + math.cos(angle) * stair_radius
        step_y = tank_y + math.sin(angle) * stair_radius
        
        bpy.ops.mesh.primitive_cube_add(size=1, location=(step_x, step_y, step_z))
        step = bpy.context.active_object
        step.scale = (0.8, 0.3, 0.05)
        step.rotation_euler = (0, 0, angle + math.pi/2)
        step.name = f"Stair_Step_{i}"
        step.data.materials.append(MATERIALS["Steel"])
        link_to_collection(step, "Infrastructure")
        
        # Vertical support post every 5 steps
        if i % 5 == 0:
            post_x = tank_x + math.cos(angle) * (stair_radius + 0.3)
            post_y = tank_y + math.sin(angle) * (stair_radius + 0.3)
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.05, 
                depth=step_z, 
                location=(post_x, post_y, step_z / 2)
            )
            post = bpy.context.active_object
            post.name = f"Stair_Post_{i}"
            post.data.materials.append(MATERIALS["Steel"])
            link_to_collection(post, "Infrastructure")

def create_building(name, x, y, width, depth, height):
    """Create a building with window strip."""
    world_x, world_y, _ = loc(x, y, 0)
    building_center_z = height / 2
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(world_x, world_y, building_center_z))
    bldg = bpy.context.active_object
    bldg.name = name
    bldg.scale = (width / 2, depth / 2, height / 2)
    bldg.data.materials.append(MATERIALS["Concrete"])
    add_bevel(bldg, 0.1)
    link_to_collection(bldg, "Buildings")
    
    # Window strip at 2/3 height
    window_z = height * 0.6
    bpy.ops.mesh.primitive_cube_add(size=1, location=(world_x, world_y, window_z))
    win = bpy.context.active_object
    win.name = f"{name}_Windows"
    win.scale = (width / 2 + 0.02, depth / 2 + 0.02, height / 8)
    win.data.materials.append(MATERIALS["Glass"])
    link_to_collection(win, "Buildings")
    
    return bldg

def create_pump_house(name, x, y, width, depth):
    """Create a pump house structure."""
    height = 4
    world_x, world_y, _ = loc(x, y, 0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(world_x, world_y, height / 2))
    pump = bpy.context.active_object
    pump.name = name
    pump.scale = (width / 2, depth / 2, height / 2)
    pump.data.materials.append(MATERIALS["Steel"])
    add_bevel(pump, 0.05)
    link_to_collection(pump, "Infrastructure")
    return pump

def create_bund_wall(name, x1, y1, x2, y2):
    """Create containment bund with floor and walls."""
    wall_h = 1.8
    wall_t = 0.5
    
    # Bund floor
    floor_w = abs(x2 - x1)
    floor_d = abs(y2 - y1)
    cx, cy, _ = loc((x1 + x2) / 2, (y1 + y2) / 2, 0)
    
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, 0.05))
    floor = bpy.context.active_object
    floor.scale = (floor_w / 2, floor_d / 2, 1)
    floor.name = f"{name}_Floor"
    floor.data.materials.append(MATERIALS["Concrete_Bund"])
    link_to_collection(floor, "Infrastructure")
    
    # Four walls
    wall_specs = [
        ((x1 + x2) / 2, y1, (x2 - x1) + wall_t, wall_t),  # South
        ((x1 + x2) / 2, y2, (x2 - x1) + wall_t, wall_t),  # North
        (x1, (y1 + y2) / 2, wall_t, (y2 - y1)),           # West
        (x2, (y1 + y2) / 2, wall_t, (y2 - y1)),           # East
    ]
    
    for i, (wx, wy, ww, wd) in enumerate(wall_specs):
        world_x, world_y, _ = loc(wx, wy, 0)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(world_x, world_y, wall_h / 2))
        wall = bpy.context.active_object
        wall.name = f"{name}_Wall_{i}"
        wall.scale = (ww / 2, wd / 2, wall_h / 2)
        wall.data.materials.append(MATERIALS["Concrete_Bund"])
        add_bevel(wall, 0.05)
        link_to_collection(wall, "Infrastructure")

def create_gantry(x, y, width, depth, lanes):
    """Create loading gantry with columns, canopy, and loading arms."""
    canopy_h = 8.5
    world_x, world_y, _ = loc(x, y, 0)
    
    # Four corner columns
    col_positions = [
        (-width / 2, -depth / 2),
        (width / 2, -depth / 2),
        (-width / 2, depth / 2),
        (width / 2, depth / 2)
    ]
    
    for cx, cy in col_positions:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.4, 
            depth=canopy_h, 
            location=(world_x + cx, world_y + cy, canopy_h / 2)
        )
        col = bpy.context.active_object
        col.name = "Gantry_Column"
        col.data.materials.append(MATERIALS["Safety_Yellow"])
        link_to_collection(col, "Infrastructure")
    
    # Canopy roof
    bpy.ops.mesh.primitive_cube_add(size=1, location=(world_x, world_y, canopy_h))
    canopy = bpy.context.active_object
    canopy.name = "Gantry_Canopy"
    canopy.scale = (width / 2 + 2, depth / 2 + 2, 0.3)
    canopy.data.materials.append(MATERIALS["Safety_Yellow"])
    link_to_collection(canopy, "Infrastructure")
    
    # Loading arms for each lane
    lane_w = width / lanes
    arm_height = 6
    for i in range(lanes):
        arm_x = world_x - width / 2 + lane_w * (i + 0.5)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.08, 
            depth=2.5, 
            location=(arm_x, world_y, arm_height)
        )
        arm = bpy.context.active_object
        arm.rotation_euler = (math.radians(60), 0, 0)
        arm.name = f"Loading_Arm_{i}"
        arm.data.materials.append(MATERIALS["Steel"])
        link_to_collection(arm, "Infrastructure")

def create_pipe_segment(start_x, start_y, end_x, end_y, pipe_height):
    """Create pipe connecting two points with vertical risers."""
    sx, sy, _ = loc(start_x, start_y, 0)
    ex, ey, _ = loc(end_x, end_y, 0)
    
    # Vertical riser at start
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15, 
        depth=pipe_height, 
        location=(sx, sy, pipe_height / 2)
    )
    v1 = bpy.context.active_object
    v1.name = "Pipe_Riser"
    v1.data.materials.append(MATERIALS["Pipe_Silver"])
    link_to_collection(v1, "Pipes")
    
    # Vertical riser at end
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15, 
        depth=pipe_height, 
        location=(ex, ey, pipe_height / 2)
    )
    v2 = bpy.context.active_object
    v2.name = "Pipe_Riser"
    v2.data.materials.append(MATERIALS["Pipe_Silver"])
    link_to_collection(v2, "Pipes")
    
    # Horizontal pipe
    dist = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
    mid_x = (sx + ex) / 2
    mid_y = (sy + ey) / 2
    angle = math.atan2(ey - sy, ex - sx)
    
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15, 
        depth=dist, 
        location=(mid_x, mid_y, pipe_height)
    )
    hor = bpy.context.active_object
    hor.rotation_euler = (0, math.pi / 2, angle)
    hor.name = "Pipe_Horizontal"
    hor.data.materials.append(MATERIALS["Pipe_Silver"])
    link_to_collection(hor, "Pipes")

def create_fence(x1, y1, x2, y2):
    """Create perimeter security fence."""
    height = 2.5
    
    # Fence segments: South, North (with gate gap), West, East
    segments = [
        ((x1 + x2) / 2, y1, x2 - x1, 0.1, False),      # South
        ((x1 + x2) / 2, y2, x2 - x1, 0.1, True),       # North (gate)
        (x1, (y1 + y2) / 2, 0.1, y2 - y1, False),      # West
        (x2, (y1 + y2) / 2, 0.1, y2 - y1, False),      # East
    ]
    
    for wx, wy, sw, sd, has_gate in segments:
        if has_gate:
            continue  # Skip north wall for gate entrance
        
        world_x, world_y, _ = loc(wx, wy, 0)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(world_x, world_y, height / 2))
        fence = bpy.context.active_object
        fence.name = "Security_Fence"
        fence.scale = (sw / 2, sd / 2, height / 2)
        fence.data.materials.append(MATERIALS["Steel"])
        fence.display_type = 'WIRE'
        link_to_collection(fence, "Infrastructure")

def create_roads_and_ground():
    """Create ground plane and road network."""
    # Main ground
    bpy.ops.mesh.primitive_plane_add(size=300, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(MATERIALS["Grass"])
    link_to_collection(ground, "Environment")
    
    # Road definitions: start, end, width
    roads = [
        {"s": (0, 115), "e": (140, 115), "w": 10},   # North perimeter
        {"s": (70, 115), "e": (70, 0), "w": 8},      # Central N-S
        {"s": (0, 55), "e": (140, 55), "w": 6},      # Central E-W
        {"s": (55, 10), "e": (120, 10), "w": 8},     # South access
        {"s": (130, 0), "e": (130, 115), "w": 6},    # East perimeter
    ]
    
    for i, r in enumerate(roads):
        sx, sy = r["s"]
        ex, ey = r["e"]
        
        start_world = loc(sx, sy, 0.02)
        end_world = loc(ex, ey, 0.02)
        
        length = math.sqrt(
            (end_world[0] - start_world[0]) ** 2 + 
            (end_world[1] - start_world[1]) ** 2
        )
        angle = math.atan2(
            end_world[1] - start_world[1], 
            end_world[0] - start_world[0]
        )
        mid = (
            (start_world[0] + end_world[0]) / 2,
            (start_world[1] + end_world[1]) / 2,
            0.02
        )
        
        bpy.ops.mesh.primitive_plane_add(size=1, location=mid)
        road = bpy.context.active_object
        road.name = f"Road_{i}"
        road.scale = (length / 2, r["w"] / 2, 1)
        road.rotation_euler = (0, 0, angle)
        road.data.materials.append(MATERIALS["Asphalt"])
        link_to_collection(road, "Environment")

# ============================================================================
# LIGHTING & CAMERA
# ============================================================================

def setup_lighting_environment():
    """Setup sky texture and lighting."""
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    
    # Get or create background node
    bg = None
    for node in nodes:
        if node.type == 'BACKGROUND':
            bg = node
            break
    if not bg:
        bg = nodes.new("ShaderNodeBackground")
    
    # Add sky texture
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = 'NISHITA'
    sky.dust_density = 1.2
    sky.sun_elevation = math.radians(35)
    sky.sun_rotation = math.radians(200)
    
    links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0

def setup_camera():
    """Setup camera with good overview angle."""
    bpy.ops.object.camera_add(
        location=(140, -100, 90), 
        rotation=(math.radians(55), 0, math.radians(45))
    )
    cam = bpy.context.active_object
    cam.name = "Main_Camera"
    cam.data.lens = 35
    bpy.context.scene.camera = cam

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main function to generate the depot."""
    clear_scene()
    setup_materials()
    
    # Create collections
    for col in ["Tanks", "Buildings", "Infrastructure", "Pipes", "Environment"]:
        get_collection(col)
    
    # Ground and roads first
    create_roads_and_ground()
    
    # Storage tanks
    for name, t in TANKS.items():
        create_tank(name, t["x"], t["y"], t["r"], t["h"], t["type"])
    
    # Fire water tanks
    for name, f in FIRE_TANKS.items():
        create_tank(name, f["x"], f["y"], f["r"], f["h"], "AGO", is_fire_tank=True)
    
    # Buildings
    for name, b in BUILDINGS.items():
        create_building(name, b["x"], b["y"], b["w"], b["d"], b["h"])
    
    # Bund walls
    for name, bund in BUND_WALLS.items():
        create_bund_wall(name, bund["x1"], bund["y1"], bund["x2"], bund["y2"])
    
    # Pump houses
    for name, p in PUMP_HOUSES.items():
        create_pump_house(name, p["x"], p["y"], p["w"], p["d"])
    
    # Gantry
    create_gantry(GANTRY["x"], GANTRY["y"], GANTRY["w"], GANTRY["d"], GANTRY["lanes"])
    
    # Pipe network
    create_pipe_segment(35, 78, 26, 62, 1.5)   # Zone A to Pump A
    create_pipe_segment(40, 38, 60, 30, 1.5)   # Zone D to Transfer
    create_pipe_segment(60, 30, 85, 25, 2.0)   # Transfer to Gantry
    
    # Perimeter fence
    create_fence(0, 0, 140, 120)
    
    # Environment
    setup_lighting_environment()
    setup_camera()
    
    # Render settings
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.cycles.use_denoising = True
    
    print("Depot generation complete!")

if __name__ == "__main__":
    main()
