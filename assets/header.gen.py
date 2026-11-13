# Generates the profile header: a spinning low-poly owl (flat-shaded, backface-culled) baked into SMIL keyframes.
# PHASE=0.3 python3 gen.py  -> same file with the spin offset, to eyeball other angles in a static renderer.
import math, os
N, DUR, CX, CY, R, F = 48, 10, 672, 134, 80, 4.2
PH = float(os.environ.get("PHASE", 0))
RAD = (1, .93, .93)
LIGHT = (-.42, .6, .68)
T = [i / N for i in range(N + 1)]
norm = lambda v: tuple(c / math.hypot(*v) for c in v)
dot = lambda a, b: sum(x * y for x, y in zip(a, b))
cross = lambda a, b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def rot(v, t):
    x, y, z = v
    a, b = 2 * math.pi * (t + PH), .22 + .12 * math.sin(2 * math.pi * t)  # spin + nod, both loop
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    return x, y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)

def proj(v):
    s = F / (F - v[2])
    return CX + v[0] * R * s, CY - v[1] * R * s

f = lambda v: f"{v:.1f}"
DISC = ' calcMode="discrete"'
def anim(attr, vals, discrete=False):
    if len(set(vals)) == 1: return ""
    return f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite"{DISC if discrete else ""} values="{";".join(vals)}"/>'

def shade(base, n):
    k = .76 + .24 * max(0, dot(n, LIGHT))
    return "#" + "".join(f"{min(255, int(int(base[i:i+2], 16) * k)):02x}" for i in (1, 3, 5))

def poly(pts, n, base, thr=0.0):
    """One flat face: pts and normal n in model space. Hidden whenever it faces away (the body is convex, so no sorting)."""
    c = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
    ds, fills, ops = [], [], []
    for t in T:
        rp, rn, rc = [rot(p, t) for p in pts], rot(n, t), rot(c, t)
        view = norm((-rc[0], -rc[1], F - rc[2]))
        ds.append("M" + "L".join(f"{f(x)} {f(y)}" for x, y in map(proj, rp)) + "Z")
        fills.append(shade(base, rn))
        ops.append("1" if dot(rn, view) > thr else "0")
    if "1" not in ops: return ""
    return f'<path stroke="#3a2a1e" stroke-width=".8" stroke-linejoin="round" d="{ds[0]}" fill="{fills[0]}" opacity="{ops[0]}">{anim("d", ds)}{anim("fill", fills)}{anim("opacity", ops, True)}</path>'

def sph(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    return (math.cos(la) * math.sin(lo) * RAD[0], math.sin(la) * RAD[1], math.cos(la) * math.cos(lo) * RAD[2])

def decal(center, shape, base, lift=1.03):
    """2D shape wrapped onto the body around `center`."""
    n = norm(center)
    u = norm(cross((0, 1, 0), n)); v = cross(n, u)
    pts = []
    for a, b in shape:
        p = norm(tuple(n[i] + u[i] * a + v[i] * b for i in range(3)))
        pts.append(tuple(p[i] * RAD[i] * lift for i in range(3)))
    return poly(pts, n, base, thr=.32)

ell = lambda rx, ry, k=12: [(rx * math.cos(2 * math.pi * i / k), ry * math.sin(2 * math.pi * i / k)) for i in range(k)]
leaf = lambda s: [(0, 0), (s * .14, .13), (s * .32, .12), (s * .46, 0), (s * .32, -.14), (s * .14, -.12)]

out = []
LATS, LONS = [-90, -54, -18, 18, 54, 90], [-18 + 36 * k for k in range(11)]
for i in range(5):
    for k in range(10):
        q = [sph(LATS[i], LONS[k]), sph(LATS[i], LONS[k + 1]), sph(LATS[i + 1], LONS[k + 1]), sph(LATS[i + 1], LONS[k])]
        c = [sum(p[j] for p in q) / 4 for j in range(3)]
        out.append(poly(q, norm(c), "#f6ecd9" if c[2] > .3 and c[1] < .7 else "#cfa77c"))
for s in (1, -1):
    out.append(decal((s * .97, -.08, .05), ell(.2, .42), "#a37c57"))            # wing
    out.append(decal((s * .37, .2, .9), ell(.2, .2), "#2b2118"))                # eye
    out.append(decal((s * .37 - .06, .28, .9), ell(.06, .06, 8), "#ffffff", 1.05))
    out.append(decal((0, -.42, .9), leaf(s), "#67bb5e", 1.05))                  # leaf bow
out.append(decal((0, -.42, .9), ell(.06, .06, 8), "#3f8f45", 1.07))
out.append(decal((0, .04, 1), [(0, .09), (.1, 0), (0, -.13), (-.1, 0)], "#f0b34a", 1.05))  # beak
body = "\n".join(o for o in out if o)

# One fixed tilted orbit: drawn whole behind the body, then its near half again in front.
def orb(a, r=1.5):
    x, y, z = r * math.cos(a), 0, r * math.sin(a)
    x, y = x * math.cos(.3) - y * math.sin(.3), x * math.sin(.3) + y * math.cos(.3)
    return x, y * math.cos(.38) - z * math.sin(.38), y * math.sin(.38) + z * math.cos(.38)
ring = [orb(2 * math.pi * k / 96) for k in range(96)]
pd = lambda ps: "M" + "L".join(f"{f(x)} {f(y)}" for x, y in map(proj, ps))
i0 = next(k for k in range(96) if ring[k - 1][2] < 0 <= ring[k][2])
front = [ring[(i0 + k) % 96] for k in range(96) if ring[(i0 + k) % 96][2] >= 0]
sat = [orb(-4 * math.pi * t) for t in T]
def satc(near):
    xy = [proj(p) for p in sat]
    ops = ["1" if (p[2] >= 0) == near else "0" for p in sat]
    return f'<circle r="5" fill="#67bb5e" cx="{f(xy[0][0])}" cy="{f(xy[0][1])}" opacity="{ops[0]}">{anim("cx", [f(x) for x, _ in xy])}{anim("cy", [f(y) for _, y in xy])}{anim("opacity", ops, True)}</circle>'

print(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 260" role="img" aria-label="Jinwon Kim — Product Designer who builds">
<style>
.ink{{fill:#1f2328}}.dim{{fill:#656d76}}.line{{stroke:#1f2328;stroke-width:1.2;fill:none;opacity:.4}}.acc{{fill:#5b6cff}}
@media (prefers-color-scheme:dark){{.ink{{fill:#e6edf3}}.dim{{fill:#8b949e}}.line{{stroke:#e6edf3}}.acc{{fill:#8b96ff}}}}
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
</style>
<text x="24" y="118" class="ink" font-size="46" font-weight="700" letter-spacing="2">JINWON KIM</text>
<text x="26" y="154" class="dim" font-size="17">Product Designer · design → prototype → ship</text>
<rect x="26" y="176" width="12" height="20" class="acc"><animate attributeName="opacity" values="1;1;0;0" dur="1.2s" repeatCount="indefinite"/></rect>
<path class="line" d="{pd(ring)}Z"/>
{satc(False)}
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -7;0 0" dur="2.5s" repeatCount="indefinite" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1"/>
{body}
</g>
<path class="line" d="{pd(front)}"/>
{satc(True)}
</svg>''')
