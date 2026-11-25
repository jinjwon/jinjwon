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
FONTS = {"P3": "BarlowCondensed-ExtraBoldItalic.ttf", "P4": "Anton-Regular.ttf", "P5A": "AbrilFatface-Regular.ttf",
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
         "p4": [(24, 24, 24), (120, 108, 60), (255, 222, 0), (255, 255, 255)],
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
        x, y = [0, -14, 6, -8, 10, -4, 4][i % 7], i * 40
        w = textw(word, "P3", 48)
        on = ";".join("1" if k == i else "0" for k in range(n))
        a = i / n
        kt = f'keyTimes="0;{a:.3f};{a + .02:.3f};{a + .05:.3f};1" {cyc}'
        tag = f"-14,-30 {w + 26:.0f},-38 {w + 14:.0f},8 {w * .5:.0f},2 -6,6"
        menu.append(f'<g>{slide_in(.05 + i * .05, 420)}<g transform="translate({x} {y})">'
                    f'<text x="3" y="3" font-size="48" fill="#0a2a9e" opacity=".5">{esc(word)}</text>'
                    f'<text font-size="48" fill="{["#bff6ff", "#7fe4ff"][i % 2]}">{esc(word)}</text>'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<polygon points="{tag}" fill="#ff3d9a" transform="translate(7 6)"/>'
                    f'<g><animateTransform attributeName="transform" type="scale" values="0 1;0 1;1.22 1.22;1.1 1.1;1.1 1.1" {kt}/>'
                    f'<polygon points="{tag}" fill="#ffffff"/><text font-size="48" fill="#ff1428">{esc(word)}</text></g></g></g></g>')
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
<text transform="translate(76 {H - 8}) rotate(-90)" font-size="112" fill="#0b0b0b">PROFILE</text>
<g transform="rotate(-2 180 40)"><rect x="84" y="16" width="200" height="46" fill="#ffffff" stroke="#0b0b0b" stroke-width="1.5"/>
<text x="94" y="40" font-size="20" fill="#0b0b0b">{name}</text><text x="95" y="55" font-size="9" fill="#0b0b0b" {KR}>{bio}</text></g>
{bubbles}
{confetti}
<g transform="translate(500 128) rotate(-18) skewX(-8)">{"".join(menu)}</g>
<rect x="640" y="482" width="296" height="1.5" fill="#ffffff"/>
<text x="640" y="476" font-size="10" fill="#ffffff">Guide</text>
{"".join(help_)}
<text x="930" y="524" text-anchor="end" font-size="13" fill="#ffffff">⊗ CONFIRM  ◎ CLOSE</text>
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
    """After P4 Revival menu frames: hot yellow, white daisies, a duotone character, black words on white tags, TV scanlines."""
    W, H = 960, 540
    items = menu_items(repos); n = len(items)
    menu, help_ = [], []
    for i, (word, desc) in enumerate(items):
        on, kt, cyc = cycle(i, n)
        x, y = [0, 18, 6, 24, 10, 28, 14][i % 7], i * 46
        w = textw(word, "P4", 44)
        tag = f"-12,-38 {w + 18:.0f},-42 {w + 10:.0f},8 -18,10"
        menu.append(f'<g>{slide_in(.05 + i * .05, 420)}<g transform="translate({x} {y})">'
                    f'<polygon points="{tag}" fill="#ffffff"/><text font-size="44" fill="#141414">{esc(word)}</text>'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<g><animateTransform attributeName="transform" type="scale" values="1 0;1 0;1.08 1.25;1.05 1.05;1.05 1.05" {kt}/>'
                    f'<polygon points="{tag}" fill="#141414"/><text font-size="44" fill="#ffde00">{esc(word)}</text></g></g></g></g>')
        help_.append(f'<text x="926" y="503" text-anchor="end" font-size="14" fill="#141414" {KR} opacity="{1 if i == 0 else 0}">'
                     f'<animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>{esc(desc)}</text>')
    def daisy(x, y, r, d, b):
        petals = "".join(f'<ellipse cx="0" cy="{-r}" rx="{r * .42:.1f}" ry="{r * .7:.1f}" fill="#ffffff" transform="rotate({a})"/>' for a in range(0, 360, 60))
        return (f'<g transform="translate({x} {y})"><g><animateTransform attributeName="transform" type="rotate" values="0;360" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
                f'{petals}<circle r="{r * .45:.1f}" fill="#ffb300"/></g></g>')
    flowers = "".join(daisy(*f) for f in [(470, 70, 16, 14, 0), (900, 90, 22, 18, 2), (520, 470, 14, 12, 1), (880, 300, 12, 10, 3), (420, 250, 10, 16, 0), (700, 40, 11, 13, 1)])
    stripes = "".join(f'<polygon points="0,0 1400,{-60 + k * 0} 1400,60" fill="#ffe94d" transform="rotate({k * 30})"/>' for k in range(12))
    scan = "".join(f'<rect y="{y}" width="{W}" height="1" fill="#000" opacity=".06"/>' for y in range(0, H, 4))
    name = esc((user.get("name") or user["login"]).upper()); bio = esc((user.get("bio") or "product designer · vibe coder")[:40])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{name} — profile menu: projects GOGO, 광탈페, EXPO, recent repositories and portfolio.">
<defs><radialGradient id="fade"><stop offset=".55" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></radialGradient>
<mask id="soft"><circle r="230" fill="url(#fade)"/></mask><clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath></defs>
<g clip-path="url(#c)" {F4}>
<rect width="{W}" height="{H}" fill="#ffd400"/>
<g transform="translate(260 290)"><g><animateTransform attributeName="transform" type="rotate" values="0;360" dur="90s" repeatCount="indefinite"/>{stripes}</g></g>
<text transform="translate(560 520) rotate(-8)" font-size="200" fill="#f2b800" opacity=".55">MENU</text>
<g transform="translate(260 290)"><g><animateTransform attributeName="transform" type="translate" values="0 -6;0 8;0 -6" dur="8s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#soft)"><image href="data:image/png;base64,{hero}" x="-230" y="-230" width="460" height="460"/></g></g></g>
<polygon points="560,0 960,0 960,540 470,540" fill="#ffffff" opacity=".35"/>
{flowers}
<rect width="80" height="{H}" fill="#141414"/>
<text transform="translate(76 {H - 8}) rotate(-90)" font-size="112" fill="#ffde00">PROFILE</text>
<g transform="rotate(-2 180 40)"><rect x="84" y="16" width="200" height="46" fill="#141414"/>
<text x="94" y="40" font-size="20" fill="#ffffff">{name}</text><text x="95" y="55" font-size="9" fill="#ffde00" {KR}>{bio}</text></g>
<g transform="translate(110 446) skewX(-12)"><rect width="300" height="66" fill="#1b2a8c"/><rect x="4" y="4" width="292" height="58" fill="none" stroke="#ffffff" stroke-width="1"/>
<text x="14" y="26" font-size="18" fill="#ffffff">{name}</text>
<text x="150" y="24" font-size="11" fill="#9fe8ff">REPO</text><text x="286" y="24" text-anchor="end" font-size="16" fill="#ffffff">{user.get("public_repos", 0)}</text>
<rect x="150" y="29" width="136" height="5" fill="#0b1440"/><rect x="150" y="29" width="{136 * min(user.get("public_repos", 0) / 30, 1):.0f}" height="5" fill="#3fd6ff"/>
<text x="150" y="50" font-size="11" fill="#b8ff8a">FOLLOW</text><text x="286" y="50" text-anchor="end" font-size="16" fill="#ffffff">{user.get("followers", 0)}</text>
<rect x="150" y="55" width="136" height="5" fill="#0b1440"/><rect x="150" y="55" width="{136 * min(user.get("followers", 0) / 30, 1):.0f}" height="5" fill="#7cf05a"/></g>
<g transform="translate(600 118) rotate(-8) skewX(-8)">{"".join(menu)}</g>
<rect x="630" y="484" width="306" height="28" fill="#ffffff" transform="skewX(-12)"/>
{"".join(help_)}
<text x="926" y="528" text-anchor="end" font-size="12" fill="#141414">⊗ CONFIRM  ◎ CLOSE</text>
{scan}
{tv_on(W, H)}
</g>
</svg>"""


def screen_p5(user, repos, hero):
    """After P5 pause-menu frames: red and black, halftone, a jagged white burst, ransom-note words, COMMAND."""
    W, H = 960, 540
    items = menu_items(repos); n = len(items)
    menu, help_ = [], []
    for i, (word, desc) in enumerate(items):
        on, kt, cyc = cycle(i, n)
        x, y = [0, -16, 8, -6, 12, -10, 4][i % 7], i * 44
        letters, cx = [], 0
        for j, ch in enumerate(word):
            fs = 36 + (j * 7 + i * 3) % 3 * 5
            fam = ["P5A", "P5B", "P4"][(j * 2 + i) % 3]
            cw = textw(ch, fam, fs)
            rot = ((j * 37 + i * 11) % 11) - 5
            style = (j + i) % 3
            if style == 1:  # white letter on a black chip, upright so it stays inside the chip
                cw *= 1.15
                body = (f'<rect x="-2" y="{-fs * .84:.0f}" width="{cw + 2:.0f}" height="{fs:.0f}" fill="#0b0b0b"/>'
                        f'<text x="{cw / 2:.0f}" text-anchor="middle" font-size="{fs}" fill="#ffffff" font-family="{fam},KRH">{esc(ch)}</text>')
            else:
                body = f'<text font-size="{fs}" fill="#0b0b0b" font-family="{fam},KRH">{esc(ch)}</text>'
            letters.append(f'<g transform="translate({cx:.0f} 0) rotate({rot})">{body}</g>')
            cx += cw + 1
        tag = f"-14,-44 {cx + 20:.0f},-50 {cx + 8:.0f},12 -8,8"
        menu.append(f'<g>{slide_in(.05 + i * .05, 420)}<g transform="translate({x} {y})">{"".join(letters)}'
                    f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>'
                    f'<g><animateTransform attributeName="transform" type="scale" values="0 1;0 1;1.18 1.18;1.08 1.08;1.08 1.08" {kt}/>'
                    f'<polygon points="{tag}" fill="#ffffff" stroke="#0b0b0b" stroke-width="3"/><text font-size="44" fill="#ff1a2e" font-family="P5A,KRH">{esc(word)}</text></g></g></g></g>')
        help_.append(f'<text x="926" y="506" text-anchor="end" font-size="14" fill="#ffffff" {KR} opacity="{1 if i == 0 else 0}">'
                     f'<animate attributeName="opacity" calcMode="discrete" values="{on}" {cyc}/>{esc(desc)}</text>')
    shards = "".join(f'<polygon points="{p}" fill="#0b0b0b"/>' for p in ["380,0 520,0 300,540 220,540", "880,0 960,0 960,140", "0,440 260,540 0,540"])
    stars = "".join(f'<path d="M0 -{r}L{r * .3:.0f} -{r * .3:.0f}L{r} 0L{r * .3:.0f} {r * .3:.0f}L0 {r}L-{r * .3:.0f} {r * .3:.0f}L-{r} 0L-{r * .3:.0f} -{r * .3:.0f}Z" fill="#0b0b0b" transform="translate({x} {y})">'
                    f'<animateTransform attributeName="transform" type="rotate" values="0 {x} {y};90 {x} {y}" dur="{d}s" repeatCount="indefinite" additive="sum"/></path>'
                    for x, y, r, d in [(470, 60, 18, 6), (920, 230, 14, 5), (520, 470, 12, 7), (860, 40, 10, 4)])
    name = esc((user.get("name") or user["login"]).upper()); bio = esc((user.get("bio") or "product designer · vibe coder")[:40])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{name} — profile menu: projects GOGO, 광탈페, EXPO, recent repositories and portfolio.">
<defs><pattern id="dots" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="5" cy="5" r="2.2" fill="#0b0b0b"/></pattern>
<radialGradient id="fade"><stop offset=".55" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></radialGradient>
<g id="hand"><rect x="-150" y="-70" width="300" height="240" rx="70"/>
<rect x="-150" y="-300" width="64" height="290" rx="32" transform="rotate(-9 -118 -40)"/><rect x="-74" y="-340" width="64" height="330" rx="32" transform="rotate(-3 -42 -40)"/>
<rect x="2" y="-330" width="64" height="320" rx="32" transform="rotate(3 34 -40)"/><rect x="78" y="-280" width="60" height="270" rx="30" transform="rotate(10 108 -40)"/>
<rect x="120" y="-10" width="58" height="200" rx="29" transform="rotate(-48 150 90)"/></g>
<pattern id="zig" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="18" height="18" fill="#ffffff"/><rect width="9" height="18" fill="#0b0b0b"/></pattern>
<mask id="soft"><circle r="230" fill="url(#fade)"/></mask><clipPath id="c"><rect width="{W}" height="{H}" rx="10"/></clipPath></defs>
<g clip-path="url(#c)" {F5}>
<rect width="{W}" height="{H}" fill="#d90012"/>
<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".18"/>
{shards}
<polygon points="860,0 960,0 960,330 896,330" fill="url(#zig)"/><polygon points="846,0 860,0 896,330 882,330" fill="#0b0b0b"/>
<g transform="translate(250 290)"><g><animateTransform attributeName="transform" type="translate" values="0 -6;0 8;0 -6" dur="8s" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<g mask="url(#soft)"><image href="data:image/png;base64,{hero}" x="-230" y="-230" width="460" height="460"/></g></g></g>
<g transform="translate(730 300) rotate(-14) scale(1.08)"><g><animateTransform attributeName="transform" type="translate" values="0 0;3 -2;0 0" dur="2.4s" repeatCount="indefinite"/>
<use href="#hand" fill="#0b0b0b" transform="translate(12 12)"/><use href="#hand" fill="#ffffff"/>
<polygon points="-190,150 210,30 222,74 -176,196" fill="#ff1a2e"/></g></g>
{stars}
<rect width="80" height="{H}" fill="#0b0b0b"/>
<text transform="translate(76 {H - 8}) rotate(-90)" font-size="112" fill="#ff1a2e">PROFILE</text>
<g transform="rotate(-3 180 40)"><rect x="90" y="22" width="200" height="46" fill="#ff1a2e"/><rect x="84" y="16" width="200" height="46" fill="#ffffff" stroke="#0b0b0b" stroke-width="2"/>
<text x="94" y="40" font-size="20" fill="#0b0b0b">{name}</text><text x="95" y="55" font-size="9" fill="#0b0b0b" {KR}>{bio}</text></g>
<g transform="translate(556 146) rotate(-10)">{"".join(menu)}</g>
<text transform="translate(330 526) rotate(-6)" font-size="46" fill="#0b0b0b" stroke="#ffffff" stroke-width="2">COMMAND</text>
{"".join(help_)}
<text x="926" y="528" text-anchor="end" font-size="12" fill="#ffffff">⊗ CONFIRM  ◎ CLOSE</text>
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
