import pytest
from comfy_api_simplified.comfy_api_wrapper import ComfyApiWrapper
from comfy_api_simplified.comfy_workflow_wrapper import ComfyWorkflowWrapper
import os

test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data")


@pytest.fixture
def api_wrapper():
    return ComfyApiWrapper("http://127.0.0.1:8188")


@pytest.fixture
def workflow_wrapper():
    wrapper = ComfyWorkflowWrapper(os.path.join(test_data_dir, "workflow_api.json"))
    return wrapper
