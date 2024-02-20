import logging
import sys
from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

api = ComfyApiWrapper("http://192.168.0.22:8188/")
# api = ComfyApiWrapper("https://smth.com/", user="user", password="password")

wf = ComfyWorkflowWrapper("examples/workflow_api_i2i.json")

input_filename = "examples/input_image.png"

image_metadata = api.upload_image(input_filename)
print(image_metadata)

wf.set_node_param("Load Image", "image", f"{image_metadata['subfolder']}/{image_metadata['name']}")

results = api.queue_and_wait_images(wf, output_node_title="Save Image")
for filename, image_data in results.items():
    with open(f"{filename}", "wb+") as f:
        f.write(image_data)