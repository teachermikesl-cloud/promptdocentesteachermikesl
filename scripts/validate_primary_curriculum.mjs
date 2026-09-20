import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../dist/data/primary-curriculum.js", import.meta.url), "utf8");
const context = { window: {} };
vm.runInNewContext(source, context);
const data = context.window.PRIMARY_CURRICULUM;

const expectedGrades = {
  medio: ["1", "2", "3", "4", "5", "6"],
  artistica: ["1", "2", "3", "4", "5", "6"],
  fisica: ["1", "2", "3", "4", "5", "6"],
  valores: ["6"],
  lengua: ["1", "2", "3", "4", "5", "6"],
  lengua_extranjera: ["1", "2", "3", "4", "5", "6"],
  mates: ["1", "2", "3", "4", "5", "6"],
};

let competencyCount = 0;
let criterionCount = 0;
let saberCount = 0;
const errors = [];

for (const [subjectId, grades] of Object.entries(expectedGrades)) {
  const subject = data.subjects[subjectId];
  if (!subject) {
    errors.push(`Missing subject: ${subjectId}`);
    continue;
  }
  const foundGrades = [];
  for (const [cycleId, cycle] of Object.entries(subject.cycles)) {
    competencyCount += cycle.competencies.length;
    saberCount += cycle.sabers.length;
    const saberCodes = new Set(cycle.sabers.map((item) => item.code));
    for (const ref of cycle.saberReferences) {
      if (!saberCodes.has(ref)) errors.push(`${subjectId}/${cycleId}: unresolved saber ${ref}`);
    }
    for (const [grade, criteria] of Object.entries(cycle.criteriaByGrade)) {
      foundGrades.push(grade);
      criterionCount += criteria.length;
      const codes = criteria.map((item) => item.code);
      if (codes.length !== new Set(codes).size) errors.push(`${subjectId}/${grade}: duplicate criterion code`);
      if (criteria.some((item) => !item.code || !item.text)) errors.push(`${subjectId}/${grade}: empty criterion`);
    }
    if (cycle.competencies.some((item) => !item.code || !item.text)) errors.push(`${subjectId}/${cycleId}: empty competency`);
    if (cycle.sabers.some((item) => !item.code || !item.text)) errors.push(`${subjectId}/${cycleId}: empty saber`);
    if (cycle.sabers.some((item) => /\s*[A-Z]\.\s*[A-ZÁÉÍÓÚÑ][^.]{2,120}$/.test(item.text))) errors.push(`${subjectId}/${cycleId}: trailing section heading in saber`);
  }
  if (grades.sort().join() !== foundGrades.sort().join()) errors.push(`${subjectId}: grade coverage mismatch`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(JSON.stringify({ subjects: Object.keys(data.subjects).length, competencyCount, criterionCount, saberCount, unresolvedReferences: 0 }));
