"""Generate repeatable synthetic sample diagrams and a short research paper."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PAPER = ROOT.parent / "output" / "pdf" / "multimodal_retrieval_demo_paper.pdf"
WIDTH, HEIGHT = 1600, 900
BG = "#F7F8F5"
INK = "#26332C"
MUTED = "#66716A"
GREEN = "#557C60"
MINT = "#E6EEE6"
BLUE = "#E8EFF5"
LAVENDER = "#EEEAF8"
AMBER = "#F5EEDF"
LINE = "#CED7CE"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fnt: ImageFont.ImageFont, fill: str) -> None:
    x0, y0, x1, y1 = box
    bounds = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=6, align="center")
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    draw.multiline_text(((x0 + x1 - width) / 2, (y0 + y1 - height) / 2), text, font=fnt, fill=fill, spacing=6, align="center")


def arrow(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], color: str = GREEN, width: int = 5) -> None:
    draw.line(points, fill=color, width=width, joint="curve")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    if abs(x2 - x1) >= abs(y2 - y1):
        side = 1 if x2 > x1 else -1
        head = [(x2, y2), (x2 - side * 17, y2 - 10), (x2 - side * 17, y2 + 10)]
    else:
        side = 1 if y2 > y1 else -1
        head = [(x2, y2), (x2 - 10, y2 - side * 17), (x2 + 10, y2 - side * 17)]
    draw.polygon(head, fill=color)


def make_architecture() -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((64, 46), "REFERENCE ARCHITECTURE", font=font(21, True), fill=GREEN)
    draw.text((64, 82), "From mixed media to cited answers", font=font(42, True), fill=INK)
    draw.text((66, 142), "A synthetic example for testing cross-source research questions", font=font(20), fill=MUTED)

    # Input cards
    inputs = [
        ("PDF PAPERS", "Text + figures", BLUE),
        ("IMAGES", "OCR labels + vision", LAVENDER),
        ("AUDIO / VIDEO", "Transcript + frames", AMBER),
        ("SPREADSHEETS", "Sheets + row ranges", MINT),
    ]
    y_positions = [228, 365, 502, 639]
    for (title, subtitle, fill), y in zip(inputs, y_positions):
        draw.rounded_rectangle((64, y, 358, y + 104), radius=17, fill="#FFFFFF", outline=LINE, width=2)
        draw.rounded_rectangle((82, y + 23, 124, y + 65), radius=10, fill=fill)
        center_text(draw, (82, y + 23, 124, y + 65), title.split()[0][:3], font(12, True), GREEN)
        draw.text((143, y + 23), title, font=font(18, True), fill=INK)
        draw.text((143, y + 55), subtitle, font=font(15), fill=MUTED)

    # Extraction block
    draw.rounded_rectangle((450, 235, 740, 705), radius=24, fill="#FFFFFF", outline="#C9D7CA", width=3)
    draw.text((480, 266), "01", font=font(15, True), fill=GREEN)
    draw.text((480, 300), "Extract +\nunderstand", font=font(27, True), fill=INK, spacing=5)
    extract_items = ["PDF parser + OCR", "Vision descriptions", "Whisper transcript", "Workbook reader"]
    for i, item in enumerate(extract_items):
        y = 408 + i * 60
        draw.ellipse((482, y + 3, 497, y + 18), fill=GREEN)
        draw.text((513, y), item, font=font(17), fill=MUTED)

    # Chunking block
    draw.rounded_rectangle((810, 320, 1090, 620), radius=24, fill="#FFFFFF", outline="#D8D1EB", width=3)
    draw.text((840, 352), "02", font=font(15, True), fill="#796BA7")
    draw.text((840, 387), "Chunk +\nembed", font=font(27, True), fill=INK, spacing=5)
    draw.text((840, 478), "Page-aware passages", font=font(16), fill=MUTED)
    draw.text((840, 509), "Text + visual labels", font=font(16), fill=MUTED)
    draw.text((840, 540), "Cross-modal vectors", font=font(16), fill=MUTED)

    # Retrieval and answer blocks
    draw.rounded_rectangle((1160, 226, 1525, 397), radius=24, fill="#FFFFFF", outline="#D7DEEA", width=3)
    draw.text((1191, 257), "03  RETRIEVE", font=font(15, True), fill="#667FA0")
    draw.text((1191, 295), "Rank relevant evidence", font=font(23, True), fill=INK)
    draw.text((1191, 338), "Across all selected sources", font=font(16), fill=MUTED)
    draw.rounded_rectangle((1160, 454, 1525, 675), radius=24, fill="#EFF4EF", outline="#C9D7CA", width=3)
    draw.text((1191, 485), "04  RESPOND", font=font(15, True), fill=GREEN)
    draw.text((1191, 524), "Answer + citations", font=font(23, True), fill=INK)
    draw.text((1191, 568), "Compare claims, show source labels,", font=font(15), fill=MUTED)
    draw.text((1191, 594), "and flag missing evidence.", font=font(15), fill=MUTED)

    # Connectors, routed around the cards.
    arrow(draw, [(358, 280), (408, 280), (408, 392), (450, 392)])
    arrow(draw, [(358, 417), (421, 417), (421, 463), (450, 463)])
    arrow(draw, [(358, 554), (421, 554), (421, 533), (450, 533)])
    arrow(draw, [(358, 691), (408, 691), (408, 606), (450, 606)])
    arrow(draw, [(740, 470), (810, 470)])
    arrow(draw, [(1090, 430), (1122, 430), (1122, 310), (1160, 310)])
    arrow(draw, [(1342, 397), (1342, 454)])
    draw.text((65, 828), "SYNTHETIC DEMO FIGURE  |  Image labels are designed for OCR testing", font=font(13, True), fill="#89938B")

    path = ROOT / "architecture_diagram.png"
    image.save(path, optimize=True)
    return path


def make_chart() -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((68, 52), "SYNTHETIC EVALUATION", font=font(21, True), fill=GREEN)
    draw.text((68, 91), "Retrieval coverage by search mode", font=font(40, True), fill=INK)
    draw.text((70, 151), "Illustrative values only - not a measured benchmark", font=font(19), fill=MUTED)

    chart_left, chart_top, chart_right, chart_bottom = 230, 248, 1410, 700
    # y-axis grid and percentages
    for pct in (0, 20, 40, 60, 80, 100):
        y = chart_bottom - int((chart_bottom - chart_top) * pct / 100)
        draw.line((chart_left, y, chart_right, y), fill="#E1E6E0", width=2)
        draw.text((160, y - 13), f"{pct}%", font=font(17), fill=MUTED)
    draw.line((chart_left, chart_top, chart_left, chart_bottom), fill="#AAB5AB", width=3)
    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill="#AAB5AB", width=3)

    values = [("Keyword\nsearch", 61, "#9EAD9F"), ("Embeddings", 82, "#78947B"), ("Embeddings +\nreranking", 90, "#52765B")]
    centers = [430, 820, 1210]
    for (label, value, color), center in zip(values, centers):
        top = chart_bottom - int((chart_bottom - chart_top) * value / 100)
        draw.rounded_rectangle((center - 92, top, center + 92, chart_bottom), radius=16, fill=color)
        draw.text((center - 33, top - 46), f"{value}%", font=font(22, True), fill=INK)
        box = draw.multiline_textbbox((0, 0), label, font=font(18, True), spacing=5, align="center")
        label_width = box[2] - box[0]
        draw.multiline_text((center - label_width / 2, chart_bottom + 24), label, font=font(18, True), fill=MUTED, spacing=5, align="center")

    draw.rounded_rectangle((315, 790, 1325, 852), radius=12, fill="#EDF1EC")
    center_text(draw, (315, 790, 1325, 852), "120 generated questions  |  12 synthetic source packets  |  Example data only", font(17, True), GREEN)
    path = ROOT / "retrieval_coverage.png"
    image.save(path, optimize=True)
    return path


def build_paper() -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image as PdfImage
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    PAPER.parent.mkdir(parents=True, exist_ok=True)
    arch = ROOT / "architecture_diagram.png"
    chart = ROOT / "retrieval_coverage.png"
    if not arch.exists() or not chart.exists():
        make_architecture()
        make_chart()

    doc = SimpleDocTemplate(
        str(PAPER), pagesize=letter,
        rightMargin=0.72 * inch, leftMargin=0.72 * inch,
        topMargin=0.72 * inch, bottomMargin=0.68 * inch,
        title="Cross-Modal Retrieval for Personal Research Libraries: A Synthetic Demonstration",
        author="Gather Demo Team",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Kicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=colors.HexColor("#52765B"), spaceAfter=11, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="PaperTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=28, textColor=colors.HexColor("#26332C"), alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#66716A"), alignment=TA_CENTER, spaceAfter=7))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#355D40"), spaceBefore=10, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name="SubSection", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor("#35443A"), spaceBefore=7, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="BodyText2", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=13.5, textColor=colors.HexColor("#313A34"), alignment=TA_LEFT, spaceAfter=7))
    styles.add(ParagraphStyle(name="Caption", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#69736C"), alignment=TA_LEFT, spaceBefore=5, spaceAfter=10))
    styles.add(ParagraphStyle(name="References", parent=styles["Normal"], fontSize=8.1, leading=11.4, leftIndent=12, firstLineIndent=-12, spaceAfter=5, textColor=colors.HexColor("#39423B")))

    story = []
    story.extend([
        Spacer(1, 0.2 * inch),
        Paragraph("SYNTHETIC RESEARCH PAPER  |  MULTIMODAL RETRIEVAL", styles["Kicker"]),
        Paragraph("Cross-Modal Retrieval for<br/>Personal Research Libraries", styles["PaperTitle"]),
        Paragraph("A reproducible demonstration using text, figures, transcripts, and tables", styles["Subtitle"]),
        Paragraph("Gather Demo Team  |  November 2026  |  Example materials for software testing", styles["Subtitle"]),
        Spacer(1, 0.13 * inch),
        Paragraph("Abstract", styles["Section"]),
        Paragraph(
            "Research notes rarely arrive in one format. A paper may describe a system in prose, a diagram may show its components, and a spreadsheet may contain the measurements used to evaluate it. This synthetic paper presents a small retrieval-augmented workflow for searching those materials together. Documents are parsed into source-labeled passages; images contribute OCR labels or visual descriptions; and retrieval returns evidence that can be cited in an answer. All numerical results in this paper are fabricated solely to exercise document ingestion and cross-source question answering. They are not empirical findings.",
            styles["BodyText2"],
        ),
        Paragraph("Keywords: multimodal retrieval; document question answering; OCR; source grounding; synthetic evaluation", styles["Caption"]),
        Paragraph("1. Introduction", styles["Section"]),
        Paragraph(
            "A research assistant must connect claims across heterogeneous sources while preserving where each claim came from. Text-only retrieval can find a paragraph about an encoder but miss a diagram label, a table row, or a spoken explanation. A practical multimodal pipeline therefore needs parsers that retain source identity and location, a common representation for retrieved evidence, and an answer layer that reports uncertainty when the sources do not support a conclusion.",
            styles["BodyText2"],
        ),
        Paragraph(
            "This example focuses on an architecture-comparison question: whether a diagram's visible components match the system described in a paper. The sample architecture image is deliberately labeled with terms such as PDF parser, OCR, Whisper transcript, workbook reader, chunking, embeddings, retrieval, and citations. These labels make the files useful for OCR and retrieval testing even when an external vision API is not configured.",
            styles["BodyText2"],
        ),
        PageBreak(),
        Paragraph("2. System design", styles["Section"]),
        Paragraph(
            "The reference workflow has four stages. First, modality-specific readers extract text and preserve page, worksheet, or time references. Second, the extracted material is divided into overlapping passages. Third, passages are ranked for a question using embeddings when available or keyword matching in local mode. Finally, the answer layer summarizes only retrieved evidence and attaches source labels. OCR supplies visible text in local mode; full diagram interpretation is an optional vision-model capability.",
            styles["BodyText2"],
        ),
        Paragraph("Figure 1. Reference architecture used by the synthetic sample packet.", styles["Caption"]),
        PdfImage(str(arch), width=6.85 * inch, height=6.85 * inch * HEIGHT / WIDTH),
        Spacer(1, 0.12 * inch),
        Paragraph("2.1 Source representation", styles["SubSection"]),
        Paragraph(
            "Each passage carries a filename, a source type, and a locator. For a PDF the locator is a page number; for a workbook it is a sheet and row range; for audio or video it can be a transcript segment or sampled frame time. Keeping these fields beside the text supports concise citations and makes it possible to compare material from different modalities without losing provenance.",
            styles["BodyText2"],
        ),
        PageBreak(),
        Paragraph("3. Synthetic evaluation", styles["Section"]),
        Paragraph(
            "To create a deterministic example, we define 12 fictional source packets and 120 generated questions. Coverage is the share of questions for which the retrieval stage returns at least one passage containing the expected synthetic label. The values below are illustrative fixtures chosen to make the chart readable; no experiment was run and no claim about real-world performance is intended.",
            styles["BodyText2"],
        ),
        Paragraph("Table 1. Fabricated retrieval-coverage values for testing only.", styles["Caption"]),
    ])
    table = Table(
        [["Search mode", "Covered questions", "Synthetic coverage"],
         ["Keyword search", "73 / 120", "61%"],
         ["Embeddings", "98 / 120", "82%"],
         ["Embeddings + reranking", "108 / 120", "90%"]],
        colWidths=[2.9 * inch, 1.75 * inch, 1.6 * inch],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EFE8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#355D40")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#303A33")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE3DC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBF9")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        table,
        Spacer(1, 0.12 * inch),
        Paragraph("Figure 2. Synthetic coverage values repeated as a labeled image for image-ingestion testing.", styles["Caption"]),
        PdfImage(str(chart), width=6.7 * inch, height=6.7 * inch * HEIGHT / WIDTH),
        PageBreak(),
        Paragraph("4. Cross-source case study", styles["Section"]),
        Paragraph(
            "Consider the question: 'Compare the architecture diagram with the architecture described in the paper.' The paper states that inputs pass through modality-specific extraction, then chunking and embedding, followed by retrieval and a source-grounded answer. Figure 1 depicts the same stages and names concrete readers for PDFs, images, audio/video, and spreadsheets. A grounded response can therefore cite both the paper's system-design section and the architecture figure's page. The sample does not ask the assistant to infer unshown implementation details.",
            styles["BodyText2"],
        ),
        Paragraph("5. Limitations", styles["Section"]),
        Paragraph(
            "The sample is intentionally small and synthetic. Its labels are unusually clear, the question set is generated, and the chart values are invented. OCR may miss small, rotated, or low-contrast text. In local mode it can recover labels but cannot explain visual relationships; that requires a vision model. Retrieval scores are useful for selecting context, not for proving that a passage entails an answer. Production systems should add privacy controls, durable indexing, access isolation, and a human review path for consequential use.",
            styles["BodyText2"],
        ),
        Paragraph("6. Conclusion", styles["Section"]),
        Paragraph(
            "A useful multimodal research assistant keeps evidence and provenance together from ingestion through response. This demo packet provides a paper, an architecture image, and a synthetic results chart so that upload, OCR, PDF page citations, image labels, and cross-source retrieval can be exercised locally. Its figures and numbers are test fixtures, not research results.",
            styles["BodyText2"],
        ),
        Paragraph("References", styles["Section"]),
        Paragraph("[1] Lewis, P. et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS, 2020.", styles["References"]),
        Paragraph("[2] Radford, A. et al. Learning Transferable Visual Models From Natural Language Supervision. ICML, 2021.", styles["References"]),
        Paragraph("[3] Radford, A. et al. Robust Speech Recognition via Large-Scale Weak Supervision. ICML, 2023.", styles["References"]),
        Paragraph("[4] Vaswani, A. et al. Attention Is All You Need. NeurIPS, 2017.", styles["References"]),
    ])

    def page_footer(canvas, document) -> None:
        canvas.saveState()
        page_width, _ = letter
        canvas.setStrokeColor(colors.HexColor("#DCE3DC"))
        canvas.setLineWidth(0.6)
        canvas.line(0.72 * inch, 0.51 * inch, page_width - 0.72 * inch, 0.51 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#7C867E"))
        canvas.drawString(0.72 * inch, 0.34 * inch, "SYNTHETIC DEMONSTRATION - NOT PEER REVIEWED")
        canvas.drawRightString(page_width - 0.72 * inch, 0.34 * inch, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return PAPER


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-only", action="store_true")
    parser.add_argument("--pdf-only", action="store_true")
    args = parser.parse_args()
    if not args.pdf_only:
        print(make_architecture())
        print(make_chart())
    if not args.images_only:
        print(build_paper())


if __name__ == "__main__":
    main()
