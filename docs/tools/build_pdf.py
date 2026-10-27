"""Build docs/Sprite-to-Bead-Pattern-User-Guide.pdf from docs/USER_GUIDE.md (the single source).

Uses Qt's own Markdown reader and PDF writer (already part of the app's
dependencies). Each main section starts on a new page; images are scaled to
the page width; pages are numbered.
    python docs/tools/build_pdf.py
"""
import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt, QUrl
from PySide6.QtGui import (QFont, QGuiApplication, QImage, QPageLayout, QPageSize, QPainter,
                           QPdfWriter, QTextBlockFormat, QTextCursor, QTextDocument,
                           QTextImageFormat)

DOCS = Path(__file__).resolve().parents[1]
SOURCE = DOCS / "USER_GUIDE.md"
OUTPUT = DOCS / "Sprite-to-Bead-Pattern-User-Guide.pdf"
DPI = 96
MARGIN_MM = 16


def add_page_numbers_to_contents(doc, page_height):
    """Printed contents: plain entries with the page each section starts on
    (links inside a printed PDF would not jump anywhere)."""
    layout = doc.documentLayout()
    starts = {}
    block = doc.begin()
    while block.isValid():
        if block.blockFormat().headingLevel() == 2:
            starts[block.text().strip()] = int(layout.blockBoundingRect(block).top() // page_height) + 1
        block = block.next()
    block = doc.begin()
    while block.isValid():
        if block.textList() is not None:
            text = block.text().strip()
            match = next((t for t in starts if t.split(". ", 1)[-1] == text), None)
            if match:
                cursor = QTextCursor(block)
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                plain = cursor.charFormat()
                plain.setAnchor(False)
                plain.setAnchorHref("")
                plain.setForeground(Qt.GlobalColor.black)
                plain.setFontUnderline(False)
                cursor.insertText(f"{text}  ·  page {starts[match]}", plain)
        block = block.next()


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    writer = QPdfWriter(str(OUTPUT))
    writer.setResolution(DPI)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                                     QMarginsF(MARGIN_MM, MARGIN_MM, MARGIN_MM, MARGIN_MM + 4),
                                     QPageLayout.Unit.Millimeter))
    writer.setTitle("Sprite-to-Bead Pattern — User Guide")
    writer.setCreator("Sprite-to-Bead Pattern documentation")
    page = writer.pageLayout().paintRectPixels(DPI)
    width, height = page.width(), page.height()

    doc = QTextDocument()
    doc.setBaseUrl(QUrl.fromLocalFile(str(DOCS) + "/"))
    doc.setDefaultFont(QFont("Segoe UI", 10))
    doc.setDocumentMargin(0)
    # Section dividers are for the web version; in print every section starts a new page.
    markdown = "\n".join(l for l in SOURCE.read_text(encoding="utf-8").splitlines() if l.strip() != "---")
    doc.setMarkdown(markdown, QTextDocument.MarkdownFeature.MarkdownDialectGitHub)
    doc.setDefaultStyleSheet("")
    doc.setPageSize(QSizeF(width, height))

    # Scale images to fit the text width; start every level-2 heading on a new page.
    block = doc.begin()
    images = 0
    while block.isValid():
        if block.blockFormat().headingLevel() == 2:
            cursor = QTextCursor(block)
            fmt = block.blockFormat()
            fmt.setPageBreakPolicy(QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore)
            fmt.setTopMargin(0)
            cursor.setBlockFormat(fmt)
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and frag.charFormat().isImageFormat():
                image_format = frag.charFormat().toImageFormat()
                path = DOCS / image_format.name()
                image = QImage(str(path))
                if image.isNull():
                    raise FileNotFoundError(path)
                scale = min(1.0, width / image.width(), (height * 0.62) / image.height())
                image_format.setWidth(image.width() * scale)
                image_format.setHeight(image.height() * scale)
                cursor = QTextCursor(doc)
                cursor.setPosition(frag.position())
                cursor.setPosition(frag.position() + frag.length(), QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(image_format)
                images += 1
            it += 1
        block = block.next()

    add_page_numbers_to_contents(doc, height)
    # Editing the contents leaves Qt's lazy layout unfinished near the end of the document
    # (text after a point is painted with zero height); lay everything out again and check.
    doc.setPageSize(QSizeF(width, height))
    layout = doc.documentLayout()
    block = doc.begin()
    while block.isValid():
        if block.text().strip() and layout.blockBoundingRect(block).height() <= 0:
            raise RuntimeError(f"text not laid out: {block.text()[:60]!r}")
        block = block.next()
    painter = QPainter(writer)
    pages = doc.pageCount()
    footer_font = QFont("Segoe UI", 8)
    for n in range(pages):
        if n:
            writer.newPage()
        painter.save()
        painter.translate(0, -n * height)
        doc.drawContents(painter, QRectF(0, n * height, width, height))
        painter.restore()
        painter.setFont(footer_font)
        painter.setPen(Qt.GlobalColor.gray)
        painter.drawText(QRectF(0, height + 4, width, 20), Qt.AlignmentFlag.AlignRight,
                         f"Sprite-to-Bead Pattern — User Guide · page {n + 1} of {pages}")
    painter.end()
    print(f"{OUTPUT.name}: {pages} pages, {images} images, {OUTPUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
