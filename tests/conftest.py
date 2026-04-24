import os
import pytest
from bench.flask_fixture import running


@pytest.fixture(scope="session", autouse=True)
def flask_server():
    with running() as info:
        os.environ["MLOPS_API_URL"] = info.url
        yield info
    os.environ.pop("MLOPS_API_URL", None)
