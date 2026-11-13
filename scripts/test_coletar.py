"""Casos fixos do coletor (sem rede).  uso: python3 scripts/test_coletar.py"""
import json
import coletar as c

def resp(obj, enc="utf-8"):
    c.get = lambda url: json.dumps(obj).encode(enc)

# AWS: grave so em Sao Paulo / N. Virginia / global; resolvido (status 0) nao conta
resp([{"status": "3", "service": "ec2-me-central-1", "service_name": "EC2", "region_name": "UAE", "summary": "x"},
      {"status": "2", "service": "s3-sa-east-1", "service_name": "S3", "region_name": "Sao Paulo", "summary": "y",
       "date": "1794411633", "event_log": [{"summary": "a", "message": "primeira", "timestamp": 1794411633},
                                          {"summary": "b", "message": "segunda", "timestamp": 1794411999}]},
      {"status": "0", "service": "ec2-us-east-1", "summary": "z"}], "utf-16")
r = c.aws()
assert r["nivel"] == "major" and r["incidentes"][0]["titulo"].startswith("S3"), r
assert [u["texto"] for u in r["incidentes"][0]["atualizacoes"]] == ["segunda", "primeira"]  # mais nova primeiro
resp([{"status": "3", "service": "ec2-me-central-1", "service_name": "EC2", "region_name": "UAE", "summary": "x"}], "utf-16")
assert c.aws()["nivel"] == "minor"
resp([])
assert c.aws() == {"nivel": "ok", "incidentes": []}

# Microsoft: Available = ok; qualquer aviso = falha parcial; interruption = fora do ar
resp({"Status": "Available"})
assert c.microsoft("azure")["nivel"] == "ok"
resp({"Status": "Service degradation", "Title": "Sem e-mail", "LastUpdatedTime": "2026-11-12T23:06:31+00:00",
      "Message": "<div>User impact: Users can't connect.</div> Current status: Restoring servers. "
                 "Previous status: Investigating. Scope of impact: Everyone. "
                 "Next update by: Friday, November 13, 2026, at 12:30 AM UTC"})
r = c.microsoft("mac")
i = r["incidentes"][0]
assert r["nivel"] == "major" and i["titulo"] == "Sem e-mail", r
assert i["atualizacoes"][0]["texto"] == "Restoring servers." and i["atualizacoes"][1]["texto"] == "Investigating."
assert i["proxima"] == "Friday, November 13, 2026, at 12:30 AM UTC" and i["resumo"].startswith("Users can't connect.")
resp({"Status": "Service degradation", "Title": "", "Message": "User impact: Users can't send mail. More info: x."})
assert c.microsoft("mac")["incidentes"][0]["titulo"] == "Users can't send mail."
resp({"Status": "Service interruption", "Title": "T", "Message": ""})
assert c.microsoft("mac")["nivel"] == "critical"

c.get = lambda url: (_ for _ in ()).throw(TimeoutError())
assert all(v["nivel"] == "erro" for v in c.coletar()["servicos"].values())
print("coletar: 9 casos ok")
