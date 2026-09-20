import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../dist/data/fp-daw-curriculum.js',import.meta.url),'utf8');
const context={window:{}};vm.createContext(context);vm.runInContext(source,context);
const data=context.window.FP_DAW_CURRICULUM,module=data?.modules?.['0612'];
if(!data||data.titleId!=='2292'||!module)throw new Error('Falta el piloto DAW 0612');
if(module.learningOutcomes.length!==7)throw new Error(`Se esperaban 7 RA y hay ${module.learningOutcomes.length}`);
const criteria=module.learningOutcomes.flatMap(item=>item.criteria);
if(criteria.length!==58)throw new Error(`Se esperaban 58 criterios y hay ${criteria.length}`);
const codes=[...module.learningOutcomes.map(item=>item.code),...criteria.map(item=>item.code)];
if(new Set(codes).size!==codes.length)throw new Error('Hay códigos duplicados');
if([...module.learningOutcomes,...criteria].some(item=>!item.text?.trim()))throw new Error('Hay elementos sin texto');
console.log(`Piloto DAW validado: ${module.learningOutcomes.length} RA y ${criteria.length} criterios.`);
