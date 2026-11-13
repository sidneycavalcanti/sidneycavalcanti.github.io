// Confere os leitores do dev.html: casos fixos e depois cada fonte real (Node 18+).  uso: node scripts/testar.js
const fs = require("fs");
const assert = require("assert");
const html = fs.readFileSync(__dirname + "/../dev.html", "utf8");
const js = html.slice(html.lastIndexOf("<script>") + 8, html.lastIndexOf("</script>"));
const { FONTES, LER, T, conferir, frase, normaliza, atividade } = new Function(js + "; return { FONTES, LER, T, conferir, frase, normaliza, atividade };")();

// leitores
assert.deepEqual(LER.sp({ status: { indicator: "none" } }), { nivel: "ok", incidentes: [] });
const m = LER.sp({ status: { indicator: "none" }, scheduled_maintenances: [{ status: "in_progress", name: "x", scheduled_until: "2026-11-13T05:00:00Z" }] });
assert.equal(m.nivel, "maint");
assert.equal(m.incidentes[0].fimManut, "2026-11-13T05:00:00Z");
const s = LER.sp({ status: { indicator: "major" }, incidents: [{ name: "API fora", status: "identified", components: [{ name: "API" }],
  incident_updates: [{ display_at: "2026-11-12T10:00:00Z", body: "velha" }, { display_at: "2026-11-12T11:00:00Z", body: "nova" }] }] });
assert.equal(s.incidentes[0].atualizacoes[0].texto, "nova");  // mais nova primeiro
assert.deepEqual(s.incidentes[0].afetados, ["API"]);
assert.equal(LER.google([{ end: "2026" }, { severity: "high", service_name: "Gmail", external_desc: "**Summary:**\nSem e-mail" }]).nivel, "critical");
assert.equal(LER.slack({ status: "active", active_incidents: [{ type: "outage", title: "t", notes: [{ body: "n" }] }] }).nivel, "major");

// previsao e proxima atualizacao saem do texto da atualizacao mais recente
let i = normaliza({ titulo: "x", atualizacoes: [{ texto: "Fixing. We expect to provide the next update by 14:00 UTC." }] });
assert.equal(i.proxima, "14:00 UTC");
i = normaliza({ titulo: "x", atualizacoes: [{ quando: "2026-11-12T23:50:00Z", texto: "We will provide another update in 4 hours or as soon as more information becomes available." }] });
assert.equal(i.proxima, "4 hours");
assert.equal(i.proximaDita, "2026-11-12T23:50:00Z");
assert.equal(normaliza({ titulo: "x", proxima: "Friday 12:30 AM UTC", atualizacoes: [] }).proxima, "Friday 12:30 AM UTC");
i = normaliza({ titulo: "x", atualizacoes: [{ texto: "Estimated time to resolve: 2 hours." }] });
assert.equal(i.previsao, "2 hours");
i = normaliza({ titulo: "x", atualizacoes: [{ texto: "Previsão de normalização: 18h" }] });
assert.equal(i.previsao, "18h");
assert.deepEqual(normaliza("antigo").atualizacoes, []);
assert.equal(normaliza({ titulo: "", resumo: "Users can't connect. More text." }).titulo, "Users can't connect.");

// frase do topo, nos dois idiomas
const S = (nome, nivel) => ({ nome, nivel });
assert.equal(frase([S("A", "major"), S("B", "critical"), S("C", "minor")]).texto, "B e A com falha agora.");
assert.equal(frase([S("A", "major"), S("B", "major"), S("C", "major"), S("D", "major")]).texto, "A, B, C e mais 1 com falha agora.");
assert.equal(frase([S("A", "minor"), S("B", "minor"), S("C", "ok")]).texto, "2 serviços com instabilidade, nenhum fora do ar.");
assert.equal(frase([S("A", "ok"), S("B", "maint")]).texto, "Todos os serviços operando normalmente.");
assert.equal(frase([S("Microsoft 365", "major")], T.en).texto, "Microsoft 365 is having an outage.");
assert.equal(frase([S("A", "major"), S("B", "major")], T.en).texto, "A and B are having an outage.");
const agora = Date.parse("2026-11-13T12:30:00Z");
const h = atividade([{ incidentes: [{ atualizacoes: [{ quando: "2026-11-13T12:10:00Z" }, { quando: "2026-11-13T11:50:00Z" },
  { quando: "2026-11-12T13:00:00Z" }, { quando: "2026-11-11T10:00:00Z" }] }] }], agora);
assert.equal(h.length, 24); assert.equal(h[23], 1); assert.equal(h[22], 1); assert.equal(h[0], 1);
assert.equal(h.reduce((a, b) => a + b, 0), 3, "fora das 24 h nao conta");
// nomes de produto protegidos da traducao
const { protege, devolve } = new Function(js + "; return { protege, devolve };")();
const p = protege("Users can't reach Exchange Online, Microsoft Teams and Teams. Exchange is down.");
assert.equal(p.s, "Users can't reach ⟦0⟧, ⟦1⟧ and ⟦2⟧. ⟦3⟧ is down.");
assert.equal(devolve("Usuários sem ⟦0⟧, ⟦1⟧ e ⟦ 2 ⟧. ⟦3⟧ fora.", p.termos), "Usuários sem Exchange Online, Microsoft Teams e Teams. Exchange fora.");
// prazo: data da Microsoft vira horario local (nunca traduzida); hora solta nao passa pelo tradutor
const { prazo } = new Function(js + "; return { prazo };")();
const sem = () => "";
assert.equal(prazo("Friday, November 13, 2026, at 12:30 AM UTC", null, sem)[1], false);
assert.match(prazo("Friday, November 13, 2026, at 12:30 AM UTC", null, sem)[0], /2026/);
assert.deepEqual(prazo("14:00 UTC", null, sem), ["14:00 UTC", false]);
assert.deepEqual(prazo("4 hours", null, sem), ["4 hours", true]);
assert.deepEqual(Object.keys(T.pt).sort(), Object.keys(T.en).sort(), "PT e EN com as mesmas chaves");
console.log("casos fixos ok");

(async () => {
  const srv = { servicos: { aws: { nivel: "ok", incidentes: [] }, azure: { nivel: "ok", incidentes: [] }, m365: { nivel: "ok", incidentes: [] } } };
  const lista = await conferir(srv);
  for (const s of lista) {
    const i = s.incidentes[0];
    console.log(s.nivel.padEnd(8), s.nome.padEnd(18), i ? `${s.incidentes.length} inc, ${i.atualizacoes.length} atualiz.` +
      (i.previsao ? ` | previsao: ${i.previsao}` : "") + (i.proxima ? ` | proxima: ${i.proxima}` : "") : "");
  }
  const erros = lista.filter((s) => s.nivel === "erro");
  console.log(`\n${lista.length} fontes, ${erros.length} sem resposta`);
  process.exit(erros.length ? 1 : 0);
})();
