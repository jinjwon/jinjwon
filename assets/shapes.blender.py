# Renders a seamless loop of four primitives, each in a different material:
# clay rounded cube, brushed-metal ring, lacquered sphere, matte faceted icosahedron.
#   Blender -b -P geo3d.py -- <out_dir> test    -> 2 stills, to check the look
#   Blender -b -P geo3d.py -- <out_dir> anim    -> all N frames
import bpy, math, sys
from mathutils import Euler, Vector

OUT, MODE = sys.argv[sys.argv.index("--") + 1:][:2]
N = 48

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def lin(hexc):
    """sRGB hex -> linear RGBA, which is what shader colors expect."""
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [((v + .055) / 1.055) ** 2.4 if v > .04045 else v / 12.92 for v in c] + [1]


def mat(name, hexc, grain=0, **inputs):
    """Principled material. `grain` adds a fine noise bump so the surface is not CG-smooth."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = lin(hexc)
    for k, v in inputs.items():
        b.inputs[k].default_value = v
    if grain:
        noise, bump = nt.nodes.new('ShaderNodeTexNoise'), nt.nodes.new('ShaderNodeBump')
        noise.inputs["Scale"].default_value, noise.inputs["Detail"].default_value = 140, 6
        bump.inputs["Strength"].default_value = grain
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def finish(material, smooth=True):
    o = bpy.context.object
    if smooth: bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


bpy.ops.mesh.primitive_cube_add(size=1.5)
cube = finish(mat("clay", "#ece6dc", grain=.12, Roughness=.9))
bev = cube.modifiers.new("round", 'BEVEL'); bev.width, bev.segments = .26, 16

bpy.ops.mesh.primitive_torus_add(major_radius=1.45, minor_radius=.1, major_segments=128, minor_segments=32)
ring = finish(mat("metal", "#d9dce2", Metallic=1, Roughness=.28, Anisotropic=.7))

bpy.ops.mesh.primitive_uv_sphere_add(radius=.36, segments=64, ring_count=32)
ball = finish(mat("lacquer", "#4f63ff", Roughness=.35, **{"Coat Weight": 1, "Coat Roughness": .04}))

bpy.ops.mesh.primitive_ico_sphere_add(radius=.34, subdivisions=1)
ico = finish(mat("matte", "#e07a5a", grain=.08, Roughness=.75), smooth=False)

# Lights show up in the metal and lacquer as soft highlights; the world keeps shadows from going black.
for loc, size, watts, color in [((-4, -5, 6), 6, 1100, (1, .97, .93)), ((5.5, -3, 1), 4, 320, (.8, .87, 1)), ((0, 6, 4), 5, 700, (1, 1, 1))]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.size, l.data.energy, l.data.color = size, watts, color
    l.rotation_euler = (-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value, bg.inputs[1].default_value = (.55, .58, .62, 1), .5

bpy.ops.object.camera_add(location=(0, -11.5, 2.7))
cam = bpy.context.object
cam.data.lens = 85
cam.rotation_euler = (-cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam

r = scene.render
r.engine = 'CYCLES'
scene.cycles.samples, scene.cycles.use_denoising = 96, True
try:  # GPU if this Mac offers it, else CPU
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("GPU unavailable, using CPU:", e)
r.resolution_x, r.resolution_y, r.film_transparent = 440, 440, True
r.image_settings.file_format, r.image_settings.color_mode = 'PNG', 'RGBA'


def orbit(t, radius, tilt, phase):
    a = 2 * math.pi * (t + phase)
    p = Vector((radius * math.cos(a), radius * math.sin(a), 0))
    p.rotate(Euler((tilt, 0, .5)))
    return p


def pose(t):
    """Every motion is a whole symmetry step per loop, so frame N equals frame 0."""
    cube.rotation_euler = Euler((.5, .35, 0)).to_matrix().to_4x4().to_euler()
    cube.rotation_euler.rotate_axis('Z', t * math.pi / 2)       # quarter turn: a cube looks the same
    ring.rotation_euler = (math.radians(68) + t * math.pi, 0, .4)  # half tumble: so does a ring
    ball.location = orbit(t, 1.95, math.radians(20), 0)
    ico.location = orbit(t, 1.95, math.radians(-35), .5)
    ico.rotation_euler = (t * 2 * math.pi, t * 2 * math.pi, 0)


frames = [0, N // 3] if MODE == "test" else range(N)
for i in frames:
    pose(i / N)
    r.filepath = f"{OUT}/g{i:03d}.png"
    bpy.ops.render.render(write_still=True)
