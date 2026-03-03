import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Firesim Infrasetup",
    "description": "infrasetup",
    "flows": ["firesim"],
    "triggers": [http("POST", "/firesim/infrasetup")],
    "enqueues": ["firesim.infrasetup"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    data = {"jobs": body.get("jobs", 16)}
    await ctx.enqueue({"topic": "firesim.infrasetup", "data": data})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
