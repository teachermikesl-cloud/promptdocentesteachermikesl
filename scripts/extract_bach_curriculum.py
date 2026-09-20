#!/usr/bin/env python3
"""Extract the official Andalusian Bachillerato curriculum into browser data."""

import json
import sys
from pathlib import Path

import pdfplumber

import extract_eso_curriculum as base


SOURCE_URLS = [
    "https://www.juntadeandalucia.es/eboja/2023/104/BOJA23-104-00281-9728-01_00284744.pdf",
    "https://www.juntadeandalucia.es/eboja/2023/104/BOJA23-104-00297-9728-02_00284744.pdf",
]

# Page numbers are one-based and refer to each signed PDF part.
SUBJECTS = [
    ("analisis_musical", "Análisis Musical", "Anexo II", [(0, 36, 42)]),
    ("artes_escenicas", "Artes Escénicas", "Anexo II", [(0, 43, 51)]),
    ("biologia", "Biología", "Anexo II", [(0, 52, 60)]),
    ("biologia_geologia", "Biología, Geología y Ciencias Ambientales", "Anexo II", [(0, 61, 69)]),
    ("ciencias_generales", "Ciencias Generales", "Anexo II", [(0, 70, 77)]),
    ("coro", "Coro y Técnica Vocal", "Anexo II", [(0, 78, 83)]),
    ("cultura_audiovisual", "Cultura Audiovisual", "Anexo II", [(0, 84, 91)]),
    ("dibujo_artistico", "Dibujo Artístico", "Anexo II", [(0, 92, 104)]),
    ("dibujo_tecnico", "Dibujo Técnico", "Anexo II", [(0, 105, 112)]),
    ("dibujo_tecnico_artes", "Dibujo Técnico Aplicado a las Artes Plásticas y al Diseño", "Anexo II", [(0, 113, 120)]),
    ("diseno", "Diseño", "Anexo II", [(0, 121, 128)]),
    ("economia", "Economía", "Anexo II", [(0, 129, 136)]),
    ("economia_emprendimiento", "Economía, Emprendimiento y Actividad Empresarial", "Anexo II", [(0, 137, 143)]),
    ("educacion_fisica", "Educación Física", "Anexo II", [(0, 144, 153)]),
    ("empresa_modelos", "Empresa y Diseño de Modelos de Negocio", "Anexo II", [(0, 154, 160)]),
    ("filosofia", "Filosofía", "Anexo II", [(0, 161, 169)]),
    ("fisica", "Física", "Anexo II", [(0, 170, 177)]),
    ("fisica_quimica", "Física y Química", "Anexo II", [(0, 178, 186)]),
    ("fundamentos_artisticos", "Fundamentos Artísticos", "Anexo II", [(0, 187, 194)]),
    ("geologia", "Geología y Ciencias Ambientales", "Anexo II", [(0, 195, 203)]),
    ("geografia", "Geografía", "Anexo II", [(0, 204, 213)]),
    ("griego", "Griego", "Anexo II", [(0, 214, 228)]),
    ("historia_arte", "Historia del Arte", "Anexo II", [(0, 229, 239)]),
    ("historia_espana", "Historia de España", "Anexo II", [(0, 240, 253)]),
    ("historia_filosofia", "Historia de la Filosofía", "Anexo II", [(0, 254, 262)]),
    ("historia_mundo", "Historia del Mundo Contemporáneo", "Anexo II", [(0, 263, 274)]),
    ("historia_musica", "Historia de la Música y de la Danza", "Anexo II", [(0, 275, 280)]),
    ("latin", "Latín", "Anexo II", [(0, 281, 281), (1, 1, 13)]),
    ("lengua", "Lengua Castellana y Literatura", "Anexo II", [(1, 14, 33)]),
    ("lengua_extranjera", "Lengua Extranjera", "Anexo II", [(1, 34, 48)]),
    ("lenguaje_musical", "Lenguaje y Práctica Musical", "Anexo II", [(1, 49, 54)]),
    ("literatura_dramatica", "Literatura Dramática", "Anexo II", [(1, 55, 62)]),
    ("literatura_universal", "Literatura Universal", "Anexo II", [(1, 63, 71)]),
    ("matematicas", "Matemáticas", "Anexo II", [(1, 72, 84)]),
    ("matematicas_ccss", "Matemáticas Aplicadas a las Ciencias Sociales", "Anexo II", [(1, 85, 97)]),
    ("matematicas_generales", "Matemáticas Generales", "Anexo II", [(1, 98, 106)]),
    ("movimientos_culturales", "Movimientos Culturales y Artísticos", "Anexo II", [(1, 107, 114)]),
    ("proyectos_artisticos", "Proyectos Artísticos", "Anexo II", [(1, 115, 120)]),
    ("quimica", "Química", "Anexo II", [(1, 121, 128)]),
    ("tecnicas_expresion", "Técnicas de Expresión Gráfico-plástica", "Anexo II", [(1, 129, 136)]),
    ("tecnologia_ingenieria", "Tecnología e Ingeniería", "Anexo II", [(1, 137, 148)]),
    ("volumen", "Volumen", "Anexo II", [(1, 149, 155)]),
    ("actividad_fisica", "Actividad Física, Salud y Sociedad", "Anexo III", [(1, 156, 164)]),
    ("anatomia", "Anatomía Aplicada", "Anexo III", [(1, 165, 170)]),
    ("antropologia", "Antropología y Sociología", "Anexo III", [(1, 171, 176)]),
    ("ciencias_tierra", "Ciencias de la Tierra y del Medio Ambiente", "Anexo III", [(1, 177, 182)]),
    ("creacion_digital", "Creación Digital y Pensamiento Computacional", "Anexo III", [(1, 183, 187)]),
    ("cultura_emprendedora", "Cultura Emprendedora y Empresarial", "Anexo III", [(1, 188, 192)]),
    ("convivencia", "Educación para la Convivencia Democrática", "Anexo III", [(1, 193, 200)]),
    ("electrotecnia", "Electrotecnia", "Anexo III", [(1, 201, 206)]),
    ("finanzas", "Finanzas y Economía", "Anexo III", [(1, 207, 212)]),
    ("administracion", "Fundamentos de Administración y Gestión", "Anexo III", [(1, 213, 218)]),
    ("imagen_sonido", "Imagen y Sonido", "Anexo III", [(1, 219, 223)]),
    ("mitologia", "Mitología Clásica", "Anexo III", [(1, 224, 230)]),
    ("patrimonio", "Patrimonio Cultural y Artístico de Andalucía", "Anexo III", [(1, 231, 236)]),
    ("programacion", "Programación y Computación", "Anexo III", [(1, 237, 242)]),
    ("psicologia", "Psicología", "Anexo III", [(1, 243, 250)]),
    ("tico", "Tecnologías de la Información y la Comunicación", "Anexo III", [(1, 251, 259)]),
]

PREFIXES = {
    "analisis_musical":{"AMUS"}, "artes_escenicas":{"ARES"}, "biologia":{"BIOL"}, "biologia_geologia":{"BGCA"},
    "ciencias_generales":{"CCGG"}, "coro":{"CORO"}, "cultura_audiovisual":{"CULA"}, "dibujo_artistico":{"DIBA"},
    "dibujo_tecnico":{"DIBT"}, "dibujo_tecnico_artes":{"DTAP"}, "diseno":{"DISE"}, "economia":{"ECON"},
    "economia_emprendimiento":{"ECYE"}, "educacion_fisica":{"EDFI"}, "empresa_modelos":{"EYDI"}, "filosofia":{"FILO"},
    "fisica":{"FISI"}, "fisica_quimica":{"FISQ"}, "fundamentos_artisticos":{"FART"}, "geologia":{"GYCA"},
    "geografia":{"GEOG"}, "griego":{"GRIE"}, "historia_arte":{"HART"}, "historia_espana":{"HESP"},
    "historia_filosofia":{"HFIL"}, "historia_mundo":{"HMCO"}, "historia_musica":{"HMUS"}, "latin":{"LATI"},
    "lengua":{"LCYL"}, "lengua_extranjera":{"LEXT"}, "lenguaje_musical":{"LYPM"}, "literatura_dramatica":{"LITD"},
    "literatura_universal":{"LITU"}, "matematicas":{"MATE"}, "matematicas_ccss":{"MACS"}, "matematicas_generales":{"MATG"},
    "movimientos_culturales":{"MCAR"}, "proyectos_artisticos":{"PART"}, "quimica":{"QUIM"}, "tecnicas_expresion":{"TEGP"},
    "tecnologia_ingenieria":{"TECI"}, "volumen":{"VOLU"}, "actividad_fisica":{"AFSS"}, "anatomia":{"AAPL"},
    "antropologia":{"AYSO"}, "ciencias_tierra":{"CCTI"}, "creacion_digital":{"CDPC"}, "cultura_emprendedora":{"CEE"},
    "convivencia":{"EPCD"}, "electrotecnia":{"ELTR"}, "finanzas":{"FYEC"}, "administracion":{"FAG"},
    "imagen_sonido":{"IMYS"}, "mitologia":{"MITO"}, "patrimonio":{"PCUL"}, "programacion":{"PRYC"},
    "psicologia":{"PSIC"}, "tico":{"TICO"},
}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: extract_bach_curriculum.py PDF_PART_1 PDF_PART_2 OUTPUT_JS")
    base.PREFIXES = PREFIXES
    pdfs = [pdfplumber.open(Path(sys.argv[1])), pdfplumber.open(Path(sys.argv[2]))]
    try:
        subjects = {config[0]: base.extract_subject(pdfs, config) for config in SUBJECTS}
    finally:
        for pdf in pdfs:
            pdf.close()

    anomalies = []
    note = ("El código aparece en las tablas de vinculación, pero no figura definido con esa misma codificación "
            "en la tabla de saberes del documento oficial. No debe completarse ni inventarse.")
    for subject_id, subject in subjects.items():
        defined = {item["code"] for grade_data in subject["grades"].values() for item in grade_data["sabers"]}
        for grade, grade_data in subject["grades"].items():
            for code in grade_data["saberReferences"]:
                if code not in defined and not any(item.startswith(code + ".") for item in defined):
                    anomalies.append({"subjectId": subject_id, "grade": grade, "code": code, "note": note})

    payload = {
        "schemaVersion":"1.0.0", "stage":"Bachillerato",
        "source": {
            "title":"Orden de 30 de mayo de 2023 - currículo de Bachillerato en Andalucía",
            "urls":SOURCE_URLS, "cve":"00284744", "annexes":["Anexo II","Anexo III"],
            "verifiedOn":"13/09/2026",
            "note":"Texto oficial normalizado para lectura digital; consérvense los dos PDF firmados como fuente auténtica."
        },
        "subjects":subjects,
        "aliases":{"lengua1":"lengua","lengua2":"lengua","ingles1":"lengua_extranjera","ingles2":"lengua_extranjera",
                   "frances1":"lengua_extranjera","frances2":"lengua_extranjera","mates1":"matematicas","mates2":"matematicas",
                   "mates-ccss1":"matematicas_ccss","mates-ccss2":"matematicas_ccss"},
        "sourceAnomalies":anomalies,
    }
    output = Path(sys.argv[3]); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("window.BACH_CURRICULUM = " + json.dumps(payload, ensure_ascii=False, separators=(",",":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
