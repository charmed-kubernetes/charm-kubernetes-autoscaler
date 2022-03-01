import lightkube
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def lightkube_client():
    # Prevent any unit test from actually invoking any lightkube api
    client = MagicMock()
    with patch.object(lightkube.Client, "__new__", return_value=client):
        yield client
