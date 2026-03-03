import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result
from utils.path import get_buckyball_path

config = {
    "name": "running sardine",
    "description": "running sardine",
    "flows": ["sardine"],
    "triggers": [http("POST", "/sardine/run")],
    "enqueues": ["sardine.run"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    bbdir = get_buckyball_path()

    body = request.body or {}

    data = {"workload": body.get("workload", "")}

    await ctx.enqueue({"topic": "sardine.run", "data": data})

    # ==================================================================================
    # Wait for execution result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
