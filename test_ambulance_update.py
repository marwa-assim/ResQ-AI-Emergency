import sys
import json
sys.path.append('.')
from app import app, db
with app.app_context():
    with app.test_client() as client:
        res = client.post('/api/ambulance/update', json={"id": "SOS-3915", "status": "ON_SCENE"})
        print('Status Code:', res.status_code)
        print('Response:', res.get_data(as_text=True))
