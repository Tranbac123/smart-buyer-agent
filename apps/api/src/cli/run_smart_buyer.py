from __future__ import annotations
import argparse, asyncio, os, json
os.environ.setdefault("PYTHONPATH", os.getcwd())

from services.orchestrator_service import OrchestratorService
from dependencies.tools_provider import get_tool_registry
from dependencies.llm_provider import get_llm
from dependencies.http_client_provider import _build_shared_httpx_client
from packages.control_plane.bootstrap import get_control_plane

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True, help="Product to search, e.g. 'iPhone 13 128GB'")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--prefs", type=str, default="{}",
                   help='JSON, e.g. {"budget":11000000,"required_tags":["fast"]}')
    p.add_argument("--criteria", type=str, default="[]",
                   help='JSON list, e.g. [{"name":"price","weight":0.6,"maximize":false}]')
    p.add_argument("--timeout", type=float, default=20.0)
    args = p.parse_args()

    prefs = json.loads(args.prefs)
    criteria = json.loads(args.criteria)

    tools = get_tool_registry()
    llm = get_llm()
    http = _build_shared_httpx_client()
    control_plane = get_control_plane()

    svc = OrchestratorService(control_plane=control_plane)
    res = await svc.run_smart_buyer(
        query=args.query,
        top_k=args.top_k,
        prefs=prefs,
        criteria=criteria,
        tools=tools,
        llm=llm,
        http=http,
        request_id="cli-run",
        timeout_s=args.timeout,
        channel="cli",
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
