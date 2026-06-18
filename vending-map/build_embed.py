"""Generate embed.html = index.html with config.js + app.js inlined.
A single, paste-ready file for GoDaddy's Custom Code section (or to host + iframe).
Run from vending-map/:  python build_embed.py
"""
import pathlib

d = pathlib.Path(__file__).parent
html = (d / "index.html").read_text(encoding="utf-8")
cfg  = (d / "config.js").read_text(encoding="utf-8")
app  = (d / "app.js").read_text(encoding="utf-8")

html = html.replace('<script src="config.js"></script>', f"<script>\n{cfg}\n</script>")
html = html.replace('<script src="app.js"></script>',    f"<script>\n{app}\n</script>")

(d / "embed.html").write_text(html, encoding="utf-8")
print(f"wrote embed.html ({len(html)} bytes); Leaflet stays on CDN, config+app inlined")
