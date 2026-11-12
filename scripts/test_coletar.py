"""Casos fixos do coletor (sem rede).  uso: python3 scripts/test_coletar.py"""
import json
import coletar as c

def resp(obj, enc="utf-8"):
    c.get = lambda url: json.dumps(obj).encode(enc)

# AWS: grave so em Sao Paulo / N. Virginia / global; resolvido (status 0) nao conta
resp([{"status": "3", "service": "ec2-me-central-1", "service_name": "EC2", "region_name": "UAE", "summary": "x"},
      {"status": "2", "service": "s3-sa-east-1", "service_name": "S3", "region_name": "Sao Paulo", "summary": "y"},
      {"status": "0", "service": "ec2-us-east-1", "summary": "z"}], "utf-16")
r = c.aws()
assert r["nivel"] == "major" and r["incidentes"][0].startswith("S3"), r
resp([{"status": "3", "service": "ec2-me-central-1", "service_name": "EC2", "region_name": "UAE", "summary": "x"}], "utf-16")
assert c.aws()["nivel"] == "minor"
resp([])
assert c.aws() == {"nivel": "ok", "incidentes": []}
resp({"Status": "Available"})
assert c.microsoft("azure")["nivel"] == "ok"
resp({"Status": "Service interruption", "Title": "T"})
assert c.microsoft("mac")["nivel"] == "major"
c.get = lambda url: (_ for _ in ()).throw(TimeoutError())
assert all(v["nivel"] == "erro" for v in c.coletar()["servicos"].values())
print("coletar: 6 casos ok")
