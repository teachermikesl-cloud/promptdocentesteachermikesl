import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../dist/data/infant-curriculum.js", import.meta.url), "utf8");
const context = { window: {} };
vm.runInNewContext(source, context);
const data = context.window.INFANT_CURRICULUM;

const expected = {
  crecimiento: { competencies: [4, 4], criteria: [15, 18], sabers: [33, 31] },
  entorno: { competencies: [3, 3], criteria: [9, 19], sabers: [16, 22] },
  comunicacion: { competencies: [5, 5], criteria: [20, 28], sabers: [37, 43] },
};
const allowedUnresolved = new Set(data.sourceAnomalies.map((item) => item.code));
const errors = [];
let competencyCount = 0;
let criterionCount = 0;
let saberCount = 0;
let unresolvedCount = 0;

for (const [subjectId, counts] of Object.entries(expected)) {
  const subject = data.subjects[subjectId];
  if (!subject) {
    errors.push(`Missing subject: ${subjectId}`);
    continue;
  }
  for (const [index, cycleId] of ["1", "2"].entries()) {
    const cycle = subject.cycles[cycleId];
    if (!cycle) {
      errors.push(`${subjectId}: missing cycle ${cycleId}`);
      continue;
    }
    competencyCount += cycle.competencies.length;
    criterionCount += cycle.criteria.length;
    saberCount += cycle.sabers.length;
    if (cycle.competencies.length !== counts.competencies[index]) errors.push(`${subjectId}/${cycleId}: competency count mismatch`);
    if (cycle.criteria.length !== counts.criteria[index]) errors.push(`${subjectId}/${cycleId}: criterion count mismatch`);
    if (cycle.sabers.length !== counts.sabers[index]) errors.push(`${subjectId}/${cycleId}: saber count mismatch`);
    for (const collection of [cycle.competencies, cycle.criteria, cycle.sabers]) {
      const codes = collection.map((item) => item.code);
      if (codes.length !== new Set(codes).size) errors.push(`${subjectId}/${cycleId}: duplicate code`);
      if (collection.some((item) => !item.code || !item.text)) errors.push(`${subjectId}/${cycleId}: empty item`);
    }
    const saberCodes = new Set(cycle.sabers.map((item) => item.code));
    for (const ref of cycle.saberReferences) {
      if (!saberCodes.has(ref)) {
        unresolvedCount += 1;
        if (!allowedUnresolved.has(ref)) errors.push(`${subjectId}/${cycleId}: unresolved saber ${ref}`);
      }
    }
    if (cycle.sabers.some((item) => /\b[A-I]\.\s*[A-ZÁÉÍÓÚÑ]/.test(item.text))) errors.push(`${subjectId}/${cycleId}: trailing section heading in saber`);
    if (cycle.criteria.some((item) => /\d+\.\d+/.test(item.text))) errors.push(`${subjectId}/${cycleId}: merged criterion code in text`);
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(JSON.stringify({
  subjects: Object.keys(data.subjects).length,
  cycles: 6,
  competencyCount,
  criterionCount,
  saberCount,
  documentedSourceAnomalies: unresolvedCount,
}));

const app=fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8');
const policyContext={};
vm.runInNewContext(app.slice(app.indexOf('function infantMapPolicy('),app.indexOf('const generatePromptBeforeBetaAudit=')),policyContext);
const selected={subject:data.subjects.crecimiento,cycle:'2',cycleData:data.subjects.crecimiento.cycles['2']};
for(const isEn of [false,true]){
  const policy=policyContext.infantMapPolicy(selected,isEn);
  for(const phrase of isEn?['play-based','repeated natural situations','developmental rhythms','not necessarily an individual task']:['situación breve de juego','situaciones naturales repetidas','ritmos individuales de desarrollo','no necesariamente una tarea individual']){
    if(!policy.includes(phrase))throw new Error(`Missing Infant policy: ${phrase}`);
  }
}
if(data.subjects.crecimiento.cycles['2'].competencies.length!==4||data.subjects.crecimiento.cycles['2'].criteria.length!==18)throw new Error('Unexpected second-cycle Growing in Harmony coverage');
