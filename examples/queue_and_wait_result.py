import logging
import sys
from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

api = ComfyApiWrapper("http://192.168.0.22:8188/")
# api = ComfyApiWrapper("https://smth.com/", user="user", password="password")

wf = ComfyWorkflowWrapper("examples/workflow_api_t2i.json")
wf.set_node_param("positive", "text", "1girl, brown hair, baking croissant, fantasy medieval bakery, medium shot, (masterpiece), (best quality)")
wf.set_node_param("KSampler", "steps", 25)

results = api.queue_and_wait_images(wf, output_node_title="Save Image")
for filename, image_data in results.items():
    with open(f"{filename}", "wb+") as f:
        f.write(image_data)