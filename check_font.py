from io import BytesIO
import sys

import fitz


PDF_PATH = "ZSD_DELIVERY_NOTE_SF (6).pdf"


def _read_font_names(font_bytes):
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return ["fontTools not installed"]

    try:
        font = TTFont(BytesIO(font_bytes))
    except Exception as exc:
        return [f"failed to parse font: {exc}"]

    names = []
    wanted_ids = {1, 2, 4, 6, 16, 17}
    for record in font["name"].names:
        if record.nameID not in wanted_ids:
            continue
        value = record.toUnicode()
        if value not in names:
            names.append(value)
    return names or ["no readable name records"]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    doc = fitz.open(PDF_PATH)
    print(f"PDF: {PDF_PATH}")
    print(f"Pages: {len(doc)}")

    seen = set()
    for page_index in range(len(doc)):
        page = doc[page_index]
        print(f"\n=== Page {page_index + 1} ===")

        for font_info in page.get_fonts(full=True):
            xref = font_info[0]
            if xref in seen:
                continue
            seen.add(xref)

            fontname, ext, ftype, data = doc.extract_font(xref)
            print(f"XREF: {xref}")
            print(f"  PDF font name: {fontname}")
            print(f"  Extension: {ext}")
            print(f"  Type: {ftype}")
            print(f"  Embedded bytes: {len(data) if data else 0}")
            if data:
                for name in _read_font_names(data):
                    print(f"  Name: {name!r}")


if __name__ == "__main__":
    main()
