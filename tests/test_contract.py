from fastapi.testclient import TestClient
from src.app import app

def test_frontend_api_trace_and_stream_contract():
    with TestClient(app) as client:
        response = client.get('/api', headers={'x-request-id': 'contract-test'})
        assert response.status_code == 200
        assert response.headers['x-request-id'] == 'contract-test'
        assert response.json()['architecture'] == 'cloud-foundation'
        assert 'fetch("/api")' in client.get('/').text
        assert client.get('/api/stream').text == 'data: 0\n\ndata: 1\n\ndata: 2\n\n'
        with client.websocket_connect('/api/ws') as socket:
            socket.send_text('arm64-stream-contract')
            assert socket.receive_text() == 'arm64-stream-contract'
        assert 'foundation_http_requests_total' in client.get('/metrics').text
