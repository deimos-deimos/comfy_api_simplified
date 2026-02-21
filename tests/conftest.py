import os
import pytest
from comfy_api_simplified.comfy_api_wrapper import ComfyApiWrapper
from comfy_api_simplified.comfy_workflow_wrapper import ComfyWorkflowWrapper

test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data")

_COMFY_SERVER_URL = os.environ.get("COMFY_SERVER_URL", "http://192.168.31.206:8188/")


@pytest.fixture
def api_wrapper():
    return ComfyApiWrapper(_COMFY_SERVER_URL)


@pytest.fixture
def workflow_wrapper():
    wrapper = ComfyWorkflowWrapper(os.path.join(test_data_dir, "workflow_api.json"))
    return wrapper
