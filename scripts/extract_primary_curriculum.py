#!/usr/bin/env python3
"""Extract the official Andalusian Primary curriculum tables into browser data.

Usage: extract_primary_curriculum.py INPUT_PDF OUTPUT_JS
The source is the signed BOJA PDF identified by CVE 00284747.
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber


SOURCE_URL = "https://www.juntadeandalucia.es/eboja/2023/104/BOJA23-104-00208-9731-01_00284747.pdf"
SUBJECTS = {
    "Conocimiento del Medio Natural, Social y Cultural": ("medio", "CMN", range(30, 38)),
    "Educación Artística": ("artistica", "EAR", range(56, 61)),
    "Educación Física": ("fisica", "EFI", range(71, 76)),
    "Educación en Valores Cívicos y Éticos": ("valores", "VCE", range(87, 90)),
    "Lengua Castellana y Literatura": ("lengua", "LCL", range(97, 103)),
    "Lengua Extranjera": ("lengua_extranjera", "LEX", range(122, 126)),
    "Matemáticas": ("mates", "MAT", range(140, 150)),
}
CYCLE_NUMBER = {"Primer": "1", "Segundo": "2", "Tercer": "3"}
CRITERIA_PAGE_RANGES = {
    ("medio", "1"): (38, 43), ("medio", "2"): (43, 48), ("medio", "3"): (48, 54),
    ("artistica", "1"): (61, 63), ("artistica", "2"): (63, 65), ("artistica", "3"): (65, 67),
    ("fisica", "1"): (76, 78), ("fisica", "2"): (79, 82), ("fisica", "3"): (82, 85),
    ("valores", "3"): (90, 92),
    ("lengua", "1"): (103, 107), ("lengua", "2"): (107, 112), ("lengua", "3"): (112, 118),
    ("lengua_extranjera", "1"): (126, 129), ("lengua_extranjera", "2"): (129, 132), ("lengua_extranjera", "3"): (132, 136),
    ("mates", "1"): (150, 153), ("mates", "2"): (153, 156), ("mates", "3"): (156, 164),
}


def clean(value):
    if not value:
        return ""
    value = value.replace("\u00ad", "")
    value = re.sub(r"\b([A-Z])\s+([A-Z])\s+([A-Z])(?=\s*\.)", r"\1\2\3", value)
    value = re.sub(r"-\s*\n\s*(?=[a-záéíóúñ])", "", value)
    value = re.sub(r"\s*\n\s*", " ", value)
    value = re.sub(r"\b([A-Z]{2,5})\s+\.", r"\1.", value)
    value = re.sub(r"\.\s+(?=\d|[A-Z]\.)", ".", value)
    value = re.sub(r"(?<=[a-záéíóúñ0-9])\.(?=[A-ZÁÉÍÓÚÑ])", ". ", value)
    value = re.sub(r",(?=[A-ZÁÉÍÓÚÑ])", ", ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def split_numbered(text, pattern):
    text = clean(text)
    matches = list(re.finditer(pattern, text))
    items = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        code = match.group(1).rstrip(".")
        body = text[match.end():end].strip(" .")
        if body:
            items.append({"code": code, "text": body})
    return items


def extract_sabers(pdf, page_indexes, cycle_count):
    columns = [""] * cycle_count
    pages = []
    for page_index in page_indexes:
        page = pdf.pages[page_index]
        if cycle_count == 1:
            columns[0] += "\n" + (page.extract_text() or "")
            pages.append(page_index + 1)
            continue
        for table in page.extract_tables():
            if not table or not table[0] or len(table[0]) != cycle_count:
                continue
            pages.append(page_index + 1)
            for row in table:
                for col in range(cycle_count):
                    columns[col] += "\n" + (row[col] or "")
    result = {}
    code_pattern = re.compile(r"\b([A-Z]{2,5}\s*\.\s*\d\s*\.\s*[A-Z]\s*\.\s*(?:\d+\s*\.){1,3})")
    for col, text in enumerate(columns):
        normalized = re.sub(r"\s*\.\s*", ".", clean(text))
        # Valores shares its last source page with the following assessment
        # table. Stop before that table so it cannot leak into the last saber.
        if cycle_count == 1:
            normalized = normalized.split("Educación en Valores Cívicos y Éticos (Tercer Ciclo)", 1)[0]
        normalized = re.sub(r"\b([A-Z]{2,5}\.\d\.[A-Z])(?=\d)", r"\1.", normalized)
        matches = list(code_pattern.finditer(normalized))
        entries = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            code = re.sub(r"\s+", "", match.group(1)).rstrip(".")
            body = clean(normalized[match.end():end]).strip(" .")
            if cycle_count == 1:
                body = body.split("Depósito Legal:", 1)[0].strip(" .")
            body = re.sub(r"\s*[A-Z]\.\s*[A-ZÁÉÍÓÚÑ][^.]{2,120}$", "", body).strip(" .")
            if body and not any(x["code"] == code for x in entries):
                entries.append({"code": code, "text": body})
        result[str(col + 1 if cycle_count == 3 else 3)] = entries
    return result, sorted(set(pages))


def extract_criteria(pdf):
    result = {}
    active = None
    active_cols = 0
    buffers = {}
    page_sets = {}
    title_pattern = re.compile(r"^(.*?) \((Primer|Segundo|Tercer) Ciclo\)$")

    column_counts = {}
    for page_index, page in enumerate(pdf.pages[:164]):
        for table in page.extract_tables():
            if not table or not table[0]:
                continue
            first = clean(table[0][0])
            title_match = title_pattern.match(first)
            start_row = 0
            if title_match and title_match.group(1) in SUBJECTS:
                subject_name, cycle_name = title_match.groups()
                subject_id = SUBJECTS[subject_name][0]
                cycle = CYCLE_NUMBER[cycle_name]
                active = (subject_id, cycle)
                active_cols = len(table[0])
                buffers.setdefault(active, ["", "", "", ""])
                column_counts[active] = active_cols
                page_sets.setdefault(active, set()).add(page_index + 1)
                start_row = 2
            elif active and len(table[0]) == active_cols and CRITERIA_PAGE_RANGES[active][0] <= page_index + 1 <= CRITERIA_PAGE_RANGES[active][1]:
                page_sets[active].add(page_index + 1)
            else:
                continue

            for row in table[start_row:]:
                if len(row) != active_cols:
                    continue
                for col, value in enumerate(row):
                    buffers[active][col] += "\n" + (value or "")

    for subject_name, (subject_id, _prefix, _pages) in SUBJECTS.items():
        result[subject_id] = {"title": subject_name, "cycles": {}}
    for (subject_id, cycle), cols in buffers.items():
        competencies = split_numbered(cols[0], r"(\d+)\.\s+(?=[A-ZÁÉÍÓÚÑ])")
        criteria_pattern = r"(\d+\.\d+\.(?:a|b)?\.?)\s*"
        grades = {}
        if column_counts[(subject_id, cycle)] == 4:
            grades[str((int(cycle) - 1) * 2 + 1)] = split_numbered(cols[1], criteria_pattern)
            grades[str((int(cycle) - 1) * 2 + 2)] = split_numbered(cols[2], criteria_pattern)
            reference_text = cols[3]
        else:
            grades["6"] = split_numbered(cols[1], criteria_pattern)
            reference_text = cols[2]
        saber_refs = sorted(set(re.sub(r"\s+", "", code).rstrip(".") for code in re.findall(r"\b[A-Z]{2,5}\s*\.\s*\d\s*\.\s*[A-Z]\s*\.\s*(?:\d+\s*\.){1,3}", reference_text)))
        result[subject_id]["cycles"][cycle] = {
            "competencies": competencies,
            "criteriaByGrade": grades,
            "saberReferences": saber_refs,
            "officialPdfPages": sorted(page_sets[(subject_id, cycle)]),
        }
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: extract_primary_curriculum.py INPUT_PDF OUTPUT_JS")
    source_path, output_path = Path(sys.argv[1]), Path(sys.argv[2])
    with pdfplumber.open(source_path) as pdf:
        subjects = extract_criteria(pdf)
        for subject_name, (subject_id, _prefix, page_indexes) in SUBJECTS.items():
            cycle_count = 1 if subject_id == "valores" else 3
            sabers, pages = extract_sabers(pdf, page_indexes, cycle_count)
            for cycle, entries in sabers.items():
                if cycle in subjects[subject_id]["cycles"]:
                    subjects[subject_id]["cycles"][cycle]["sabers"] = entries
                    subjects[subject_id]["cycles"][cycle]["officialSaberPages"] = pages

    payload = {
        "schemaVersion": "1.0.0",
        "stage": "Primaria",
        "source": {
            "title": "Orden de 30 de mayo de 2023 - currículo de Educación Primaria en Andalucía",
            "url": SOURCE_URL,
            "cve": "00284747",
            "annex": "Anexo II",
            "verifiedOn": "12/09/2026",
            "note": "Texto oficial normalizado para lectura digital; consérvese el PDF firmado como fuente auténtica.",
        },
        "subjects": subjects,
        "aliases": {"ingles": "lengua_extranjera", "frances": "lengua_extranjera"},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("window.PRIMARY_CURRICULUM = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
