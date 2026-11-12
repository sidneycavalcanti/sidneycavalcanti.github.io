// Confere cada fonte do dev.html contra as APIs reais (Node 18+).  uso: node scripts/testar.js
const fs = require("fs");
const assert = require("assert");
const html = fs.readFileSync(__dirname + "/../dev.html", "utf8");
const js = html.slice(html.lastIndexOf("<script>") + 8, html.lastIndexOf("</script>"));
const { FONTES, LER, conferir, frase } = new Function(js + "; return { FONTES, LER, conferir, frase };")();

// casos fixos dos leitores
assert.deepEqual(LER.sp({ status: { indicator: "none" } }), { nivel: "ok", incidentes: [] });
assert.equal(LER.sp({ status: { indicator: "none" }, scheduled_maintenances: [{ status: "in_progress", name: "x" }] }).nivel, "maint");
assert.equal(LER.google([{ end: "2026" }, { severity: "high", service_name: "Gmail", external_desc: "**Resumo:** fora" }]).nivel, "critical");
assert.equal(LER.slack({ status: "active", active_incidents: [{ type: "outage", title: "t" }] }).nivel, "major");
const S = (nome, nivel) => ({ nome, nivel });
assert.equal(frase([S("A", "major"), S("B", "critical"), S("C", "minor")]).texto, "B e A com falha agora.");
assert.equal(frase([S("A", "major"), S("B", "major"), S("C", "major"), S("D", "major")]).texto, "A, B, C e mais 1 com falha agora.");
assert.equal(frase([S("A", "minor"), S("B", "minor"), S("C", "ok")]).texto, "Nada fora do ar. 2 serviços instáveis.");
assert.equal(frase([S("A", "ok"), S("B", "maint")]).texto, "Tudo operando.");

(async () => {
  const srv = { servicos: { aws: { nivel: "ok", incidentes: [] }, azure: { nivel: "ok", incidentes: [] }, m365: { nivel: "ok", incidentes: [] } } };
  const lista = await conferir(srv);
  for (const s of lista) console.log(s.nivel.padEnd(8), s.nome, s.nivel === "ok" ? "" : "| " + s.incidentes.slice(0, 2).join(" / "));
  const erros = lista.filter((s) => s.nivel === "erro");
  console.log(`\n${lista.length} fontes, ${erros.length} sem resposta`);
  process.exit(erros.length ? 1 : 0);
})();
