#!/usr/bin/env python3
"""
Convert Markdown reports to PDF via fpdf2 with full Cyrillic support.

Usage:
  python md_to_pdf.py              → docs/ru/progress/10_final_report_shamalgan.pdf
  python md_to_pdf.py concepts     → docs/ru/MATSim_basic_concepts_guide.pdf

Optional (better tables via browser rendering):
  python md_to_pdf.py chromium
  python md_to_pdf.py concepts chromium
"""

import pathlib
import re
import sys
from fpdf import FPDF
import fpdf.html

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS_DIR = pathlib.Path("C:/Windows/Fonts")

# (md_file, out_pdf, base_dir for relative images)
REPORTS = {
    "default": (
        ROOT / "docs" / "ru" / "progress" / "10_final_report_shamalgan.md",
        ROOT / "docs" / "ru" / "progress" / "10_final_report_shamalgan.pdf",
        ROOT / "docs" / "ru" / "progress",
    ),
    "concepts": (
        ROOT / "docs" / "ru" / "MATSim_basic_concepts_guide.md",
        ROOT / "docs" / "ru" / "MATSim_basic_concepts_guide.pdf",
        ROOT / "docs" / "ru",
    ),
}


def md_to_html(
    md_text: str,
    src_dir: pathlib.Path,
    *,
    image_max_w_mm: float = 170,
    image_max_h_mm: float = 100,
) -> str:
    import markdown as md_lib

    html = md_lib.markdown(
        md_text,
        extensions=["tables", "fenced_code"],
        output_format="html5",
    )

    def abs_img(m):
        alt, src = m.group(1), m.group(2)
        if not src.startswith(("http", "file")):
            src = str((src_dir / src).resolve())

        # fpdf2 interprets <img width/height> as "points" which are then converted to the
        # PDF unit. With unit="mm", width_mm = width_pt / pdf.k (where pdf.k = 72/25.4).
        # If height is omitted, fpdf2 keeps aspect ratio based on width and may force a page break,
        # leaving large whitespace. To reduce this, cap image height and set both width & height.
        k = 72 / 25.4  # points per mm (matches FPDF(unit="mm").k)
        max_w_mm = image_max_w_mm
        max_h_mm = image_max_h_mm

        w_pt = int(max_w_mm * k)
        h_pt = 0
        try:
            from PIL import Image  # pillow

            with Image.open(src) as im:
                w_px, h_px = im.size
            if w_px > 0 and h_px > 0:
                aspect = w_px / h_px
                w_mm = min(max_w_mm, max_h_mm * aspect)
                h_mm = w_mm / aspect
                w_pt = int(w_mm * k)
                h_pt = int(h_mm * k)
        except Exception:
            # Fallback: only set width (older behavior) if pillow isn't available or image fails to open.
            pass

        if h_pt:
            return f'<img alt=\"{alt}\" src=\"{src}\" width=\"{w_pt}\" height=\"{h_pt}\">'
        return f'<img alt=\"{alt}\" src=\"{src}\" width=\"{w_pt}\">'

    html = re.sub(r'<img\s+alt="([^"]*)"\s+src="([^"]*)"[^>]*>', abs_img, html)

    def clean_cell(m):
        tag, attrs, content = m.group(1), m.group(2) or "", m.group(3)
        content = re.sub(r'<(strong|em|code|b|i)>(.*?)</\1>', r"\2", content)
        # fpdf2 does not support nested tags in td/th (e.g. <p>, <td>, <a>); strip any remaining tags
        content = re.sub(r'<[^>]+>', '', content)
        return f"<{tag}{attrs}>{content}</{tag}>"

    html = re.sub(r"<(td|th)(\s[^>]*)?>(.+?)</\1>", clean_cell, html, flags=re.DOTALL)

    # Нумерованные списки: fpdf2 рисует номера в одной точке (наложение). Заменяем <ol> на абзацы с явными номерами.
    def replace_ol(m):
        inner = m.group(1)
        items = re.findall(r"<li>(.*?)</li>", inner, re.DOTALL)
        if not items:
            return m.group(0)
        parts = []
        for i, content in enumerate(items, 1):
            content = content.strip()
            parts.append(f"<p><strong>{i}.</strong> &nbsp;&nbsp; {content}</p>")
        return "".join(parts)

    html = re.sub(r"<ol>\s*(.*?)\s*</ol>", replace_ol, html, flags=re.DOTALL)

    # Маркированные списки: отступ после буллета, чтобы не налезал на текст
    html = re.sub(r"<li>\s*", "<li>&nbsp;&nbsp;&nbsp;&nbsp;", html)
    return html


def md_to_html_browser(md_text: str, src_dir: pathlib.Path) -> str:
    """
    Markdown -> HTML для рендера браузером (Chromium). В отличие от fpdf2-ветки, не "приплющивает" таблицы.
    """
    import markdown as md_lib
    import base64
    import mimetypes

    html = md_lib.markdown(
        md_text,
        extensions=["tables", "fenced_code"],
        output_format="html5",
    )

    def abs_img(m):
        alt, src = m.group(1), m.group(2)
        if src.startswith(("http://", "https://", "file://")):
            return f'<img alt="{alt}" src="{src}">'

        # Resolve relative (and tolerate absolute Windows paths) to a proper file URI.
        p = pathlib.Path(src)
        if not p.is_absolute():
            p = (src_dir / p).resolve()
        else:
            p = p.resolve()
        if p.exists() and p.is_file():
            mime, _ = mimetypes.guess_type(str(p))
            if not mime:
                # Default to png if unknown; worst case browser ignores, but keeps processing.
                mime = "image/png"
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            return f'<img alt="{alt}" src="data:{mime};base64,{data}">'

        # Fallback (should be rare): keep as file URI.
        return f'<img alt="{alt}" src="{p.as_uri()}">'

    html = re.sub(r'<img\s+alt="([^"]*)"\s+src="([^"]*)"[^>]*>', abs_img, html)
    return html


def build_pdf_chromium(md_file: pathlib.Path, out_pdf: pathlib.Path, src_dir: pathlib.Path) -> None:
    """
    Печать PDF через headless Chromium (Playwright). Таблицы и границы выглядят как в браузере.
    """
    from playwright.sync_api import sync_playwright

    md_text = md_file.read_text(encoding="utf-8")
    body = md_to_html_browser(md_text, src_dir)

    # CSS: читаемая типографика + "красивые" таблицы (border-collapse, zebra, видимые границы)
    css = """
    :root{
      --bg:#0f1115;
      --fg:#e7eaf0;
      --muted:#a9b1c2;
      --grid: rgba(231,234,240,0.18);
      --grid-strong: rgba(231,234,240,0.28);
      --head: rgba(231,234,240,0.08);
      --zebra: rgba(231,234,240,0.04);
      --codebg: rgba(231,234,240,0.06);
    }
    @page { size: A4; margin: 14mm 14mm; }
    html,body{ background: #fff; }
    body{
      font-family: Arial, "Segoe UI", sans-serif;
      font-size: 11px;
      line-height: 1.45;
      color: #111;
    }
    h1{ font-size: 20px; margin: 0 0 8px; color:#1a3c6e; }
    h2{ font-size: 16px; margin: 18px 0 8px; color:#1a3c6e; }
    h3{ font-size: 13px; margin: 14px 0 6px; color:#2d5b9e; }
    p{ margin: 6px 0; }
    code{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 10px; background: #f3f5f8; padding: 1px 3px; border-radius: 3px; }
    pre code{ display:block; padding: 8px 10px; border-radius: 6px; }
    img{ max-width: 100%; height: auto; }

    table{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 12px;
      table-layout: fixed;
    }
    th, td{
      border: 1px solid rgba(0,0,0,0.28);
      padding: 6px 8px;
      vertical-align: top;
      word-wrap: break-word;
      overflow-wrap: anywhere;
    }
    th{
      background: rgba(0,0,0,0.06);
      font-weight: 700;
    }
    tbody tr:nth-child(even) td{
      background: rgba(0,0,0,0.02);
    }
    """

    html_doc = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>{md_file.name}</title>
    <style>{css}</style>
  </head>
  <body>
    {body}
  </body>
</html>
"""

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_doc, wait_until="networkidle")
        page.pdf(path=str(out_pdf), format="A4", print_background=True, prefer_css_page_size=True)
        browser.close()

    sz = out_pdf.stat().st_size / 1024
    print(f"PDF saved: {out_pdf} ({sz:.0f} KB) [engine=chromium]")


def build_pdf(
    md_file: pathlib.Path,
    out_pdf: pathlib.Path,
    src_dir: pathlib.Path,
    *,
    font_size_pt: float = 9,
    image_max_w_mm: float = 170,
    image_max_h_mm: float = 100,
) -> None:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_font("Arial", "", str(FONTS_DIR / "arial.ttf"))
    pdf.add_font("Arial", "B", str(FONTS_DIR / "arialbd.ttf"))
    pdf.add_font("Arial", "I", str(FONTS_DIR / "ariali.ttf"))
    pdf.add_font("Arial", "BI", str(FONTS_DIR / "arialbi.ttf"))
    pdf.add_font("Consolas", "", str(FONTS_DIR / "consola.ttf"))
    pdf.add_font("Consolas", "B", str(FONTS_DIR / "consolab.ttf"))
    # Consolas I/BI — чтобы курсив внутри <code> не вызывал Undefined font: consolasI
    for style, fname in (("I", "consolai.ttf"), ("BI", "consolaz.ttf")):
        path = FONTS_DIR / fname
        if path.exists():
            pdf.add_font("Consolas", style, str(path))

    pdf.set_font("Arial", size=font_size_pt)
    pdf.add_page()
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)

    md_text = md_file.read_text(encoding="utf-8")
    html = md_to_html(md_text, src_dir, image_max_w_mm=image_max_w_mm, image_max_h_mm=image_max_h_mm)

    # Heading sizes scale with body font; code slightly smaller than body
    h1_pt = font_size_pt + 7
    h2_pt = font_size_pt + 4
    h3_pt = font_size_pt + 2
    code_pt = max(8, font_size_pt - 1)

    pdf.write_html(
        html,
        tag_styles={
            "h1": fpdf.html.FontFace(family="Arial", size_pt=h1_pt, color="#1a3c6e"),
            "h2": fpdf.html.FontFace(family="Arial", size_pt=h2_pt, color="#1a3c6e"),
            "h3": fpdf.html.FontFace(family="Arial", size_pt=h3_pt, color="#2d5b9e"),
            "p": fpdf.html.FontFace(family="Arial", size_pt=font_size_pt),
            "li": fpdf.html.FontFace(family="Arial", size_pt=font_size_pt),
            "code": fpdf.html.FontFace(family="Consolas", size_pt=code_pt),
        },
    )

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_pdf))
    sz = out_pdf.stat().st_size / 1024
    print(f"PDF saved: {out_pdf} ({sz:.0f} KB)")


if __name__ == "__main__":
    args = [a.strip().lower() for a in sys.argv[1:] if a.strip()]
    mode = "concepts" if (args and args[0] == "concepts") else "default"
    engine = "chromium" if ("chromium" in args) else "fpdf"
    md_file, out_pdf, src_dir = REPORTS[mode]
    if engine == "chromium":
        build_pdf_chromium(md_file, out_pdf, src_dir)
    else:
        if mode == "concepts":
            # Гайд: крупнее шрифт и картинки, высота картинок ограничена чтобы не было пустых страниц
            build_pdf(
                md_file,
                out_pdf,
                src_dir,
                font_size_pt=10,
                image_max_w_mm=178,
                image_max_h_mm=102,
            )
        else:
            build_pdf(md_file, out_pdf, src_dir)
