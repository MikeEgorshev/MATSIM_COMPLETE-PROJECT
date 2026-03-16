#!/usr/bin/env python3
"""
Convert Markdown reports to PDF via fpdf2 with full Cyrillic support.

Usage:
  python md_to_pdf.py              → docs/ru/progress/10_final_report_shamalgan.pdf
  python md_to_pdf.py concepts     → docs/ru/MATSim_basic_concepts_guide.pdf
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


def md_to_html(md_text: str, src_dir: pathlib.Path) -> str:
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
        return f'<img alt="{alt}" src="{src}" width="480">'

    html = re.sub(r'<img\s+alt="([^"]*)"\s+src="([^"]*)"[^>]*>', abs_img, html)

    def clean_cell(m):
        tag, attrs, content = m.group(1), m.group(2) or "", m.group(3)
        content = re.sub(r'<(strong|em|code|b|i)>(.*?)</\1>', r"\2", content)
        return f"<{tag}{attrs}>{content}</{tag}>"

    html = re.sub(r"<(td|th)(\s[^>]*)?>(.+?)</\1>", clean_cell, html, flags=re.DOTALL)
    return html


def build_pdf(md_file: pathlib.Path, out_pdf: pathlib.Path, src_dir: pathlib.Path) -> None:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_font("Arial", "", str(FONTS_DIR / "arial.ttf"))
    pdf.add_font("Arial", "B", str(FONTS_DIR / "arialbd.ttf"))
    pdf.add_font("Arial", "I", str(FONTS_DIR / "ariali.ttf"))
    pdf.add_font("Arial", "BI", str(FONTS_DIR / "arialbi.ttf"))
    pdf.add_font("Consolas", "", str(FONTS_DIR / "consola.ttf"))
    pdf.add_font("Consolas", "B", str(FONTS_DIR / "consolab.ttf"))

    pdf.set_font("Arial", size=10)
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    md_text = md_file.read_text(encoding="utf-8")
    html = md_to_html(md_text, src_dir)

    pdf.write_html(
        html,
        tag_styles={
            "h1": fpdf.html.FontFace(family="Arial", size_pt=18, color="#1a3c6e"),
            "h2": fpdf.html.FontFace(family="Arial", size_pt=14, color="#1a3c6e"),
            "h3": fpdf.html.FontFace(family="Arial", size_pt=12, color="#2d5b9e"),
            "code": fpdf.html.FontFace(family="Consolas", size_pt=9),
        },
    )

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_pdf))
    sz = out_pdf.stat().st_size / 1024
    print(f"PDF saved: {out_pdf} ({sz:.0f} KB)")


if __name__ == "__main__":
    mode = "concepts" if len(sys.argv) > 1 and sys.argv[1].strip().lower() == "concepts" else "default"
    md_file, out_pdf, src_dir = REPORTS[mode]
    build_pdf(md_file, out_pdf, src_dir)
