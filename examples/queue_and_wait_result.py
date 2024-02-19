from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper

api = ComfyApiWrapper("http://192.168.0.22:8188/")
# api = ComfyApiWrapper("https://smth.com/", user="user", password="password")

wf = ComfyWorkflowWrapper("examples/workflow_api.json")
results = api.queue_and_wait_images(wf, "Save Image")
for filename, image_data in results.items():
    with open(f"{filename}", "wb+") as f:
        f.write(image_data)