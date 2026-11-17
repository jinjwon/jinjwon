# Generates the profile graphics: a game-menu style header (menu.svg) and one list plate per project.
#   python3 assets/menu.gen.py     (run from the repo root; rewrites assets/menu.svg and assets/plate-*.svg)
# GitHub READMEs run no scripts or CSS, so everything is plain SVG with SMIL animation.
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = 'font-family="Arial Black,Helvetica Neue,Impact,Apple SD Gothic Neo,Malgun Gothic,sans-serif" font-weight="900" font-style="italic"'
CYANS = ["#c4f6ff", "#86e6ff", "#5ad2ff"]
NUMERALS = ["I", "II", "III", "IV"]


def header():
    items = [("DESIGN", 58, 0, 0), ("PROTOTYPE", 46, 26, 48), ("BUILD", 56, 8, 96), ("SHIP", 50, 40, 146), ("PORTFOLIO", 46, 4, 192)]
    slot, menu = 1.6, []
    total = slot * len(items)
    for i, (word, size, x, y) in enumerate(items):
        w = len(word) * size * .74  # rough width of heavy italic caps; the plate only needs to roughly cover the word
        shown = ";".join("1" if k == i else "0" for k in range(len(items)))
        menu.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{CYANS[i % 3]}">{word}</text>')
        menu.append(  # the "selected" look, shown only during this item's slot
            f'<g opacity="{1 if i == 0 else 0}"><animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" calcMode="discrete" values="{shown}"/>'
            f'<polygon points="{x - 34},{y - size * .86:.0f} {x + w + 60:.0f},{y - size * .62:.0f} {x + w + 22:.0f},{y + size * .3:.0f} {x - 14},{y + size * .12:.0f}" fill="#ff2a6d"/>'
            f'<polygon points="{x - 26},{y - size * .8:.0f} {x + w + 46:.0f},{y - size * .58:.0f} {x + w + 16:.0f},{y + size * .22:.0f} {x - 10},{y + size * .06:.0f}" fill="#ffffff"/>'
            f'<text x="{x + 4}" y="{y + 3}" font-size="{size}" fill="#101010">{word}</text>'
            f'<text x="{x}" y="{y}" font-size="{size}" fill="#ff1a2e">{word}</text></g>')
    shards = "".join(  # drifting confetti
        f'<polygon points="0,0 {w},{h * .3:.0f} {w * .3:.0f},{h}" fill="{c}" opacity=".85" transform="translate({x} {y})">'
        f'<animateTransform attributeName="transform" type="translate" values="{x} {y};{x + dx} {y - 26};{x} {y}" dur="{d}s" repeatCount="indefinite"/></polygon>'
        for x, y, w, h, c, dx, d in [(250, 250, 16, 20, "#ff3d9a", 8, 5), (300, 300, 12, 14, "#3b5bff", -6, 6.5), (215, 310, 10, 16, "#9b4dff", 5, 4.4),
                                     (392, 44, 14, 12, "#ffffff", -8, 7), (770, 96, 12, 16, "#ff3d9a", 6, 5.6), (350, 330, 18, 12, "#bff3ff", -7, 6)])
    caustics = "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#ffffff" opacity=".2"><animate attributeName="cx" values="{x};{x + 22};{x}" dur="{d}s" repeatCount="indefinite"/></ellipse>'
        for x, y, rx, ry, d in [(430, 26, 70, 12, 7), (560, 52, 46, 8, 9), (690, 22, 88, 14, 8), (790, 60, 40, 7, 6), (500, 84, 30, 5, 10)])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 360" role="img" aria-label="Jinwon Kim — Product Designer. Design, prototype, build, ship.">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#62d2ff"/><stop offset=".45" stop-color="#1c7ff2"/><stop offset="1" stop-color="#0a22c2"/></linearGradient>
<clipPath id="c"><rect width="840" height="360" rx="10"/></clipPath>
</defs>
<g clip-path="url(#c)" {FONT}>
<rect width="840" height="360" fill="url(#bg)"/>
{caustics}
<polygon points="0,0 360,0 176,360 0,360" fill="#ffffff"/>
<polygon points="360,0 398,0 214,360 176,360" fill="#0a22c2"/>
<polygon points="398,0 410,0 226,360 214,360" fill="#ffffff" opacity=".55"/>
<text transform="translate(86 372) rotate(-90)" font-size="118" fill="#c9cfd8">PROFILE</text>
<text transform="translate(76 366) rotate(-90)" font-size="118" fill="#111111">PROFILE</text>
<g transform="rotate(-3 200 60)">
<rect x="104" y="30" width="226" height="62" fill="#ffffff" stroke="#111111" stroke-width="1.5"/>
<text x="116" y="62" font-size="25" fill="#111111">JINWON KIM</text>
<text x="117" y="81" font-size="11" fill="#111111" font-weight="700">product designer who ships</text>
</g>
{shards}
<g transform="translate(452 92) rotate(-7) skewX(-6)">
{"".join(menu)}
</g>
<text x="820" y="318" text-anchor="end" font-size="16" fill="#ffffff">design → prototype → ship</text>
<rect x="596" y="325" width="224" height="1.5" fill="#ffffff"/>
<text x="596" y="337" font-size="9" fill="#ffffff" font-weight="700">Command</text>
<text x="820" y="350" text-anchor="end" font-size="13" fill="#ffffff">⊗ SELECT  ◎ BACK</text>
</g>
</svg>'''


def plate(i, name, tag_label, tag, desc):
    first = i == 0  # the top row of each list wears the "selected" colors
    bar, ink, sub, sub_ink = ("#ffffff", "#111111", "#111111", "#ffffff") if first else ("#141c5c", "#c4f6ff", "#6fe0ff", "#0b1440")
    edge = '<polygon points="14,2 834,8 838,12 826,62 8,56 6,50" fill="#ff1a2e"/>' if first else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 100" role="img" aria-label="{name} — {desc} ({tag})">
<g {FONT} transform="rotate(-1 420 50)">
{edge}
<polygon points="18,6 830,12 822,58 10,52" fill="{bar}"/>
<rect x="36" y="13" width="26" height="36" rx="2" fill="none" stroke="{ink}" stroke-width="2" transform="rotate(-9 49 31)"/>
<text x="49" y="39" text-anchor="middle" font-size="18" fill="{ink}" font-style="normal">{NUMERALS[i]}</text>
<text x="80" y="45" font-size="31" fill="{ink}">{name}</text>
<text x="808" y="45" text-anchor="end" font-size="{30 if len(tag) < 9 else 26}" fill="{ink}">{tag}</text>
<text x="{808 - len(tag) * (25 if len(tag) < 9 else 18) - 14}" y="45" text-anchor="end" font-size="11" fill="{ink}">{tag_label}</text>
<polygon points="72,57 812,62 806,92 66,87" fill="{sub}"/>
<text x="440" y="82" text-anchor="middle" font-size="17" fill="{sub_ink}" font-style="normal" font-weight="700">{desc}</text>
</g>
</svg>'''


BUILD = [("undertow", "TypeScript", "Claude Code · Codex 중심의 데스크톱 코드 에디터"),
         ("figmon", "HTML", "작업한 시간만큼 자라는 데스크톱 펫"),
         ("wuwa-spire", "HTML", "팬메이드 덱빌딩 로그라이크"),
         ("silent-dawn", "JavaScript", "2인 협동 픽셀 판타지 RPG 프롤로그")]
DESIGN = [("VENDIT", "TEAM LEAD", "숙박 요금 관리 · 운영자 리서치 · 요금 결정 UX · Framer 프로토타입"),
          ("WALLA", "PRODUCT", "설문 제작 · 문제·가설 정의 · IA·User Flow · UT 설계"),
          ("GOGO", "SOLO UI/UX", "체육대회 서비스 · 화면·인터랙션 설계 · 개발 협업 · QA·출시 대응"),
          ("PAWCE", "BRAND", "반려견 훈련 · 브랜드·공통 컴포넌트 · 화면 일관성 정리")]

if __name__ == "__main__":
    out = {"menu.svg": header()}
    for kind, label, rows in (("build", "STACK", BUILD), ("design", "ROLE", DESIGN)):
        for i, (name, tag, desc) in enumerate(rows):
            out[f"plate-{kind}-{i + 1}.svg"] = plate(i, name, label, tag, desc)
    for name, svg in out.items():
        assert "&" not in svg and svg.count("<svg") == 1, name  # no unescaped entities slipped into the text
        open(os.path.join(HERE, name), "w").write(svg)
    print(len(out), "files")
