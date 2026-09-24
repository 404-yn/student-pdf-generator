from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import config


def find_libreoffice() -> str | None:
    names = ["soffice.com", "soffice.exe", "soffice"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if sys.platform == "win32":
        candidates = [
            Path(r"C:\Program Files\LibreOffice\program\soffice.com"),
            Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.com"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        ]
        local_app_data = Path.home() / "AppData" / "Local"
        candidates.extend(local_app_data.glob("Programs/LibreOffice/program/soffice.*"))
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def convert_with_docx2pdf() -> bool:
    try:
        from docx2pdf import convert
        convert(str(config.FRONTPAGE_DOCX), str(config.FRONTPAGE_PDF))
        return config.FRONTPAGE_PDF.is_file()
    except Exception as error:
        print(f"docx2pdf unavailable or failed: {error}", file=sys.stderr)
        return False


def convert_with_libreoffice(executable: str) -> bool:
    command = [executable, "--headless", "--convert-to", "pdf", "--outdir", str(config.TEMPLATES_DIR), str(config.FRONTPAGE_DOCX)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    converted = config.TEMPLATES_DIR / f"{config.FRONTPAGE_DOCX.stem}.pdf"
    if result.returncode != 0 or not converted.is_file():
        print(result.stdout.strip() or result.stderr.strip() or "LibreOffice conversion failed.", file=sys.stderr)
        return False
    converted.replace(config.FRONTPAGE_PDF)
    return True


def main() -> int:
    if config.FRONTPAGE_PDF.is_file():
        print("Already configured: templates/frontpage_template.pdf")
        return 0
    if not config.FRONTPAGE_DOCX.is_file():
        print("Missing templates/frontpage.docx.", file=sys.stderr)
        return 1
    if convert_with_docx2pdf():
        print("Created templates/frontpage_template.pdf using docx2pdf.")
        return 0
    libreoffice = find_libreoffice()
    if libreoffice and convert_with_libreoffice(libreoffice):
        print("Created templates/frontpage_template.pdf using LibreOffice.")
        return 0
    print("Could not convert DOCX. Install Microsoft Word with docx2pdf support or LibreOffice.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
