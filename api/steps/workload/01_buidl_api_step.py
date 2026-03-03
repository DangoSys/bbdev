import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result
from utils.path import get_buckyball_path

config = {
    "name": "build workload",
    "description": "build workload",
    "flows": ["workload"],
    "triggers": [http("POST", "/workload/build")],
    "enqueues": ["workload.build"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    bbdir = get_buckyball_path()
    body = request.body or {}
    data = {"workload": body.get("workload", "")}
    await ctx.enqueue({"topic": "workload.build", "data": data})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
