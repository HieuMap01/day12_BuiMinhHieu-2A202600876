# Day 12 Lab - Mission Answers

Student: Bui Minh Hieu  
Student ID: 2A202600876

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. The develop app uses local/default configuration instead of strict environment-based configuration.
2. The develop app is designed for quick local testing, not production operations.
3. It has limited operational endpoints compared with the production version.
4. It does not include strong startup/shutdown lifecycle handling.
5. It does not include structured production logging.
6. It has fewer security controls around secrets and runtime environment.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---|---|---|---|
| Config | Mostly local/simple defaults | Environment variables | Lets the same image run in dev, staging, and production without code changes. |
| Secrets | Easy to accidentally hardcode | Loaded from `.env` or cloud env vars | Prevents leaking API keys and keeps secrets out of Git. |
| Port | Usually fixed for localhost | Reads `PORT` from environment | Cloud platforms inject dynamic ports. |
| Health check | Minimal or absent | `/health` endpoint | Platforms can detect broken containers and restart them. |
| Readiness | Minimal or absent | `/ready` endpoint | Load balancers can avoid routing traffic before startup finishes. |
| Logging | Simple prints | Structured JSON logging | Easier to search and monitor in cloud logs. |
| Shutdown | Abrupt stop | Graceful shutdown/lifespan hooks | Allows in-flight requests to finish and readiness to change safely. |
| Security | Basic demo behavior | API key auth, CORS, security headers | Reduces abuse and protects public endpoints. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11` in the develop Dockerfile.
2. Working directory: `/app`.
3. `requirements.txt` is copied before the app code so Docker can cache the dependency installation layer. If only source code changes, pip install does not need to run again.
4. `CMD` provides the default command that can be overridden at runtime. `ENTRYPOINT` defines the executable that is harder to override and is usually used when the container should always run one specific program.

### Exercise 2.2: Build and run result

Develop image build command used from project root:

```powershell
docker build -t my-agent -f .\02-docker\develop\Dockerfile .
docker run --rm -p 8000:8000 my-agent
```

The important fix was to build from the project root because the Dockerfile copies files such as `02-docker/develop/app.py` and `utils/mock_llm.py`.

PowerShell test command:

```powershell
curl.exe -X POST "http://localhost:8000/ask?question=What%20is%20Docker%3F"
```

### Exercise 2.3: Image size comparison

| Image | Build style | Expected result |
|---|---|---|
| `my-agent:develop` | Single-stage `python:3.11` | Larger because it keeps the full base image and build/runtime environment together. |
| `my-agent:advanced` / final Dockerfile | Multi-stage `python:3.11-slim` | Smaller and cleaner because build tools stay in the builder stage. |

The production Dockerfile uses a builder stage for dependency installation and a runtime stage with only the app and installed packages.

### Exercise 2.4: Docker Compose architecture

The production compose stack includes:

| Service | Role |
|---|---|
| `agent` | FastAPI AI agent service. |
| `redis` | Cache/session/rate-limit backing service. |
| `qdrant` | Vector database for RAG examples. |
| `nginx` | Reverse proxy and load balancer in front of agent. |

Communication flow:

```text
Client -> Nginx -> Agent -> Redis / Qdrant
```

## Part 3: Cloud Deployment

### Exercise 3.1 / 3.2: Render deployment

I deployed the service to Render instead of Railway.

Public URL:

```text
https://day12-agent.onrender.com
```

Health check:

```powershell
curl.exe "https://day12-agent.onrender.com/health"
```

Observed result:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "checks": {
    "llm": "mock"
  }
}
```

### Railway vs Render configuration

| Item | Railway | Render |
|---|---|---|
| Config file | `railway.toml` | `render.yaml` |
| Deploy style | CLI-first or GitHub connected | Dashboard/Blueprint or GitHub Web Service |
| Port | Injected via `PORT` | Injected via `$PORT` |
| Environment variables | Railway variables | Render Environment tab |
| Health checks | Platform-detected or configured | `healthCheckPath: /health` |

## Part 4: API Security

### Exercise 4.1: API key authentication

PowerShell setup:

```powershell
cd "D:\VinUni\GG Colab\Day 12\day12_BuiMinhHieu-2A202600876\04-api-gateway\develop"
$env:AGENT_API_KEY="my-secret-key"
python app.py
```

Test body:

```powershell
$body = @{ question = "Hello" } | ConvertTo-Json
```

Without key:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/ask" `
  -ContentType "application/json" `
  -Body $body
```

Expected result: `401 Unauthorized`.

With key:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/ask" `
  -Headers @{ "X-API-Key" = "my-secret-key" } `
  -ContentType "application/json" `
  -Body $body
```

Expected result: `200 OK`.

### Exercise 4.2: JWT authentication

JWT is useful when a system needs user identity, expiration time, and claims. API key authentication is simpler for service-to-service or demo agents, while JWT is better for end-user authentication.

### Exercise 4.3: Rate limiting

The API gateway limits repeated requests. This prevents abuse, accidental loops, and unnecessary LLM cost. The final project uses a sliding-window style in-memory limiter and returns HTTP `429` when the request limit is exceeded.

### Exercise 4.4: Cost guard implementation

The cost guard estimates token usage from request/response length and accumulates daily spend. If the configured daily budget is exceeded, the API rejects new requests with `503`. In production this should use persistent storage such as Redis or a database so the budget survives restarts.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

The final app exposes:

```text
GET /health
GET /ready
```

`/health` is for liveness: the platform can restart the service if it fails. `/ready` is for readiness: the load balancer should send traffic only when this returns OK.

### Exercise 5.2: Graceful shutdown

The final app uses FastAPI lifespan handling and a `SIGTERM` handler. On shutdown it marks the service as not ready and logs the shutdown event. This avoids dropping traffic abruptly.

### Exercise 5.3: Stateless design

The application stores configuration in environment variables and does not depend on local disk state. This allows multiple replicas to serve requests. Shared state such as rate-limit counters or sessions should be moved to Redis in a real deployment.

### Exercise 5.4: Load balancing

The production Docker Compose stack uses Nginx as a reverse proxy/load balancer in front of agent replicas. In cloud platforms, Render/Railway/Cloud Run provide routing and load balancing at the platform level.

### Exercise 5.5: Test stateless

Stateless behavior can be tested by sending repeated requests across multiple replicas and confirming responses do not depend on local process memory. For rate limits and cost guard in true production, Redis should be used so all replicas share the same counters.

## Part 6: Final Project

### Production readiness validation

Command:

```powershell
cd "D:\VinUni\GG Colab\Day 12\day12_BuiMinhHieu-2A202600876\06-lab-complete"
$env:PYTHONIOENCODING="utf-8"
..\.venv\Scripts\python.exe check_production_ready.py
```

Result:

```text
20/20 checks passed (100%)
PRODUCTION READY
```

The final project includes:

- Multi-stage Dockerfile
- Docker Compose stack
- `.dockerignore`
- Health and readiness endpoints
- API key authentication
- Rate limiting
- Cost guard
- Environment-based config
- Structured logging
- Graceful shutdown
- Render/Railway deployment config
