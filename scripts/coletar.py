"""Status de AWS, Azure e Microsoft 365, que nao liberam leitura direta pelo navegador (sem CORS).

Roda no GitHub Actions a cada 5 min e imprime o JSON que o dev.html le do branch "dados".
Uso: python3 scripts/coletar.py > status.json
"""
import datetime
import json
import urllib.request

REGIOES = ("-sa-east-1", "-us-east-1")  # Sao Paulo e N. Virginia; servico sem regiao = global


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "painel-status/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


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
    return {
        "nivel": ["ok", "minor", "major", "critical"][min(pior, 3)],
        "incidentes": [f"{e.get('service_name')} ({e.get('region_name')}): {e.get('summary')}" for e in ativos],
    }


def microsoft(servico):
    # mesma API que a pagina status.cloud.microsoft usa; Status "Available" = sem problema
    d = json.loads(get(f"https://status.cloud.microsoft/api/posts/{servico}"))
    st = str(d.get("Status") or "Available")
    if st == "Available":
        return {"nivel": "ok", "incidentes": []}
    grave = any(p in st.lower() for p in ("interruption", "outage", "down"))
    return {"nivel": "major" if grave else "minor", "incidentes": [f"{d.get('Title')} ({st})"]}


def coletar():
    fontes = {"aws": aws, "azure": lambda: microsoft("azure"), "m365": lambda: microsoft("mac")}
    servicos = {}
    for chave, fn in fontes.items():
        try:
            servicos[chave] = fn()
        except Exception as e:  # uma fonte fora nao derruba as outras
            servicos[chave] = {"nivel": "erro", "incidentes": [f"Sem resposta da fonte: {type(e).__name__}"]}
    agora = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {"gerado": agora, "servicos": servicos}


if __name__ == "__main__":
    print(json.dumps(coletar(), ensure_ascii=False, indent=1))
