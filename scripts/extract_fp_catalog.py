#!/usr/bin/env python3
"""Build a guided Andalusian FP catalogue from the Junta's official title pages."""

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path


BASE = "https://www.juntadeandalucia.es"
CATALOGUES = {
    "basico": "https://www.juntadeandalucia.es/educacion/portales/web/formacion-profesional-andaluza/grado-basico-catalogo-de-titulos",
    "medio": "https://www.juntadeandalucia.es/educacion/portales/web/formacion-profesional-andaluza/grado-medio-catalogo-de-titulos",
    "superior": "https://www.juntadeandalucia.es/educacion/portales/web/formacion-profesional-andaluza/grado-superior-catalogo-de-titulos",
    "especializacion": "https://www.juntadeandalucia.es/educacion/portales/web/formacion-profesional-andaluza/cursos-de-especializacion-catalogo-de-titulos",
}


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


class CaptureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = None
        self.buffer = []

    @staticmethod
    def attrs_dict(attrs):
        return dict(attrs)

    def begin(self, kind, meta=None):
        self.capture = (kind, meta)
        self.buffer = []

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)


class CatalogueParser(CaptureParser):
    def __init__(self):
        super().__init__()
        self.family = ""
        self.titles = []

    def handle_starttag(self, tag, attrs):
        values = self.attrs_dict(attrs)
        classes = values.get("class", "")
        if tag == "h3" and "catalogo-titulos-fp__familia-titulo" in classes:
            self.begin("family")
        elif tag == "a" and "catalogo-titulos-fp__enlace" in classes:
            self.begin("title", values.get("href", ""))

    def handle_endtag(self, tag):
        if not self.capture:
            return
        kind, meta = self.capture
        if (kind == "family" and tag == "h3") or (kind == "title" and tag == "a"):
            value = clean("".join(self.buffer))
            if kind == "family":
                self.family = value
            elif value and self.family and "idTitulo=" in meta:
                url = urllib.parse.urljoin(BASE, html.unescape(meta))
                title_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("idTitulo", [""])[0]
                self.titles.append({"id": title_id, "title": value, "family": self.family, "url": url})
            self.capture = None
            self.buffer = []


class DetailParser(CaptureParser):
    def __init__(self):
        super().__init__()
        self.course = "unico"
        self.in_module_table = 0
        self.in_row = False
        self.cells = []
        self.modules = {}
        self.norms = []
        self.duration = ""

    def handle_starttag(self, tag, attrs):
        values = self.attrs_dict(attrs)
        classes = values.get("class", "")
        if tag == "h3" and "detalle-titulo-fp__curso-title" in classes:
            self.begin("course")
        elif tag == "table" and "detalle-titulo-fp__tabla-modulos" in classes:
            self.in_module_table += 1
        elif self.in_module_table and tag == "tr":
            self.in_row = True
            self.cells = []
        elif self.in_row and tag == "td":
            self.begin("cell")
        elif tag == "p" and "detalle-titulo-fp__text" in classes:
            self.begin("paragraph")
        elif tag == "a" and "detalle-titulo-fp__doc-link" in classes:
            self.begin("norm-link")

    def handle_endtag(self, tag):
        if self.capture:
            kind, _ = self.capture
            if kind == "course" and tag == "h3":
                label = clean("".join(self.buffer)).lower()
                self.course = "1" if "primer" in label else "2" if "segundo" in label else "unico"
                self.capture = None
                self.buffer = []
            elif kind == "cell" and tag == "td":
                self.cells.append(clean("".join(self.buffer)))
                self.capture = None
                self.buffer = []
            elif kind == "paragraph" and tag == "p":
                value = clean("".join(self.buffer))
                if value.lower().startswith("duración:"):
                    self.duration = value.split(":", 1)[1].strip()
                if value.lower().startswith("normativa"):
                    self.norms.append(value)
                self.capture = None
                self.buffer = []
            elif kind == "norm-link" and tag == "a":
                value = clean("".join(self.buffer))
                if value and value not in self.norms:
                    self.norms.append(value)
                self.capture = None
                self.buffer = []
        if self.in_row and tag == "tr":
            if len(self.cells) >= 2 and self.cells[0].lower() != "código":
                module = {"code": self.cells[0], "name": self.cells[1]}
                if len(self.cells) >= 3 and self.cells[2]:
                    module["hours"] = self.cells[2]
                self.modules.setdefault(self.course, []).append(module)
            self.in_row = False
            self.cells = []
        elif self.in_module_table and tag == "table":
            self.in_module_table -= 1


def parse_catalogue(path):
    parser = CatalogueParser()
    parser.feed(Path(path).read_text(encoding="utf-8"))
    return parser.titles


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "PromptDocentes curriculum indexer/1.0"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as error:
            last_error = error
            time.sleep(1 + attempt)
    raise last_error


def enrich(title):
    parser = DetailParser()
    parser.feed(fetch(title["url"]))
    result = dict(title)
    result["modules"] = parser.modules
    result["norms"] = parser.norms
    if parser.duration:
        result["duration"] = parser.duration
    return result


def main():
    if len(sys.argv) != 6:
        raise SystemExit("Usage: extract_fp_catalog.py BASIC_HTML MEDIUM_HTML HIGHER_HTML SPECIALISATION_HTML OUTPUT_JS")
    inputs = dict(zip(CATALOGUES, sys.argv[1:5]))
    titles = []
    for grade, path in inputs.items():
        for title in parse_catalogue(path):
            title["grade"] = grade
            titles.append(title)

    enriched, failures = [], []
    with ThreadPoolExecutor(max_workers=12) as executor:
        pending = {executor.submit(enrich, title): title for title in titles}
        for future in as_completed(pending):
            title = pending[future]
            try:
                enriched.append(future.result())
            except Exception as error:
                failures.append({"id": title["id"], "title": title["title"], "error": str(error)})

    if failures:
        raise SystemExit("No se pudieron leer fichas oficiales: " + json.dumps(failures, ensure_ascii=False))

    grades = {}
    for grade in CATALOGUES:
        grade_titles = sorted((item for item in enriched if item["grade"] == grade), key=lambda item: (item["family"], item["title"]))
        families = {}
        for item in grade_titles:
            families.setdefault(item["family"], []).append(item)
        grades[grade] = {"catalogueUrl": CATALOGUES[grade], "families": families}

    payload = {
        "schemaVersion": "1.0.0",
        "stage": "Formación Profesional",
        "verifiedOn": "14/09/2026",
        "source": {
            "title": "Catálogo oficial de títulos de Formación Profesional Andaluza",
            "catalogueUrls": CATALOGUES,
            "orderingUrl": "https://www.juntadeandalucia.es/boja/2025/217901/1.html",
            "evaluationUrl": "https://www.juntadeandalucia.es/boja/2025/180/c01/1",
            "note": "El catálogo identifica títulos, cursos, módulos, horas y normativa publicada en cada ficha. Los resultados de aprendizaje y criterios deben verificarse en la norma específica del título y módulo.",
        },
        "grades": grades,
    }
    output = Path(sys.argv[5])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("window.FP_CATALOG = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    counts = {grade: sum(len(items) for items in data["families"].values()) for grade, data in grades.items()}
    print(json.dumps({"titles": sum(counts.values()), "byGrade": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
