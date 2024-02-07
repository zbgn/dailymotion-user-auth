"""Invoke tasks for the backend project."""
import sys

from colorlog import getLogger
from invoke import Collection, Context, task

logger = getLogger(__name__)


@task
def update_dependencies(ctx: Context, *, sync: bool = True) -> None:
    """Update the dependencies."""
    compile_dependencies(ctx, update=True, sync=sync)


@task
def compile_dependencies(ctx: Context, *, update: bool = False, sync: bool = False) -> None:
    """Compile the dependencies."""
    base_args = [
        "-q",
        "--allow-unsafe",
        "--no-emit-options",
        "--resolver=backtracking",
        "--strip-extras",
    ]
    main_args_no_hash = [
        *base_args,
        "--output-file=requirements/main-no-hash.txt",
        "requirements/main.in",
    ]
    main_args = [
        *base_args,
        "--generate-hashes",
        "--output-file=requirements/main.txt",
        "requirements/main.in",
    ]
    dev_args = [
        *base_args,
        "--output-file=requirements/dev.txt",
        "requirements/dev.in",
    ]
    test_args = [
        *base_args,
        "--output-file=requirements/test.txt",
        "requirements/test.in",
    ]
    if update:
        ctx.run("rm -vf requirements/*.txt")
    ctx.run("pip-compile " + " ".join(main_args_no_hash), echo=True)
    ctx.run("pip-compile " + " ".join(main_args), echo=True)
    ctx.run("pip-compile " + " ".join(dev_args), echo=True)
    ctx.run("pip-compile " + " ".join(test_args), echo=True)
    if sync:
        sync_dependencies(ctx)


@task
def sync_dependencies(ctx: Context) -> None:
    """Sync the dependencies."""
    ctx.run("pip-sync requirements/main.txt requirements/dev.txt requirements/test.txt", echo=True)


@task
def tests_all(ctx: Context) -> None:
    """Run all the tests."""
    ctx.run("tox", echo=True)


@task
def tests_run(ctx: Context, *, args: str = "") -> None:
    """
    Run pytests with args.

    Usage:
    ------
    inv tests.run -- -k test_name
    """
    if not args:
        ctx.run("inv tests.run -h")
        logger.error("No arguments provided, exiting...")
        sys.exit(1)
    ctx.run(f"pytest {args}", echo=True)


@task
def server_run_prod(ctx: Context) -> None:
    """Run the server in production mode."""
    ctx.run("uvicorn app.main:app --host 0.0.0.0 --port 8000", echo=True)


@task
def server_run_debug(ctx: Context) -> None:
    """Run the server in debug mode."""
    ctx.run("uvicorn app.main:app --reload --log-level debug", echo=True)


@task
def server_run_reload(ctx: Context) -> None:
    """Run the server with auto-reload."""
    ctx.run("uvicorn app.main:app --reload", echo=True)


dependencies = Collection("dependencies")
dependencies.add_task(update_dependencies, "update")
dependencies.add_task(compile_dependencies, "compile")
dependencies.add_task(sync_dependencies, "sync")
tests = Collection("tests")
tests.add_task(tests_all, "all")
tests.add_task(tests_run, "run")
server = Collection("server")
server.add_task(server_run_prod, "prod")
server.add_task(server_run_debug, "debug")
server.add_task(server_run_reload, "reload")
ns = Collection()
ns.add_collection(dependencies)
ns.add_collection(tests)
ns.add_collection(server)
