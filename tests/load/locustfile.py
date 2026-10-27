"""Locust Load Testing Suite for AegisGate Production Performance Benchmarking.

Workloads simulate realistic developer and AI Agent traffic:
- Read endpoints: /health, /api/plugins, /api/rules, /api/monitor/executions, /api/executions/page
- Write endpoints: /api/monitor/executions (sync & async execution lifecycle)
- Streaming endpoints: /api/monitor/events (SSE stream connection handshake)
- MCP flows: /api/mcp/config, /api/plugins/sqlserver_prod/mcp-config, /api/knowledge
"""

import random

from locust import HttpUser, between, task


class AegisGateUser(HttpUser):
    """Simulates an AI Agent or Developer interacting with AegisGate."""

    wait_time = between(0.05, 0.2)  # High-throughput realistic internal agent pacing

    def on_start(self) -> None:
        """Initialize session and seed sample query patterns."""
        self.sample_queries = [
            ("SELECT * FROM Customers WHERE Id = 101;", "READ"),
            ("SELECT * FROM Orders WHERE Amount > 1500;", "READ"),
            ("UPDATE Inventory SET Stock = Stock - 1 WHERE ItemId = 99;", "WRITE"),
            ("SELECT COUNT(*) FROM Invoices WHERE Status = 'PAID';", "READ"),
            ("SELECT TOP 10 * FROM Products ORDER BY Price DESC;", "READ"),
        ]
        self.created_exec_ids: list[str] = []

    @task(5)
    def health_check(self) -> None:
        """Rapid health ping (read)."""
        self.client.get("/health", name="/health")

    @task(10)
    def list_plugins(self) -> None:
        """Retrieve registered plugin profiles (read)."""
        self.client.get("/api/plugins", name="/api/plugins")

    @task(10)
    def list_rules(self) -> None:
        """Retrieve active governance rules (read)."""
        self.client.get("/api/rules", name="/api/rules")

    @task(5)
    def get_mcp_config(self) -> None:
        """Retrieve MCP server tool definitions and server configurations (MCP flow)."""
        self.client.get("/api/mcp/config", name="/api/mcp/config")

    @task(5)
    def list_knowledge(self) -> None:
        """Explore cached schema knowledge chunks (MCP flow)."""
        self.client.get("/api/knowledge", name="/api/knowledge")

    @task(15)
    def list_executions(self) -> None:
        """Fetch latest 50 execution logs (read)."""
        self.client.get("/api/monitor/executions?limit=50", name="/api/monitor/executions")

    @task(10)
    def paginate_executions(self) -> None:
        """Cursor pagination and search on audit logs (read)."""
        self.client.get("/api/executions/page?limit=20", name="/api/executions/page")

    @task(20)
    def submit_execution_sync(self) -> None:
        """Submit query with synchronous wait for dry-run and execution (write)."""
        query, q_type = random.choice(self.sample_queries)
        payload = {
            "target_id": "sqlserver_prod",
            "query": query,
            "reasoning": "Load test automated AI query submission",
        }
        with self.client.post(
            "/api/monitor/executions?wait=true",
            json=payload,
            name="/api/monitor/executions [sync]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                try:
                    data = resp.json()
                    exec_id = data.get("id")
                    if exec_id and len(self.created_exec_ids) < 50:
                        self.created_exec_ids.append(exec_id)
                    resp.success()
                except Exception:
                    resp.failure("Failed to parse JSON response")
            elif resp.status_code == 429:
                # 429 is expected under severe load backpressure, track separately
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(10)
    def submit_execution_async(self) -> None:
        """Submit query in background mode (write)."""
        query, _ = random.choice(self.sample_queries)
        payload = {
            "target_id": "sqlserver_prod",
            "query": query,
            "reasoning": "Load test async background dispatch",
        }
        self.client.post(
            "/api/monitor/executions?wait=false",
            json=payload,
            name="/api/monitor/executions [async]",
        )

    @task(5)
    def get_execution_detail(self) -> None:
        """Fetch details of a previously submitted execution (read)."""
        if self.created_exec_ids:
            exec_id = random.choice(self.created_exec_ids)
            self.client.get(
                f"/api/monitor/executions/{exec_id}",
                name="/api/monitor/executions/{id}",
            )

    @task(5)
    def sse_event_stream_connect(self) -> None:
        """Connect to SSE endpoint and stream initial handshake (streaming read)."""
        with self.client.get(
            "/api/monitor/events",
            stream=True,
            timeout=5.0,
            name="/api/monitor/events [stream]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                # Read initial chunk (connected packet)
                for chunk in resp.iter_content(chunk_size=512):
                    if b"connected" in chunk:
                        resp.success()
                        break
            else:
                resp.failure(f"SSE connect failed: {resp.status_code}")
            resp.close()
