# Builds a round grass-owl typing at a laptop and renders a seamless loop of PNG frames.
#   Blender -b -P owl3d.py -- <out_dir> test    -> 3 stills, to check the look
#   Blender -b -P owl3d.py -- <out_dir> anim    -> all N frames
# Owl faces -Y, Z is up, body radius is 1.
import bpy, math, sys
from mathutils import Vector

OUT, MODE = sys.argv[sys.argv.index("--") + 1:][:2]
N = 40
BODY = Vector((1, .97, 1.1))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def lin(hexc):
    """sRGB hex -> linear RGBA, which is what shader colors expect."""
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [((v + .055) / 1.055) ** 2.4 if v > .04045 else v / 12.92 for v in c] + [1]


def mat(name, hexc, rough=.7, emit=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = lin(hexc)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = .15
    if emit:
        b.inputs["Emission Color"].default_value = lin(hexc)
        b.inputs["Emission Strength"].default_value = emit
    return m


def body_mat():
    """Beige body with the white face discs and pale belly painted on by direction from the center."""
    m = mat("body", "#f0d3b5")
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    co = nt.nodes.new('ShaderNodeTexCoord')
    nrm = nt.nodes.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'
    nt.links.new(co.outputs['Object'], nrm.inputs[0])
    color = None
    for d, cos_r, hexc in [((0, -.7, -.72), .80, "#ececec"),
                           ((.37, -.87, .33), .925, "#ffffff"), ((-.37, -.87, .33), .925, "#ffffff")]:
        dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
        dot.inputs[1].default_value = Vector(d).normalized()
        nt.links.new(nrm.outputs[0], dot.inputs[0])
        gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = cos_r
        nt.links.new(dot.outputs['Value'], gt.inputs[0])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        nt.links.new(gt.outputs[0], mix.inputs[0])
        if color: nt.links.new(color, mix.inputs[6])
        else: mix.inputs[6].default_value = lin("#f0d3b5")
        mix.inputs[7].default_value = lin(hexc)
        color = mix.outputs[2]
    nt.links.new(color, bsdf.inputs["Base Color"])
    return m


def ball(name, loc, scale, material, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=loc, rotation=rot)
    o = bpy.context.object
    o.name, o.scale = name, scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    if parent: o.parent = parent
    return o


def box(name, loc, scale, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name, o.scale = name, scale
    o.data.materials.append(material)
    return o


def surf(d, lift=1.0):
    """Point on the body surface in direction d, and the rotation that lays a part flat there (local Y = outward)."""
    d = Vector(d).normalized()
    return Vector((d.x * BODY.x, d.y * BODY.y, d.z * BODY.z)) * lift, Vector((0, -1, 0)).rotation_difference(d).to_euler()


# --- owl ---
owl = bpy.data.objects.new("owl", None)
scene.collection.objects.link(owl)
ball("body", (0, 0, 0), BODY, body_mat(), parent=owl)
INK, GREEN, ORANGE = mat("ink", "#1b1b1b", .3), mat("leaf", "#3fa98a"), mat("orange", "#e88a4a")
wings = []
for s in (1, -1):
    p, r = surf((s * .21, -.93, .3), 1.0); ball("eye", p, (.06, .03, .105), INK, r, owl)
    p, r = surf((s * .21, -.93, .245), 1.035); ball("glint", p, (.024, .012, .024), mat("glint", "#9a9a9a"), r, owl)
    p, r = surf((s * .26, -.9, -.33), 1.03); ball("leaf", p, (.29, .07, .19), GREEN, r, owl)
    p, r = surf((s * .97, -.1, -.22), 1.0); wings.append(ball("wing", p, (.2, .08, .44), mat("wing", "#e3bf9c"), r, owl))
    for dx in (-.08, .08):
        ball("toe", (s * .32 + dx, -.5, -1.05), (.065, .17, .05), ORANGE, parent=owl)
p, r = surf((0, -.93, .36), 1.0); ball("beak", p, (.105, .1, .22), mat("white", "#ffffff"), r, owl)
p, r = surf((0, -1, .12), 1.0); ball("mouth", p, (.09, .08, .095), mat("mouth", "#e2704a"), r, owl)

# --- laptop, in front of the owl, screen toward it ---
SILVER = mat("silver", "#d3d8de", .45)
TILT = math.radians(15)
hinge = Vector((0, -1.97, -1.11))
up, back = Vector((0, -math.sin(TILT), math.cos(TILT))), Vector((0, math.cos(TILT), math.sin(TILT)))
box("base", (0, -1.55, -1.13), (.62, .42, .022), SILVER)
box("keys", (0, -1.6, -1.105), (.53, .25, .004), mat("keys", "#8d949c"))
box("lid", hinge + up * .4, (.62, .018, .4), SILVER, (TILT, 0, 0))
box("screen", hinge + up * .4 + back * .02, (.57, .004, .36), mat("screen", "#c9f5e8", emit=1.2), (TILT, 0, 0))
ball("logo", hinge + up * .4 - back * .02, (.08, .012, .12), GREEN, (TILT, 0, 0))

# --- light, camera, render ---
bpy.ops.object.light_add(type='SUN', rotation=Vector((.35, 1, -.9)).to_track_quat('-Z', 'Y').to_euler())  # from front-left, above
bpy.context.object.data.energy = 1.4
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value, bg.inputs[1].default_value = (1, 1, 1, 1), .75  # flat white fill light
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.lens = 85
scene.camera = cam

r = scene.render
try: r.engine = 'BLENDER_EEVEE'
except TypeError: r.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples = 32
r.resolution_x, r.resolution_y, r.film_transparent = 480, 400, True
r.image_settings.file_format, r.image_settings.color_mode, r.image_settings.compression = 'PNG', 'RGBA', 100
scene.view_settings.view_transform = 'Standard'
r.use_freestyle = True
ls = bpy.context.view_layer.freestyle_settings.linesets.new("outline")
ls.linestyle.thickness, ls.linestyle.color = 1.6, lin("#3b2a20")[:3]

TARGET = Vector((0, -.75, -.12))
base_rot = [w.rotation_euler.copy() for w in wings]


def pose(t):
    """Everything is periodic in t, so frame N equals frame 0."""
    a, e = math.radians(32 + 22 * math.sin(2 * math.pi * t)), math.radians(17)
    cam.location = TARGET + 9.0 * Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.rotation_euler = (TARGET - cam.location).to_track_quat('-Z', 'Y').to_euler()
    owl.location.z = .03 * math.sin(4 * math.pi * t)
    owl.rotation_euler = (math.radians(-6), 0, math.radians(7) * math.sin(4 * math.pi * t))
    for i, w in enumerate(wings):  # alternate taps
        w.rotation_euler = base_rot[i]
        w.rotation_euler.x += math.radians(16) * max(0, math.sin(8 * math.pi * t + i * math.pi))


frames = [0, N // 4, 3 * N // 4] if MODE == "test" else range(N)
for i in frames:
    pose(i / N)
    r.filepath = f"{OUT}/f{i:03d}.png"
    bpy.ops.render.render(write_still=True)
