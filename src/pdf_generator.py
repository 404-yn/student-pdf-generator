from __future__ import annotations

import io
import logging
import re
import time
import unicodedata
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


class PdfGenerator:
    def __init__(self, config_module) -> None:
        self.frontpage_pdf: Path = config_module.FRONTPAGE_PDF
        self.report_pdf: Path = config_module.REPORT_PDF
        self.output_dir: Path = config_module.OUTPUT_DIR
        self.overlay: dict = config_module.OVERLAY
        self.max_age_seconds: int = config_module.OUTPUT_MAX_AGE_SECONDS
        self.logger = logging.getLogger(__name__)

    def generate(self, student_name: str, register_number: str) -> Path:
        self._ensure_storage()
        self.cleanup_old_files()
        self._require_file(self.frontpage_pdf, "front-page PDF template")
        self._require_file(self.report_pdf, "report PDF template")

        frontpage_reader = PdfReader(str(self.frontpage_pdf))
        if not frontpage_reader.pages:
            raise RuntimeError("The front-page PDF template has no pages.")

        overlay_stream = self._build_overlay(
            frontpage_reader.pages[0].mediabox.width,
            frontpage_reader.pages[0].mediabox.height,
            student_name,
            register_number,
        )
        overlay_reader = PdfReader(overlay_stream)

        writer = PdfWriter()
        first_page = frontpage_reader.pages[0]
        first_page.merge_page(overlay_reader.pages[0])
        writer.add_page(first_page)
        for page in frontpage_reader.pages[1:]:
            writer.add_page(page)
        for page in PdfReader(str(self.report_pdf)).pages:
            writer.add_page(page)

        filename = f"{self._sanitize_part(student_name)}_{self._sanitize_part(register_number)}.pdf"
        destination = self.output_dir / filename
        temporary = self.output_dir / f".{filename}.{time.time_ns()}.tmp"
        try:
            with temporary.open("wb") as file_handle:
                writer.write(file_handle)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            self.logger.exception("Failed to write generated PDF")
            raise RuntimeError("The PDF could not be generated.") from None
        return destination

    def cleanup_old_files(self) -> None:
        cutoff = time.time() - self.max_age_seconds
        for path in self.output_dir.glob("*.pdf"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                self.logger.warning("Could not remove old generated file: %s", path.name)

    def _build_overlay(self, page_width: float, page_height: float, student_name: str, register_number: str) -> io.BytesIO:
        stream = io.BytesIO()
        pdf = canvas.Canvas(stream, pagesize=(float(page_width), float(page_height)))
        values = {
            "student_name": student_name.upper(),
            "register_number": f"REG NO : {register_number.upper()}",
        }
        for field, value in values.items():
            settings = self.overlay[field]
            mask_x = settings["x"] - settings["mask_width"] / 2 if settings.get("align") == "center" else settings["x"]
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(mask_x, settings["y"] - 4, settings["mask_width"], settings["mask_height"], fill=1, stroke=0)
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont(settings["font_name"], settings["font_size"])
            baseline = settings["y"]
            if settings.get("align") == "center":
                pdf.drawCentredString(settings["x"], baseline, value)
            else:
                pdf.drawString(settings["x"], baseline, value)
        pdf.save()
        stream.seek(0)
        return stream

    def _ensure_storage(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _require_file(path: Path, description: str) -> None:
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"The {description} is missing.")

    @staticmethod
    def _sanitize_part(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").upper()
        return cleaned or "STUDENT"
