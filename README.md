# Comfy API Simplified
This is a little python wrapper over the [ComfyUI](https://github.com/comfyanonymous/ComfyUI) API. It allows you to edit API-format ComfyUI workflows and queue them programmaticaly to the already running ComfyUI.

I use it to iterate over multiple prompts and key parameters of workflow and get hundreds of images overnight to cherrypick from.

## Limitations

This wrapper only calls "/prompt" method to queue prompt. For now there is no way to track the status of prompts or to retrieve the results from the server -- it is possible, but it is simply not needed in my case for now. May be I will add it in future.

Only Basic auth and no auth (for local server) are supported.

## Install

`pip3 install comfy_api_simplified`

## Use prerequisits

### Prepare workflow

You would like to have your node titles unique. Usually both positive and negative prompts have title "CLIP Text Encode (Prompt)", you would like to at least give them different names in case you would like to change it's parameters from python.

### Enable "dev options"

In ComfyUI settings, check "Enable Dev mode Options":
![Alt text](misc/dev_opt.png)

### Download your workflow in API-format
<img src="misc/download.png" width="150">

### Have running ComfyUI server

## Use

See [examples](examples/queue_with_different_params.py).

## Additional info
Check out official ComfyUI API examples (no need for this package for them): https://github.com/comfyanonymous/ComfyUI/tree/master/script_examples