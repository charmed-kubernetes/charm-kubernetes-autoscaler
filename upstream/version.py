import json
from urllib.request import urlopen

URL = "https://api.github.com/repos/kubernetes/autoscaler/releases/latest"
with urlopen(URL) as doc:
    resp = json.loads(doc.read())
print(resp["name"].rsplit("-", 1)[-1])
