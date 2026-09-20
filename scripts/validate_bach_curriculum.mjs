import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../dist/data/bach-curriculum.js', import.meta.url), 'utf8');
const context = {window:{}};vm.runInNewContext(source, context);
const data = context.window.BACH_CURRICULUM;
const expectedGrades = {
  analisis_musical:'12',artes_escenicas:'12',biologia:'2',biologia_geologia:'1',ciencias_generales:'2',coro:'12',
  cultura_audiovisual:'1',dibujo_artistico:'12',dibujo_tecnico:'12',dibujo_tecnico_artes:'12',diseno:'2',economia:'1',
  economia_emprendimiento:'1',educacion_fisica:'1',empresa_modelos:'2',filosofia:'1',fisica:'2',fisica_quimica:'1',
  fundamentos_artisticos:'2',geologia:'2',geografia:'2',griego:'12',historia_arte:'2',historia_espana:'2',
  historia_filosofia:'2',historia_mundo:'1',historia_musica:'2',latin:'12',lengua:'12',lengua_extranjera:'12',
  lenguaje_musical:'1',literatura_dramatica:'2',literatura_universal:'1',matematicas:'12',matematicas_ccss:'12',
  matematicas_generales:'1',movimientos_culturales:'2',proyectos_artisticos:'1',quimica:'2',tecnicas_expresion:'2',
  tecnologia_ingenieria:'12',volumen:'1',actividad_fisica:'2',anatomia:'1',antropologia:'1',ciencias_tierra:'2',
  creacion_digital:'1',cultura_emprendedora:'1',convivencia:'12',electrotecnia:'2',finanzas:'2',administracion:'2',
  imagen_sonido:'2',mitologia:'2',patrimonio:'1',programacion:'2',psicologia:'2',tico:'12'
};
const allowedAnomalies = new Set(['MACS.2.C.1.1','MITO.2.A.4']);
const errors=[],totals={competencies:0,criteria:0,sabers:0};
if(!data||data.stage!=='Bachillerato')errors.push('No se ha cargado una base de Bachillerato válida.');
if(Object.keys(data.subjects).length!==58)errors.push(`Materias: ${Object.keys(data.subjects).length}, esperadas 58.`);
for(const [id,expected] of Object.entries(expectedGrades)){
  const subject=data.subjects[id];if(!subject){errors.push(`Falta ${id}.`);continue}
  const actual=Object.keys(subject.grades).sort().join('');if(actual!==expected)errors.push(`${id}: cursos ${actual}, esperados ${expected}.`);
  const defined=new Set(Object.values(subject.grades).flatMap(g=>g.sabers.map(item=>item.code)));
  for(const [grade,gradeData] of Object.entries(subject.grades)){
    for(const key of ['competencies','criteria','sabers']){
      const items=gradeData[key];totals[key]+=items.length;if(!items.length)errors.push(`${id} ${grade}: ${key} vacío.`);
      if(new Set(items.map(item=>item.code)).size!==items.length)errors.push(`${id} ${grade}: códigos duplicados en ${key}.`);
      for(const item of items)if(!item.code?.trim()||!item.text?.trim())errors.push(`${id} ${grade}: entrada vacía en ${key}.`);
    }
    for(const item of gradeData.sabers)if(/Depósito Legal|\bBOJA\b|Competencias específicas|Criterios de evaluación/i.test(item.text))errors.push(`${id} ${grade}: texto ajeno filtrado en ${item.code}.`);
    for(const code of gradeData.saberReferences){const parent=defined.has(code)||[...defined].some(item=>item.startsWith(code+'.'));if(!parent&&!allowedAnomalies.has(code))errors.push(`${id} ${grade}: referencia no definida ${code}.`)}
  }
}
const expectedTotals={competencies:364,criteria:930,sabers:2465};
for(const [key,expected] of Object.entries(expectedTotals))if(totals[key]!==expected)errors.push(`${key}: ${totals[key]}, esperados ${expected}.`);
const actualAnomalies=new Set(data.sourceAnomalies.map(item=>item.code));
if(actualAnomalies.size!==allowedAnomalies.size||[...actualAnomalies].some(code=>!allowedAnomalies.has(code)))errors.push('La lista de incidencias oficiales ha cambiado.');
if(errors.length){console.error(errors.join('\n'));process.exit(1)}
console.log(`Bachillerato validado: 58 materias, ${totals.competencies} competencias por curso, ${totals.criteria} criterios, ${totals.sabers} registros de saberes y 2 incidencias oficiales señaladas.`);
