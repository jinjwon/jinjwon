# Builds assets/screen.svg: the whole profile as one pause-menu screen.
# Pulls the live GitHub profile (avatar, name, bio, latest repos), so a profile change shows up on the next run.
#   python3 assets/screen.gen.py            (from the repo root; needs Pillow; GITHUB_TOKEN is optional)
# Run daily and on push by .github/workflows/screen.yml. GitHub READMEs run no scripts, so the motion is SMIL.
import base64, io, json, os, urllib.request
from PIL import Image, ImageFilter, ImageOps

USER = "jinjwon"
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = 'font-family="Arial Black,Helvetica Neue,Impact,Apple SD Gothic Neo,Malgun Gothic,sans-serif" font-weight="900" font-style="italic"'
KR = 'font-family="Apple SD Gothic Neo,Malgun Gothic,Noto Sans KR,sans-serif" font-weight="700" font-style="normal"'
NUMERALS = ["0", "I", "II", "III", "IV"]
# Same order as the portfolio site. Hand-kept: the site has no API.
PROJECTS = [("GOGO", "24.12–25.05", "학교 스포츠 행사 관리 · 승부 예측 플랫폼"),
            ("광탈페", "25.04–25.09", "홍보 · 신청 · 투표 통합 행사 관리 플랫폼"),
            ("EXPO", "24.06–25.05", "교육청 연수 · 박람회 통합 관리 플랫폼")]


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-screen"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if raw else json.loads(data)


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def poster(avatar_bytes):
    """Avatar -> four flat blues, the way the menu colors its character art."""
    g = ImageOps.autocontrast(Image.open(io.BytesIO(avatar_bytes)).convert("L"), cutoff=2).filter(ImageFilter.SMOOTH_MORE)
    tones, cuts = [(7, 22, 176), (22, 115, 239), (127, 228, 255), (255, 255, 255)], [70, 130, 190]
    lut = [tones[sum(v > c for c in cuts)] for v in range(256)]
    im = Image.new("RGB", g.size)
    im.putdata([lut[v] for v in g.getdata()])
    buf = io.BytesIO()
    im.resize((300, 300)).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


OPEN = 1.1  # seconds of the white-out + splash before the menu arrives


def slide_in(delay, dx=-260):
    """Row waits off-screen through the opening splash, then flies in once and holds."""
    dur = OPEN + delay + .5
    a, b = (OPEN + delay) / dur, (OPEN + delay + .38) / dur
    return (f'<animateTransform attributeName="transform" type="translate" values="{dx} 0;{dx} 0;8 0;0 0" keyTimes="0;{a:.3f};{b:.3f};1" '
            f'dur="{dur:.2f}s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.2 .8 .3 1;.4 0 .6 1"/>')


def splash(W, H):
    """Opening like diving in: hold on white, the white thins out into foam that rises and pops over deep blue."""
    t = OPEN * .5
    out = [f'<rect width="{W}" height="{H}" fill="#ffffff"><animate attributeName="opacity" values="1;1;0" keyTimes="0;{t / OPEN:.3f};1" '
           f'dur="{OPEN}s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.5 0 .7 1"/></rect>']
    for k in range(26):  # foam: born where the white breaks, rises with ease-out, swells and pops
        x, y, r = (k * 137) % W, (k * 89 + 160) % H, 3 + (k * 7) % 12
        d = OPEN + .6 + (k % 5) * .15
        kt = f'keyTimes="0;{t / d:.3f};1" dur="{d:.2f}s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.2 .7 .3 1"'
        out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#e9fbff" fill-opacity=".35" stroke="#ffffff" stroke-width="1.5" opacity="0">'
                   f'<animate attributeName="opacity" values="0;1;0" {kt}/>'
                   f'<animate attributeName="cy" values="{y};{y};{y - 90 - r * 8}" keyTimes="0;{t / d:.3f};1" dur="{d:.2f}s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.2 .7 .3 1"/>'
                   f'<animate attributeName="r" values="{r * .4:.1f};{r * 1.4:.1f}" dur="{d:.2f}s" fill="freeze"/></circle>')
    return "\n".join(out)


def screen(user, repos, hero):
    W, H = 840, 600
    menu_words = ["PROJECT", "BUILD", "SKILL", "CONTACT", "PORTFOLIO"]
    slot = 1.4
    menu = []
    for i, word in enumerate(menu_words):
        x, y = [0, 26, 10, 38, 6][i], i * 40
        w = len(word) * 36 * .74
        shown = ";".join("1" if k == i else "0" for k in range(len(menu_words)))
        menu.append(f'<g>{slide_in(.1 + i * .07, 600)}')
        menu.append(f'<text x="{x}" y="{y}" font-size="36" fill="{["#bff6ff", "#7fe4ff", "#4fd0ff"][i % 3]}">{word}</text>')
        a = i / len(menu_words)
        kt = f'keyTimes="0;{a:.3f};{a + .025:.3f};{a + .05:.3f};1" dur="{slot * 5}s" repeatCount="indefinite"'
        box = f"-12,-24 {w + 22:.0f},-30 {w + 12:.0f},5 -5,3"
        menu.append(f'<g transform="translate({x} {y})"><g opacity="{1 if i == 0 else 0}">'
                    f'<animate attributeName="opacity" dur="{slot * 5}s" repeatCount="indefinite" calcMode="discrete" values="{shown}"/>'
                    f'<polygon points="{box}" fill="#ff3d9a" opacity="0"><animate attributeName="opacity" values="0;0;.8;0;0" {kt}/>'
                    f'<animateTransform attributeName="transform" type="scale" values="1 1;1 1;1.06 1.3;1.25 1.9;1.25 1.9" {kt}/></polygon>'
                    f'<g><animateTransform attributeName="transform" type="scale" values="0 1;0 1;1.1 1;1 1;1 1" {kt}/>'
                    f'<polygon points="{box}" fill="#ffffff" opacity=".92"/><text font-size="36" fill="#ff1428">{word}</text></g></g></g>')
        menu.append('</g>')

    rows = []
    for i, (name, term, desc) in enumerate(PROJECTS):
        y = 392 + i * 54
        rows.append(f'''<g>{slide_in(.35 + i * .1)}
<polygon points="34,{y} 520,{y - 6} 514,{y + 30} 28,{y + 36}" fill="#14206e"/>
<rect x="44" y="{y + 4}" width="20" height="28" rx="2" fill="#14206e" stroke="#8ff0ff" stroke-width="2" transform="rotate(-9 54 {y + 18})"/>
<text x="54" y="{y + 25}" text-anchor="middle" font-size="14" fill="#8ff0ff" font-style="normal" font-family="Georgia,serif">{NUMERALS[i]}</text>
<text x="78" y="{y + 26}" font-size="22" fill="#8ff0ff">{esc(name)}</text>
<text x="506" y="{y + 24}" text-anchor="end" font-size="16" fill="#8ff0ff">{term}</text>
<polygon points="70,{y + 34} 508,{y + 30} 504,{y + 48} 66,{y + 52}" fill="#8ff0ff"/>
<text x="287" y="{y + 46}" text-anchor="middle" font-size="11" fill="#0b1440" {KR}>{esc(desc)}</text>
</g>''')
    # a quiet cursor walks down the project rows
    n = len(PROJECTS)
    cur = ";".join(f"0 {i * 54};0 {i * 54}" for i in range(n)) + ";0 0"
    ckt = ";".join(f"{i / n + (.03 if i else 0):.3f};{(i + 1) / n - .03:.3f}" for i in range(n))
    rows.append(f'<rect x="-120" y="372" width="70" height="170" fill="#ffffff" opacity=".22" transform="skewX(-20)">'
                f'<animate attributeName="x" values="-120;-120;700" keyTimes="0;.8;1" dur="6s" begin="{OPEN + 1}s" repeatCount="indefinite"/></rect>')
    rows.append(f'<polygon points="22,386 528,380 520,422 16,428" fill="none" stroke="#ffffff" stroke-width="2.5">'
                f'<animateTransform attributeName="transform" type="translate" dur="{len(PROJECTS) * 1.6}s" repeatCount="indefinite" values="{cur}" keyTimes="0;{ckt};1" calcMode="spline" keySplines="{";".join([".4 0 .2 1"] * (2 * n))}"/></polygon>')

    build = []
    for i, r in enumerate(repos):
        y = 396 + i * 38
        build.append(f'''<g>{slide_in(.5 + i * .08, 500)}
<polygon points="552,{y} 818,{y - 3} 812,{y + 28} 546,{y + 31}" fill="#ffffff" opacity=".92"/>
<text x="560" y="{y + 21}" font-size="16" fill="#0b0b0b">{esc(r["name"])}</text>
<text x="806" y="{y + 20}" text-anchor="end" font-size="11" fill="#1673ef">{esc(r.get("language") or "—")}</text>
</g>''')

    caustics = "".join(
        f'<path d="M{x} {y}q{rx * .4:.0f} {-ry} {rx:.0f} 0t{rx * .8:.0f} {ry * .6:.0f}q{-rx * .9:.0f} {ry * 1.4:.0f} {-rx * 1.8:.0f} 0z" fill="#d8f6ff" opacity="{o}">'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx} 4;0 0" dur="{d}s" repeatCount="indefinite"/></path>'
        for x, y, rx, ry, o, dx, d in [(420, 30, 60, 14, .35, 26, 7), (560, 60, 40, 10, .3, -18, 9), (680, 26, 80, 16, .35, 22, 8),
                                      (780, 70, 34, 8, .3, -14, 6), (470, 96, 30, 7, .25, 16, 10), (620, 300, 44, 9, .2, -20, 11)])
    windows = "".join(f'<rect x="{x}" y="0" width="3" height="{H}" fill="#0716b0" opacity=".16"/>' for x in range(440, 840, 64))
    # Underwater layer, after the art director's notes: shimmer and gradation as if underwater,
    # bubbles, and glass-like sparkle; light rays sway, bubbles rise, the menu drifts like the mind sinking.
    rays = "".join(
        f'<polygon points="{x},0 {x + w},0 {x + w - 90},{H} {x - 150},{H}" fill="#e6fbff" opacity=".07">'
        f'<animateTransform attributeName="transform" type="skewX" values="0;{k};0" dur="{d}s" repeatCount="indefinite"/></polygon>'
        for x, w, k, d in [(470, 40, 4, 9), (600, 70, -3, 11), (730, 30, 5, 8)])
    bubbles = "".join(
        f'<circle cx="{x}" cy="{H + 10}" r="{r}" fill="none" stroke="#e6fbff" stroke-width="1.2" opacity="0">'
        f'<animate attributeName="cy" values="{H + 10};-20" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="cx" values="{x};{x + 10};{x - 6};{x}" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;.7;.7;0" keyTimes="0;.1;.8;1" dur="{d}s" begin="{b}s" repeatCount="indefinite"/></circle>'
        for x, r, d, b in [(470, 3, 7, 0), (520, 5, 9, 2), (610, 2, 6, 1), (700, 4, 8, 3.5), (780, 3, 7.5, 1.5), (430, 2, 6.5, 4), (560, 2.5, 8.5, 5)])
    sparkles = "".join(  # four-point glints, like light catching glass
        f'<path d="M{x} {y - 9}L{x + 2} {y - 2}L{x + 9} {y}L{x + 2} {y + 2}L{x} {y + 9}L{x - 2} {y + 2}L{x - 9} {y}L{x - 2} {y - 2}Z" fill="#ffffff" opacity="0">'
        f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.1;.25;1" dur="{d}s" begin="{b}s" repeatCount="indefinite"/></path>'
        for x, y, d, b in [(812, 40, 4, 0), (452, 180, 5, 1.6), (300, 92, 4.5, 2.8), (760, 300, 6, .8)])
    # A huge numeral for the highlighted menu slot, swapped in step with the selection
    numeral = "".join(
        f'<text x="420" y="300" font-size="230" fill="#c9cfd8" opacity="0" font-style="normal">{i + 1}'
        f'<animate attributeName="opacity" dur="{slot * 5}s" repeatCount="indefinite" calcMode="discrete" values="{";".join(".55" if k == i else "0" for k in range(5))}"/></text>'
        for i in range(5))
    streaks = "".join(  # thin directional lines that point the eye toward the menu
        f'<rect x="{x}" y="{y}" width="{w}" height="2" fill="#ffffff" opacity=".5" transform="rotate(-7 {x} {y})"/>'
        for x, y, w in [(440, 60, 120), (470, 286, 90), (760, 250, 70)])
    name = esc((user.get("name") or user["login"]).upper())
    bio = esc((user.get("bio") or "product designer · vibe coder")[:40])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{name} — profile menu: projects GOGO, 광탈페, EXPO and recent repositories.">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2=".7" y2="1"><stop offset="0" stop-color="#55d3ff"/><stop offset=".4" stop-color="#1673ef"/><stop offset="1" stop-color="#0716b0"/></linearGradient>
<clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath>
<radialGradient id="glow" cx=".28" cy=".22" r=".75"><stop offset="0" stop-color="#ffffff"/><stop offset=".4" stop-color="#e9fbff" stop-opacity=".8"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<radialGradient id="fade"><stop offset=".5" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></radialGradient>
<mask id="soft"><circle r="150" fill="url(#fade)"/></mask>
</defs>
<g clip-path="url(#c)" {FONT}>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{windows}
{caustics}
{rays}
{numeral}
{streaks}
<text transform="translate(690 640) rotate(-62)" font-size="170" fill="#ffffff" opacity=".18">LIST</text>
<text transform="translate(640 330) rotate(-62)" font-size="130" fill="#ffffff" opacity=".18">MENU</text>
<ellipse cx="170" cy="120" rx="330" ry="250" fill="url(#glow)"/>
<text transform="translate(58 346) rotate(-90)" font-size="104" fill="#ffffff" opacity=".22">PROFILE</text>
<g transform="translate(215 190)"><g><animateTransform attributeName="transform" type="translate" values="-6 -10;4 8;-6 -10" dur="10s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="rotate" values="164;171;164" dur="13s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#soft)"><image href="data:image/png;base64,{hero}" x="-150" y="-150" width="300" height="300"/></g></g></g></g>
<g transform="rotate(-2 200 50)">
<rect x="92" y="18" width="220" height="50" fill="#ffffff" stroke="#0b0b0b" stroke-width="1.5"/>
<text x="102" y="44" font-size="22" fill="#0b0b0b">{name}</text>
<text x="103" y="60" font-size="9" fill="#0b0b0b" {KR}>{bio}</text>
</g>
{bubbles}
{sparkles}
<g transform="translate(486 92) rotate(-7) skewX(-6)">{"".join(menu)}</g>
<g transform="rotate(-3 120 370)"><text x="30" y="378" font-size="34" fill="#ffffff">LIST</text><text x="122" y="378" font-size="12" fill="#bff6ff">PROJECT</text></g>
<g transform="rotate(-3 640 370)"><text x="552" y="378" font-size="22" fill="#ffffff">BUILD</text><text x="640" y="378" font-size="11" fill="#bff6ff">recently pushed</text></g>
{"".join(rows)}
{"".join(build)}
<rect x="596" y="566" width="224" height="1.5" fill="#ffffff"/>
<text x="596" y="578" font-size="9" fill="#ffffff">Guide</text>
<text x="820" y="592" text-anchor="end" font-size="12" fill="#ffffff">⊗ SELECT  ◎ BACK</text>
{splash(W, H)}
</g>
</svg>'''


if __name__ == "__main__":
    user = get(f"https://api.github.com/users/{USER}")
    repos = [r for r in get(f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=30")
             if not r["fork"] and not r["private"] and r["name"] != USER][:4]
    svg = screen(user, repos, poster(get(user["avatar_url"] + "&s=300" if "?" in user["avatar_url"] else user["avatar_url"] + "?s=300", raw=True)))
    assert svg.count("<svg") == 1 and len(repos) <= 4
    open(os.path.join(HERE, "screen.svg"), "w").write(svg)
    print("screen.svg", len(svg) // 1024, "KB,", len(repos), "repos")
