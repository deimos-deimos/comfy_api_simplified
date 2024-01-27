from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper

api = ComfyApiWrapper("http://192.168.0.22:8188/")
# api = ComfyApiWrapper("https://smth.com/", user="user", password="password")

wf = ComfyWorkflowWrapper("workflow_api.json")

prompts = [
    "1girl, brown hair, baking croissant, fantasy medieval bakery,\n\nmedium shot,\n\n(masterpiece), (best quality)",
    "1girl, brown hair, selling croissants, fantasy medieval market,\n\nmedium shot,\n\n(masterpiece), (best quality)",
    "1girl, brown hair, drinking beer, fantasy medieval pub,\n\nmedium shot,\n\n(masterpiece), (best quality)"
]

wf.set_node_param("negative", "text", "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name, embedding:EasyNegative, embedding:badhandv4, ")
wf.set_node_param("Empty Latent Image", "batch_size", 2)

for i, prompt in enumerate(prompts):
    wf.set_node_param("positive", "text", prompt)
    seed = wf.get_node_param("KSampler (pipe)", "seed")
    wf.set_node_param("KSampler (pipe)", "seed", seed + 10)
    wf.set_node_param("hires", "seed", seed + 10)
    wf.set_node_param("Save Image", "filename_prefix", f"batches/char2/p{i}")
    resp = api.queue_prompt(wf)
    print(resp['prompt_id'])

# wf.save_to_file("modified_wf.json")
