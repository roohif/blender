import bpy
import math
import random
import mathutils

from pprint import pprint as pp

EARTH_JPG = "C:\\Users\\glenn\\Dropbox\\Desktop\\Earth_Diffuse_6K.jpg"

################################################################################

def createRotationMatrix(up, forward):
    
    up.normalize()
    forward.normalize()
    
    # Calculate the right vector (perpendicular to forward and up)
    right = up.cross(forward).normalized()
    
    # Recalculate the up vector to ensure orthogonality
    up = forward.cross(right).normalized()
    
    # Create the rotation matrix
    rotationMatrix = mathutils.Matrix((
        right.to_4d(),      # Right vector as the first column
        up.to_4d(),         # Up vector as the second column
        forward.to_4d(),    # Forward vector as the third column
        mathutils.Vector((0, 0, 0, 1))  # Homogeneous coordinate for translation
    )).transposed()  # Transpose for row-major order
    
    return rotationMatrix

################################################################################

def UpdateCamera(self, context):
    
    # We might be animating - get the rotation of the earth!
    earth = bpy.data.objects["Earth"]
    # print("Earth Rotation", earth.rotation_euler.z)
    
    lat = math.radians(self.latitude)
    lon = math.radians(self.longitude) + earth.rotation_euler.z
    
    alt = math.radians(-self.altitude) # NEGATIVE
    az = math.radians(self.azimuth - 180)
    
    # Get an 'Object'-TYPED reference to the camera so that we can access the location
    camera = bpy.data.objects[self.name]
    
    # Move the camera to the new location
    earthRadius = 1.0
    obsX = earthRadius * math.cos(lat) * math.cos(lon)
    obsY = earthRadius * math.cos(lat) * math.sin(lon)
    obsZ = earthRadius * math.sin(lat)
    
    camera.location = newLocation = (obsX, obsY, obsZ)
    
    surfaceNormal = mathutils.Vector(newLocation)
    surfaceNormal.normalize()
    
    zAxis = mathutils.Vector((0, 0, 1))
    
    eastVector = zAxis.cross(surfaceNormal)
    eastVector.normalize()
    
    northVector = surfaceNormal.cross(eastVector)
    
    direction = math.cos(alt) * (math.cos(az) * northVector + math.sin(az) * eastVector) + math.sin(alt) * surfaceNormal
    direction.normalize()
    
    camera.matrix_world = createRotationMatrix(surfaceNormal, direction)
    camera.location = newLocation = (obsX, obsY, obsZ)
    
################################################################################

def UpdateScene(scene):
    
    earth = bpy.data.objects["Earth"]
    earth.rotation_euler.z = scene.rotation # Radians

    print(scene.rotation, earth.rotation_euler.z)
    
    camera = bpy.data.cameras["Camera"]
    UpdateCamera(camera, bpy.context)

################################################################################

class ObserverPanel(bpy.types.Panel):
    """Creates a Panel in the Camera properties window"""
    bl_label = "Earth Observer"
    bl_idname = "CAMERA_PT_Observer"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    
    @classmethod
    def poll(cls, context):
        if context.object is None:
            return False
        
        # Checks the context to make sure we are only operating on a CAMERA type
        return (context.object.type == 'CAMERA')

    def draw(self, context):
        
        layout = self.layout

        row = layout.row()
        row.prop(context.active_object.data, 'latitude', toggle=True, text='Latitude:')
        row.prop(context.active_object.data, 'longitude', toggle=True, text='Longitude:')

        layout.separator()

        row = layout.row()
        row.prop(context.active_object.data, 'altitude', toggle=True, text='Altitude:')
        row.prop(context.active_object.data, 'azimuth', toggle=True, text='Azimuth:')

        layout.separator()

def register():
    
    # Default Camera position is in Sydney, looking SOUTH
    bpy.types.Camera.latitude = bpy.props.FloatProperty(name='latitude', default=-33.87, min=-90, max=90, update=UpdateCamera)
    bpy.types.Camera.longitude = bpy.props.FloatProperty(name='longitude', default=151.21, min=-180, max=180, update=UpdateCamera)

    bpy.types.Camera.altitude = bpy.props.FloatProperty(name='altitude', default=33.87, min=0, max=89.99, update=UpdateCamera)
    bpy.types.Camera.azimuth = bpy.props.IntProperty(name='azimuth', default=180, min=0, max=360, update=UpdateCamera)

    rc = bpy.utils.register_class(ObserverPanel)

def unregister():
    
    bpy.utils.unregister_class(ObserverPanel)


################################################################################

if __name__ == "__main__":
    register()

# Create a custom property that controls the overall rotation, be it the globe
# or the stars - and set two keyframes
bpy.types.Scene.rotation = bpy.props.FloatProperty(name='rotation', default=0, min=0.0, max=math.pi * 2)

if UpdateScene in bpy.app.handlers.frame_change_post:
    bpy.app.handlers.frame_change_post.remove(UpdateScene)

# Register the new handler    
bpy.app.handlers.frame_change_post.append(UpdateScene)
        
# Beginning frame
bpy.context.scene.rotation = 0.0
bpy.context.scene.keyframe_insert(data_path='rotation', frame=1)

# Last frame
bpy.context.scene.rotation = math.pi * 2
bpy.context.scene.keyframe_insert(data_path='rotation', frame=250)

# Set it to LINEAR
action = bpy.context.scene.animation_data.action
fcurve = None

# Loop through F-Curves to find the one corresponding to "rotation"
for fc in action.fcurves:
    if fc.data_path == "rotation":  # X location
        fcurve = fc
        break

# Step 4: Set the interpolation type to "LINEAR" for each keyframe
if fcurve:
    for keyframe in fcurve.keyframe_points:
        keyframe.interpolation = 'LINEAR'

################################################################################

# Create the earth and overlap the map on it
earthMaterial = bpy.data.materials.new('earthMaterial')
earthMaterial.use_nodes = True

bsdf = earthMaterial.node_tree.nodes.get("Principled BSDF")

earthTexture = earthMaterial.node_tree.nodes.new("ShaderNodeTexImage")
earthTexture.image = bpy.data.images.load(EARTH_JPG)

earthMaterial.node_tree.links.new(earthTexture.outputs[0], bsdf.inputs[0])

bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
earth = bpy.context.active_object
earth.data.materials.append(earthMaterial)
earth.name = "Earth"

################################################################################

starMaterial = bpy.data.materials.new(name="starMaterial")
starMaterial.diffuse_color = (1, 1, 0, 1) # Yellow RGBA

# Create the celestial sphere
CELESTIAL_SPHERE_RADIUS = 100

print(bpy.data.collections)

# Put a bunch of stars on the celestial sphere
TOTAL_STARS = 500
for c in range(0, TOTAL_STARS):
    # Randomly create a point on the surface
    X = random.uniform(-CELESTIAL_SPHERE_RADIUS, CELESTIAL_SPHERE_RADIUS)
    
    # Constrain Y
    maxY =  math.sqrt(CELESTIAL_SPHERE_RADIUS**2 - X**2)
    Y = random.uniform(-maxY, maxY)
    
    # Compute Z
    Z = math.sqrt(CELESTIAL_SPHERE_RADIUS**2 - X**2 - Y**2) * random.choice([-1, 1])
    
    # place the star!
    locationTuple = [X, Y, Z]
    random.shuffle(locationTuple)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(0.2, 0.5), subdivisions=2, location=locationTuple)
    star = bpy.context.active_object
    star.name = f"star.{c:03}"
    bpy.ops.object.material_slot_add()
    bpy.context.object.material_slots[0].material = starMaterial

################################################################################

print("DONE")