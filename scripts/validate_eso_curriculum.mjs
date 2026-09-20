import fs from 'node:fs';
import vm from 'node:vm';

const file = new URL('../dist/data/eso-curriculum.js', import.meta.url);
const source = fs.readFileSync(file, 'utf8');
const context = {window: {}};
vm.runInNewContext(source, context);
const data = context.window.ESO_CURRICULUM;

const expectedGrades = {
  bio:'134', digitalizacion:'4', economia:'4', fisica:'1234', plastica:'13', valores:'2', expresion:'4',
  fisqui:'234', orientacion:'4', geohis:'1234', latin:'4', lengua:'1234', lengua_extranjera:'1234', mates:'123',
  mates_a:'4', mates_b:'4', musica:'124', tecnologia:'4', tecnologia_digitalizacion:'23', ampliacion_clasica:'4',
  aprendizaje_social:'4', artes_escenicas:'4', computacion:'123', cultura_cientifica:'4', cultura_clasica:'123',
  flamenco:'3', dibujo_tecnico:'4', filosofia:'4', filosofia_argumentacion:'3', emprendimiento:'3', oratoria:'123',
  proyecto_plastica:'2', 'ambito-cient':'12', 'ambito-ling':'12'
};
const allowedAnomalies = new Set([
  'GEH.3.B.2','GEH.3.B.3','LCL.4.B.1','MAT.2.C.4.1','CYR.1.E.1','CYR.1.E.2','CYR.1.E.3',
  'CYR.1.E.4','CCL.1.A.7','CCL.1.E.5','CF.3.A.6','ACT.1.C.3','ACT.1.L.5','ACT.1.L.6'
]);
const errors = [];
const totals = {competencies:0, criteria:0, sabers:0};
const uniqueCodes = items => new Set(items.map(item => item.code));

if (!data || data.stage !== 'ESO') errors.push('No se ha cargado una base ESO válida.');
if (Object.keys(data.subjects).length !== 34) errors.push(`Materias/ámbitos: ${Object.keys(data.subjects).length}, esperados 34.`);
for (const [id, expected] of Object.entries(expectedGrades)) {
  const subject = data.subjects[id];
  if (!subject) { errors.push(`Falta ${id}.`); continue; }
  const actual = Object.keys(subject.grades).sort().join('');
  if (actual !== expected) errors.push(`${id}: cursos ${actual}, esperados ${expected}.`);
  for (const [grade, gradeData] of Object.entries(subject.grades)) {
    for (const key of ['competencies','criteria','sabers']) {
      const items = gradeData[key]; totals[key] += items.length;
      if (!items.length) errors.push(`${id} ${grade}: ${key} vacío.`);
      if (uniqueCodes(items).size !== items.length) errors.push(`${id} ${grade}: códigos duplicados en ${key}.`);
      for (const item of items) if (!item.code?.trim() || !item.text?.trim()) errors.push(`${id} ${grade}: entrada vacía en ${key}.`);
    }
    const defined = new Set(Object.values(subject.grades).flatMap(g => g.sabers.map(item => item.code)));
    for (const code of gradeData.saberReferences) if (!defined.has(code) && !allowedAnomalies.has(code)) errors.push(`${id} ${grade}: referencia no definida ${code}.`);
  }
}
const expectedTotals = {competencies:436, criteria:1230, sabers:2213};
for (const [key, expected] of Object.entries(expectedTotals)) if (totals[key] !== expected) errors.push(`${key}: ${totals[key]}, esperados ${expected}.`);
const actualAnomalies = new Set(data.sourceAnomalies.map(item => item.code));
if (actualAnomalies.size !== allowedAnomalies.size || [...actualAnomalies].some(code => !allowedAnomalies.has(code))) errors.push('La lista de incidencias de la fuente oficial ha cambiado.');
if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
console.log(`ESO validada: 34 materias/ámbitos, ${totals.competencies} competencias por curso, ${totals.criteria} criterios, ${totals.sabers} registros de saberes y 14 incidencias oficiales señaladas.`);
