#!/usr/bin/env python3
"""
Собрать презентацию PowerPoint по итоговому отчёту Шамалган.
Требует: pip install python-pptx

Выход: docs/ru/progress/10_final_report_shamalgan.pptx
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PPTX = ROOT / "docs" / "ru" / "progress" / "10_final_report_shamalgan.pptx"
VIS = ROOT / "Visualization"


def add_slide(prs, title: str, body_lines: list[str], image_path: Path | None = None):
    from pptx.util import Inches, Pt
    layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(layout)
    left, top, width = Inches(0.5), Inches(0.4), Inches(9)
    tb = slide.shapes.add_textbox(left, top, width, Inches(0.8))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(24)
    p.font.bold = True
    y = Inches(1.2)
    for line in body_lines:
        if not line.strip():
            y += Inches(0.15)
            continue
        tb2 = slide.shapes.add_textbox(Inches(0.5), y, Inches(9), Inches(0.5))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = line
        p2.font.size = Pt(12)
        y += Inches(0.35)
    if image_path and image_path.exists():
        try:
            slide.shapes.add_picture(
                str(image_path),
                Inches(0.5), Inches(4),
                width=Inches(6),
                height=Inches(4.2),
            )
        except Exception:
            pass
    return slide


def main():
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError:
        print("Установите python-pptx: pip install python-pptx")
        return

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # 1. Титульный слайд
    layout0 = prs.slide_layouts[6]
    s0 = prs.slides.add_slide(layout0)
    tb = s0.shapes.add_textbox(Inches(0.5), Inches(2.2), Inches(9), Inches(1.2))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "Транспортная модель сценария «Шамалган»"
    p.font.size = Pt(32)
    p.font.bold = True
    p.alignment = 1  # center
    tb2 = s0.shapes.add_textbox(Inches(0.5), Inches(3.6), Inches(9), Inches(0.6))
    tb2.text_frame.paragraphs[0].text = "Итоговый отчёт"
    tb2.text_frame.paragraphs[0].font.size = Pt(20)
    tb2.text_frame.paragraphs[0].alignment = 1
    tb3 = s0.shapes.add_textbox(Inches(0.5), Inches(4.4), Inches(9), Inches(0.5))
    tb3.text_frame.paragraphs[0].text = "Село Шамалган и окрестности (Алматинская область, Казахстан)"
    tb3.text_frame.paragraphs[0].font.size = Pt(14)
    tb3.text_frame.paragraphs[0].alignment = 1
    tb4 = s0.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(9), Inches(0.4))
    tb4.text_frame.paragraphs[0].text = "MATSim · proof-of-concept"
    tb4.text_frame.paragraphs[0].font.size = Pt(11)
    tb4.text_frame.paragraphs[0].alignment = 1

    # 2. Постановка задачи
    add_slide(prs, "Постановка задачи", [
        "• Территория: село Шамалган и ближние окрестности (закрытая система без кордонов).",
        "• Цель: отработать полный цикл — от подготовки данных до агентной симуляции с ОТ.",
        "• УДС, выбор режимов (car / pt / walk), визуализация результатов.",
        "• Фреймворк: MATSim.",
    ])

    # 3. Исходные данные
    add_slide(prs, "Исходные данные", [
        "• GeoPackage (new_map.gpkg): линки УДС, точки (остановки ОТ, POI), полигоны.",
        "• OSM (map): геометрия дорог для построения сети.",
        "• Растр плотности населения → скрипт derive_shamalgan_zones.py → сетка зон 10×8, zones-derived.csv.",
        "• Остановки ОТ размечены вручную в QGIS (route direction).",
        "",
        "Карта зон (прямоугольники 10×8, заливка по home_weight):",
    ], image_path=VIS / "zone-derivation" / "08_zones_rectangles.png")

    # 4. Дорожная сеть
    add_slide(prs, "Дорожная сеть (УДС)", [
        "• Построение: PrepareShamalganNetwork, OSM → EPSG:32643, правила MATSim OsmNetworkReader.",
        "• Полосность: 1 полоса на направление (большинство), магистраль — 2. Профиль «poor» (плохое покрытие).",
        "• Скорости: местные ~20 км/ч, магистраль ~70 км/ч. Пропускная способность снижена на 15–30%.",
        "• Итог: 1 128 узлов, 2 991 линк, одна связная компонента, 0 тупиков и изолятов.",
        "",
        "Обзор полосности и скоростей по сети:",
    ], image_path=VIS / "network-qc" / "network_lane_overview.png")

    # 5. Население
    add_slide(prs, "Распределение населения", [
        "• Зоны 10×8 (долгота/широта), home_weight / work_weight, sigma_m = 300 м.",
        "• Размещение: выбор зоны по весам → линк в радиусе sigma_m (вероятность ∝ длине линка) → координата на линке.",
        "• ~30 481 агент, 65% занятых. Планы: дом→работа→дом / дом→другое→дом.",
        "• Начальные режимы: авто 55%, ОТ 25%, пешком 20% (далее перераспределяет MATSim).",
        "",
        "Распределение активностей по звеньям:",
    ], image_path=VIS / "population_on_network_map.png")

    # 6. Общественный транспорт
    add_slide(prs, "Общественный транспорт", [
        "• 4 маршрута (6, 11, 213, 256) — 8 направлений. Источники: citybus.kz, Яндекс, 2ГИС.",
        "• Трасса: Дейкстра по сети + коридоры (213 — ключевой линк; 256 — по origid).",
        "• 58 остановок, snap < 21 м. Расписание 06:00–23:00, интервалы 10–30 мин по маршруту.",
        "• 522 рейса/сутки, 40 ТС. Автобус 65 чел., маршрутка 26 чел. Стоянка 60 с.",
        "",
        "Маршруты ОТ по сети:",
    ], image_path=VIS / "pt-data" / "pt_network_infographic.png")

    # 7. Запуск и результаты
    add_slide(prs, "Запуск и результаты симуляции", [
        "• RunShamalgan, config.xml, 11 итераций (0–10), qsim.endTime=30:00:00, SwissRailRaptor.",
        "• Результаты (ит. 10): авто 52,4%, ОТ 13,9%, пешком 33,6%. Средняя полезность 126,0 (рост с 115,3).",
        "• Сходимость: рост полезности по итерациям. Доля ОТ снизилась — модель перевела часть на пешие поездки.",
        "",
        "Сходимость (средняя полезность и доли режимов):",
    ], image_path=VIS / "docs-progress" / "simulation_convergence.png")

    # 8. Аудит реалистичности
    add_slide(prs, "Аудит реалистичности", [
        "УДС: пропускная способность и полосность в рамках HCM/МГСН (магистраль 1500–2000 авт/ч на полосу, местные 300–600).",
        "",
        "ОТ: вместимость автобуса 65 чел. и маршрутки 26 чел. — норма; скорость 25–32 км/ч и интервалы 10–30 мин — типично для пригорода; стоянка 60 с — консервативно.",
        "",
        "Подробно: 08_uds_capacity_lanes_audit.md, 09_pt_network_attributes_audit.md.",
    ])

    # 9. Ограничения
    add_slide(prs, "Ограничения и следующие шаги", [
        "• Упрощённая геометрия линков (спрямление дуг) — средний приоритет.",
        "• ОТ — макет без GTFS — средний.",
        "• Нет калибровки по наблюдениям — высокий при переходе к production.",
        "• Нет facilities, синтетическое население без демографии — низкий для proof-of-concept.",
        "",
        "Для production: GTFS, данные обследований, калибровка на замерах.",
    ])

    # 10. Выводы
    add_slide(prs, "Выводы", [
        "1. Полный цикл пройден: от геоданных до многоитерационной симуляции с ОТ и выбором режимов.",
        "2. Сценарий работоспособен: 10+ итераций без ошибок, сходимость и перераспределение режимов.",
        "3. Атрибуты сети и ОТ в рамках нормативов (HCM, МГСН, Яндекс/2ГИС).",
        "4. При минимальных данных (OSM, растр, маршруты) можно быстро собрать работающий сценарий MATSim; для production нужны GTFS и калибровка.",
    ])

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    print(f"Saved: {OUT_PPTX}")


if __name__ == "__main__":
    main()
