import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result
from utils.path import get_buckyball_path

config = {
    "name": "palladium Verilog",
    "description": "generate verilog code",
    "flows": ["palladium"],
    "triggers": [http("POST", "/palladium/verilog")],
    "enqueues": ["palladium.verilog"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    bbdir = get_buckyball_path()
    body = request.body or {}

    # Get config name, must be provided
    config_name = body.get("config")
    if not config_name or config_name == "None":
        return ApiResponse(
            status=400,
            body={
                "status": "error",
                "message": "Configuration name is required. Please specify --config_name parameter.",
                "example": './bbdev palladium --verilog "--config_name sims.palladium.BuckyballToyP2EConfig"',
            },
        )

    data = {
        "config": config_name,
        "balltype": body.get("balltype"),
        "output_dir": body.get("output_dir", f"{bbdir}/arch/build/"),
    }
    await ctx.enqueue({"topic": "palladium.verilog", "data": data})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
