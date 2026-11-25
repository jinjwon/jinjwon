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
    """Layout read off P3R pause-menu frames: full-bleed water, character bleeding off the left, a tilted
    stack of words center-right (selected = red on a white jagged tag), wallet box top-left, help line bottom-right."""
    W, H = 960, 540
    items = [(n, f"{d} · {t}") for n, t, d in PROJECTS]
    items += [(r["name"].upper(), f"{r.get('language') or 'code'} · recently pushed") for r in repos[:3]]
    items += [("PORTFOLIO", "전체 포트폴리오 보기 · framer")]
    n, slot = len(items), 1.6
    cyc = f'dur="{slot * n}s" repeatCount="indefinite"'

    menu, help_ = [], []
    for i, (word, desc) in enumerate(items):
        x, y = [0, -14, 6, -8, 10, -4, 4][i % 7], i * 36
        w = len(word) * 40 * .7 + (40 if not word.isascii() else 0)
        on = ";".join("1" if k == i else "0" for k in range(n))
        a = i / n
        kt = f'keyTimes="0;{a:.3f};{a + .02:.3f};{a + .05:.3f};1" {cyc}'
        tag = f"-14,-30 {w + 26:.0f},-38 {w + 14:.0f},8 {w * .5:.0f},2 -6,6"
        menu.append(f'<g>{slide_in(.05 + i * .05, 420)}<g transform="translate({x} {y})">'
                    f'<text x="3" y="3" font-size="40" fill="#0a2a9e" opacity=".5">{esc(word)}</text>'
                    f'<text font-size="40" fill="{["#bff6ff", "#7fe4ff"][i % 2]}">{esc(word)}</text>'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<polygon points="{tag}" fill="#ff3d9a" transform="translate(7 6)"/>'
                    f'<g><animateTransform attributeName="transform" type="scale" values="0 1;0 1;1.22 1.22;1.1 1.1;1.1 1.1" {kt}/>'
                    f'<polygon points="{tag}" fill="#ffffff"/><text font-size="40" fill="#ff1428">{esc(word)}</text></g></g></g></g>')
        help_.append(f'<text x="930" y="500" text-anchor="end" font-size="14" fill="#ffffff" {KR} opacity="{1 if i == 0 else 0}">'
                     f'<animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>{esc(desc)}</text>')

    caustics = "".join(
        f'<path d="M{x} {y}q{rx * .4:.0f} {-ry} {rx:.0f} 0t{rx * .8:.0f} {ry * .6:.0f}q{-rx * .9:.0f} {ry * 1.4:.0f} {-rx * 1.8:.0f} 0z" fill="#e6fbff" opacity="{o}">'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx} 5;0 0" dur="{d}s" repeatCount="indefinite"/></path>'
        for x, y, rx, ry, o, dx, d in [(380, 24, 70, 14, .45, 26, 7), (520, 58, 46, 10, .35, -18, 9), (660, 22, 90, 16, .45, 22, 8), (820, 64, 60, 12, .35, -14, 6),
                                      (450, 96, 34, 7, .25, 16, 10), (760, 110, 40, 8, .25, -20, 11), (900, 30, 40, 9, .4, 12, 7.5)])
    rays = "".join(
        f'<polygon points="{x},0 {x + w},0 {x + w - 100},{H} {x - 160},{H}" fill="#e6fbff" opacity=".08">'
        f'<animateTransform attributeName="transform" type="skewX" values="0;{k};0" dur="{d}s" repeatCount="indefinite"/></polygon>'
        for x, w, k, d in [(430, 50, 4, 9), (620, 80, -3, 11), (820, 40, 5, 8)])
    bubbles = "".join(
        f'<circle cx="{x}" cy="{H + 10}" r="{r}" fill="none" stroke="#e6fbff" stroke-width="1.2" opacity="0">'
        f'<animate attributeName="cy" values="{H + 10};-20" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="cx" values="{x};{x + 10};{x - 6};{x}" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;.7;.7;0" keyTimes="0;.1;.8;1" dur="{d}s" begin="{b}s" repeatCount="indefinite"/></circle>'
        for x, r, d, b in [(420, 3, 7, 0), (500, 5, 9, 2), (640, 2, 6, 1), (720, 4, 8, 3.5), (880, 3, 7.5, 1.5), (360, 2, 6.5, 4), (590, 2.5, 8.5, 5)])
    confetti = "".join(  # the small pink/red shards that drift around the menu
        f'<polygon points="0,0 {w},{w * .3:.0f} {w * .3:.0f},{w * .9:.0f}" fill="{c}">'
        f'<animateTransform attributeName="transform" type="translate" values="{x} {y};{x + dx} {y - 30};{x} {y}" dur="{d}s" repeatCount="indefinite"/></polygon>'
        for x, y, w, c, dx, d in [(520, 150, 10, "#ff3d9a", 8, 5), (880, 220, 8, "#ff1428", -6, 6.5), (600, 420, 9, "#ff7ab8", 5, 4.4),
                                  (930, 380, 7, "#ff3d9a", -8, 7), (470, 300, 6, "#ff1428", 6, 5.6), (760, 470, 8, "#ff7ab8", -7, 6)])
    name = esc((user.get("name") or user["login"]).upper())
    bio = esc((user.get("bio") or "product designer · vibe coder")[:40])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{name} — profile menu: projects GOGO, 광탈페, EXPO, recent repositories and portfolio.">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3fd6ff"/><stop offset=".35" stop-color="#1673ef"/><stop offset="1" stop-color="#0716b0"/></linearGradient>
<radialGradient id="glow" cx=".2" cy=".3" r=".7"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#e9fbff" stop-opacity=".75"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<radialGradient id="fade"><stop offset=".55" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></radialGradient>
<mask id="soft"><circle r="230" fill="url(#fade)"/></mask>
<clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath>
</defs>
<g clip-path="url(#c)" {FONT}>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{caustics}
{rays}
<ellipse cx="190" cy="240" rx="320" ry="330" fill="url(#glow)"/>
<g transform="translate(250 280)"><g><animateTransform attributeName="transform" type="translate" values="0 -6;0 8;0 -6" dur="8s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#soft)"><image href="data:image/png;base64,{hero}" x="-230" y="-230" width="460" height="460"/></g></g></g>
<rect width="62" height="{H}" fill="#ffffff"/>
<text transform="translate(56 {H + 20}) rotate(-90)" font-size="88" fill="#0b0b0b">PROFILE</text>
<g transform="rotate(-2 180 40)"><rect x="84" y="16" width="200" height="46" fill="#ffffff" stroke="#0b0b0b" stroke-width="1.5"/>
<text x="94" y="40" font-size="20" fill="#0b0b0b">{name}</text><text x="95" y="55" font-size="9" fill="#0b0b0b" {KR}>{bio}</text></g>
{bubbles}
{confetti}
<g transform="translate(610 120) rotate(-18) skewX(-8)">{"".join(menu)}</g>
<rect x="640" y="482" width="296" height="1.5" fill="#ffffff"/>
<text x="640" y="476" font-size="10" fill="#ffffff">Guide</text>
{"".join(help_)}
<text x="930" y="524" text-anchor="end" font-size="13" fill="#ffffff">⊗ CONFIRM  ◎ CLOSE</text>
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
