import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Verilator Complete Workflow",
    "description": "trigger complete verilator workflow",
    "flows": ["verilator"],
    "triggers": [http("POST", "/verilator/run")],
    "enqueues": ["verilator.run"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}

    data = {
        "binary": body.get("binary", ""),
        "config": body.get("config", "sims.verilator.BuckyballToyVerilatorConfig"),
        "jobs": body.get("jobs", "16"),
        "batch": body.get("batch", False),
        "cosim": body.get("cosim", False),
        "from_run_workflow": True,
    }

    await ctx.enqueue({"topic": "verilator.run", "data": data})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
