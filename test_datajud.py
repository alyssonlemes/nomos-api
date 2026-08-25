import urllib.request
import json
req = urllib.request.Request(
    'https://api-publica.datajud.cnj.jus.br/api_publica_trt1/_search',
    headers={'Authorization': 'APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==', 'Content-Type': 'application/json'},
    data=b'{"size": 1, "query": {"match_all": {}}}'
)
res = urllib.request.urlopen(req)
data = json.loads(res.read())
for hit in data.get('hits', {}).get('hits', []):
    print(hit['_source']['numeroProcesso'])
