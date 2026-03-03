import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Verilator Cosim",
    "description": "run verilator cosimulation",
    "flows": ["verilator"],
    "triggers": [http("POST", "/verilator/cosim")],
    "enqueues": ["verilator.cosim"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    binary = body.get("binary", "")
    batch = body.get("batch", False)
    if not binary:
        return ApiResponse(
            status=400,
            body={
                "success": False,
                "failure": True,
                "returncode": 400,
                "message": "binary parameter is required",
            },
        )

    await ctx.enqueue({"topic": "verilator.cosim", "data": {**body, "task": "cosim"}})
    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
