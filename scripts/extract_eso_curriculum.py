#!/usr/bin/env python3
"""Extract the official Andalusian ESO curriculum into browser data.

Usage: extract_eso_curriculum.py PDF_PART_1 PDF_PART_2 OUTPUT_JS
The source is the two-part signed BOJA disposition identified by CVE 00284752.
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber


SOURCE_URLS = [
    "https://www.juntadeandalucia.es/eboja/2023/104/BOJA23-104-00289-9727-01_00284752.pdf",
    "https://www.juntadeandalucia.es/eboja/2023/104/BOJA23-104-00246-9727-02_00284752.pdf",
]

# Page numbers are one-based and refer to each signed PDF part.
SUBJECTS = [
    ("bio", "Biología y Geología", "Anexo II", [(0, 50, 68)]),
    ("digitalizacion", "Digitalización", "Anexo II", [(0, 68, 73)]),
    ("economia", "Economía y Emprendimiento", "Anexo II", [(0, 73, 81)]),
    ("fisica", "Educación Física", "Anexo II", [(0, 81, 104)]),
    ("plastica", "Educación Plástica, Visual y Audiovisual", "Anexo II", [(0, 104, 121)]),
    ("valores", "Educación en Valores Cívicos y Éticos", "Anexo II", [(0, 116, 123)]),
    ("expresion", "Expresión Artística", "Anexo II", [(0, 123, 128)]),
    ("fisqui", "Física y Química", "Anexo II", [(0, 128, 146)]),
    ("orientacion", "Formación y Orientación Personal y Profesional", "Anexo II", [(0, 146, 153)]),
    ("geohis", "Geografía e Historia", "Anexo II", [(0, 153, 183)]),
    ("latin", "Latín", "Anexo II", [(0, 183, 191)]),
    ("lengua", "Lengua Castellana y Literatura", "Anexo II", [(0, 191, 222)]),
    ("lengua_extranjera", "Lengua Extranjera", "Anexo II", [(0, 222, 245)]),
    ("mates", "Matemáticas", "Anexo II", [(0, 245, 269)]),
    ("mates_a", "Matemáticas A", "Anexo II", [(0, 269, 274)]),
    ("mates_b", "Matemáticas B", "Anexo II", [(0, 274, 279)]),
    ("musica", "Música", "Anexo II", [(0, 279, 288)]),
    ("tecnologia", "Tecnología", "Anexo II", [(0, 288, 289), (1, 1, 6)]),
    ("tecnologia_digitalizacion", "Tecnología y Digitalización", "Anexo II", [(1, 6, 17)]),
    ("ampliacion_clasica", "Ampliación de Cultura Clásica", "Anexo III", [(1, 17, 26)]),
    ("aprendizaje_social", "Aprendizaje Social y Emocional", "Anexo III", [(1, 26, 33)]),
    ("artes_escenicas", "Artes Escénicas y Danza", "Anexo III", [(1, 33, 39)]),
    ("computacion", "Computación y Robótica", "Anexo III", [(1, 39, 50)]),
    ("cultura_cientifica", "Cultura Científica", "Anexo III", [(1, 50, 57)]),
    ("cultura_clasica", "Cultura Clásica", "Anexo III", [(1, 57, 71)]),
    ("flamenco", "Cultura del Flamenco", "Anexo III", [(1, 71, 75)]),
    ("dibujo_tecnico", "Dibujo Técnico", "Anexo III", [(1, 75, 80)]),
    ("filosofia", "Filosofía", "Anexo III", [(1, 80, 88)]),
    ("filosofia_argumentacion", "Filosofía y Argumentación", "Anexo III", [(1, 88, 94)]),
    ("emprendimiento", "Iniciación a la Actividad Emprendedora y Empresarial", "Anexo III", [(1, 94, 102)]),
    ("oratoria", "Oratoria y Debate", "Anexo III", [(1, 102, 114)]),
    ("proyecto_plastica", "Proyecto de Educación Plástica y Audiovisual", "Anexo III", [(1, 114, 120)]),
    ("ambito-cient", "Ámbito Científico-Tecnológico", "Anexo IV", [(1, 120, 142)]),
    ("ambito-ling", "Ámbito Lingüístico y Social", "Anexo IV", [(1, 142, 165)]),
]

PREFIXES = {
    "bio": {"BYG"}, "digitalizacion": {"DIG"}, "economia": {"ECE"}, "fisica": {"EFI"},
    "plastica": {"EPV"}, "valores": {"VCE"}, "expresion": {"EAR"}, "fisqui": {"FYQ"},
    "orientacion": {"FOP"}, "geohis": {"GEH"}, "latin": {"LAT"}, "lengua": {"LCL"},
    "lengua_extranjera": {"LEX"}, "mates": {"MAT"}, "mates_a": {"MAA"}, "mates_b": {"MAB"},
    "musica": {"MUS"}, "tecnologia": {"TEC"}, "tecnologia_digitalizacion": {"TYD"},
    "ampliacion_clasica": {"ACC"}, "aprendizaje_social": {"ASE"}, "artes_escenicas": {"AED"},
    "computacion": {"CYR"}, "cultura_cientifica": {"CCI"}, "cultura_clasica": {"CCL"},
    "flamenco": {"CF"}, "dibujo_tecnico": {"DBT"}, "filosofia": {"FIL"},
    "filosofia_argumentacion": {"FYA"}, "emprendimiento": {"IAE"}, "oratoria": {"OYD"},
    "proyecto_plastica": {"PEPA"}, "ambito-cient": {"ACT"}, "ambito-ling": {"ALS"},
}

SABER_CODE = re.compile(r"\b([A-ZÁÉÍÓÚÑ]{2,8})\s*\.\s*([1-4])\s*\.\s*([A-Z])\s*\.\s*((?:\d+\s*\.?){1,4})")
CRITERION_CODE = re.compile(r"(?<!\d)(\d+\s*\.\s*\d+(?:\s*\.\s*[ab])?\s*\.?)\s*")
COMPETENCY_CODE = re.compile(r"(?<!\d)(\d+)\s*\.\s*(?=[A-ZÁÉÍÓÚÑ])")


def clean(value):
    if not value:
        return ""
    value = value.replace("\u00ad", "")
    value = re.sub(r"-\s*\n\s*(?=[a-záéíóúñ])", "", value)
    value = re.sub(r"\s*\n\s*", " ", value)
    value = re.sub(r"\b([A-ZÁÉÍÓÚÑ]{2,8})\s+\.", r"\1.", value)
    value = re.sub(r"\.\s+(?=\d|[A-ZÁÉÍÓÚÑ]+\.)", ".", value)
    value = re.sub(r"(?<=[a-záéíóúñ0-9])\.(?=[A-ZÁÉÍÓÚÑ])", ". ", value)
    value = re.sub(r",(?=[A-ZÁÉÍÓÚÑ])", ", ", value)
    value = re.sub(r"\b([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{5,})\s+(s|ose)\b", r"\1\2", value)
    value = re.sub(r"\b([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{5,})\s+([aeo])(?=[,.;:])", r"\1\2", value)
    return re.sub(r"\s+", " ", value).strip()


def normalise_code(match):
    return re.sub(r"\s+", "", match.group(0)).rstrip(".")


def split_numbered(text, pattern):
    text = clean(text)
    matches = list(pattern.finditer(text))
    items = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        code = re.sub(r"\s+", "", match.group(1)).rstrip(".")
        body = clean(text[match.end():end]).strip(" .")
        body = re.split(r"\b(?:CCL|CP|STEM|CD|CPSAA|CC|CE|CCEC)\d", body, maxsplit=1)[0].strip(" .,;")
        if body and not any(item["code"] == code for item in items):
            items.append({"code": code, "text": body})
    return items


def parse_sabers(text):
    text = clean(text)
    matches = list(SABER_CODE.finditer(text))
    entries = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        code = normalise_code(match)
        body = clean(text[match.end():end]).strip(" .")
        body = body.split("Depósito Legal:", 1)[0].strip(" .")
        body = re.sub(r"\s*[A-Z]\s*\.\s*[A-ZÁÉÍÓÚÑ][^.]{2,140}$", "", body).strip(" .")
        if body:
            entries.append({"code": code, "text": body})
    return entries


def table_text(table):
    return " ".join(clean(cell) for row in table for cell in row if cell)


def is_alignment_header(table):
    head = " ".join(clean(cell) for row in table[:3] for cell in row if cell).lower()
    return len(table[0]) >= 3 and len(table[0]) % 2 == 1 and "criterios de evaluación" in head and "saberes" in head


def is_saber_header(table):
    head = " ".join(clean(cell) for row in table[:2] for cell in row if cell)
    return len(table[0]) <= 4 and bool(re.search(r"\b(?:PRIMER|SEGUNDO|TERCER|CUARTO)\s+CURSO\b", head.upper())) and not is_alignment_header(table)


def extract_subject(pdfs, config):
    subject_id, title, annex, ranges = config
    allowed_prefixes = PREFIXES[subject_id]
    tables = []
    page_texts = []
    official_pages = []
    for part, start, end in ranges:
        for page_number in range(start, end + 1):
            page = pdfs[part].pages[page_number - 1]
            page_texts.append(page.extract_text() or "")
            official_pages.append({"part": part + 1, "page": page_number})
            for table in page.extract_tables():
                if table and table[0]:
                    tables.append((part, page_number, table))

    # The prose presentation of each competency is wider and cleaner than the
    # repeated narrow table column. Prefer it whenever it can be identified.
    joined_pages = "\n".join(page_texts)
    competency_master = []
    for title_match in re.finditer(re.escape(title), joined_pages, re.IGNORECASE):
        start = joined_pages.find("Competencias específicas", title_match.end())
        if start < 0 or start - title_match.end() > 4000:
            continue
        end = joined_pages.find("Saberes básicos", start)
        if end < 0:
            continue
        candidate = split_numbered(joined_pages[start:end], COMPETENCY_CODE)
        for item in candidate:
            item["text"] = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])", item["text"], maxsplit=1)[0]
        if len(candidate) > len(competency_master):
            competency_master = candidate

    saber_by_code = {}
    direct_saber_by_code = {}
    for _, _, table in tables:
        for row in table:
            for cell in row:
                for item in parse_sabers(cell or ""):
                    if item["code"].split(".")[0] not in allowed_prefixes:
                        continue
                    if re.search(r"Competencias(?:\s+\w+){0,6}\s+Saberes\s+Saberes", item["text"], re.IGNORECASE):
                        continue
                    if len(item["text"]) > len(direct_saber_by_code.get(item["code"], {}).get("text", "")):
                        direct_saber_by_code[item["code"]] = item
    groups = []
    active = None
    mode = None
    saber_buffers = {}
    saber_column_grades = {}
    for part, page_number, table in tables:
        width = len(table[0])
        if is_alignment_header(table):
            active = {
                "width": width,
                "columns": [""] * width,
                "pages": [],
                "header": table_text(table[:3]),
                "headerColumns": [" ".join(clean(row[col]) for row in table[:3] if len(row) == width) for col in range(width)],
            }
            groups.append(active)
            mode = "alignment"
        elif is_saber_header(table):
            mode = "sabers"
            active = None
            saber_column_grades = {}
            for col in range(width):
                column_text = " ".join((row[col] or "") for row in table if len(row) == width)
                matches = [match for match in SABER_CODE.finditer(column_text) if match.group(1) in allowed_prefixes]
                if matches:
                    saber_column_grades[col] = matches[0].group(2)
        if mode == "sabers":
            for row in table:
                for col, cell in enumerate(row):
                    if col in saber_column_grades:
                        grade = saber_column_grades[col]
                        saber_buffers[grade] = saber_buffers.get(grade, "") + "\n" + (cell or "")
                    for item in parse_sabers(cell or ""):
                        if item["code"].split(".")[0] not in allowed_prefixes:
                            continue
                        if len(item["text"]) > len(saber_by_code.get(item["code"], {}).get("text", "")):
                            saber_by_code[item["code"]] = item
            continue
        elif mode != "alignment" or not active or width != active["width"]:
            continue
        active["pages"].append({"part": part + 1, "page": page_number})
        for row in table:
            if len(row) != width:
                continue
            for col, cell in enumerate(row):
                active["columns"][col] += "\n" + (cell or "")

    for text in saber_buffers.values():
        for item in parse_sabers(text):
            if item["code"].split(".")[0] not in allowed_prefixes:
                continue
            if item["code"] not in saber_by_code:
                saber_by_code[item["code"]] = item

    # Single-column saber lists have no table borders. Parse only the pages
    # between their explicit "Saberes básicos" heading and the next alignment.
    raw_saber_mode = False
    for part, start, end in ranges:
        for page_number in range(start, end + 1):
            page = pdfs[part].pages[page_number - 1]
            text = page.extract_text() or ""
            page_tables = [table for p, n, table in tables if p == part and n == page_number]
            page_has_alignment = any(is_alignment_header(table) for table in page_tables)
            if re.search(r"(?m)^Saberes básicos(?:[^\n]*)\.\s*$", text):
                raw_saber_mode = True
            if raw_saber_mode:
                source_text = text
                if page_has_alignment:
                    marker = "\n" + title + "\n"
                    if marker in source_text:
                        source_text = source_text.rsplit(marker, 1)[0]
                    else:
                        source_text = source_text.split("\nCompetencias específicas", 1)[0]
                for item in parse_sabers(source_text):
                    if item["code"].split(".")[0] not in allowed_prefixes:
                        continue
                    if item["code"] not in saber_by_code:
                        saber_by_code[item["code"]] = item
            if page_has_alignment:
                raw_saber_mode = False

    # In two-course annexes, the final saber cell can share an extracted PDF
    # table with the following competency-alignment header. Stop the saber at
    # the repeated subject title instead of leaking that next table into it.
    repeated_title = re.compile(rf"\s+{re.escape(title)}\s+I\b", re.IGNORECASE)
    for item in saber_by_code.values():
        item["text"] = repeated_title.split(item["text"], maxsplit=1)[0].strip(" .")
    saber_by_code.update(direct_saber_by_code)

    grades = {}
    for group in groups:
        width = group["width"]
        if width < 3 or width % 2 == 0:
            continue
        table_competencies = split_numbered(group["columns"][0], COMPETENCY_CODE)
        master_by_code = {item["code"]: item for item in competency_master}
        competencies = [master_by_code.get(item["code"], item) for item in table_competencies]
        for criterion_col in range(1, width, 2):
            reference_col = criterion_col + 1
            refs = sorted(set(normalise_code(match) for match in SABER_CODE.finditer(group["columns"][reference_col]) if match.group(1) in allowed_prefixes))
            header_grade = re.search(r"\b([1-4])\s*º", group["headerColumns"][criterion_col])
            grade_counts = {grade: sum(code.split(".")[1] == grade for code in refs) for grade in "1234"}
            grade = header_grade.group(1) if header_grade else max(grade_counts, key=grade_counts.get, default="")
            if not grade or not grade_counts.get(grade):
                continue
            criteria = split_numbered(group["columns"][criterion_col], CRITERION_CODE)
            if not criteria:
                continue
            entry = grades.setdefault(grade, {"competencies": [], "criteria": [], "sabers": [], "saberReferences": [], "officialPdfPages": []})
            for key, values in (("competencies", competencies), ("criteria", criteria)):
                known = {item["code"] for item in entry[key]}
                entry[key].extend(item for item in values if item["code"] not in known)
            entry["saberReferences"] = sorted(set(entry["saberReferences"] + refs))
            entry["officialPdfPages"] = sorted(group["pages"], key=lambda item: (item["part"], item["page"]))

    for grade, entry in grades.items():
        referenced = set(entry["saberReferences"])
        entry["sabers"] = sorted(
            (item for code, item in saber_by_code.items() if code.split(".")[1] == grade or code in referenced),
            key=lambda item: item["code"],
        )

    return {"title": title, "annex": annex, "grades": grades, "officialPdfPages": official_pages}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: extract_eso_curriculum.py PDF_PART_1 PDF_PART_2 OUTPUT_JS")
    source_paths = [Path(sys.argv[1]), Path(sys.argv[2])]
    output_path = Path(sys.argv[3])
    pdfs = [pdfplumber.open(path) for path in source_paths]
    try:
        subjects = {config[0]: extract_subject(pdfs, config) for config in SUBJECTS}
    finally:
        for pdf in pdfs:
            pdf.close()

    source_anomalies = []
    anomaly_note = (
        "El código aparece en las tablas de vinculación, pero no figura definido con esa misma "
        "codificación en la tabla de saberes del documento oficial. No debe completarse ni inventarse."
    )
    for subject_id, subject in subjects.items():
        defined_codes = {
            item["code"]
            for grade_data in subject["grades"].values()
            for item in grade_data["sabers"]
        }
        for grade, grade_data in subject["grades"].items():
            for code in grade_data["saberReferences"]:
                if code not in defined_codes:
                    source_anomalies.append({
                        "subjectId": subject_id,
                        "grade": grade,
                        "code": code,
                        "note": anomaly_note,
                    })

    payload = {
        "schemaVersion": "1.0.0",
        "stage": "ESO",
        "source": {
            "title": "Orden de 30 de mayo de 2023 - currículo de Educación Secundaria Obligatoria en Andalucía",
            "urls": SOURCE_URLS,
            "cve": "00284752",
            "annexes": ["Anexo II", "Anexo III", "Anexo IV"],
            "verifiedOn": "13/09/2026",
            "note": "Texto oficial normalizado para lectura digital; consérvense los dos PDF firmados como fuente auténtica.",
        },
        "subjects": subjects,
        "aliases": {"ingles": "lengua_extranjera", "frances": "lengua_extranjera"},
        "sourceAnomalies": source_anomalies,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("window.ESO_CURRICULUM = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
