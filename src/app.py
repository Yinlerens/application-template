import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

VERSION = os.getenv('RELEASE_VERSION', 'development')
APP_NAME = os.getenv('APP_NAME', 'acceptance')
ROLE = os.getenv('WORKLOAD_ROLE', 'api')
ENVIRONMENT = os.getenv('APP_ENVIRONMENT', 'development')
requests = Counter('foundation_http_requests_total', 'HTTP requests', ['method', 'path', 'status'])
latency = Histogram('foundation_http_request_seconds', 'HTTP duration', ['path'])

def connect():
    return psycopg.connect(host=os.environ['PGHOST'], dbname=os.environ['PGDATABASE'],
                          user=os.environ['PGUSER'], password=os.environ['PGPASSWORD'],
                          connect_timeout=5)

def initialize_database():
    if not os.getenv('PGHOST'): return
    with connect() as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS foundation_events '
                           '(id bigserial PRIMARY KEY, source text NOT NULL, created_at timestamptz DEFAULT now())')

def write_event(source):
    with connect() as connection:
        connection.execute('INSERT INTO foundation_events(source) VALUES (%s)', (source,))

@asynccontextmanager
async def lifespan(_):
    await asyncio.to_thread(initialize_database)
    yield

app = FastAPI(lifespan=lifespan)
if os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT'):
    provider = TracerProvider(resource=Resource.create({
        'service.name': f'{APP_NAME}-{ROLE}', 'service.version': VERSION,
        'deployment.environment.name': ENVIRONMENT}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)

@app.middleware('http')
async def structured_logging(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
    path = request.url.path if request.url.path in {'/', '/api', '/api/db', '/api/stream', '/metrics', '/healthz', '/readyz'} else 'other'
    with latency.labels(path).time():
        response = await call_next(request)
    requests.labels(request.method, path, response.status_code).inc()
    span = trace.get_current_span().get_span_context()
    print(json.dumps({'request_id': request_id, 'trace_id': f'{span.trace_id:032x}',
                      'app': APP_NAME, 'environment': ENVIRONMENT, 'version': VERSION,
                      'method': request.method, 'path': path, 'status': response.status_code}, separators=(',', ':')), flush=True)
    response.headers['x-request-id'] = request_id
    response.headers['x-release-version'] = VERSION
    return response

@app.get('/healthz')
def health(): return {'status': 'ok', 'role': ROLE, 'version': VERSION}

@app.get('/readyz')
def readiness():
    if os.getenv('PGHOST'):
        try:
            with connect() as connection: connection.execute('SELECT 1')
        except psycopg.Error: return Response('database unavailable', status_code=503)
    return {'ready': True}

@app.get('/', response_class=HTMLResponse)
def frontend():
    return '<!doctype html><html lang="zh"><meta charset="utf-8"><title>架构验收</title>' \
           '<h1>云原生基础架构验收应用</h1><pre id="result"></pre>' \
           '<script>fetch("/api").then(r=>r.json()).then(d=>document.getElementById("result").textContent=JSON.stringify(d,null,2))</script></html>'

@app.get('/api')
def api(): return {'architecture': 'cloud-foundation', 'version': VERSION, 'environment': ENVIRONMENT}

@app.post('/api/db')
def db_write():
    write_event('api')
    with connect() as connection:
        count = connection.execute('SELECT count(*) FROM foundation_events').fetchone()[0]
    return {'events': count}

@app.get('/api/stream')
async def stream():
    async def events():
        for i in range(3):
            yield f'data: {i}\n\n'
            await asyncio.sleep(0.1)
    return StreamingResponse(events(), media_type='text/event-stream', headers={'cache-control': 'no-cache'})

@app.websocket('/api/ws')
async def websocket(socket: WebSocket):
    await socket.accept()
    try:
        while True: await socket.send_text(await socket.receive_text())
    except Exception:
        pass

@app.get('/metrics')
def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    import time
    initialize_database()
    while True:
        write_event(ROLE)
        print(json.dumps({'app': APP_NAME, 'role': ROLE, 'version': VERSION, 'event': 'database-write'}), flush=True)
        if ROLE == 'cronjob': break
        time.sleep(30)
