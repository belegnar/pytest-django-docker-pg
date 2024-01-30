import pytest
from docker.models.containers import Container


def test_plugin():
    container = pytest.django_docker_pg_container  # type: ignore[reportAttributeAccessIssue]
    assert isinstance(container, Container)
    container.reload()
    assert container.status == "running"
