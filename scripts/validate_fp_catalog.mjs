import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../dist/data/fp-catalog.js',import.meta.url),'utf8');
const context={window:{}};vm.runInNewContext(source,context);
const data=context.window.FP_CATALOG,errors=[],titles=[];
const expected={basico:28,medio:56,superior:89,especializacion:36};
if(!data||data.stage!=='Formación Profesional')errors.push('No se ha cargado un catálogo de FP válido.');
for(const [grade,count] of Object.entries(expected)){
  const block=data?.grades?.[grade];if(!block){errors.push(`Falta ${grade}.`);continue}
  const gradeTitles=Object.entries(block.families).flatMap(([family,items])=>items.map(item=>({...item,family,grade})));
  if(gradeTitles.length!==count)errors.push(`${grade}: ${gradeTitles.length} títulos, esperados ${count}.`);
  titles.push(...gradeTitles);
}
if(new Set(titles.map(item=>`${item.grade}:${item.id}`)).size!==titles.length)errors.push('Hay identificadores de título duplicados dentro de un grado.');
let moduleCount=0;
for(const title of titles){
  if(!title.id||!title.title||!title.family||!title.url.startsWith('https://www.juntadeandalucia.es/'))errors.push(`Ficha incompleta: ${title.grade}:${title.id}.`);
  if(!title.norms?.length)errors.push(`Sin normativa enlazada: ${title.title}.`);
  const modules=Object.values(title.modules||{}).flat();moduleCount+=modules.length;if(!modules.length)errors.push(`Sin módulos: ${title.title}.`);
  for(const [course,items] of Object.entries(title.modules||{})){
    if(new Set(items.map(item=>item.code)).size!==items.length)errors.push(`Códigos duplicados en ${title.title}, curso ${course}.`);
    for(const item of items)if(!item.code?.trim()||!item.name?.trim())errors.push(`Módulo incompleto en ${title.title}, curso ${course}.`);
  }
}
if(titles.length!==209)errors.push(`Total de títulos: ${titles.length}, esperados 209.`);
if(new Set(titles.map(item=>item.family)).size!==26)errors.push('El número de familias profesionales ya no es 26.');
if(moduleCount!==2836)errors.push(`Total de módulos por curso: ${moduleCount}, esperados 2836.`);
const sample=titles.find(item=>item.id==='2329'&&item.grade==='superior');
if(!sample||!sample.modules['1']?.some(item=>item.code==='0647')||!sample.modules['2']?.some(item=>item.code==='0655'))errors.push('La ficha de control de Administración y Finanzas ha cambiado.');
if(errors.length){console.error(errors.join('\n'));process.exit(1)}
console.log(`FP validada: ${titles.length} títulos, 26 familias profesionales y ${moduleCount} módulos organizados por curso.`);
