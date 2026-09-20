"""Extract row-level Mathematics links from the signed 2023 Primary annex.

Mechanical extraction only: never infer links from neighbouring criteria.
Usage: extract_primary_math_alignment.py INPUT_PDF OUTPUT_JS
"""
import json
import re
import sys
import pdfplumber
from extract_primary_curriculum import clean

links = {}
active = None
last = {}
with pdfplumber.open(sys.argv[1]) as pdf:
    for index in range(149, 164):
        for table in pdf.pages[index].extract_tables():
            if not table or len(table[0]) != 4:
                continue
            title = clean(table[0][0])
            match = re.fullmatch(r"Matemáticas \((Primer|Segundo|Tercer) Ciclo\)", title)
            start = 0
            if match:
                cycle = {"Primer": 1, "Segundo": 2, "Tercer": 3}[match[1]]
                active = [str(cycle * 2 - 1), str(cycle * 2)]
                last = {}
                start = 2
            if not active:
                continue
            for row in table[start:]:
                refs = list(dict.fromkeys(re.findall(r"MAT\.\d\.[A-Z]\.\d+\.\d+", re.sub(r"\s*\.\s*", ".", clean(row[3])))))
                starts = {}
                for col, grade in enumerate(active, 1):
                    code = re.match(r"(\d+\.\d+\.[ab])(?:\.|\s)", clean(row[col]))
                    if code:
                        starts[grade] = code[1]
                        last[grade] = code[1]
                        links.setdefault(grade, {})[code[1]] = {"sabers": [], "pages": []}
                # A blank criterion opposite a newly started criterion is not a
                # shared continuation (e.g. 2.3.b has no third-year counterpart).
                targets = starts if starts else {g: last[g] for col, g in enumerate(active, 1) if clean(row[col]) and g in last}
                for grade, code in targets.items():
                    entry = links[grade][code]
                    entry["sabers"] = list(dict.fromkeys(entry["sabers"] + refs))
                    entry["pages"] = list(dict.fromkeys(entry["pages"] + [index + 1]))

payload = {"sourceCve": "00284747", "annex": "II", "subjectId": "mates", "extractedOn": "16/09/2026", "criteriaByGrade": links}
with open(sys.argv[2], "w") as output:
    output.write("window.PRIMARY_MATH_ALIGNMENT = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
print({grade: len(items) for grade, items in links.items()})
