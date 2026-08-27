import asyncio
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import src.Agent as agent_module


async def main() -> None:
    events = []
    async for event in agent_module.stream(
        "SONY WH-1000XM5", thread_id=f"sync-test-{uuid.uuid4().hex[:8]}"
    ):
        events.append(event)

    tools = [e for e in events if e["type"] == "tool"]
    product_events = [e for e in events if e["type"] == "products"]
    tokens = "".join(e.get("text", "") for e in events if e["type"] == "token")

    print(f"tool events: {len(tools)}")
    print(f"products events: {len(product_events)}")
    if product_events:
        products = product_events[-1]["products"]
        print(f"products in event: {len(products)}")
        for p in products[:3]:
            print(f"  - {p['name']} | {p['price']} EGP | img={'yes' if p.get('thumbnail') else 'no'}")
    print(f"\nreply (first 250 chars): {tokens[:250]}")

    assert not ("http://" in tokens or "https://" in tokens), "REPLY CONTAINS LINKS!"
    assert product_events and len(product_events[-1]["products"]) >= 1, "NO PRODUCTS EVENT!"
    print("\nOK: no links in reply + products event matches agent results")


if __name__ == "__main__":
    asyncio.run(main())
