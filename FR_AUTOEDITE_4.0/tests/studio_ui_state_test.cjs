#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "assets/studio/index.html"), "utf8");
const lines = html.split(/\r?\n/);

function functionLine(name) {
  const source = lines.find((line) => line.startsWith(`function ${name}(`));
  if (!source) throw new Error(`Função ausente: ${name}`);
  return source;
}

const source = `
let plan={revision:"raw-local"},readyPlan={revision:"ready-local"};
let mainPlanDirty=true,readyPlanDirty=true;
${functionLine("applyPolledMainPlan")}
${functionLine("applyPolledReadyPlan")}
if(applyPolledMainPlan({revision:"raw-stale"})!==false)throw Error("raw deveria ser preservado");
if(plan.revision!=="raw-local")throw Error("poll descartou alteração raw não salva");
if(applyPolledReadyPlan({revision:"ready-stale"})!==false)throw Error("ready deveria ser preservado");
if(readyPlan.revision!=="ready-local")throw Error("poll descartou overlay não salvo");
mainPlanDirty=false;readyPlanDirty=false;
if(!applyPolledMainPlan({revision:"raw-current"})||plan.revision!=="raw-current")throw Error("raw salvo não atualizou");
if(!applyPolledReadyPlan({revision:"ready-current"})||readyPlan.revision!=="ready-current")throw Error("ready salvo não atualizou");
`;

vm.runInNewContext(source, Object.create(null));
if (!html.includes('if(requestedProject!==currentProject)return;')) {
  throw new Error("troca de projeto não invalida carregamento obsoleto do Card Editor");
}
if (!html.includes('cardContentProject!==currentProject')) {
  throw new Error("troca de projeto não bloqueia save obsoleto do Card Editor");
}
console.log("STUDIO UI STATE TEST OK");
