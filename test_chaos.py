import sys
import json
sys.path.append('.')
from app import app, db
with app.app_context():
    with app.test_client() as client:
        res = client.post('/api/chaos')
        print('Chaos Status Code:', res.status_code)
        print('Chaos Response:', res.get_data(as_text=True))
