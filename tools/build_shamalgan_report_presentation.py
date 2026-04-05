#!/usr/bin/env python3
"""
Собрать презентацию PowerPoint (~22 слайда) по:
  - итоговому отчёту «Шамалган»  (10_final_report_shamalgan.md)
  - введению в MATSim            (MATSim_basic_concepts_guide.md)

Требует: pip install python-pptx
Выход  : docs/ru/progress/10_final_report_shamalgan.pptx
"""

from __future__ import annotations

from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
except ImportError:
    raise SystemExit("Установите python-pptx:  pip install python-pptx")

ROOT = Path(__file__).resolve().parents[1]
OUT_PPTX = ROOT / "docs" / "ru" / "progress" / "10_final_report_shamalgan.pptx"
VIS = ROOT / "Visualization"
DOCS = ROOT / "docs"

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)  # widescreen 16:9

ACCENT = RGBColor(0x1B, 0x3A, 0x5C)   # dark navy
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
GRAY   = RGBColor(0x55, 0x55, 0x55)
LIGHT  = RGBColor(0xF2, 0xF2, 0xF2)
ORANGE = RGBColor(0xE8, 0x8D, 0x2A)

FONT_TITLE = "Segoe UI"
FONT_BODY  = "Segoe UI"
FONT_MONO  = "Consolas"


# ---------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------

def _set_slide_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_title_bar(slide, text: str, *, subtitle: str | None = None):
    """Dark bar at the top with white title."""
    bar = slide.shapes.add_shape(
        1, Inches(0), Inches(0), SLIDE_W, Inches(1.15),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.18), Inches(12), Inches(0.75))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_TITLE

    if subtitle:
        tb2 = slide.shapes.add_textbox(Inches(0.6), Inches(0.72), Inches(12), Inches(0.4))
        p2 = tb2.text_frame.paragraphs[0]
        p2.text = subtitle
        p2.font.size = Pt(13)
        p2.font.color.rgb = RGBColor(0xBB, 0xCC, 0xDD)
        p2.font.name = FONT_BODY


def _add_bullets(slide, lines: list[str], *,
                 left=Inches(0.6), top=Inches(1.45),
                 width=Inches(5.8), height=Inches(5.5),
                 font_size=Pt(14)):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = font_size
        p.font.name = FONT_BODY
        p.font.color.rgb = GRAY
        p.space_after = Pt(6)
    return tb


def _add_image(slide, path: Path, left, top, width, height=None):
    if not path.exists():
        return None
    kw = {"width": width}
    if height:
        kw["height"] = height
    return slide.shapes.add_picture(str(path), left, top, **kw)


def _add_table(slide, rows: list[list[str]], left, top, width, row_h=Inches(0.38)):
    n_rows, n_cols = len(rows), len(rows[0])
    col_w = width // n_cols
    tbl_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, row_h * n_rows)
    tbl = tbl_shape.table
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = val
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.name = FONT_BODY
                if ri == 0:
                    p.font.bold = True
                    p.font.color.rgb = WHITE
            if ri == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = ACCENT
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT if ri % 2 == 0 else WHITE
    for ci in range(n_cols):
        tbl.columns[ci].width = col_w
    return tbl_shape


def _add_slide_number(slide, num: int):
    tb = slide.shapes.add_textbox(Inches(12.4), Inches(7.05), Inches(0.7), Inches(0.35))
    p = tb.text_frame.paragraphs[0]
    p.text = str(num)
    p.alignment = PP_ALIGN.RIGHT
    p.font.size = Pt(9)
    p.font.color.rgb = GRAY
    p.font.name = FONT_BODY


# ---------------------------------------------------------------------------
#  slide builders
# ---------------------------------------------------------------------------

def slide_01_title(prs):
    """Титульный слайд."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, ACCENT)

    tb = slide.shapes.add_textbox(Inches(1), Inches(1.8), Inches(11), Inches(1.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "Транспортная модель\nсценария «Шамалган»"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_TITLE
    p.alignment = PP_ALIGN.CENTER

    tb2 = slide.shapes.add_textbox(Inches(1), Inches(3.7), Inches(11), Inches(0.6))
    p2 = tb2.text_frame.paragraphs[0]
    p2.text = "MATSim · proof-of-concept · Алматинская область"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(0xBB, 0xCC, 0xDD)
    p2.font.name = FONT_BODY
    p2.alignment = PP_ALIGN.CENTER

    tb3 = slide.shapes.add_textbox(Inches(1), Inches(4.6), Inches(11), Inches(0.5))
    p3 = tb3.text_frame.paragraphs[0]
    p3.text = "февраль – март 2026"
    p3.font.size = Pt(14)
    p3.font.color.rgb = RGBColor(0x88, 0xAA, 0xCC)
    p3.font.name = FONT_BODY
    p3.alignment = PP_ALIGN.CENTER

    line = slide.shapes.add_shape(1, Inches(4.5), Inches(4.3), Inches(4.3), Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = ORANGE
    line.line.fill.background()


def slide_02_agenda(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Содержание")

    col1 = [
        "Часть I  -- Введение в MATSim",
        "",
        "  1. Что такое MATSim",
        "  2. Агент и план на день",
        "  3. Сеть и транспортные отрезки",
        "  4. Общественный транспорт",
        "  5. Оценка плана, итерации, сходимость",
        "  6. Применения MATSim",
    ]
    col2 = [
        "Часть II -- Сценарий «Шамалган»",
        "",
        "  7.  Постановка задачи",
        "  8.  Исходные данные (GeoPackage)",
        "  9.  Дорожная сеть -- построение",
        "  10. Дорожная сеть -- контроль качества",
        "  11. Распределение населения -- зоны",
        "  12. Население -- алгоритм и параметры",
        "  13. Общественный транспорт -- маршруты",
        "  14. ОТ -- расписание и подвижной состав",
        "  15. Запуск и результаты симуляции",
        "  16. Валидация: УДС и ОТ",
        "  17. Ограничения и следующие шаги",
        "  18. Выводы",
    ]
    _add_bullets(slide, col1, left=Inches(0.6), top=Inches(1.45),
                 width=Inches(5.8), font_size=Pt(14))
    _add_bullets(slide, col2, left=Inches(6.8), top=Inches(1.45),
                 width=Inches(6.0), font_size=Pt(14))
    _add_slide_number(slide, 2)


# ── Part I: MATSim Concepts ──────────────────────────────────────────────

def slide_03_what_is_matsim(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Что такое MATSim",
                   subtitle="Multi-Agent Transport Simulation")
    _add_bullets(slide, [
        "• Open-source платформа для имитации транспортного спроса и потоков",
        "• Используется по всему миру: Берлин, Париж, Вена и др.",
        "",
        "• Открытый исходный код — можно адаптировать и верифицировать",
        "• Агентный подход — каждый «житель» — отдельный агент с расписанием",
        "• Итеративная настройка — агенты «проживают» день многократно,",
        "  постепенно улучшая свои решения",
    ], width=Inches(6.0))
    _add_image(slide, DOCS / "examples" / "berlin_1.jpg",
               Inches(7.2), Inches(1.5), Inches(5.5))
    _add_slide_number(slide, 3)


def slide_04_agent_plan(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Агент и план на день")
    _add_bullets(slide, [
        "Каждый агент — упрощённое представление человека.",
        "У агента есть план на день (цепочка активностей и поездок):",
        "",
        "  1. Активность «дом» (до 07:30)",
        "  2. Поездка до работы (car / pt / walk)",
        "  3. Активность «работа» (до 17:00)",
        "  4. Поездка домой",
        "  5. Активность «дом» до конца дня",
        "",
        "Агент привязан к местам и режимам.",
        "Анализ: доли режимов, загрузка, время в пути.",
    ], width=Inches(5.5))
    _add_image(slide, VIS / "docs-progress" / "matsim_agent_plan_diagram.png",
               Inches(6.2), Inches(1.4), Inches(6.8))
    _add_slide_number(slide, 4)


def slide_05_network(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Сеть и транспортные отрезки")
    _add_bullets(slide, [
        "Сеть = граф: узлы (перекрёстки) + отрезки / линки (участки дорог)",
        "",
        "Атрибуты каждого линка:",
        "• Длина и допустимая скорость → время проезда",
        "• Пропускная способность → задержки при перегрузке",
        "• Полосность → интерпретация вместимости",
        "",
        "Качество сети напрямую влияет на реалистичность результатов.",
    ], width=Inches(5.8))
    _add_image(slide, VIS / "network-qc" / "network_speed_overview.png",
               Inches(7.0), Inches(1.4), Inches(5.8))
    _add_slide_number(slide, 5)


def slide_06_pt_concept(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Общественный транспорт в MATSim")
    _add_bullets(slide, [
        "ОТ задаётся тремя компонентами:",
        "",
        "• Остановки — привязаны к линкам сети",
        "• Маршруты — последовательность остановок и линков",
        "• Расписание — время отправления и интервалы",
        "",
        "Агенты с режимом «ОТ» получают маршрут",
        "с учётом расписания, пересадок, ожидания.",
        "",
        "Можно оценивать влияние изменения интервалов",
        "или новых линий на пассажиропотоки и время поездок.",
    ], width=Inches(5.8))
    _add_image(slide, VIS / "pt-data" / "pt_schematic.png",
               Inches(7.0), Inches(1.4), Inches(5.8))
    _add_slide_number(slide, 6)


def slide_07_scoring_iterations(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Оценка плана, итерации и сходимость")
    _add_bullets(slide, [
        "Полезность (utility) — числовая оценка «качества» дня агента:",
        "  + время в нужных активностях (работа, дом, покупки)",
        "  − время в пути, ожидание, пересадки, расходы",
        "",
        "Итерация = один «виртуальный день»:",
        "  1. Выполнение планов (симуляция)",
        "  2. Оценка результатов (scoring)",
        "  3. Перепланирование — часть агентов меняет решения",
        "",
        "Повторяется десятки — сотни раз → доли режимов, загрузка,",
        "средняя полезность выходят на устойчивое состояние.",
    ], width=Inches(5.8))
    _add_image(slide, VIS / "docs-progress" / "simulation_convergence.png",
               Inches(7.0), Inches(1.4), Inches(5.8))
    _add_slide_number(slide, 7)


def slide_08_why_matsim(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Зачем нужен MATSim: примеры задач")
    _add_table(slide, [
        ["Задача", "Как помогает MATSim"],
        ["Новая линия ОТ / изменение расписания",
         "Перераспределение пассажиров, время в пути, загрузка пересадочных узлов"],
        ["Ремонт или сужение дороги",
         "Задержки, смена маршрутов и режимов (часть переходит на ОТ)"],
        ["Сравнение сценариев до/после застройки",
         "Анализ интенсивности, загрузки ОТ и прочих параметров"],
        ["Политики (тарифы, ограничения въезда)",
         "Влияние на полезность поездки → сдвиг модального распределения"],
    ], Inches(0.6), Inches(1.5), Inches(12.1))

    _add_bullets(slide, [
        "",
        "",
        "",
        "",
        "Результаты зависят от качества входных данных.",
        "MATSim даёт инструмент; интерпретация — за экспертами.",
    ], top=Inches(3.9), width=Inches(6.5), font_size=Pt(13))

    video_url = "https://www.youtube.com/watch?v=AE9SadF8jnc"
    box = slide.shapes.add_shape(
        1, Inches(7.5), Inches(4.0), Inches(5.2), Inches(3.0),
    )
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xEE, 0xEE, 0xEE)
    box.line.color.rgb = ACCENT
    box.line.width = Pt(1.5)

    tf = box.text_frame
    tf.word_wrap = True
    p1 = tf.paragraphs[0]
    p1.text = "MATSim Explained"
    p1.font.size = Pt(16)
    p1.font.bold = True
    p1.font.color.rgb = ACCENT
    p1.font.name = FONT_TITLE
    p1.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = ""
    p2.space_after = Pt(4)

    p3 = tf.add_paragraph()
    run = p3.add_run()
    run.text = video_url
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x00, 0x66, 0xCC)
    run.font.name = FONT_BODY
    run.font.underline = True
    run.hyperlink.address = video_url
    p3.alignment = PP_ALIGN.CENTER

    p4 = tf.add_paragraph()
    p4.text = ""
    p4.space_after = Pt(6)

    p5 = tf.add_paragraph()
    p5.text = "(кликните для просмотра)"
    p5.font.size = Pt(10)
    p5.font.color.rgb = GRAY
    p5.font.name = FONT_BODY
    p5.alignment = PP_ALIGN.CENTER

    _add_slide_number(slide, 8)


# ── Part II: Shamalgan Scenario ──────────────────────────────────────────

def slide_09_intro(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, ACCENT)

    tb = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(1.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "Часть II\nСценарий «Шамалган»"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_TITLE
    p.alignment = PP_ALIGN.CENTER

    tb2 = slide.shapes.add_textbox(Inches(1), Inches(4.3), Inches(11), Inches(0.5))
    p2 = tb2.text_frame.paragraphs[0]
    p2.text = "Proof-of-concept: от подготовки данных до агентной симуляции"
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(0xBB, 0xCC, 0xDD)
    p2.font.name = FONT_BODY
    p2.alignment = PP_ALIGN.CENTER

    _add_slide_number(slide, 9)


def slide_10_task(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Постановка задачи")
    _add_bullets(slide, [
        "• Территория: село Шамалган и ближние",
        "  окрестности (Алматинская область, Казахстан)",
        "",
        "• Закрытая система без кордонов",
        "  (без моделирования внешнего спроса)",
        "",
        "• Цель: отработать полный цикл",
        "  MATSim-моделирования — от подготовки",
        "  геоданных до агентной симуляции с ОТ",
        "",
        "• Режимы: car, pt, walk",
        "• Контроль качества, визуализация",
    ], width=Inches(5.0))
    _add_image(slide, VIS / "docs-progress" / "shamalgan_satellite_wide.png",
               Inches(5.6), Inches(1.3), Inches(3.7))
    _add_image(slide, VIS / "docs-progress" / "shamalgan_satellite_closeup.png",
               Inches(9.5), Inches(1.3), Inches(3.7))
    _add_slide_number(slide, 10)


def slide_11_geodata(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Исходные данные: GeoPackage")
    _add_table(slide, [
        ["Слой", "Тип геометрии", "Содержание"],
        ["map__lines", "Линии", "Осевые линии УДС"],
        ["map__multilinestrings", "Линии", "Двойные линии магистрали"],
        ["New_Points", "Точки", "Коммерческие объекты + остановки ОТ"],
        ["map__multipolygons", "Полигоны", "Границы застройки (не используются)"],
    ], Inches(0.6), Inches(1.5), Inches(12.1))

    _add_bullets(slide, [
        "",
        "",
        "",
        "",
        "• Из точек извлечены POI → work_weight зон",
        "• Остановки ОТ размечены в QGIS (route direction)",
        "• Формат: «6»=>«7», «11»=>«15»",
        "  (маршрут → порядковый номер остановки)",
    ], top=Inches(3.7), width=Inches(5.8), font_size=Pt(13))

    _add_image(slide, VIS / "docs-progress" / "qgis_gpkg_screenshot.png",
               Inches(6.5), Inches(3.7), Inches(6.5))
    _add_slide_number(slide, 11)


def slide_12_network_build(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Дорожная сеть — построение")
    _add_bullets(slide, [
        "• Источник: OSM-файл территории",
        "• PrepareShamalganNetwork: OSM → EPSG:32643 (UTM 43N)",
        "  → стандартные правила MATSim OsmNetworkReader",
        "",
        "Полосность:",
        "• Большинство линков: 1 полоса на направление",
        "• Единственная магистраль: 2 полосы на направление",
        "",
        "Профиль «poor» (плохое покрытие):",
        "• Местные / дворовые: ~20 км/ч, ×0,70",
        "• Коллекторные: ~30 км/ч, ×0,75",
        "• Магистраль: ~70 км/ч, ×0,85",
    ], width=Inches(5.2))
    _add_image(slide, VIS / "network-qc" / "network_lane_overview.png",
               Inches(5.8), Inches(1.3), Inches(7.2))
    _add_slide_number(slide, 12)


def slide_13_network_qc(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Дорожная сеть — контроль качества")
    _add_bullets(slide, [
        "Итого: 1 128 узлов, 2 991 линк, одна связная компонента, 0 тупиков.  "
        "Геометрия из OSM упрощена (дуги спрямлены) — для PoC не критично.",
    ], left=Inches(0.6), top=Inches(1.3), width=Inches(12.0), font_size=Pt(14))
    _add_image(slide, VIS / "network-qc" / "network_speed_overview.png",
               Inches(0.4), Inches(2.3), Inches(6.2))
    _add_image(slide, VIS / "network-qc" / "network_capacity_overview.png",
               Inches(6.8), Inches(2.3), Inches(6.2))
    _add_slide_number(slide, 13)


def slide_14_zones(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Распределение населения — зоны")
    _add_bullets(slide, [
        "• Источник: растр плотности населения",
        "  (data.humdata.org)",
        "• derive_shamalgan_zones.py →",
        "  сетка 10x8 (80 ячеек)",
        "",
        "• Ячейка: ~800 м x ~600 м = 0,5 км2",
        "• Активны только ячейки с плотностью > 0",
        "",
        "Для каждой зоны:",
        "• home_weight — число жителей",
        "• work_weight — число рабочих мест",
        "  (больше для зон с POI)",
    ], width=Inches(5.2))
    _add_image(slide, VIS / "zone-derivation" / "06_zone_weight_map_with_grid.png",
               Inches(5.8), Inches(1.3), Inches(7.2))
    _add_slide_number(slide, 14)


def slide_15_population(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Население — алгоритм и параметры")
    _add_bullets(slide, [
        "Алгоритм размещения агента:",
        "1. Выбор зоны дома (∝ home_weight) и зоны работы (∝ work_weight)",
        "2. Внутри зоны: length-weighted выбор линка (радиус 300 м от центроида)",
        "3. Случайная координата на выбранном линке",
        "   Fallback: разброс вокруг центроида → snap к ближайшему линку",
    ], width=Inches(12.0))

    _add_table(slide, [
        ["Параметр", "Значение"],
        ["Число агентов", "~30 481"],
        ["Доля занятых", "65%"],
        ["Начальные режимы", "авто 55%, ОТ 25%, пешком 20%"],
        ["План занятого", "дом → работа → дом"],
        ["План незанятого", "дом → другое → дом"],
        ["Выезд на работу", "07:00–08:59"],
        ["Возврат с работы", "16:00–18:59"],
    ], Inches(0.6), Inches(4.0), Inches(6.5))

    _add_image(slide, VIS / "zone-derivation" / "08_zones_rectangles.png",
               Inches(7.5), Inches(3.6), Inches(5.3))
    _add_slide_number(slide, 15)


def slide_16_pt_routes(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Общественный транспорт — маршруты")
    _add_bullets(slide, [
        "• 4 маршрута: 6, 11, 213, 256 — 8 направлений",
        "• Источники: citybus.kz, Яндекс.Карты, 2ГИС",
        "• Без GTFS — маршруты размечены вручную",
        "",
        "Трасса маршрутов:",
        "• Алгоритм Дейкстры по дорожной сети",
        "• Коридоры: 213 — обязательный линк 2011;",
        "  256 — фильтр по origid",
        "",
        "Привязка остановок:",
        "• 58 остановок, snap к ближайшему линку",
        "• Макс. расстояние snap: 20,6 м",
    ], width=Inches(5.8))
    _add_image(slide, VIS / "docs-progress" / "pt_routes_diagram.png",
               Inches(7.0), Inches(1.4), Inches(5.8))
    _add_slide_number(slide, 16)


def slide_17_pt_schedule(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "ОТ — расписание и подвижной состав")
    _add_table(slide, [
        ["Маршрут", "Тип ТС", "Вместимость", "Интервал", "Макс. скорость"],
        ["6", "Автобус (12 м)", "35 + 30 стоячих", "~30 мин", "50 км/ч"],
        ["11", "Автобус (12 м)", "35 + 30 стоячих", "~15 мин", "50 км/ч"],
        ["213", "Автобус (12 м)", "35 + 30 стоячих", "~10 мин", "50 км/ч"],
        ["256", "Маршрутка (7,5 м)", "18 + 8 стоячих", "~20 мин", "50 км/ч"],
    ], Inches(0.6), Inches(1.5), Inches(12.1))

    _add_bullets(slide, [
        "",
        "",
        "",
        "",
        "• Расписание: 06:00–23:00 с переменными интервалами по периодам дня",
        "• Стоянка на остановке: 30 с; обгон на конечных: 5–7 мин",
        "• Всего: 522 рейса/сутки, 40 ТС в парке, 4 типа ТС",
    ], top=Inches(3.8), font_size=Pt(13))

    _add_image(slide, VIS / "docs-progress" / "pt_routes_schematic.png",
               Inches(7.0), Inches(3.5), Inches(5.8))
    _add_slide_number(slide, 17)


def slide_18_results(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Запуск и результаты симуляции")
    _add_bullets(slide, [
        "RunShamalgan + config.xml:",
        "• 101 итерация (0-100), qsim.endTime = 30:00:00",
        "• transit = true, SwissRailRaptor",
        "• SubtourModeChoice: car, pt, walk",
    ], width=Inches(5.8))

    _add_table(slide, [
        ["Показатель", "Итерация 100"],
        ["Доля авто", "56,0%"],
        ["Доля ОТ", "19,3%"],
        ["Доля пеших", "24,7%"],
        ["Средняя полезность", "124,1 (ит. 0: −24,0)"],
    ], Inches(0.6), Inches(3.6), Inches(5.8))

    _add_image(slide, VIS / "docs-progress" / "simulation_convergence.png",
               Inches(7.0), Inches(1.4), Inches(5.8))

    tb = slide.shapes.add_textbox(Inches(0.6), Inches(6.3), Inches(12), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "Доля ОТ выросла с ~12,5% (ит. 0) до 19,3% (ит. 100); доля авто остаётся доминирующей (закрытая система, настройки сценария и сети)."
    p.font.size = Pt(12)
    p.font.color.rgb = GRAY
    p.font.name = FONT_BODY
    _add_slide_number(slide, 18)


def slide_19_validation(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Валидация: УДС и ОТ")

    _add_bullets(slide, [
        "УДС (после 100 итераций):",
    ], width=Inches(12.0))

    _add_table(slide, [
        ["Показатель", "Значение", "Источник / ориентир"],
        ["Загрузка УДС", "0,068", "traffic_stats_by_road_type_daily.csv"],
        ["Макс. скорость (ограничение)", "60 км/ч", "Городской лимит"],
        ["Средняя фактическая скорость", "23,0 км/ч", "traffic_stats (Avg. Speed)"],
    ], Inches(0.6), Inches(2.3), Inches(12.1))

    _add_bullets(slide, [
        "",
        "",
        "",
        "",
        "",
        "ОТ — сравнение с практикой:",
        "• Вместимость автобуса 65 чел. — норма для средней вместимости",
        "• Вместимость маршрутки 26 чел. — типично для класса «Газель»",
        "• Скорость 25–32 км/ч — типовая для пригородных маршрутов",
        "• Стоянка 30 с — типично при умеренной посадке",
        "• Интервалы 10–30 мин — характерны для пригорода",
    ], top=Inches(3.0), font_size=Pt(13))
    _add_slide_number(slide, 19)


def slide_20_limitations(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Ограничения и следующие шаги")
    _add_table(slide, [
        ["Ограничение", "Влияние", "Приоритет"],
        ["Упрощённая геометрия линков", "Неточные длины перегонов", "Средний"],
        ["ОТ — макет без GTFS", "Расписание по допущениям", "Средний"],
        ["Нет калибровки по наблюдениям", "Доли режимов не верифицированы", "Высокий"],
        ["Нет facilities", "Упрощённый спрос: дом→работа→дом", "Низкий"],
        ["Население без демографии", "Нет возраста, наличия авто, дохода", "Низкий"],
    ], Inches(0.6), Inches(1.5), Inches(12.1))

    _add_bullets(slide, [
        "",
        "",
        "",
        "",
        "",
        "Для перехода к production-уровню необходимы:",
        "• GTFS данные по общественному транспорту",
        "• Данные транспортных обследований",
        "• Цикл калибровки на реальных замерах",
    ], top=Inches(4.2), font_size=Pt(14))
    _add_slide_number(slide, 20)


def slide_21_sources(prs):
    """Предпоследний слайд: источники данных и литература (научный формат, URL в тексте)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, "Источники данных и литература")

    lines = [
        "Данные и геоматериалы",
        "• OpenStreetMap (OSM) — геометрия УДС, экстент: https://www.openstreetmap.org/  (ODbL: https://opendatacommons.org/licenses/odbl/1-0/)",
        "• Humanitarian Data Exchange (HDX) — растр плотности 100 м: https://data.humdata.org/  (файл kaz_pop_2025_CN_100m_R2025A_v1.tif)",
        "• GeoPackage new_map.gpkg — остановки ОТ, POI; подготовка в QGIS: https://qgis.org/",
        "• citybus.kz — справочно по маршрутам: https://citybus.kz/",
        "• Яндекс.Карты — маршруты, интервалы, панорамы: https://yandex.ru/maps/",
        "• 2ГИС — маршруты и контекст: https://2gis.ru/",
        "",
        "Нормативы и справочники (ориентиры в отчёте)",
        "• СН РК 3.03-01-2013 «Автомобильные дороги» — диапазоны пропускной способности в сравнительной таблице",
        "• HCM (Highway Capacity Manual), МГСН — упомянуты в отчёте как ориентиры проверки атрибутов сети",
        "",
        "Методология и ПО симуляции",
        "• Horni A., Nagel K., Axhausen K.W. (eds.) The Multi-Agent Transport Simulation MATSim. Ubiquity Press.",
        "  https://www.ubiquitypress.com/reader/books/pdf/10.5334/baw",
        "• MATSim Book Part One (PDF): https://matsim.org/files/book/partOne-latest.pdf",
        "• Экосистема MATSim: https://github.com/matsim-org/matsim-code-examples  ·  GTFS2MATSim: https://github.com/matsim-org/GTFS2MATSim",
    ]
    _add_bullets(
        slide,
        lines,
        left=Inches(0.55),
        top=Inches(1.35),
        width=Inches(12.2),
        height=Inches(5.85),
        font_size=Pt(10),
    )
    _add_slide_number(slide, 21)


def slide_22_conclusions(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, ACCENT)

    tb = slide.shapes.add_textbox(Inches(1), Inches(0.6), Inches(11), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Выводы"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_TITLE
    p.alignment = PP_ALIGN.CENTER

    conclusions = [
        ("1", "Полный цикл пройден",
         "От подготовки геоданных до запуска многоитерационной\n"
         "симуляции с ОТ, выбором режимов и визуализацией."),
        ("2", "Сценарий работоспособен",
         "10+ итераций без ошибок, наблюдается сходимость\n"
         "полезности и перераспределение режимов."),
        ("3", "Атрибуты в рамках нормативов",
         "Сеть и ОТ проверены по HCM, МГСН,\n"
         "открытым данным Яндекс/2ГИС."),
        ("4", "Минимальные данные → работающая модель",
         "OSM + растр плотности + маршруты — достаточно для\n"
         "proof-of-concept. Для production: GTFS + калибровка."),
    ]
    y = Inches(1.7)
    for num, heading, detail in conclusions:
        circ = slide.shapes.add_shape(9, Inches(1.2), y, Inches(0.55), Inches(0.55))
        circ.fill.solid()
        circ.fill.fore_color.rgb = ORANGE
        circ.line.fill.background()
        circ.text_frame.paragraphs[0].text = num
        circ.text_frame.paragraphs[0].font.size = Pt(18)
        circ.text_frame.paragraphs[0].font.bold = True
        circ.text_frame.paragraphs[0].font.color.rgb = WHITE
        circ.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        circ.text_frame.paragraphs[0].font.name = FONT_TITLE
        circ.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

        tb_h = slide.shapes.add_textbox(Inches(2.0), y - Inches(0.03), Inches(9.5), Inches(0.4))
        ph = tb_h.text_frame.paragraphs[0]
        ph.text = heading
        ph.font.size = Pt(20)
        ph.font.bold = True
        ph.font.color.rgb = WHITE
        ph.font.name = FONT_TITLE

        tb_d = slide.shapes.add_textbox(Inches(2.0), y + Inches(0.42), Inches(9.5), Inches(0.7))
        pd = tb_d.text_frame.paragraphs[0]
        pd.text = detail
        pd.font.size = Pt(14)
        pd.font.color.rgb = RGBColor(0xBB, 0xCC, 0xDD)
        pd.font.name = FONT_BODY

        y += Inches(1.35)

    _add_slide_number(slide, 22)


# ---------------------------------------------------------------------------
#  main
# ---------------------------------------------------------------------------

def main():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_01_title(prs)
    slide_02_agenda(prs)
    slide_03_what_is_matsim(prs)
    slide_04_agent_plan(prs)
    slide_05_network(prs)
    slide_06_pt_concept(prs)
    slide_07_scoring_iterations(prs)
    slide_08_why_matsim(prs)
    slide_09_intro(prs)
    slide_10_task(prs)
    slide_11_geodata(prs)
    slide_12_network_build(prs)
    slide_13_network_qc(prs)
    slide_14_zones(prs)
    slide_15_population(prs)
    slide_16_pt_routes(prs)
    slide_17_pt_schedule(prs)
    slide_18_results(prs)
    slide_19_validation(prs)
    slide_20_limitations(prs)
    slide_21_sources(prs)
    slide_22_conclusions(prs)

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    print(f"Saved {len(prs.slides)} slides -> {OUT_PPTX}")


if __name__ == "__main__":
    main()
