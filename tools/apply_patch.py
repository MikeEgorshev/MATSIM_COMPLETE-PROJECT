# Apply edits to plot_pt_routes_schematic_simple.py
path = "plot_pt_routes_schematic_simple.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

# 1) For route 11: add remove_last_if_outlier after dedupe_consecutive
s = s.replace(
    "pts = dedupe_consecutive(pts)\n            if len(pts) < 2:\n                continue\n\n        # Обрезаем только маршрут 6",
    "pts = dedupe_consecutive(pts)\n            pts = remove_last_if_outlier(pts, ROUTE_11_X_MAX)\n            if len(pts) < 2:\n                continue\n\n        # Обрезаем только маршрут 6"
)

# 2) For route 6: add simplify before offset; then add drop_duplicates for all
s = s.replace(
    "if len(pts) < 2:\n                continue\n\n        # 6 и 11: параллельный сдвиг по нормали к сегментам",
    "if len(pts) < 2:\n                continue\n            if HAS_SHAPELY and len(pts) >= 2:\n                simplified = LineString(pts).simplify(tolerance=5.0)\n                if not simplified.is_empty and simplified.geom_type == \"LineString\":\n                    pts = list(simplified.coords)\n                if len(pts) < 2:\n                    continue\n\n        # Очистка перед отрисовкой: дубликаты, порядок уже по последовательности.\n        pts = drop_duplicates_keep_order(pts)\n        pts = dedupe_consecutive(pts)\n        if len(pts) < 2:\n            continue\n\n        # 6 и 11: параллельный сдвиг по нормали к сегментам"
)

# 3) mitre_limit=1.0 in offset_polyline_shapely call
s = s.replace(
    "pts_off = offset_polyline_shapely(pts, base_off, join_style=2)",
    "pts_off = offset_polyline_shapely(pts, base_off, join_style=2, mitre_limit=1.0)"
)

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(s)
print("Patch applied.")
