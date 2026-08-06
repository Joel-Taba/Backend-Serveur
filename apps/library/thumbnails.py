"""
Génération de miniatures — équivalent Python de lib/thumbnail.ts côté
frontend. Les miniatures sont mises en cache sur disque sous
media/_thumbnails/, à l'écart des fichiers sources.

Dépendances optionnelles : Pillow (images), PyMuPDF/`fitz` (PDF). Si
PyMuPDF n'est pas installé, les miniatures de PDF sont simplement
indisponibles (retour None) plutôt que de faire planter la requête —
mêmes garanties que côté frontend, où l'absence de pdftoppm désactive
juste les miniatures.
"""
import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from django.conf import settings

from .models import Document

CACHE_DIR = settings.MEDIA_ROOT / "_thumbnails"

CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}


def get_thumbnail_path(document: Document, page: int = 1) -> Path | None:
    # JSON n'a pas d'aperçu visuel possible ; la vidéo en aurait un (une
    # image extraite d'une frame) mais ça suppose ffmpeg, une dépendance
    # non installée ici — indisponible plutôt que de faire planter la
    # requête, même logique que pour les PDF sans PyMuPDF.
    if document.doc_type in ("json", "video"):
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target_page = max(1, page) if document.doc_type == "pdf" else 1
    suffix = f"-p{target_page}" if target_page > 1 else ""
    mtime = int(document.updated_at.timestamp())
    cache_path = CACHE_DIR / f"{document.pk}-{mtime}{suffix}.png"

    if cache_path.exists():
        return cache_path

    try:
        if document.doc_type == "image":
            return _generate_image_thumbnail(document, cache_path)
        if document.doc_type == "pdf":
            return _generate_pdf_thumbnail(document, cache_path, target_page)
        if document.doc_type == "epub":
            return _generate_epub_thumbnail(document, cache_path)
    except Exception:
        return None
    return None


def _generate_image_thumbnail(document: Document, cache_path: Path) -> Path | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    with document.file.open("rb") as handle:
        image = Image.open(handle)
        image.load()
    width = settings.THUMBNAIL_COVER_WIDTH
    ratio = width / image.width if image.width else 1
    image = image.resize((width, max(1, int(image.height * ratio))))
    image.convert("RGB").save(cache_path, "PNG")
    return cache_path


def _generate_pdf_thumbnail(document: Document, cache_path: Path, page: int) -> Path | None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    with document.file.open("rb") as handle:
        data = handle.read()

    pdf = fitz.open(stream=data, filetype="pdf")
    try:
        if page > pdf.page_count:
            return None
        pdf_page = pdf.load_page(page - 1)
        width = settings.THUMBNAIL_COVER_WIDTH if page == 1 else settings.THUMBNAIL_PAGE_WIDTH
        zoom = width / pdf_page.rect.width if pdf_page.rect.width else 1
        pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pixmap.save(str(cache_path))
    finally:
        pdf.close()
    return cache_path


def _find_epub_cover_href(opf_xml: bytes) -> str | None:
    root = ET.fromstring(opf_xml)

    cover_id = None
    for meta in root.findall(".//opf:metadata/opf:meta", OPF_NS):
        if meta.attrib.get("name") == "cover":
            cover_id = meta.attrib.get("content")
            break

    items = root.findall(".//opf:manifest/opf:item", OPF_NS)

    if cover_id:
        for item in items:
            if item.attrib.get("id") == cover_id:
                return item.attrib.get("href")

    for item in items:
        if "cover-image" in item.attrib.get("properties", ""):
            return item.attrib.get("href")

    return None


def _generate_epub_thumbnail(document: Document, cache_path: Path) -> Path | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    with document.file.open("rb") as handle:
        with zipfile.ZipFile(handle) as archive:
            container_xml = archive.read("META-INF/container.xml")
            opf_path = ET.fromstring(container_xml).find(".//c:rootfile", CONTAINER_NS).attrib["full-path"]
            opf_dir = "/".join(opf_path.split("/")[:-1])
            opf_xml = archive.read(opf_path)

            cover_href = _find_epub_cover_href(opf_xml)
            if not cover_href:
                return None

            cover_path = f"{opf_dir}/{cover_href}" if opf_dir else cover_href
            cover_bytes = archive.read(cover_path)

    image = Image.open(io.BytesIO(cover_bytes))
    width = settings.THUMBNAIL_COVER_WIDTH
    ratio = width / image.width if image.width else 1
    image = image.resize((width, max(1, int(image.height * ratio))))
    image.convert("RGB").save(cache_path, "PNG")
    return cache_path
