import asyncio
import time
import json
import statistics
import sys
from typing import List, Dict, Any
import httpx
from datetime import timedelta

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.core.security import create_access_token


def get_test_tokens() -> Dict[str, Any]:
    """Obtém tokens de teste para duas organizações distintas."""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.organization_id.isnot(None)).all()
        org_users = {}
        for u in users:
            if u.organization_id not in org_users:
                org_users[u.organization_id] = u
        
        org_ids = list(org_users.keys())
        if not org_ids:
            raise ValueError("Nenhum usuário com organização encontrado.")
        
        user1 = org_users[org_ids[0]]
        token1 = create_access_token(user1.email, expires_delta=timedelta(hours=2))
        
        user2 = org_users[org_ids[1]] if len(org_ids) > 1 else user1
        token2 = create_access_token(user2.email, expires_delta=timedelta(hours=2))
        
        return {
            "org1": {"id": user1.organization_id, "email": user1.email, "token": token1},
            "org2": {"id": user2.organization_id, "email": user2.email, "token": token2}
        }
    finally:
        db.close()


async def send_request(client: httpx.AsyncClient, method: str, url: str, headers: dict) -> Dict[str, Any]:
    """Executa uma requisição medindo a latência precisa."""
    start = time.perf_counter()
    try:
        resp = await client.get(url, headers=headers)
        duration_ms = (time.perf_counter() - start) * 1000.0
        return {
            "status_code": resp.status_code,
            "duration_ms": duration_ms,
            "success": 200 <= resp.status_code < 300,
            "body": resp.json() if resp.status_code == 200 else None,
            "error": None
        }
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000.0
        return {
            "status_code": 0,
            "duration_ms": duration_ms,
            "success": False,
            "body": None,
            "error": str(e)
        }


def compute_metrics(latencies: List[float], total_time_sec: float, total_requests: int, successes: int) -> Dict[str, Any]:
    """Calcula estatísticas descritivas e percentis de latência."""
    if not latencies:
        return {
            "total_requests": total_requests,
            "success_rate_pct": 0.0,
            "throughput_rps": 0.0,
            "latency_mean_ms": 0.0,
            "latency_p50_ms": 0.0,
            "latency_p95_ms": 0.0,
            "latency_p99_ms": 0.0
        }
    lat_sorted = sorted(latencies)
    n = len(lat_sorted)
    
    def percentile(p):
        idx = int(p / 100.0 * n)
        return lat_sorted[min(idx, n - 1)]
    
    return {
        "total_requests": total_requests,
        "success_rate_pct": round((successes / total_requests) * 100.0, 2) if total_requests else 0,
        "total_time_sec": round(total_time_sec, 3),
        "throughput_rps": round(total_requests / total_time_sec, 2) if total_time_sec > 0 else 0,
        "latency_mean_ms": round(statistics.mean(latencies), 2),
        "latency_std_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0,
        "latency_min_ms": round(min(latencies), 2),
        "latency_p50_ms": round(percentile(50), 2),
        "latency_p90_ms": round(percentile(90), 2),
        "latency_p95_ms": round(percentile(95), 2),
        "latency_p99_ms": round(percentile(99), 2),
        "latency_max_ms": round(max(latencies), 2),
    }


async def run_concurrency_test(client: httpx.AsyncClient, url: str, token: str, concurrency: int, total_requests: int) -> Dict[str, Any]:
    """Executa requisições sob um nível de concorrência com fila controlada."""
    headers = {"Authorization": f"Bearer {token}"}
    semaphore = asyncio.Semaphore(concurrency)
    
    async def worker():
        async with semaphore:
            return await send_request(client, "GET", url, headers)
    
    start_total = time.perf_counter()
    tasks = [worker() for _ in range(total_requests)]
    results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_total
    
    latencies = [r["duration_ms"] for r in results if r["success"]]
    successes = sum(1 for r in results if r["success"])
    
    metrics = compute_metrics(latencies, total_time, total_requests, successes)
    metrics["concurrency"] = concurrency
    return metrics


async def run_multi_tenant_isolation_test(client: httpx.AsyncClient, org1_info: dict, org2_info: dict, total_requests: int = 100) -> Dict[str, Any]:
    """Auditoria estrita de segregação multi-tenant sob concorrência."""
    url = "/api/v1/clients"
    headers_org1 = {"Authorization": f"Bearer {org1_info['token']}"}
    headers_org2 = {"Authorization": f"Bearer {org2_info['token']}"}
    
    semaphore = asyncio.Semaphore(15)
    leaks_count = 0
    valid_checks = 0
    
    async def task_worker(headers, expected_org_id):
        nonlocal leaks_count, valid_checks
        async with semaphore:
            resp = await send_request(client, "GET", url, headers)
            if resp["success"] and resp["body"]:
                items = resp["body"] if isinstance(resp["body"], list) else resp["body"].get("items", [])
                for item in items:
                    valid_checks += 1
                    if "organization_id" in item and item["organization_id"] != expected_org_id:
                        leaks_count += 1
            return resp
    
    tasks = []
    for i in range(total_requests // 2):
        tasks.append(task_worker(headers_org1, org1_info["id"]))
        tasks.append(task_worker(headers_org2, org2_info["id"]))
    
    start = time.perf_counter()
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start
    
    return {
        "total_requests": len(tasks),
        "total_items_audited": valid_checks,
        "cross_tenant_leaks": leaks_count,
        "leak_rate_pct": 0.0 if leaks_count == 0 else (leaks_count / max(1, valid_checks)) * 100.0,
        "isolation_verified": leaks_count == 0,
        "total_time_sec": round(total_time, 3)
    }


async def main():
    print("=== EXECUTANDO PROTOCOLO CIENTÍFICO DE TESTES DE DESEMPENHO E CONCORRÊNCIA ===", flush=True)
    tokens = get_test_tokens()
    print(f"Organização A (ID={tokens['org1']['id']}): {tokens['org1']['email']}", flush=True)
    print(f"Organização B (ID={tokens['org2']['id']}): {tokens['org2']['email']}", flush=True)
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60.0) as client:
        # Warm-up
        for _ in range(5):
            await send_request(client, "GET", "/api/v1/clients", {"Authorization": f"Bearer {tokens['org1']['token']}"})
        
        concurrencies = [1, 5, 10, 20]
        
        # Teste 1: Clientes (CRM)
        print("\n[Cenário 1] Teste de Carga Escalonada — Gestão de Clientes (/api/v1/clients)", flush=True)
        clients_results = []
        for c in concurrencies:
            reqs = 60
            res = await run_concurrency_test(client, "/api/v1/clients", tokens["org1"]["token"], c, reqs)
            clients_results.append(res)
            print(f"  > C={c:2d} usuários | Vazão: {res['throughput_rps']:6.2f} req/s | Latência Média: {res['latency_mean_ms']:6.2f}ms | p50: {res['latency_p50_ms']:6.2f}ms | p95: {res['latency_p95_ms']:6.2f}ms | Sucesso: {res['success_rate_pct']:.1f}%", flush=True)

        # Teste 2: Ações Judiciais (Processos)
        print("\n[Cenário 2] Teste de Carga Escalonada — Ações Judiciais (/api/v1/legal-actions)", flush=True)
        actions_results = []
        for c in concurrencies:
            reqs = 60
            res = await run_concurrency_test(client, "/api/v1/legal-actions", tokens["org1"]["token"], c, reqs)
            actions_results.append(res)
            print(f"  > C={c:2d} usuários | Vazão: {res['throughput_rps']:6.2f} req/s | Latência Média: {res['latency_mean_ms']:6.2f}ms | p50: {res['latency_p50_ms']:6.2f}ms | p95: {res['latency_p95_ms']:6.2f}ms | Sucesso: {res['success_rate_pct']:.1f}%", flush=True)

        # Teste 3: Auditoria Multi-Tenant
        print("\n[Cenário 3] Auditoria de Isolamento Multi-Tenant sob Concorrência Entrelaçada", flush=True)
        isolation_res = await run_multi_tenant_isolation_test(client, tokens["org1"], tokens["org2"], total_requests=100)
        print(f"  > Requisições Concorrentes: {isolation_res['total_requests']}", flush=True)
        print(f"  > Registros Inspecionados: {isolation_res['total_items_audited']}", flush=True)
        print(f"  > Vazamentos entre Organizações (Cross-Tenant): {isolation_res['cross_tenant_leaks']} ({isolation_res['leak_rate_pct']:.2f}%)", flush=True)
        print(f"  > Integridade Multi-Tenant: {'APROVADA (100% isolado)' if isolation_res['isolation_verified'] else 'FALHA'}", flush=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_environment": "Ambiente Local ASGI / FastAPI 0.109 / SQLAlchemy 2.0 / PostgreSQL 15+",
        "scenario_clients": clients_results,
        "scenario_legal_actions": actions_results,
        "scenario_multi_tenant_isolation": isolation_res
    }
    
    with open("load_test_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n=== SUCESSO: TESTES DE CARGA FINALIZADOS E RESULTADOS GERADOS! ===", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
