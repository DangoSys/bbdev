import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Verilator Build",
    "description": "build verilator executable",
    "flows": ["verilator"],
    "triggers": [http("POST", "/verilator/build")],
    "enqueues": ["verilator.build"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    data = {
        "jobs": body.get("jobs", 16),
        "cosim": body.get("cosim", False),
    }
    await ctx.enqueue({"topic": "verilator.build", "data": data})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
