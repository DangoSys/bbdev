"""
bebop p2e batch event handler

Runs bebop p2e nextest batch regression (aligned with runworkload):
  1. Resolve VSRC from bitstream case and rebuild VVAC runtime into case dir
  2. Build bebop with p2e feature and OUT_PATH=<case_dir>
  3. Run cargo nextest with the same OUT_PATH (serial, single FPGA)
"""
import os
import re
import shlex
import sys
import tomllib
from pathlib import Path

from motia import FlowContext, queue

utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)
bebop_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if bebop_path not in sys.path:
    sys.path.insert(0, bebop_path)

from utils.event_common import require_chip
from utils.path import bebop_cargo_env, get_buckyball_path, rtl_dir, workload_tests_root, workloads_output_root
from utils.search_workload import search_workload
from utils.stream_run import stream_run_logger_async
from utils.event_common import check_result, get_origin_trace_id
from regression import regression_workload_toml
from regression_harness import nextest_harness_args

config = {
    "name": "bebop-p2e-batch",
    "description": "Run bebop p2e nextest batch regression",
    "flows": ["bebop"],
    "triggers": [queue("bebop.p2e.batch")],
    "enqueues": [],
}


def resolve_runtime_config(bitstream: str, requested_config: object) -> str:
    if isinstance(requested_config, str) and requested_config:
        return requested_config

    build_dir = os.path.dirname(os.path.dirname(os.path.abspath(bitstream)))
    case_name = os.path.basename(build_dir)
    return re.sub(r"-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$", "", case_name)


async def handler(input_data: dict, ctx: FlowContext) -> None:
    origin_tid = get_origin_trace_id(input_data, ctx)
    bbdir = get_buckyball_path()
    bebop_dir = f"{bbdir}/bebop"
    nextest_config = f"{os.path.dirname(os.path.abspath(__file__))}/scripts/nextest.toml"

    bitstream = input_data.get("bitstream", "")
    if not bitstream or not os.path.isfile(bitstream):
        ctx.logger.error(f"bitstream .bit file not found: {bitstream}")
        await check_result(
            ctx, 1, continue_run=False,
            extra_fields={"error": "bitstream_not_found", "bitstream": bitstream},
            trace_id=origin_tid,
        )
        return

    bitstream = os.path.abspath(bitstream)
    # Same as runworkload: case home is parent of fpgaCompDir/
    build_dir = os.path.dirname(os.path.dirname(bitstream))
    if not os.path.isdir(build_dir):
        ctx.logger.error(f"P2E build case not found for bitstream: {build_dir}")
        await check_result(
            ctx, 1, continue_run=False,
            extra_fields={"error": "build_dir_not_found", "build_dir": build_dir},
            trace_id=origin_tid,
        )
        return

    chip = input_data.get("chip")
    if not chip:
        ctx.logger.error("Missing required parameter: chip must be specified")
        await check_result(
            ctx, 1, continue_run=False,
            extra_fields={"error": "missing_chip"},
            trace_id=origin_tid,
        )
        return
    elf_root = workloads_output_root(bbdir)
    cargo_env = bebop_cargo_env(bbdir, chip)

    test_type = input_data.get("test", "elf-tests")
    diff = bool(input_data.get("diff", False))
    try:
        workload_toml = regression_workload_toml(chip, "p2e", test_type, bbdir, diff=diff)
    except ValueError as e:
        ctx.logger.error(str(e))
        await check_result(
            ctx, 1, continue_run=False,
            extra_fields={"error": "invalid_regression", "test": test_type, "chip": chip},
            trace_id=origin_tid,
        )
        return

    ctx.logger.info(f"Running {test_type} with workload config: {workload_toml} diff={diff}")
    ctx.logger.info(f"P2E case dir (from bitstream): {build_dir}")

    if test_type == "elf-tests":
        workload_names = tomllib.loads(Path(workload_toml).read_text())["workloads"]["tests"]
        converter = os.path.join(bbdir, "bbdev", "api", "steps", "workload", "scripts", "elf2hex.py")
        search_root = workload_tests_root(bbdir, chip)
        for image_name in workload_names:
            if not image_name.endswith(".hex"):
                raise ValueError(f"P2E ELF workload must end in .hex: {image_name}")
            elf_name = image_name.removesuffix(".hex")
            elf_path = search_workload(search_root, elf_name)
            if elf_path is None:
                raise FileNotFoundError(f"P2E workload ELF not found: {elf_name}")
            convert_result = await stream_run_logger_async(
                cmd=shlex.join(["python3", converter, elf_path]),
                logger=ctx.logger,
                cwd=os.path.dirname(elf_path),
                stdout_prefix=f"p2e image {elf_name}",
                stderr_prefix=f"p2e image {elf_name}",
            )
            if convert_result.returncode != 0:
                await check_result(
                    ctx,
                    convert_result.returncode,
                    continue_run=False,
                    extra_fields={"task": "tohex", "elf": elf_path},
                    trace_id=origin_tid,
                )
                return

    vsrc_dir = rtl_dir(bbdir, chip, "p2e", input_data.get("vsrc_dir"))
    # Rebuild VVAC host runtime in the bitstream case (same as runworkload).
    manifest = Path(bebop_dir) / "Cargo.toml"
    features = ["p2e"]
    runtime_env = {**os.environ.copy(), **cargo_env}
    if diff:
        manifest = Path(bbdir) / "examples" / "chips" / chip / "generated" / "bebop" / "Cargo.toml"
        features.extend(["bemu", "difftest"])
        hpec_home = "/home/x-epic/hpe-24.12.01.s008"
        runtime_env.update({
            "BEBOP_BEMU_P2E_ABI": "1",
            "BEBOP_BEMU_CC": os.path.join(hpec_home, "tools", "gcc-8.3.0", "gcc-8.3.0", "bin", "gcc"),
            "BEBOP_BEMU_CXX": os.path.join(hpec_home, "tools", "gcc-8.3.0", "gcc-8.3.0", "bin", "g++"),
            "BEBOP_BEMU_DTC": os.path.join(bbdir, "result", "bin", "dtc"),
            "CARGO_TARGET_DIR": os.path.join(bebop_dir, "target", f"{chip}-p2e-diff"),
            "BEBOP_BEMU_COMPILER_LIBRARY_PATH": ":".join([
                os.path.join(hpec_home, "tools", "gcc-8.3.0", "gmp-6.2.1", "lib"),
                os.path.join(hpec_home, "tools", "gcc-8.3.0", "mpfr-4.1.0", "lib"),
                os.path.join(hpec_home, "tools", "gcc-8.3.0", "mpc-1.2.1", "lib"),
            ]),
        })
    feature_arg = ",".join(features)
    runtime_cmd = shlex.join([
        "env",
        "BEBOP_P2E_RUNTIME_ONLY=1",
        "BEBOP_P2E_REBUILD_RUNTIME=1",
        f"VSRC_PATH={vsrc_dir}",
        f"OUT_PATH={build_dir}",
        "cargo", "run", "--release",
        "--manifest-path", str(manifest),
        "--bin", "bebop",
        "--features", feature_arg,
        "--", "build", "p2e",
        "--rtl-dir", vsrc_dir,
        "--out-dir", build_dir,
        *( ["--diff"] if diff else [] ),
    ])
    ctx.logger.info("Preparing bebop p2e runtime for the selected bitstream ...")
    runtime_result = await stream_run_logger_async(
        cmd=runtime_cmd,
        logger=ctx.logger,
        cwd=str(manifest.parent),
        stdout_prefix="bebop p2e runtime",
        stderr_prefix="bebop p2e runtime",
        env=runtime_env,
    )
    rtcfg_path = os.path.join(build_dir, "vvacDir", "runtimeDir", "rtcfg")
    libvctb_path = os.path.join(build_dir, "vvacDir", "runtimeDir", "lib", "lib_arm", "libvCtb.so")
    runtime_artifacts = [rtcfg_path, libvctb_path]
    if diff:
        runtime_artifacts.append(os.path.join(build_dir, "libriscv.so"))
    if runtime_result.returncode != 0 or not all(os.path.isfile(path) for path in runtime_artifacts):
        missing = [path for path in runtime_artifacts if not os.path.isfile(path)]
        if missing:
            ctx.logger.error(f"P2E runtime artifacts missing: {missing}")
        await check_result(
            ctx,
            runtime_result.returncode or 1,
            continue_run=False,
            extra_fields={
                "task": "runtime",
                "vsrc_dir": vsrc_dir,
                "build_dir": build_dir,
                "missing": missing,
            },
            trace_id=origin_tid,
        )
        return

    # cargo global --config so OUT_PATH reaches bebop-p2e build.rs (same as runworkload).
    cargo_out = f"--config=\"env.OUT_PATH='{build_dir}'\""

    # ── Build bebop p2e (tests), linked against case libvCtb ───────────────
    build_cmd = (
        f"nix develop -c cargo {cargo_out} build --release "
        f"--manifest-path {shlex.quote(str(manifest))} --features {shlex.quote(feature_arg)} --tests"
    )
    ctx.logger.info("Building bebop p2e (tests)...")
    build_result = await stream_run_logger_async(
        cmd=build_cmd,
        logger=ctx.logger,
        cwd=bebop_dir,
        stdout_prefix="bebop p2e build",
        stderr_prefix="bebop p2e build",
        env=runtime_env,
    )

    if build_result.returncode != 0:
        await check_result(
            ctx, build_result.returncode, continue_run=False,
            extra_fields={"task": "build", "backend": "p2e", "build_dir": build_dir},
            trace_id=origin_tid,
        )
        return

    # ── Run nextest ───────────────────────────────────────────────────────
    env = runtime_env.copy()
    env["OUT_PATH"] = build_dir
    harness = nextest_harness_args(workload_toml, elf_root, env, p2e_bitstream=bitstream)
    nextest_cmd = (
        f"nix develop -c cargo {cargo_out} nextest run --release "
        f"--manifest-path {shlex.quote(str(manifest))} --features {shlex.quote(feature_arg)} "
        f"--test test_p2e --config-file \"{nextest_config}\" {harness}"
    )

    ctx.logger.info(f"Running bebop p2e nextest: {nextest_cmd}")
    run_result = await stream_run_logger_async(
        cmd=nextest_cmd,
        logger=ctx.logger,
        cwd=bebop_dir,
        stdout_prefix="bebop p2e batch",
        stderr_prefix="bebop p2e batch",
        env=env,
    )

    extra_fields = {
        "task": "batch",
        "backend": "p2e",
        "chip": chip,
        "bitstream": bitstream,
        "build_dir": build_dir,
        "test_type": test_type,
        "diff": diff,
        "nextest_config": nextest_config,
        "workload_toml": workload_toml,
    }

    if input_data.get("from_regression_check"):
        # Model accuracy is filled by eval-performance, not pk pass rate.
        if run_result.returncode != 0:
            await check_result(
                ctx, run_result.returncode, continue_run=False,
                extra_fields={**extra_fields, "error": "pk_tests_failed"},
                trace_id=origin_tid,
            )
            return

    await check_result(
        ctx,
        run_result.returncode,
        continue_run=False,
        extra_fields=extra_fields,
        trace_id=origin_tid,
    )
