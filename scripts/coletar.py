"""Status de AWS, Azure e Microsoft 365, que nao liberam leitura direta pelo navegador (sem CORS).

Roda no GitHub Actions a cada 5 min e imprime o JSON que o dev.html le do branch "dados".
Cada incidente sai no mesmo formato que o dev.html usa para as outras fontes:
  {titulo, status, inicio, atualizado, resumo, afetados, atualizacoes: [{quando, texto, status}], proxima, previsao}
Uso: python3 scripts/coletar.py > status.json
"""
import datetime
import html
import json
import re
import urllib.request

REGIOES = ("-sa-east-1", "-us-east-1")  # Sao Paulo e N. Virginia; servico sem regiao = global
# rotulos que a Microsoft usa no texto de cada aviso
ROTULOS = ["User impact", "More info", "Current status", "Previous status", "Scope of impact", "Start time",
           "Estimated time to resolve", "Root cause", "Preliminary root cause", "Next update by", "Final status"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "painel-status/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def iso(epoch):
    try:
        return datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def aws():
    raw = get("https://health.aws.amazon.com/public/currentevents")
    eventos = None
    for enc in ("utf-16", "utf-8-sig"):  # a AWS responde em UTF-16
        try:
            eventos = json.loads(raw.decode(enc))
            break
        except (UnicodeDecodeError, ValueError):
            pass
    if not isinstance(eventos, list):
        raise ValueError("formato inesperado da AWS")
    # status "0" = resolvido; 1, 2, 3 = informativo, degradado, fora do ar
    ativos = [e for e in eventos if str(e.get("status", "0")) != "0" and not e.get("end_time")]
    # so conta como grave o que afeta as regioes que empresas no Brasil usam; o resto vira no maximo "instavel"
    perto = lambda e: str(e.get("service", "")).endswith(REGIOES) or not any(c.isdigit() for c in str(e.get("service", "")))
    pior = max((int(e.get("status") or 1) if perto(e) else 1 for e in ativos), default=0)
    ativos.sort(key=lambda e: not perto(e))
    incidentes = []
    for e in ativos:
        log = e.get("event_log") if isinstance(e.get("event_log"), list) else []
        afetados = e.get("impacted_services") if isinstance(e.get("impacted_services"), dict) else {}
        incidentes.append({
            "titulo": f"{e.get('service_name')} ({e.get('region_name')}): {e.get('summary')}",
            "status": e.get("summary"),
            "inicio": iso(e.get("date")),
            "afetados": sorted({v.get("service_name", k) for k, v in afetados.items() if isinstance(v, dict)})[:30],
            "atualizacoes": [{"quando": iso(x.get("timestamp")), "texto": x.get("message") or x.get("summary"),
                              "status": x.get("summary")} for x in reversed(log)][:15],
        })
    return {"nivel": ["ok", "minor", "major", "critical"][min(pior, 3)], "incidentes": incidentes}


def secoes(texto):
    partes = re.split("(" + "|".join(map(re.escape, ROTULOS)) + "):", texto)
    return {partes[i]: partes[i + 1].strip() for i in range(1, len(partes) - 1, 2)}


def microsoft(servico):
    # mesma API que a pagina status.cloud.microsoft usa; Status "Available" = sem problema
    d = json.loads(get(f"https://status.cloud.microsoft/api/posts/{servico}"))
    st = str(d.get("Status") or "Available")
    if st == "Available":
        return {"nivel": "ok", "incidentes": []}
    texto = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", d.get("Message") or ""))).strip()
    s = secoes(texto)
    atualizacoes = [{"quando": d.get("LastUpdatedTime"), "status": st,
                     "texto": s.get("Current status") or s.get("Final status") or texto[:2000]}]
    if s.get("Previous status"):
        atualizacoes.append({"quando": None, "status": "Previous status", "texto": s["Previous status"]})
    # a pagina publica da Microsoft so mostra incidente amplo: qualquer aviso ja e falha parcial
    grave = any(p in st.lower() for p in ("interruption", "outage", "down"))
    # a Microsoft as vezes publica o aviso sem titulo: usa a primeira frase do impacto
    titulo = (d.get("Title") or "").strip() or re.split(r"(?<=\.)\s", s.get("User impact") or st)[0][:160]
    return {"nivel": "critical" if grave else "major", "incidentes": [{
        "titulo": titulo, "status": st,
        "inicio": s.get("Start time") or d.get("AuthoredDateTime"), "atualizado": d.get("LastUpdatedTime"),
        "resumo": " ".join(x for x in (s.get("User impact"), s.get("More info"), s.get("Scope of impact")) if x)[:2500],
        "afetados": [], "atualizacoes": atualizacoes,
        "proxima": s.get("Next update by"), "previsao": s.get("Estimated time to resolve"),
    }]}


def coletar():
    fontes = {"aws": aws, "azure": lambda: microsoft("azure"), "m365": lambda: microsoft("mac")}
    servicos = {}
    for chave, fn in fontes.items():
        try:
            servicos[chave] = fn()
        except Exception as e:  # uma fonte fora nao derruba as outras
            servicos[chave] = {"nivel": "erro", "incidentes": [], "erro": type(e).__name__}
    agora = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {"gerado": agora, "servicos": servicos}


if __name__ == "__main__":
    print(json.dumps(coletar(), ensure_ascii=False, indent=1))
