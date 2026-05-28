import sys
import json
sys.path.append('.')
from app import app, db
with app.app_context():
    with app.test_client() as client:
        res = client.post('/api/emergency/dispatch', json={"lat": 26.2, "lng": 50.5})
        print('Status Code:', res.status_code)
        print('Response:', res.get_data(as_text=True))
