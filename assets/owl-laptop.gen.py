# Generates the profile header: a round owl working at a laptop, with the camera swaying around the scene.
# Everything is baked into SMIL keyframes (GitHub READMEs run no scripts).
# The owl is a unit sphere stretched vertically; its markings are wrapped on it and clipped at the horizon.
# PHASE=0.25 python3 gen.py  -> same file with the sway offset, to eyeball other angles in a static renderer.
import math, os
N, DUR, CX, CY, R, F, TALL = 48, 8, 676, 100, 64, 8, 1.12
PH = float(os.environ.get("PHASE", 0))
ZH = 1 / F  # with perspective, the visible cap of a unit sphere is z > 1/F
T = [i / N for i in range(N + 1)]
norm = lambda v: tuple(c / math.hypot(*v) for c in v)
cross = lambda a, b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def rot(v, t):  # camera sways left-right and bobs up-down; both loop
    x, y, z = v
    a, b = .5 * math.sin(2 * math.pi * (t + PH)), .2 + .05 * math.sin(4 * math.pi * (t + PH))
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    return x, y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)

def proj(v, tall=1.0):
    s = F / (F - v[2])
    return CX + v[0] * R * s, CY - v[1] * R * s * tall

f = lambda v: f"{v:.1f}"
def anim(attr, vals, discrete=False):
    if len(set(vals)) == 1: return ""
    mode = ' calcMode="discrete"' if discrete else ""
    return f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite"{mode} values="{";".join(vals)}"/>'

def mark(center, shape, fill, lift=1.0, stroke="none"):
    """2D shape wrapped onto the owl around `center`. Points past the horizon slide onto the outline."""
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
        ds.append("M" + "L".join(f"{f(x)} {f(y)}" for x, y in (proj(p, TALL) for p in rp)) + "Z")
        ops.append("1" if seen else "0")
    return f'<path fill="{fill}" stroke="{stroke}" stroke-linejoin="round" d="{ds[0]}" opacity="{ops[0]}">{anim("d", ds)}{anim("opacity", ops, True)}</path>'

def flat(pts, fill, stroke="none", w=1.2):
    """Plain 3D polygon (the laptop)."""
    ds = ["M" + "L".join(f"{f(x)} {f(y)}" for x, y in (proj(rot(p, t)) for p in pts)) + "Z" for t in T]
    return f'<path fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" d="{ds[0]}">{anim("d", ds)}</path>'

def ell(rx, ry, k=24):
    return [(rx * math.cos(2 * math.pi * i / k), ry * math.sin(2 * math.pi * i / k)) for i in range(k)]
def bow(s):  # one rounded leaf of the bow tie, pinched at the knot
    return [(s * a, b) for a, b in [(0, 0), (.07, .1), (.2, .18), (.36, .19), (.5, .12), (.55, 0), (.5, -.12), (.36, -.19), (.2, -.18), (.07, -.1)]]

INK, WHITE = "#3b2a20", "#ffffff"
m = []
for s in (1, -1):
    m.append(mark((s * .97, -.3, .12), ell(.15, .4), "#dcb692", stroke=INK))           # wing
m.append(mark((0, -.72, .7), ell(.6, .45), "#ececec"))                                 # belly
for s in (1, -1):
    m.append(mark((s * .37, .33, .87), ell(.37, .38), WHITE, stroke=INK))              # face disc
for s in (1, -1):
    m.append(mark((s * .21, .3, .93), ell(.055, .1, 14), "#1d1d1d"))                   # eye
    m.append(mark((s * .21, .25, .93), ell(.03, .03, 8), "#8c8c8c", 1.01))
m.append(mark((0, .13, 1), ell(.09, .1, 14), "#e2704a", 1.05, INK))                    # beak, lower
m.append(mark((0, .36, .93), ell(.1, .21, 18), WHITE, 1.07, INK))                      # beak, upper
for s in (1, -1):
    m.append(mark((0, -.3, .95), bow(s), "#41a98b", 1.06, "#2c7c66"))                  # leaf bow
owl = "\n".join(m)

# Laptop on the ground in front of the owl, lid leaning toward the camera so we see its back.
G, W = -1.12, .78
base = [(-W, G, .95), (W, G, .95), (W, G, 1.7), (-W, G, 1.7)]
LB, LT = (0, G, 1.7), (0, G + .92, 1.95)
lid = [(-W, *LB[1:]), (W, *LB[1:]), (W, *LT[1:]), (-W, *LT[1:])]
mid, up = tuple((a + b) / 2 for a, b in zip(LB, LT)), norm(tuple(b - a for a, b in zip(LB, LT)))
logo = [(mid[0] + a, mid[1] + up[1] * b, mid[2] + up[2] * b) for a, b in [(0, -.17), (.1, -.07), (.12, .05), (0, .19), (-.12, .05), (-.1, -.07)]]
laptop = flat(base, "#aeb4bb", "#4a5058") + flat(lid, "#d9dde2", "#4a5058") + flat(logo, "#41a98b")

RS = R * F / math.sqrt(F * F - 1)  # projected outline radius of the unit sphere
def glyph(txt, x, delay):  # code symbol drifting up out of the laptop
    return (f'<text x="{x}" y="200" font-size="15" font-weight="700" fill="#41a98b" opacity="0">{txt}'
            f'<animate attributeName="y" values="200;120" dur="4s" begin="{delay}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.2;.7;1" dur="4s" begin="{delay}s" repeatCount="indefinite"/></text>')

print(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 260" role="img" aria-label="Jinwon Kim — Product Designer who builds">
<style>
.ink{{fill:#1f2328}}.dim{{fill:#656d76}}.acc{{fill:#41a98b}}
@media (prefers-color-scheme:dark){{.ink{{fill:#e6edf3}}.dim{{fill:#8b949e}}}}
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
</style>
<defs>
<radialGradient id="b" cx=".36" cy=".3" r=".8"><stop offset="0" stop-color="#f4dcc3"/><stop offset="1" stop-color="#e3bf9c"/></radialGradient>
<radialGradient id="s" cx=".36" cy=".3" r=".8"><stop offset=".6" stop-color="#5a3a20" stop-opacity="0"/><stop offset="1" stop-color="#5a3a20" stop-opacity=".2"/></radialGradient>
</defs>
<text x="24" y="118" class="ink" font-size="46" font-weight="700" letter-spacing="2">JINWON KIM</text>
<text x="26" y="154" class="dim" font-size="17">Product Designer · design → prototype → ship</text>
<rect x="26" y="176" width="12" height="20" class="acc"><animate attributeName="opacity" values="1;1;0;0" dur="1.2s" repeatCount="indefinite"/></rect>
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" dur="1.6s" repeatCount="indefinite"/>
<ellipse cx="{CX}" cy="{CY}" rx="{f(RS)}" ry="{f(RS * TALL)}" fill="url(#b)"/>
{owl}
<ellipse cx="{CX}" cy="{CY}" rx="{f(RS)}" ry="{f(RS * TALL)}" fill="url(#s)"/>
<ellipse cx="{CX}" cy="{CY}" rx="{f(RS)}" ry="{f(RS * TALL)}" fill="none" stroke="{INK}" stroke-width="1.6"/>
</g>
{laptop}
{glyph("&lt;/&gt;", 772, 0)}{glyph("{{ }}", 548, 1.3)}{glyph(";", 800, 2.6)}
</svg>''')
