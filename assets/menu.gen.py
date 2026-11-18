# Generates the profile graphics in a pause-menu style: a header (menu.svg) and one list plate per project.
#   python3 assets/menu.gen.py     (run from the repo root; rewrites assets/menu.svg and assets/plate-*.svg)
# GitHub READMEs run no scripts or CSS, so everything is plain SVG with SMIL animation.
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = 'font-family="Arial Black,Helvetica Neue,Impact,Apple SD Gothic Neo,Malgun Gothic,sans-serif" font-weight="900" font-style="italic"'
CYANS = ["#bff6ff", "#7fe4ff", "#4fd0ff"]
NUMERALS = ["0", "I", "II", "III", "IV"]

# Same order and links as the Framer portfolio site.
DESIGN = [("GOGO", "24.12–25.05", "학교 스포츠 행사 관리와 승부 예측을 지원하는 플랫폼", "https://free-surface-343720.framer.app/gogo"),
          ("광탈페", "25.04–25.09", "광탈페 홍보, 신청, 투표를 통합 관리하는 행사 관리 플랫폼", "https://free-surface-343720.framer.app/%EA%B4%91%ED%83%88%ED%8E%98"),
          ("EXPO", "24.06–25.05", "교육청 연수와 박람회를 효율적으로 관리하는 통합 플랫폼", "https://free-surface-343720.framer.app/expo")]
BUILD = [("undertow", "TypeScript", "Claude Code · Codex 중심의 데스크톱 코드 에디터"),
         ("figmon", "HTML", "작업한 시간만큼 자라는 데스크톱 펫"),
         ("wuwa-spire", "HTML", "팬메이드 덱빌딩 로그라이크"),
         ("silent-dawn", "JavaScript", "2인 협동 픽셀 판타지 RPG 프롤로그")]


def header():
    items = [("PROJECT", 56, 0, 0), ("BUILD", 52, 30, 50), ("SKILL", 48, 12, 98), ("CONTACT", 46, 44, 144), ("PORTFOLIO", 44, 6, 188)]
    slot, menu = 1.4, []
    total = slot * len(items)
    for i, (word, size, x, y) in enumerate(items):
        w = len(word) * size * .74  # rough width of heavy italic caps; the plate only needs to roughly cover the word
        shown = ";".join("1" if k == i else "0" for k in range(len(items)))
        menu.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{CYANS[i % 3]}">{word}</text>')
        menu.append(  # the "selected" look: pink-edged white slash, red word with a black drop
            f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" calcMode="discrete" values="{shown}"/>'
            f'<polygon points="{x - 60},{y - size * .5:.0f} {x + w + 90:.0f},{y - size * .95:.0f} {x + w + 40:.0f},{y + size * .3:.0f} {x - 30},{y + size * .18:.0f}" fill="#ff2f86"/>'
            f'<polygon points="{x - 50},{y - size * .48:.0f} {x + w + 74:.0f},{y - size * .86:.0f} {x + w + 32:.0f},{y + size * .2:.0f} {x - 24},{y + size * .1:.0f}" fill="#ffffff"/>'
            f'<text x="{x + 4}" y="{y + 3}" font-size="{size}" fill="#0b0b0b">{word}</text>'
            f'<text x="{x}" y="{y}" font-size="{size}" fill="#ff1428">{word}</text></g>')
    shards = "".join(  # drifting glass shards
        f'<polygon points="0,0 {w},{h * .3:.0f} {w * .3:.0f},{h}" fill="{c}" opacity=".8" transform="translate({x} {y})">'
        f'<animateTransform attributeName="transform" type="translate" values="{x} {y};{x + dx} {y - 24};{x} {y}" dur="{d}s" repeatCount="indefinite"/></polygon>'
        for x, y, w, h, c, dx, d in [(250, 262, 16, 22, "#ff3d9a", 8, 5), (300, 318, 12, 16, "#3047ff", -6, 6.5), (205, 300, 10, 18, "#8f4dff", 5, 4.4),
                                     (430, 40, 14, 12, "#ffffff", -8, 7), (785, 120, 12, 16, "#ff3d9a", 6, 5.6), (360, 340, 18, 12, "#bff3ff", -7, 6)])
    caustics = "".join(  # pool-light blotches drifting across the water
        f'<path d="M{x} {y}q{rx * .4:.0f} {-ry} {rx:.0f} 0t{rx * .8:.0f} {ry * .6:.0f}q{-rx * .9:.0f} {ry * 1.4:.0f} {-rx * 1.8:.0f} 0z" fill="#d8f6ff" opacity="{o}">'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx} 4;0 0" dur="{d}s" repeatCount="indefinite"/></path>'
        for x, y, rx, ry, o, dx, d in [(420, 30, 60, 14, .35, 26, 7), (560, 60, 40, 10, .3, -18, 9), (680, 26, 80, 16, .35, 22, 8),
                                      (780, 70, 34, 8, .3, -14, 6), (470, 96, 30, 7, .25, 16, 10), (620, 120, 44, 9, .2, -20, 11)])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 360" role="img" aria-label="Jinwon Kim — Product Designer. Project, build, skill, contact.">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2=".8" y2="1"><stop offset="0" stop-color="#55d3ff"/><stop offset=".4" stop-color="#1673ef"/><stop offset="1" stop-color="#0716b0"/></linearGradient>
<clipPath id="c"><rect width="840" height="360" rx="10"/></clipPath>
</defs>
<g clip-path="url(#c)" {FONT}>
<rect width="840" height="360" fill="url(#bg)"/>
{caustics}
<text transform="translate(640 420) rotate(-62)" font-size="150" fill="#ffffff" opacity=".22">MENU</text>
<polygon points="0,0 360,0 176,360 0,360" fill="#ffffff"/>
<polygon points="360,0 400,0 216,360 176,360" fill="#0716b0"/>
<polygon points="400,0 412,0 228,360 216,360" fill="#ffffff" opacity=".55"/>
<text transform="translate(86 372) rotate(-90)" font-size="118" fill="#c9cfd8">PROFILE</text>
<text transform="translate(76 366) rotate(-90)" font-size="118" fill="#0b0b0b">PROFILE</text>
<g transform="rotate(-2 210 60)">
<rect x="104" y="28" width="230" height="64" fill="#ffffff" stroke="#0b0b0b" stroke-width="1.5"/>
<text x="116" y="62" font-size="26" fill="#0b0b0b">JINWON KIM</text>
<text x="117" y="81" font-size="11" fill="#0b0b0b" font-weight="700">product designer · vibe coder</text>
</g>
{shards}
<g transform="translate(470 96) rotate(-7) skewX(-6)">
{"".join(menu)}
</g>
<text x="820" y="318" text-anchor="end" font-size="16" fill="#ffffff" font-style="normal" font-weight="700">어떤 프로젝트를 확인할까?</text>
<rect x="596" y="325" width="224" height="1.5" fill="#ffffff"/>
<text x="596" y="337" font-size="9" fill="#ffffff" font-weight="700">Guide</text>
<text x="820" y="352" text-anchor="end" font-size="13" fill="#ffffff">⊗ SELECT  ◎ BACK</text>
</g>
</svg>'''


def plate(i, name, label, tag, desc):
    first = i == 0  # the top row of each list wears the "selected" colors
    bar, ink, sub, sub_ink = ("#ffffff", "#0b0b0b", "#0b0b0b", "#ffffff") if first else ("#14206e", "#8ff0ff", "#8ff0ff", "#0b1440")
    edge = '<polygon points="14,2 834,8 838,12 826,62 8,56 6,50" fill="#ff1428"/>' if first else ""
    tag_size = 30 if len(tag) < 9 else 24
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 100" role="img" aria-label="{name} — {desc} ({tag})">
<g {FONT} transform="rotate(-1 420 50)">
{edge}
<polygon points="18,6 830,12 822,58 10,52" fill="{bar}"/>
<rect x="34" y="11" width="28" height="40" rx="2" fill="{bar}" stroke="{ink}" stroke-width="2.4" transform="rotate(-9 48 31)"/>
<text x="48" y="40" text-anchor="middle" font-size="20" fill="{ink}" font-style="normal" font-family="Georgia,serif">{NUMERALS[i]}</text>
<text x="80" y="46" font-size="32" fill="{ink}">{name}</text>
<text x="808" y="46" text-anchor="end" font-size="{tag_size}" fill="{ink}">{tag}</text>
<text x="{808 - len(tag) * tag_size * .72 - 12:.0f}" y="46" text-anchor="end" font-size="12" fill="{ink}">{label}</text>
<polygon points="72,57 812,62 806,92 66,87" fill="{sub}"/>
<text x="440" y="82" text-anchor="middle" font-size="17" fill="{sub_ink}" font-style="normal" font-weight="700">{desc}</text>
</g>
</svg>'''


if __name__ == "__main__":
    out = {"menu.svg": header()}
    for i, (name, term, desc, _) in enumerate(DESIGN):
        out[f"plate-design-{i + 1}.svg"] = plate(i, name, "TERM", term, desc)
    for i, (name, stack, desc) in enumerate(BUILD):
        out[f"plate-build-{i + 1}.svg"] = plate(i, name, "STACK", stack, desc)
    for f in os.listdir(HERE):  # drop plates for projects no longer listed
        if f.startswith("plate-") and f not in out:
            os.remove(os.path.join(HERE, f))
    for name, svg in out.items():
        assert "&" not in svg and svg.count("<svg") == 1, name  # no unescaped entities slipped into the text
        open(os.path.join(HERE, name), "w").write(svg)
    print(len(out), "files")
