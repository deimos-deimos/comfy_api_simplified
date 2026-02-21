import json
import pytest
from comfy_api_simplified.comfy_api_wrapper import ComfyApiWrapper
from comfy_api_simplified.comfy_workflow_wrapper import ComfyWorkflowWrapper
from PIL import Image, ImageChops
import numpy as np

import io
import os


from .conftest import test_data_dir


# Compare two images
def compare_images(img1: Image.Image, img2: Image.Image) -> bool:
    arr1 = np.array(img1)
    arr2 = np.array(img2)
    if arr1.shape != arr2.shape:
        return False

    distance = np.sqrt(np.sum((arr1 - arr2) ** 2, axis=-1))
    threshold = 1
    if np.mean(distance) < threshold:
        return True
    return False


def load_image_from_test_data(image_name):
    path = os.path.join(test_data_dir, image_name)
    return Image.open(path)


def test_upload_image(api_wrapper: ComfyApiWrapper):
    path = os.path.join(test_data_dir, "input.png")
    assert os.path.exists(path)
    try:
        response = api_wrapper.upload_image(path)
    except:
        pytest.fail("Unexpected error")

    assert response


def test_queue_prompt(
    api_wrapper: ComfyApiWrapper, workflow_wrapper: ComfyWorkflowWrapper
):
    image_metadata = api_wrapper.upload_image(os.path.join(test_data_dir, "input.png"))

    workflow_wrapper.set_node_param(
        "Load Image",
        "image",
        f"{image_metadata['subfolder']}/{image_metadata['name']}",
    )

    response = api_wrapper.queue_prompt(workflow_wrapper)
    prompt_id = response["prompt_id"]
    assert api_wrapper.get_queue_size_before(prompt_id) == 0


@pytest.mark.asyncio
async def test_get_history(
    api_wrapper: ComfyApiWrapper, workflow_wrapper: ComfyWorkflowWrapper
):
    image_metadata = api_wrapper.upload_image(os.path.join(test_data_dir, "input.png"))

    workflow_wrapper.set_node_param(
        "Load Image",
        "image",
        f"{image_metadata['subfolder']}/{image_metadata['name']}",
    )

    prompt_id, images = await api_wrapper.queue_prompt_and_wait(workflow_wrapper)

    try:
        response = api_wrapper.get_history(prompt_id)
    except:
        pytest.fail("Unexpected error")

    assert response


def test_workflow_wrapper_from_dict(workflow_wrapper: ComfyWorkflowWrapper):
    """Test that ComfyWorkflowWrapper can be initialized from a dict (PR #16 feature)."""
    with open(os.path.join(test_data_dir, "workflow_api.json"), "r", encoding="utf-8") as f:
        workflow_dict = json.load(f)

    wrapper = ComfyWorkflowWrapper(workflow_dict)
    assert wrapper.list_nodes() == workflow_wrapper.list_nodes()
    assert dict(wrapper) == dict(workflow_wrapper)


@pytest.mark.asyncio
async def test_queue_prompt_and_wait_returns_tuple(
    api_wrapper: ComfyApiWrapper, workflow_wrapper: ComfyWorkflowWrapper
):
    """Test that queue_prompt_and_wait returns a (prompt_id, images) tuple (PR #16)."""
    image_metadata = api_wrapper.upload_image(os.path.join(test_data_dir, "input.png"))
    workflow_wrapper.set_node_param(
        "Load Image",
        "image",
        f"{image_metadata['subfolder']}/{image_metadata['name']}",
    )

    result = await api_wrapper.queue_prompt_and_wait(workflow_wrapper)
    assert isinstance(result, tuple) and len(result) == 2, "Should return a 2-tuple"
    prompt_id, images = result
    assert isinstance(prompt_id, str) and prompt_id, "prompt_id should be a non-empty string"
    assert isinstance(images, list), "images should be a list"
    for img_bytes in images:
        assert isinstance(img_bytes, bytes), "each image should be bytes"


def test_queue_and_wait_images(
    api_wrapper: ComfyApiWrapper, workflow_wrapper: ComfyWorkflowWrapper
):
    """Test that queue_and_wait_images returns a dict of images (PR #16)."""
    image_metadata = api_wrapper.upload_image(os.path.join(test_data_dir, "input.png"))
    workflow_wrapper.set_node_param(
        "Load Image",
        "image",
        f"{image_metadata['subfolder']}/{image_metadata['name']}",
    )

    result = api_wrapper.queue_and_wait_images(workflow_wrapper, "Save Image")
    assert isinstance(result, dict), "Should return a dict"
    assert len(result) > 0, "Should return at least one image"
    for key, img_bytes in result.items():
        assert isinstance(img_bytes, bytes), f"Image '{key}' should be bytes"
        assert len(img_bytes) > 0, f"Image '{key}' should not be empty"


def test_negative_set_node_param(workflow_wrapper: ComfyWorkflowWrapper):
    try:
        workflow_wrapper.set_node_param(
            "a node that does not exist",
            "image",
            "",
        )
        pytest.fail("Unexpected success")
    except:
        pass


@pytest.mark.asyncio
async def test_get_image(
    api_wrapper: ComfyApiWrapper, workflow_wrapper: ComfyWorkflowWrapper
):
    expected_image = load_image_from_test_data("output.png")

    image_metadata = api_wrapper.upload_image(os.path.join(test_data_dir, "input.png"))

    workflow_wrapper.set_node_param(
        "Load Image",
        "image",
        f"{image_metadata['subfolder']}/{image_metadata['name']}",
    )

    prompt_id, images = await api_wrapper.queue_prompt_and_wait(workflow_wrapper)
    response = api_wrapper.get_history(prompt_id)

    print(response[prompt_id]["outputs"]["9"]["images"][0])
    output = response[prompt_id]["outputs"]["9"]["images"][0]
    filename = output["filename"]
    subfolder = output["subfolder"]
    type = output["type"]
    image = api_wrapper.get_image(filename, subfolder, type)

    returned_image = Image.open(io.BytesIO(image))

    assert compare_images(
        returned_image, expected_image
    ), "The returned image does not match the expected image"
