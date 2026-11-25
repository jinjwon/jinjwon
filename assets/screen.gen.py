# Builds assets/screen.svg: the whole profile as one pause-menu screen.
# Pulls the live GitHub profile (avatar, name, bio, latest repos), so a profile change shows up on the next run.
#   python3 assets/screen.gen.py            (from the repo root; needs Pillow; GITHUB_TOKEN is optional)
# Theme follows Korean time (morning P3R, afternoon P4, night P5); .github/workflows/screen.yml runs it at each switch. GitHub READMEs run no scripts, so the motion is SMIL.
import base64, datetime, io, json, os, re, urllib.request
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from PIL import Image, ImageFilter, ImageOps

USER = "jinjwon"
HERE = os.path.dirname(os.path.abspath(__file__))
# Embedded font families (assets/fonts, OFL). Latin comes from the first family, Hangul falls back to KRH/KRB.
FONT = 'font-family="P3,KRH,sans-serif"'
F4 = 'font-family="P4,KRH,sans-serif"'
F5 = 'font-family="P5B,KRH,sans-serif"'
KR = 'font-family="KRB,sans-serif" font-style="normal"'
FONTS = {"P3": "Barlow-BlackItalic.ttf", "P4R": "PTSerif-Bold.ttf", "P4": "Anton-Regular.ttf", "P5A": "AbrilFatface-Regular.ttf",
         "P5B": "ArchivoBlack-Regular.ttf", "KRH": "BlackHanSans-Regular.ttf", "KRB": "DoHyeon-Regular.ttf"}


_metrics = {}


def textw(text, fam, size):
    """Real advance width of text in an embedded family (Hangul measured in KRH), so tags hug their words."""
    def adv(f, ch):
        if f not in _metrics:
            t = TTFont(os.path.join(HERE, "fonts", FONTS[f]))
            _metrics[f] = (t.getBestCmap(), t["hmtx"].metrics, t["head"].unitsPerEm)
        cmap, hm, em = _metrics[f]
        return hm[cmap[ord(ch)]][0] / em if ord(ch) in cmap else None
    return sum((adv(fam, ch) or adv("KRH", ch) or .6) * size for ch in text)


def embed_fonts(svg):
    """Subset every family the SVG names to the characters it shows and inline it, so the type renders anywhere."""
    text = "".join(re.findall(r">([^<>]+)<", svg)) + "0123456789"
    css = []
    for fam, file in FONTS.items():
        if not re.search(rf'font-family="[^"]*\b{fam}\b', svg):
            continue
        font, opts = TTFont(os.path.join(HERE, "fonts", file)), Options()
        opts.layout_features, opts.name_IDs, opts.notdef_outline = ["kern", "liga"], [], True
        sub = Subsetter(opts); sub.populate(text=text); sub.subset(font)
        buf = io.BytesIO(); font.save(buf)
        css.append(f"@font-face{{font-family:{fam};src:url(data:font/ttf;base64,{base64.b64encode(buf.getvalue()).decode()})}}")
    return svg.replace("<defs>", f"<defs><style>{''.join(css)}</style>", 1)
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


TONES = {"p3r": [(7, 22, 176), (22, 115, 239), (127, 228, 255), (255, 255, 255)],
         "p4": [(46, 13, 58), (190, 104, 12), (255, 214, 20), (255, 250, 214)],
         "p5": [(12, 12, 12), (12, 12, 12), (214, 0, 24), (255, 255, 255)]}


def theme_now():
    """Morning P3R, afternoon P4, evening and night P5, by Korean time. THEME=p3r|p4|p5 forces one."""
    h = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).hour
    return os.environ.get("THEME") or ("p3r" if 6 <= h < 12 else "p4" if 12 <= h < 18 else "p5")


def menu_items(repos):
    items = [(n, f"{d} · {t}") for n, t, d in PROJECTS]
    items += [(r["name"].upper(), f"{r.get('language') or 'code'} · recently pushed") for r in repos[:3]]
    return items + [("PORTFOLIO", "전체 포트폴리오 보기 · framer")]


def cycle(i, n, slot=1.6):
    """Timing shared by every theme: one item highlighted per slot. Returns (on-values, pop keyTimes+dur)."""
    a, cyc = i / n, f'dur="{slot * n}s" repeatCount="indefinite"'
    return ";".join("1" if k == i else "0" for k in range(n)), f'keyTimes="0;{a:.3f};{a + .02:.3f};{a + .05:.3f};1" {cyc}', cyc


def poster(avatar_bytes, tones):
    """Avatar -> four flat tones, the way the menus color their character art."""
    g = ImageOps.autocontrast(Image.open(io.BytesIO(avatar_bytes)).convert("L"), cutoff=2).filter(ImageFilter.SMOOTH_MORE)
    cuts = [70, 130, 190]
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


def buttons(x, y, fg, bg, labels):
    """Round controller-button hints, right-aligned at x."""
    out = []
    for key, label in reversed(labels):
        w = textw(label, "P3", 15)
        x -= w
        out.append(f'<text x="{x:.0f}" y="{y}" font-size="15" fill="{fg}" font-family="P3">{label}</text>'
                   f'<circle cx="{x - 12:.0f}" cy="{y - 5}" r="8" fill="{fg}"/><text x="{x - 12:.0f}" y="{y - 1}" text-anchor="middle" font-size="11" fill="{bg}" font-family="P3">{key}</text>')
        x -= 32
    return "".join(out)


def screen_p3r(user, repos, hero):
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
        x, y = [0, -16, 6, -10, 12, -4, 6][i % 7], i * 40
        fs = [40, 52, 40, 50, 38, 46, 42][i % 7]  # every word its own size, lines biting into each other
        w = textw(word, "P3", fs)
        on = ";".join("1" if k == i else "0" for k in range(n))
        a = i / n
        kt = f'keyTimes="0;{a:.3f};{a + .02:.3f};{a + .05:.3f};1" {cyc}'
        off = ";".join("0" if v == "1" else "1" for v in on.split(";"))
        white = f"-20,-18 {w + 112:.0f},-48 {w + 18:.0f},6 -6,12"
        pink = f"-36,18 {w + 70:.0f},-14 {w + 22:.0f},6 -26,26"
        menu.append(f'<g>{slide_in(.05 + i * .05, 420)}<g transform="translate({x} {y})">'
                    f'<g opacity="{0 if i == 0 else 1}"><animate attributeName="opacity" calcMode="discrete" values="{off}" {cyc}/>'
                    f'<text x="3" y="3" font-size="{fs}" letter-spacing="-1.5" fill="#00128f" opacity=".45">{esc(word)}</text>'
                    f'<text font-size="{fs}" letter-spacing="-1.5" fill="{["#8ffbff", "#52e6ff", "#aef4ff", "#2fc4ff"][i % 4]}">{esc(word)}</text></g>'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<g><animateTransform attributeName="transform" type="scale" values="0 1;0 1;1.15 1;1 1;1 1" {kt}/>'
                    f'<polygon points="{pink}" fill="#ff3d9a"/><polygon points="{white}" fill="#ffffff"/></g>'
                    f'<g transform="translate(-14 2) scale(1.18)"><animateTransform attributeName="transform" type="translate" additive="sum" values="-30 0;-30 0;4 0;0 0;0 0" {kt}/>'
                    f'<text x="-4" y="5" font-size="{fs}" letter-spacing="-1.5" fill="#0b0b0b">{esc(word)}</text><text font-size="{fs}" letter-spacing="-1.5" fill="url(#split)">{esc(word)}</text></g></g></g></g>')
        help_.append(f'<text x="930" y="478" text-anchor="end" font-size="18" fill="#ffffff" {KR} opacity="{1 if i == 0 else 0}">'
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
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2ff2ff"/><stop offset=".38" stop-color="#0a74ff"/><stop offset="1" stop-color="#0000c4"/></linearGradient>
<linearGradient id="split" x1="0" y1="0" x2="1" y2=".35"><stop offset=".2" stop-color="#14000a"/><stop offset=".2" stop-color="#ff1428"/></linearGradient>
<radialGradient id="glow" cx=".2" cy=".3" r=".7"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#e9fbff" stop-opacity=".75"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<radialGradient id="fade"><stop offset=".55" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></radialGradient>
<linearGradient id="lf" x1="0" x2="1"><stop offset=".6" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></linearGradient>
<mask id="half"><rect x="-300" y="-300" width="600" height="600" fill="url(#lf)"/></mask>
<clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath>
</defs>
<g clip-path="url(#c)" {FONT}>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{caustics}
{rays}
<ellipse cx="190" cy="240" rx="320" ry="330" fill="url(#glow)"/>
<g transform="translate(300 270)"><g><animateTransform attributeName="transform" type="translate" values="0 -6;0 8;0 -6" dur="8s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#half)"><image href="data:image/png;base64,{hero}" x="-300" y="-300" width="600" height="600"/></g></g></g>
<path d="M0 0H94C122 90 72 170 102 260S70 430 106 540H0Z" fill="#ffffff"/>
<text transform="translate(80 214) rotate(-97)" font-size="108" fill="#aab2bd">{user.get("public_repos", 0):02d}</text>
<text transform="translate(86 {H + 4}) rotate(-96)" font-size="102" letter-spacing="-4" fill="#0b0b0b">PROFILE</text>
<g transform="rotate(-2 180 40)"><rect x="84" y="16" width="200" height="46" fill="#ffffff" stroke="#0b0b0b" stroke-width="1.5"/>
<text x="94" y="40" font-size="20" fill="#0b0b0b">{name}</text><text x="95" y="55" font-size="9" fill="#0b0b0b" {KR}>{bio}</text></g>
{bubbles}
{confetti}
<g transform="translate(500 128) rotate(-18) skewX(-8)">{"".join(menu)}</g>
{"".join(help_)}
<rect x="620" y="488" width="330" height="1.5" fill="#ffffff"/>
<text x="624" y="500" font-size="10" fill="#ffffff">Command</text>
{buttons(932, 522, "#ffffff", "#0000c4", [("A", "Confirm"), ("B", "Close")])}
{splash(W, H)}
</g>
</svg>'''


def tv_on(W, H):
    """P4 opening: a TV switching on, a white line opening to full picture."""
    return (f'<rect width="{W}" height="{H}" fill="#111"><animate attributeName="opacity" values="1;1;0" keyTimes="0;.6;1" dur="{OPEN}s" fill="freeze"/></rect>'
            f'<rect x="0" y="{H / 2 - 2}" width="{W}" height="4" fill="#ffffff" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.2;.6;1" dur="{OPEN}s" fill="freeze"/>'
            f'<animate attributeName="height" values="4;4;{H};{H}" keyTimes="0;.4;.75;1" dur="{OPEN}s" fill="freeze"/>'
            f'<animate attributeName="y" values="{H / 2 - 2};{H / 2 - 2};0;0" keyTimes="0;.4;.75;1" dur="{OPEN}s" fill="freeze"/></rect>')


def p5_wipe(W, H):
    """P5 opening: black shards slash away off a red flash."""
    out = [f'<rect width="{W}" height="{H}" fill="#ff1a2e"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.35;.7;1" dur="{OPEN}s" fill="freeze"/></rect>']
    for k, (pts, dx) in enumerate([("0,0 620,0 360,560 0,560", -900), ("540,-20 980,-20 980,300 300,560", 900), ("200,300 980,240 980,560 120,560", 1100)]):
        out.append(f'<polygon points="{pts}" fill="#0b0b0b"><animateTransform attributeName="transform" type="translate" values="0 0;0 0;{dx} {-dx * .25:.0f}" '
                   f'keyTimes="0;{.3 + k * .08:.2f};1" dur="{OPEN}s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.6 0 .9 .5"/></polygon>')
    return "".join(out)


def screen_p4(user, repos, hero):
    """P4 Revival pause menu (docs/persona-ui-style.md): yellow split by a diagonal window of blue sky, bold
    serif words stepping down the diagonal (dark on yellow, yellow on the dark mass), the picked one huge and
    white with TV colour fringing, fat round flowers, drifting petals, a dark pill help line."""
    W, H = 960, 540
    items = menu_items(repos); n = len(items)
    menu, help_ = [], []
    for i, (word, desc) in enumerate(items):
        on, kt, cyc = cycle(i, n)
        word = word.title()
        x, y = i * 24, i * 52
        dark_on_light = i < 3
        fill, shade = ("#3a2400", "#e8a800") if dark_on_light else ("#ffe83d", "#14021c")
        w = textw(word, "P4R", 46)
        off = ";".join("0" if v == "1" else "1" for v in on.split(";"))
        wedge = f"-50,-30 {w * .5:.0f},-44 {w * .28:.0f},6 -18,22"
        txt = lambda dx, dy, c, extra="": f'<text x="{dx}" y="{dy}" font-size="46" fill="{c}" font-family="P4R,KRH" {extra}>{esc(word)}</text>'
        menu.append(f'<g>{slide_in(.05 + i * .06, -300)}<g transform="translate({x} {y})">'
                    f'<g opacity="{0 if i == 0 else 1}"><animate attributeName="opacity" calcMode="discrete" values="{off}" {cyc}/>{txt(4, 4, shade)}{txt(0, 0, fill)}</g>'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<g transform="translate(-6 4) scale(1.28)"><animateTransform attributeName="transform" type="scale" additive="sum" values=".7 .7;.7 .7;1.12 1.12;1 1;1 1" {kt}/>'
                    f'<polygon points="{wedge}" fill="url(#shard)"/>{txt(6, 6, "#14021c")}'
                    f'<g opacity=".9"><animateTransform attributeName="transform" type="translate" values="-3 0;-7 1;-2 -1;-3 0" dur=".5s" repeatCount="indefinite"/>{txt(0, 0, "#ff1f6b")}</g>'
                    f'<g opacity=".9"><animateTransform attributeName="transform" type="translate" values="3 0;7 -1;2 1;3 0" dur=".5s" repeatCount="indefinite"/>{txt(0, 0, "#12d6ff")}</g>'
                    f'{txt(0, 0, "#ffffff")}</g></g></g></g>')
        help_.append(f'<text x="936" y="486" text-anchor="end" font-size="15" fill="#ffffff" {KR} opacity="{1 if i == 0 else 0}">'
                     f'<animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>{esc(desc)}</text>')

    def flower(x, y, r, color, d, fringe=False):
        petals = "".join(f'<ellipse cx="0" cy="{-r * .62:.0f}" rx="{r * .25:.0f}" ry="{r * .42:.0f}" transform="rotate({a})"/>' for a in range(0, 360, 60))
        body = f'<circle r="{r * .2:.0f}"/>{petals}'
        ghost = (f'<g fill="#ff1f6b" transform="translate(-4 0)">{body}</g><g fill="#18e06b" transform="translate(4 0)">{body}</g>') if fringe else ""
        return (f'<g transform="translate({x} {y})"><g><animateTransform attributeName="transform" type="rotate" values="0;360" dur="{d}s" repeatCount="indefinite"/>'
                f'{ghost}<g fill="{color}">{body}</g></g></g>')

    def cloud(x, y, k, d):
        puffs = "".join(f'<circle cx="{a * k:.0f}" cy="{b * k:.0f}" r="{r * k:.0f}"/>' for a, b, r in [(0, 0, 26), (30, -14, 30), (62, -2, 24), (90, 8, 16), (-26, 10, 16), (34, 8, 28)])
        return (f'<g transform="translate({x} {y})"><g fill="#ffffff"><animateTransform attributeName="transform" type="translate" values="0 0;34 0;0 0" dur="{d}s" repeatCount="indefinite"/>{puffs}</g></g>')

    petals = "".join(
        f'<g><animateTransform attributeName="transform" type="translate" values="{x} -20;{x - 120} {H + 20}" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<ellipse rx="9" ry="3.5" fill="#fff06a"><animateTransform attributeName="transform" type="rotate" values="0;360" dur="{d / 4:.1f}s" repeatCount="indefinite"/></ellipse></g>'
        for x, d, b in [(380, 9, 0), (560, 11, 2.5), (700, 8, 1), (860, 12, 4), (940, 10, 6)])
    sky = "430,0 960,0 960,196 610,258 452,330 296,178"
    name = esc((user.get("name") or user["login"]).split()[0].title()); bio = esc((user.get("bio") or "product designer · vibe coder")[:40])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{name} — profile menu: projects GOGO, 광탈페, EXPO, recent repositories and portfolio.">
<defs><linearGradient id="y" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe92e"/><stop offset=".6" stop-color="#ffd000"/><stop offset="1" stop-color="#ff8a00"/></linearGradient>
<linearGradient id="skyg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f9dff"/><stop offset="1" stop-color="#a9e6ff"/></linearGradient>
<linearGradient id="shard" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2742ff"/><stop offset=".6" stop-color="#ffffff"/></linearGradient>
<linearGradient id="lf" x1="0" x2="1"><stop offset=".68" stop-color="#ffffff"/><stop offset=".9" stop-color="#000000"/></linearGradient>
<mask id="half"><rect x="-300" y="-300" width="600" height="600" fill="url(#lf)"/></mask>
<clipPath id="sk"><polygon points="{sky}"/></clipPath><clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath></defs>
<g clip-path="url(#c)" {F4}>
<rect width="{W}" height="{H}" fill="url(#y)"/>
<g clip-path="url(#sk)"><rect width="{W}" height="340" fill="url(#skyg)"/>{cloud(800, 176, 1.1, 14)}{cloud(800, 100, .9, 19)}{cloud(450, 60, .6, 11)}</g>
<g transform="translate(236 290)"><g><animateTransform attributeName="transform" type="translate" values="0 -4;0 6;0 -4" dur="7s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#half)"><image href="data:image/png;base64,{hero}" x="-300" y="-300" width="600" height="600"/></g></g></g>
<polygon points="440,318 650,214 726,262 560,356" fill="#7a5414"/>
<polygon points="262,540 372,430 428,324 452,214 640,204 790,236 826,288 884,306 846,540" fill="#2e0b3c"/>
<polygon points="884,306 960,284 960,540 846,540" fill="#ffb000" opacity=".75"/>
<line x1="286" y1="528" x2="640" y2="274" stroke="#ffe83d" stroke-width="2" stroke-dasharray="9 7" opacity=".8"/>
{flower(790, 468, 92, "#ffe83d", 40)}{flower(70, 506, 62, "#ffffff", 30, True)}{flower(300, 82, 17, "#e8a800", 18)}
{petals}
<g transform="translate(366 112) rotate(-14)">{"".join(menu)}</g>
<text x="934" y="50" text-anchor="end" font-size="38" fill="#ffffff" stroke="#0d3f8f" stroke-width="5" paint-order="stroke" font-family="P4R">{name}</text>
<text x="934" y="72" text-anchor="end" font-size="13" fill="#ffffff" stroke="#0d3f8f" stroke-width="3" paint-order="stroke" {KR}>{bio}</text>
<text x="470" y="522" font-size="30" fill="#ffe83d" stroke="#14021c" stroke-width="4" paint-order="stroke" font-family="P4R">★ {user.get("public_repos", 0)} <tspan font-size="15">repos</tspan></text>
<rect x="636" y="465" width="340" height="31" rx="15" fill="#14021c" opacity=".9"/><text x="654" y="486" font-size="15" fill="#ffe83d" {KR}>✦</text>
{"".join(help_)}
<rect x="738" y="504" width="212" height="28" rx="14" fill="#14021c" opacity=".9"/>
{buttons(936, 524, "#ffffff", "#14021c", [("A", "Confirm"), ("B", "Back")])}
{tv_on(W, H)}
</g>
</svg>"""


def screen_p5(user, repos, hero):
    """P5 as a title screen: the name as a ransom-note game logo over a spinning star burst, a tagline strip,
    the projects as the title menu (NEW GAME / LOAD GAME style, picked = red on a black bar with a star),
    the character on the right behind a red slash, a B/W collage strip and a repo counter."""
    W, H = 960, 540
    items = menu_items(repos); n = len(items)
    menu, help_ = [], []
    def ransom(word, i, base):
        out, cx = [], 0
        for j, ch in enumerate(word):
            fs = base + (j * 7 + i * 3) % 3 * 5
            fam = ["P5A", "P5B", "P4"][(j * 2 + i) % 3]
            ch = ch.lower() if fam == "P5A" and j % 2 else ch
            cw = textw(ch, fam, fs)
            rot = ((j * 37 + i * 11) % 11) - 5
            if (j + i) % 3 == 1:  # white letter on a black chip
                cw *= 1.15
                body = (f'<rect x="-2" y="{-fs * .84:.0f}" width="{cw + 2:.0f}" height="{fs:.0f}" fill="#0b0b0b"/>'
                        f'<text x="{cw / 2:.0f}" text-anchor="middle" font-size="{fs}" fill="#ffffff" font-family="{fam},KRH">{esc(ch)}</text>')
            else:  # white letter with a heavy black outline
                body = f'<text font-size="{fs}" fill="#ffffff" stroke="#0b0b0b" stroke-width="6" paint-order="stroke" stroke-linejoin="round" font-family="{fam},KRH">{esc(ch)}</text>'
            out.append(f'<g transform="translate({cx:.0f} 0) rotate({rot})">{body}</g>')
            cx += cw + 1
        return "".join(out), cx
    for i, (word, desc) in enumerate(items):
        on, kt, cyc = cycle(i, n)
        mixed = "".join(c.lower() if k % 2 else c for k, c in enumerate(word))
        x, y = i * 7, i * 31
        ww = textw(mixed, "P5A", 28)
        menu.append(f'<g>{slide_in(.25 + i * .05, -460)}<g transform="translate({x} {y})">'
                    f'<text font-size="28" fill="#ffffff" stroke="#0b0b0b" stroke-width="5" paint-order="stroke" font-family="P5A,KRH">{esc(mixed)}</text>'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<g><animateTransform attributeName="transform" type="translate" values="-16 0;-16 0;6 0;0 0;0 0" {kt}/>'
                    f'<polygon points="-34,-26 {ww + 18:.0f},-30 {ww + 10:.0f},8 -40,10" fill="#0b0b0b"/>'
                    f'<path d="M-22 -18L-19 -11L-11 -10L-17 -5L-15 3L-22 -1L-29 3L-27 -5L-33 -10L-25 -11Z" fill="#ffffff"/>'
                    f'<text font-size="28" fill="#ff1a2e" font-family="P5A,KRH">{esc(mixed)}</text></g></g></g></g>')
        help_.append(f'<text x="936" y="512" text-anchor="end" font-size="14" fill="#ffffff" {KR} opacity="{1 if i == 0 else 0}">'
                     f'<animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>{esc(desc)}</text>')
    logo, lw = ransom((user.get("name") or user["login"]).split()[0].upper(), 1, 92)
    burst = "M0 -230L40 -90L150 -170L95 -45L235 -40L110 30L190 140L50 85L20 220L-30 90L-150 180L-95 40L-230 10L-100 -40L-170 -160L-40 -95Z"
    shards = "".join(f'<polygon points="{p}" fill="#0b0b0b"/>' for p in ["0,0 150,0 40,540 0,540", "560,0 640,0 520,540 470,540"])
    stars = "".join(f'<path d="M0 -{r}L{r * .3:.0f} -{r * .3:.0f}L{r} 0L{r * .3:.0f} {r * .3:.0f}L0 {r}L-{r * .3:.0f} {r * .3:.0f}L-{r} 0L-{r * .3:.0f} -{r * .3:.0f}Z" fill="#0b0b0b" transform="translate({x} {y})">'
                    f'<animateTransform attributeName="transform" type="rotate" values="0 {x} {y};90 {x} {y}" dur="{d}s" repeatCount="indefinite" additive="sum"/></path>'
                    for x, y, r, d in [(520, 60, 16, 6), (900, 360, 14, 5), (600, 470, 12, 7)])
    rp = user.get("public_repos", 0)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{esc((user.get("name") or user["login"]).upper())} — profile menu: projects GOGO, 광탈페, EXPO, recent repositories and portfolio.">
<defs><pattern id="dots" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="5" cy="5" r="2.2" fill="#000000"/></pattern>
<pattern id="zig" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="18" height="18" fill="#ffffff"/><rect width="9" height="18" fill="#0b0b0b"/></pattern>
<linearGradient id="rf" x1="0" x2="1"><stop offset="0" stop-color="#000000"/><stop offset=".35" stop-color="#ffffff"/></linearGradient>
<mask id="right"><rect x="-300" y="-300" width="600" height="600" fill="url(#rf)"/></mask><clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath></defs>
<g clip-path="url(#c)" {F5}>
<rect width="{W}" height="{H}" fill="#a3000f"/>
<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".22"/>
{shards}
<g transform="translate(730 300)"><g><animateTransform attributeName="transform" type="translate" values="0 -6;0 8;0 -6" dur="8s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#right)"><image href="data:image/png;base64,{hero}" x="-300" y="-300" width="600" height="600"/></g></g></g>
<polygon points="470,540 560,250 700,60 820,0 700,200 640,540" fill="#ff1a2e"/>
<polygon points="880,0 960,0 960,300 910,300" fill="url(#zig)"/><polygon points="866,0 880,0 910,300 896,300" fill="#0b0b0b"/>
<g transform="translate(300 170)"><g><animateTransform attributeName="transform" type="rotate" values="0;360" dur="40s" repeatCount="indefinite"/>
<path d="{burst}" fill="#0b0b0b" transform="scale(1.12)"/><path d="{burst}" fill="#ff1a2e"/></g></g>
<g transform="translate({300 - lw / 2:.0f} 200) rotate(-7)"><g><animateTransform attributeName="transform" type="scale" values="1.6;1.6;.96;1" keyTimes="0;.55;.8;1" dur="{OPEN + .6}s" fill="freeze"/>
<polygon points="-30,-112 {lw + 40:.0f},-128 {lw + 26:.0f},34 {lw * .55:.0f},22 -40,40" fill="#ffffff" stroke="#0b0b0b" stroke-width="5"/>{logo}</g></g>
<g transform="translate(110 262) rotate(-7)"><rect width="370" height="30" fill="#0b0b0b"/><text x="14" y="21" font-size="15" fill="#ffffff" {KR}>{esc((user.get("bio") or "product designer · vibe coder")[:40])}</text></g>
{stars}
<g transform="translate(130 336) rotate(-7)">{"".join(menu)}</g>
<g transform="translate(40 512) rotate(-6)"><text font-size="38" fill="#ffffff" stroke="#0b0b0b" stroke-width="6" paint-order="stroke" font-family="P5A">★{rp}</text><text x="{textw(f"★{rp}", "P5A", 38) + 8:.0f}" font-size="14" fill="#ffffff">REPOS</text></g>
<polygon points="690,492 960,484 960,540 676,540" fill="#0b0b0b"/>
{"".join(help_)}
<text x="936" y="530" text-anchor="end" font-size="12" fill="#ffffff">⊗ CONFIRM  ◎ CLOSE</text>
{p5_wipe(W, H)}
</g>
</svg>"""


if __name__ == "__main__":
    user = get(f"https://api.github.com/users/{USER}")
    repos = [r for r in get(f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=30")
             if not r["fork"] and not r["private"] and r["name"] != USER][:4]
    theme = theme_now()
    avatar = get(user["avatar_url"] + ("&" if "?" in user["avatar_url"] else "?") + "s=300", raw=True)
    svg = embed_fonts({"p3r": screen_p3r, "p4": screen_p4, "p5": screen_p5}[theme](user, repos, poster(avatar, TONES[theme])))
    assert svg.count("<svg") == 1 and len(repos) <= 4
    open(os.path.join(HERE, "screen.svg"), "w").write(svg)
    print("screen.svg", theme, len(svg) // 1024, "KB,", len(repos), "repos")
