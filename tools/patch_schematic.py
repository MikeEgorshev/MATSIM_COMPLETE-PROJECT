path = "plot_pt_routes_schematic_simple.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
old1 = "if line_id == \"line_11\":\n            pts = longest_connected_segment"
new1 = "if line_id == \"line_11\":\n            pts = longest_connected_segment"
# just add trim after the next line
s = s.replace(
    "pts = longest_connected_segment(pts, gap_threshold_m=1500.0)\n            if len(pts) < 2:",
    "pts = longest_connected_segment(pts, gap_threshold_m=1500.0)\n            pts = trim_tail_outliers(pts, n_check=5)\n            if len(pts) < 2:"
)
s = s.replace(
    "pts_off = offset_polyline(pts, base_off)\n        xs = [p[0] for p in pts_off]",
    "if line_id in (\"line_6\", \"line_11\") and base_off != 0:\n            pts_off = offset_polyline_segment_normal(pts, base_off)\n        else:\n            pts_off = offset_polyline(pts, base_off)\n        xs = [p[0] for p in pts_off]"
)
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(s)
print("Done")
