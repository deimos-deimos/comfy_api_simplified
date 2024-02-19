from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper

api = ComfyApiWrapper("http://192.168.0.22:8188/")
# api = ComfyApiWrapper("https://smth.com/", user="user", password="password")

wf = ComfyWorkflowWrapper("examples/workflow_api_input_image.json")

input_filename = "examples/input_image.webp"

image_metadata = api.upload_image(input_filename)
print(image_metadata)

wf.set_node_param("input_image", "image", f"{image_metadata['subfolder']}/{image_metadata['name']}")

results = api.queue_and_wait_images(wf, "output_image")
for filename, image_data in results.items():
    with open(f"{filename}", "wb+") as f:
        f.write(image_data)