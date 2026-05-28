import sys
import json
sys.path.append('.')
from app import app
with app.app_context():
    with app.test_client() as client:
        res = client.get('/api/beds')
        print(json.dumps(res.get_json(), indent=2))
