# Generates the profile header: a spinning round owl baked into SMIL keyframes.
# The body is a true sphere, so its outline never changes; only the markings move, clipped at the horizon.
# PHASE=0.3 python3 gen.py  -> same file with the spin offset, to eyeball other angles in a static renderer.
import math, os
N, DUR, CX, CY, R, F = 60, 9, 672, 132, 84, 4.2
PH = float(os.environ.get("PHASE", 0))
ZH = 1 / F  # with perspective, the visible cap of a unit sphere is z > 1/F
T = [i / N for i in range(N + 1)]
norm = lambda v: tuple(c / math.hypot(*v) for c in v)
cross = lambda a, b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def rot(v, t):
    x, y, z = v
    a, b = 2 * math.pi * (t + PH), .18 + .1 * math.sin(2 * math.pi * t)  # spin + nod, both loop
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    return x, y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)

def proj(v):
    s = F / (F - v[2])
    return CX + v[0] * R * s, CY - v[1] * R * s

f = lambda v: f"{v:.1f}"
def anim(attr, vals, discrete=False):
    if len(set(vals)) == 1: return ""
    mode = ' calcMode="discrete"' if discrete else ""
    return f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite"{mode} values="{";".join(vals)}"/>'

def mark(center, shape, fill, lift=1.0, stroke="none"):
    """2D shape wrapped onto the sphere around `center`. Points past the horizon slide onto the outline."""
    n = norm(center)
    u = norm(cross((0, 1, 0), n)); v = cross(n, u)
    pts = [norm(tuple(n[i] + u[i] * a + v[i] * b for i in range(3))) for a, b in shape]
    ds, ops = [], []
    for t in T:
        rp, seen = [], False
        for p in pts:
            x, y, z = rot(p, t)
            if z >= ZH: seen = True; x, y, z = x * lift, y * lift, z * lift
            else:
                k = math.sqrt(1 - ZH * ZH) / (math.hypot(x, y) or 1)
                x, y, z = x * k, y * k, ZH
            rp.append((x, y, z))
        ds.append("M" + "L".join(f"{f(x)} {f(y)}" for x, y in map(proj, rp)) + "Z")
        ops.append("1" if seen else "0")
    return f'<path fill="{fill}" stroke="{stroke}" stroke-linejoin="round" d="{ds[0]}" opacity="{ops[0]}">{anim("d", ds)}{anim("opacity", ops, True)}</path>'

def ell(rx, ry, k=28, ox=0, oy=0):
    return [(ox + rx * math.cos(2 * math.pi * i / k), oy + ry * math.sin(2 * math.pi * i / k)) for i in range(k)]
def leaf(s, droop=-.3):  # pointed leaf growing sideways from the knot
    raw = [(0, 0), (.1, .1), (.25, .15), (.4, .11), (.56, 0), (.4, -.13), (.25, -.16), (.1, -.09)]
    c, d = math.cos(droop), math.sin(droop)
    return [(s * (a * c - b * d), a * d + b * c) for a, b in raw]

WHITE, TAN_D, INK, GREEN, GREEN_D, ORANGE = "#fbf6ea", "#b08a62", "#2a1f17", "#6cbf5f", "#3f8f45", "#f2a94a"
m = []
for s in (1, -1):
    m.append(mark((s * .98, -.12, -.05), ell(.2, .46), TAN_D, stroke=INK))        # wing
for s in (1, -1):
    m.append(mark((s * .36, .22, .9), ell(.43, .43), WHITE))                         # face disc
m.append(mark((0, -.5, .87), ell(.74, .62), WHITE))                                # belly
for s in (1, -1):
    m.append(mark((s * .3, -.9, .3), ell(.13, .1, 10), ORANGE, 1.05, INK))         # foot
    m.append(mark((s * .37, .2, .9), ell(.15, .16, 16), INK))                      # eye
    m.append(mark((s * .37 - .05, .27, .9), ell(.05, .05, 8), "#ffffff", 1.01))
m.append(mark((0, .02, 1), [(-.09, .06), (0, .1), (.09, .06), (.05, -.02), (-.05, -.02)], WHITE, 1.04, INK))   # beak, upper
m.append(mark((0, .02, 1), [(-.05, -.02), (.05, -.02), (0, -.12)], ORANGE, 1.04, INK))                          # beak, lower
for s in (1, -1):
    m.append(mark((0, -.36, .93), leaf(s), GREEN, 1.05, GREEN_D))                  # leaf bow
m.append(mark((0, -.36, .93), ell(.06, .06, 8), GREEN_D, 1.07))
marks = "\n".join(m)

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
    return f'<circle r="5" fill="{GREEN}" cx="{f(xy[0][0])}" cy="{f(xy[0][1])}" opacity="{ops[0]}">{anim("cx", [f(x) for x, _ in xy])}{anim("cy", [f(y) for _, y in xy])}{anim("opacity", ops, True)}</circle>'

RS = R * F / math.sqrt(F * F - 1)  # projected outline radius of the unit sphere
print(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 260" role="img" aria-label="Jinwon Kim — Product Designer who builds">
<style>
.ink{{fill:#1f2328}}.dim{{fill:#656d76}}.line{{stroke:#1f2328;stroke-width:1.2;fill:none;opacity:.4}}.acc{{fill:#5b6cff}}
@media (prefers-color-scheme:dark){{.ink{{fill:#e6edf3}}.dim{{fill:#8b949e}}.line{{stroke:#e6edf3}}.acc{{fill:#8b96ff}}}}
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
</style>
<defs>
<radialGradient id="b" cx=".36" cy=".3" r=".8"><stop offset="0" stop-color="#e2c29c"/><stop offset="1" stop-color="#c39b72"/></radialGradient>
<radialGradient id="s" cx=".36" cy=".3" r=".8"><stop offset=".55" stop-color="#3a2410" stop-opacity="0"/><stop offset="1" stop-color="#3a2410" stop-opacity=".28"/></radialGradient>
<clipPath id="c"><circle cx="{CX}" cy="{CY}" r="{f(RS)}"/></clipPath>
</defs>
<text x="24" y="118" class="ink" font-size="46" font-weight="700" letter-spacing="2">JINWON KIM</text>
<text x="26" y="154" class="dim" font-size="17">Product Designer · design → prototype → ship</text>
<rect x="26" y="176" width="12" height="20" class="acc"><animate attributeName="opacity" values="1;1;0;0" dur="1.2s" repeatCount="indefinite"/></rect>
<path class="line" d="{pd(ring)}Z"/>
{satc(False)}
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -7;0 0" dur="2.4s" repeatCount="indefinite" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1"/>
<circle cx="{CX}" cy="{CY}" r="{f(RS)}" fill="url(#b)"/>
{marks}
<circle cx="{CX}" cy="{CY}" r="{f(RS)}" fill="url(#s)"/>
<circle cx="{CX}" cy="{CY}" r="{f(RS)}" fill="none" stroke="{INK}" stroke-width="1.6"/>
</g>
<path class="line" d="{pd(front)}"/>
{satc(True)}
</svg>''')
