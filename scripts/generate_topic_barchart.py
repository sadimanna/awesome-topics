import json
from pathlib import Path

INPUT_JSON = Path("./../data/topic_counts.json")
OUTPUT_SVG = Path("./../docs/assets/topic_distribution.svg")
ALT_OUTPUT_SVG = Path("./../assets/topic_distribution.svg")

BAR_HEIGHT = 24
BAR_GAP = 10
LABEL_WIDTH = 180
MAX_BAR_WIDTH = 400
FONT_SIZE = 14

data = json.loads(INPUT_JSON.read_text())
max_count = max(data.values())

height = len(data) * (BAR_HEIGHT + BAR_GAP) + 40
width = LABEL_WIDTH + MAX_BAR_WIDTH + 100

svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
    '<style>',
    'text { font-family: Times New Roman, sans-serif; }',
    '</style>'
]

y = 30
for topic, count in sorted(data.items(), key=lambda x: -x[1]):
    bar_width = int((count / max_count) * MAX_BAR_WIDTH)

    svg.append(f'<text x="10" y="{y + 16}" font-size="{FONT_SIZE}">{topic}</text>')
    svg.append(
        f'<rect x="{LABEL_WIDTH}" y="{y}" width="{bar_width}" '
        f'height="{BAR_HEIGHT}" fill="#4c72b0" rx="4" />'
    )
    svg.append(
        f'<text x="{LABEL_WIDTH + bar_width + 8}" y="{y + 16}" '
        f'font-size="{FONT_SIZE}">{count}</text>'
    )

    y += BAR_HEIGHT + BAR_GAP

svg.append("</svg>")
OUTPUT_SVG.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_SVG.write_text("\n".join(svg))

ALT_OUTPUT_SVG.parent.mkdir(parents=True, exist_ok=True)
ALT_OUTPUT_SVG.write_text("\n".join(svg))
