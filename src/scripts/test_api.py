import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient

from src.main import app


def main() -> None:
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        print(f"GET /health -> {health.status_code}: {health.json()['message']}")

        r1 = client.post(
            "/api/v1/chat",
            json={"message": "I need a laptop bag under 800 EGP", "thread_id": "api-demo"},
        )
        body = r1.json()
        print(f"\nPOST /chat -> {r1.status_code}")
        print(f"Agent: {body['data']['reply'][:300]}")

        r2 = client.post(
            "/api/v1/chat",
            json={"message": "What was my budget?", "thread_id": "api-demo"},
        )
        body2 = r2.json()
        print(f"\nPOST /chat (memory check) -> {r2.status_code}")
        print(f"Agent: {body2['data']['reply'][:200]}")

        print("\nPOST /chat/stream ->")
        with client.stream(
            "POST", "/api/v1/chat/stream", json={"message": "gaming mouse", "thread_id": "api-demo"}
        ) as resp:
            tokens = []
            tools = 0
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[len("data: "):])
                if event["type"] == "tool":
                    tools += 1
                    print("  [tool call]", event["name"])
                elif event["type"] == "token":
                    tokens.append(event["text"])
                elif event["type"] == "done":
                    break
            print("  Agent:", "".join(tokens)[:300])
            print(f"  ({tools} tool call, {len(''.join(tokens))} chars streamed)")


if __name__ == "__main__":
    main()
