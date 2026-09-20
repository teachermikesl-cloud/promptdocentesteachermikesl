#!/usr/bin/env python3
"""Extract the official Andalusian Infant Education curriculum tables.

Usage: extract_infant_curriculum.py INPUT_PDF OUTPUT_JS
The source is the signed BOJA PDF identified by CVE 00284745.
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber


SOURCE_URL = "https://www.juntadeandalucia.es/boja/2023/104/BOJA23-104-00078-9729-01_00284745.pdf"
SUBJECTS = {
    "Crecimiento en Armonía": ("crecimiento", "CA", range(25, 28)),
    "Descubrimiento y Exploración del Entorno": ("entorno", "DEE", range(36, 39)),
    "Comunicación y Representación de la Realidad": ("comunicacion", "CRR", range(49, 53)),
}
TITLE_TO_ID = {title.lower(): data[0] for title, data in SUBJECTS.items()}
CYCLE_NUMBER = {"primer": "1", "segundo": "2"}


def clean(value):
    if not value:
        return ""
    value = value.replace("\u00ad", "")
    value = re.sub(r"-\s*\n\s*(?=[a-záéíóúñ])", "", value)
    value = re.sub(r"\s*\n\s*", " ", value)
    value = re.sub(r"\b([A-Z]{2,4})\s+\.", r"\1.", value)
    value = re.sub(r"\.\s+(?=\d|[A-Z]\.)", ".", value)
    value = re.sub(r"(?<=[a-záéíóúñ0-9])\.(?=[A-ZÁÉÍÓÚÑ])", ". ", value)
    value = re.sub(r",(?=[A-ZÁÉÍÓÚÑ])", ", ", value)
    return re.sub(r"\s+", " ", value).strip()


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


def extract_sabers(pdf, page_indexes):
    columns = ["", ""]
    pages = []
    for page_index in page_indexes:
        for table in pdf.pages[page_index].extract_tables():
            if not table or not table[0] or len(table[0]) != 2:
                continue
            pages.append(page_index + 1)
            for row in table:
                columns[0] += "\n" + (row[0] or "")
                columns[1] += "\n" + (row[1] or "")

    result = {}
    code_pattern = re.compile(r"\b([A-Z]{2,4}\s*\.\s*\d{2}\s*\.\s*[A-Z]\s*\.\s*\d{2}\s*\.?)")
    for col, text in enumerate(columns):
        normalized = re.sub(r"\s*\.\s*", ".", clean(text))
        matches = list(code_pattern.finditer(normalized))
        entries = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            code = re.sub(r"\s+", "", match.group(1)).rstrip(".")
            body = clean(normalized[match.end():end]).strip(" .")
            # Column extraction can append the following section heading to
            # the last knowledge item (for example "D.Interacción...").
            body = re.sub(r"\s+[A-I]\.(?=[A-ZÁÉÍÓÚÑ]).*$", "", body).strip(" .")
            if body and not any(item["code"] == code for item in entries):
                entries.append({"code": code, "text": body})
        result[str(col + 1)] = entries
    return result, sorted(set(pages))


def extract_criteria(pdf):
    result = {sid: {"title": title, "cycles": {}} for title, (sid, _prefix, _pages) in SUBJECTS.items()}
    buffers = {}
    page_sets = {}
    active = None
    title_pattern = re.compile(r"^(.*?) \((Primer|Segundo) ciclo\)$", re.I)

    for page_index in range(27, 58):
        for table in pdf.pages[page_index].extract_tables():
            if not table or not table[0] or len(table[0]) != 3:
                continue
            first = clean(table[0][0])
            title_match = title_pattern.match(first)
            start_row = 0
            if title_match:
                title, cycle_name = title_match.groups()
                subject_id = TITLE_TO_ID.get(title.lower())
                if not subject_id:
                    active = None
                    continue
                active = (subject_id, CYCLE_NUMBER[cycle_name.lower()])
                buffers.setdefault(active, ["", "", ""])
                page_sets.setdefault(active, set())
                start_row = 1
            if not active:
                continue
            page_sets[active].add(page_index + 1)
            for row in table[start_row:]:
                if len(row) != 3:
                    continue
                if clean(row[0]).lower() == "competencias específicas":
                    continue
                for col, value in enumerate(row):
                    buffers[active][col] += "\n" + (value or "")

    for (subject_id, cycle), cols in buffers.items():
        competencies = split_numbered(cols[0], r"(\d+)\.\s+(?=[A-ZÁÉÍÓÚÑ])")
        # Some official-table rows omit the full stop after the code (for
        # example 2.1 in second-cycle Growing in Harmony). Require the
        # following uppercase text instead of requiring that punctuation.
        criteria = split_numbered(cols[1], r"(?<!\d)(\d+\.\d+)\.?\s+(?=[A-ZÁÉÍÓÚÑ])")
        refs = re.findall(r"\b(?:CA|DEE|CRR)\s*\.\s*\d{2}\s*\.\s*[A-Z]\s*\.\s*\d{2}", cols[2])
        saber_refs = sorted(set(re.sub(r"\s+", "", code) for code in refs))
        result[subject_id]["cycles"][cycle] = {
            "competencies": competencies,
            "criteria": criteria,
            "saberReferences": saber_refs,
            "officialPdfPages": sorted(page_sets[(subject_id, cycle)]),
        }
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: extract_infant_curriculum.py INPUT_PDF OUTPUT_JS")
    source_path, output_path = Path(sys.argv[1]), Path(sys.argv[2])
    with pdfplumber.open(source_path) as pdf:
        subjects = extract_criteria(pdf)
        for _title, (subject_id, _prefix, page_indexes) in SUBJECTS.items():
            sabers, pages = extract_sabers(pdf, page_indexes)
            for cycle, entries in sabers.items():
                subjects[subject_id]["cycles"][cycle]["sabers"] = entries
                subjects[subject_id]["cycles"][cycle]["officialSaberPages"] = pages

    payload = {
        "schemaVersion": "1.0.0",
        "stage": "Infantil",
        "source": {
            "title": "Orden de 30 de mayo de 2023 - currículo de Educación Infantil en Andalucía",
            "url": SOURCE_URL,
            "cve": "00284745",
            "annex": "Anexo I",
            "verifiedOn": "20/09/2026",
            "note": "Texto oficial normalizado para lectura digital; consérvese el PDF firmado como fuente auténtica.",
        },
        "sourceAnomalies": [{
            "code": "CRR.02.H.04",
            "note": "El código aparece en la vinculación del criterio 3.7 del segundo ciclo, pero no figura definido en la tabla de saberes básicos del área. No debe completarse ni inventarse.",
        }],
        "subjects": subjects,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("window.INFANT_CURRICULUM = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
