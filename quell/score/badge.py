"""Generates shields.io-style SVG badge for README embedding."""
from pathlib import Path


def generate_badge(score: float) -> str:
    """Generate an SVG badge for the given Quell score (0.0–1.0)."""
    pct = int(score * 100)
    color = "#4c1" if score >= 0.80 else "#dfb317" if score >= 0.60 else "#e05d44"
    label, value = "quell score", f"{pct}%"
    lw = len(label) * 6 + 10
    vw = len(value) * 6 + 10
    tw = lw + vw
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{tw}" height="20">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{tw}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw}" height="20" fill="#555"/>
    <rect x="{lw}" width="{vw}" height="20" fill="{color}"/>
    <rect width="{tw}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle"
     font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{lw//2}" y="14" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{lw//2}" y="13">{label}</text>
    <text x="{lw + vw//2}" y="14" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{lw + vw//2}" y="13">{value}</text>
  </g>
</svg>'''


def write_badge(score: float, output_dir: Path = Path(".quell")) -> Path:
    """Write badge to output_dir/badge.svg. Returns path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    badge_path = output_dir / "badge.svg"
    badge_path.write_text(generate_badge(score), encoding="utf-8")
    return badge_path
