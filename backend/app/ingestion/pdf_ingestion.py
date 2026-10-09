import os
import fitz # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger

class PDFIngestionService:
    """Extracts text, headings, tables, equations, and images from PDFs while preserving page numbers."""

    def __init__(self):
        self.image_output_dir = Path(settings.PROCESSED_DIR) / "images"
        self.image_output_dir.mkdir(parents=True, exist_ok=True)

    def extract_pdf(self, file_path: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Parses PDF file page-by-page.
        Returns a list of page data dictionaries:
        [{
            "page_number": 1,
            "text": "...",
            "headings": [...],
            "tables": [...],
            "equations": [...],
            "images": [{"image_path": "...", "xref": 12, "bbox": [...]}]
        }]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(file_path)
        pages_data = []

        try:
            for page_index in range(len(doc)):
                page_number = page_index + 1
                page = doc[page_index]

                # 1. Extract text and identify headings using font size heuristics
                blocks = page.get_text("dict")["blocks"]
                page_text_lines = []
                headings = []
                equations = []

                for block in blocks:
                    if block.get("type") == 0: # Text block
                        for line in block.get("lines", []):
                            line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                            if not line_text:
                                continue
                            page_text_lines.append(line_text)

                            # Font size heuristic for headings
                            max_font_size = max((span.get("size", 10) for span in line.get("spans", [])), default=10)
                            if max_font_size >= 14 and len(line_text) < 120:
                                headings.append(line_text)

                            # Math / Equation heuristic
                            if any(sym in line_text for sym in ["∑", "∫", "∂", "±", "≤", "≥", "λ", "μ", "σ", "P(L)", "Need[i]"]):
                                equations.append(line_text)

                raw_text = "\n".join(page_text_lines)

                # 2. Extract tables
                extracted_tables = []
                try:
                    tables = page.find_tables()
                    for t in tables:
                        df_rows = t.extract()
                        if df_rows:
                            extracted_tables.append(df_rows)
                except Exception as e:
                    logger.debug(f"Table extraction notice on page {page_number}: {e}")

                # 3. Extract embedded images
                images = []
                image_list = page.get_images(full=True)
                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    w = base_image.get("width", 0)
                    h = base_image.get("height", 0)
                    # Filter out tiny icons, bullets, and decorative lines
                    if w < 120 or h < 120 or (w * h < 15000):
                        continue

                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    img_filename = f"{document_id}_p{page_number}_img{img_idx + 1}.{image_ext}"
                    img_path = self.image_output_dir / img_filename

                    with open(img_path, "wb") as f_img:
                        f_img.write(image_bytes)

                    images.append({
                        "image_path": str(img_path),
                        "page_number": page_number,
                        "xref": xref,
                        "width": base_image.get("width"),
                        "height": base_image.get("height")
                    })

                pages_data.append({
                    "page_number": page_number,
                    "text": raw_text,
                    "headings": headings,
                    "tables": extracted_tables,
                    "equations": equations,
                    "images": images
                })

            logger.info(f"Extracted {len(pages_data)} pages from PDF {path.name}")
            return pages_data

        finally:
            doc.close()

pdf_ingestor = PDFIngestionService()
