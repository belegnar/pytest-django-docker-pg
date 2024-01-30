import dataclasses
import os
import socket
import time
import uuid
from typing import Callable, Optional, cast

import docker
import pytest
from docker.models.containers import Container


@pytest.hookimpl()
def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("pytest-django-docker-pg")
    group.addoption(
        "--django-docker-pg-image",
        action="store",
        dest="django_docker_pg_image",
        default="postgres:16-alpine",
        help="Postgres image to use for tests",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: pytest.Config, parser: pytest.Parser, args: list[str]) -> None:
    options = parser.parse_known_args(args)
    instance, pytest.django_docker_pg_container = start_postgres(  # type: ignore[assignment]
        options.django_docker_pg_image
    )
    os.environ["DB_HOST"] = instance.host
    os.environ["DB_PORT"] = str(instance.port)
    os.environ["DB_USER"] = instance.user
    os.environ["DB_PASSWORD"] = instance.password
    os.environ["DB_DATABASE"] = instance.database


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session):
    container = cast(Container, pytest.django_docker_pg_container)  # type: ignore[reportAttributeAccessIssue]
    assert container
    container.reload()
    if container.status == "running":
        container.kill()
    container.remove(v=True, force=True)


DEFAULT_PG_USER = "postgres"
DEFAULT_PG_PASSWORD = "1"
DEFAULT_PG_DATABASE = "postgres"
LOCALHOST = "127.0.0.1"
PGDATA = "/var/lib/postgresql/data"


def start_postgres(image: str):
    unused_port = find_unused_local_port()
    client = docker.from_env()
    container = client.containers.run(
        name=f"pytest-django-postgres-{uuid.uuid4()}",
        image=image,
        environment={
            "POSTGRES_HOST_AUTH_METHOD": "trust",
            "POSTGRES_USER": DEFAULT_PG_USER,
            "POSTGRES_PASSWORD": DEFAULT_PG_PASSWORD,
            "POSTGRES_DB": DEFAULT_PG_DATABASE,
            "PGDATA": PGDATA,
        },
        command="-c fsync=off -c full_page_writes=off -c synchronous_commit=off -c bgwriter_lru_maxpages=0 -c jit=off",
        ports={5432: unused_port},
        detach=True,
        tmpfs={PGDATA: ""},
        stderr=True,
    )
    assert isinstance(container, Container)

    started_at = time.time()
    while time.time() - started_at < 30:
        container.reload()
        if container.status == "running" and _is_ready(container):
            break

        time.sleep(0.5)
    else:
        raw_logs = client.api.logs(container.id).decode()  # type: ignore[attr-defined]
        pytest.fail(f"Failed to start django test postgres using postgres:16-alpine in 30" f" seconds:\n{raw_logs}")

    return (
        PG(
            host=LOCALHOST,
            port=unused_port,
            user=DEFAULT_PG_USER,
            password=DEFAULT_PG_PASSWORD,
            database=DEFAULT_PG_DATABASE,
        ),
        container,
    )


def _is_ready(container) -> bool:
    bindings = (container.attrs or {}).get("HostConfig", {}).get("PortBindings", {})
    assert bindings
    port = bindings["5432/tcp"][0]["HostPort"]
    return is_pg_ready(
        host=LOCALHOST,
        port=port,
        database=DEFAULT_PG_DATABASE,
        user=DEFAULT_PG_USER,
        password=DEFAULT_PG_PASSWORD,
    )


def _is_ready_psycopg3() -> Optional[Callable[..., bool]]:
    try:
        import psycopg  # type: ignore[import]

        def _is_postgres_ready(*, host: str, port: str, user: str, password: str, **_: str) -> bool:
            try:
                with psycopg.connect(user=user, password=password, host=host, port=port):
                    return True
            except psycopg.OperationalError:
                return False

        return _is_postgres_ready
    except ImportError:
        return None


def _is_ready_psycopg2() -> Optional[Callable[..., bool]]:
    try:
        import psycopg2  # type: ignore[import]

        def _is_postgres_ready(*, host: str, port: str, user: str, password: str, database: str, **_: str) -> bool:
            try:
                with psycopg2.connect(user=user, password=password, host=host, port=port, database=database):
                    return True
            except psycopg2.OperationalError:
                return False

        return _is_postgres_ready
    except ImportError:
        return None


def _is_ready_dummy() -> Callable[..., bool]:
    def _is_postgres_ready(**_: str) -> bool:
        return True

    return _is_postgres_ready


is_pg_ready = _is_ready_psycopg3() or _is_ready_psycopg2() or _is_ready_dummy()


@dataclasses.dataclass(frozen=True)
class PG:
    host: str
    port: int
    user: str
    password: str
    database: str


def find_unused_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]  # type: ignore
