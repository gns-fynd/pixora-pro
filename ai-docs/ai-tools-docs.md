# 1. OpenAI GPT-4o (JSON Mode with Structured Output)

**Installation & Setup:** Install the OpenAI Python SDK and configure your API key via an environment variable. For example:

```bash
pip install --upgrade openai
export OPENAI_API_KEY="your_openai_api_key"
```

Then in code:

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**JSON Mode / Structured Output:** GPT-4o supports “JSON mode,” which constrains outputs to valid JSON. To enable it, set the `response_format` parameter to `{"type": "json_object"}` or `{"type": "json_schema", ...}`.  You must also instruct the model via the system prompt to output JSON (e.g. `"You are a JSON agent."`), otherwise you’ll get an error. Azure’s docs note that both enabling the JSON response format and telling the model to produce JSON are required to avoid malformed output. For example, using a JSON Schema for structured output:

```python
# Define conversation and schema
messages = [
    {"role": "system", "content": "You are a JSON assistant that lists fruits with prices."},
    {"role": "user", "content": "From the following table, extract each fruit's name and price."}
]
schema = {
    "type": "object",
    "properties": {
        "fruits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"}
                },
                "required": ["name", "price"]
            }
        }
    },
    "required": ["fruits"]
}

# Call GPT-4o with JSON Schema (strict output)
response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=messages,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "FruitPrices",
            "strict": True,
            "schema": schema
        }
    }
)
print(response.choices[0].message.content)
```

In the above, `strict: True` ensures the model’s output **exactly** matches the schema. For example, OpenAI’s docs show that with a strict JSON schema the model reliably outputs only the specified JSON fields. The `.message.content` will be a JSON object or string; you can parse it with `json.loads()`.  Always check `response.choices[0].finish_reason` for `"stop"` (complete output) vs `"length"` (truncated) and handle errors:

```python
if response.choices[0].finish_reason != "stop":
    print("Warning: output may be incomplete")
```

Include try/except to catch `OpenAIError` for issues like rate limits or bad schema.

**Rate Limits & Constraints:** GPT-4o models are high-tier. Consult [OpenAI’s rate limit guide](https://platform.openai.com/docs/guides/rate-limits) for your account’s limits. JSON mode has a token limit (for GPT-4o-8K or 32K context) and a 10-image limit if using Vision.  Mentioning “JSON” in prompts is required to avoid a 400 error. Outputs will be valid JSON (no extra text) if done correctly.

**Production Tips:** Store the `OPENAI_API_KEY` as an environment variable, not in code. Structure your payloads in JSON (not concatenated strings) to avoid injection. Validate the response (e.g. with a JSON schema validator) before using it. Add retry logic for transient errors. Use batching or content moderation as needed. See \[Structured Outputs docs] for more details.

# 2. FAL.ai ElevenLabs Multilingual TTS v2

**Installation & Setup:** FAL.ai provides a Python client. Install it and set your API key:

```bash
pip install fal-client
export FAL_KEY="your_fal_ai_api_key"
```

(You can get `FAL_KEY` from your fal.ai dashboard.) The client will use the `FAL_KEY` env var automatically. Alternatively, configure in code:

```python
import fal_client
fal_client.configure(api_key=os.getenv("FAL_KEY"))
```

**API Call (Python):** Use the `fal_client.subscribe()` method to submit a request and wait for the result. For ElevenLabs TTS Multilingual v2, the endpoint is `"fal-ai/elevenlabs/tts/multilingual-v2"`, and the required input is `text` (string). Optional fields include `voice`, `stability`, `similarity_boost`, `style`, and `speed`. Example:

```python
result = fal_client.subscribe(
    "fal-ai/elevenlabs/tts/multilingual-v2",
    arguments={
        "text": "Hello! This is a test of the ElevenLabs TTS.",
        "voice": "Rachel",           # default voice (string)
        "speed": 1.0,               # normal speed
        # You could also set stability=0.5, similarity_boost=0.75, etc.
    }
)
print("Audio URL:", result["audio"]["url"])
```

The response JSON has an `"audio": {"url": ...}` field with an MP3 file URL. Download or stream that URL to get the audio.

**Handling the Response:** Check `result["audio"]["url"]`. The client’s `subscribe` method already waits for completion, but you can also use `fal_client.submit()` with polling or webhooks for asynchronous use. Handle exceptions for network or API errors. For production, you may want to set `with_logs=True` and attach an `on_queue_update` callback to log progress:

```python
def on_update(update):
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
            print("[LOG]", log["message"])

result = fal_client.subscribe(
    "fal-ai/elevenlabs/tts/multilingual-v2",
    arguments={"text": "Multilingual text to speech test", "voice": "Aria"},
    with_logs=True,
    on_queue_update=on_update
)
```

This will print server-side logs while waiting.

**Rate Limits & Constraints:** Each character costs `$0.0001` (0.1¢). Check fal.ai’s rate limits for your tier if you make many calls. The text length limit isn’t explicitly documented, but very long texts will increase cost and time. The model supports 29 languages (accents) as noted on the model page.

**Production Tips:** As above, keep `FAL_KEY` out of source (use env vars). Validate the URL (e.g. ensure it starts with `https://`) before downloading. Handle possible errors (e.g. HTTP 429 for rate limit). Because the API may take time (the playground noted \~6 minutes for a Kling video example, though TTS is faster), consider async patterns or jobs queue. Always check for null or missing `"audio"` in the response and log if transcription failed.

# 3. OpenAI GPT-4 Vision (`gpt-image-1`)

**Installation & Setup:** The same OpenAI SDK is used as for text. Ensure `OPENAI_API_KEY` is set. Prepare images as files or URLs. Keep images under size limits (roughly 4.5MB or \~1.5M pixels; e.g. 1024×1024 or 2048×768) and in common formats (JPEG, PNG) to fit GPT-4 Vision constraints. OpenAI’s docs note you can send up to 10 images per request.

**API Call (Python):** Vision-capable models accept images in the chat message content. You can embed an image as a base64 data URI. For example:

```python
import os, base64
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
with open("scene.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode('utf-8')

messages = [
    {"role": "system", "content": "You are an assistant that describes images."},
    {"role": "user", "content": [
        {"type": "text", "text": "Analyze the following image and list objects seen."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
    ]}
]
response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=messages,
    max_tokens=500
)
print(response.choices[0].message.content)
```

In this example, we send a system prompt and a user message that is an **array** containing a text piece and an image. The `"type": "image_url"` block carries the base64-encoded image. You could also provide a public image URL instead of base64. The model (here `gpt-4o-2024-08-06`) will process both text and image inputs together.

**Structured Response:** If you want the model to return JSON, combine JSON mode as above. For example:

```python
messages[0]["content"] = "You output JSON: identify each object in the image with its label and bounding box."
schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "object": {"type": "string"},
            "confidence": {"type": "number"}
        },
        "required": ["object", "confidence"]
    }
}
response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=messages,
    response_format={"type": "json_schema", "json_schema": {"name": "DetectedObjects", "strict": True, "schema": schema}},
    max_tokens=500
)
print(response.choices[0].message.content)  # JSON list of objects
```

This forces the model to output JSON matching the schema. If JSON mode isn’t used, you’ll get a normal text answer. Always check `finish_reason` in case of truncation.

**Rate Limits & Constraints:** Vision models use larger context, so costs and limits differ from text-only. You can send up to **10 images per request**. There is a max image size (approximately 1.5M pixels or 4.5MB uncompressed). Avoid sending very large images. Also, watch token limits; even though output is text, the image adds to context use. Use `max_tokens` to bound response length and check for `"length"` finish\_reason. If you need to process many images or large images, consult OpenAI’s pricing and rate limits for vision models.

**Production Tips:** Encode images carefully (e.g. use Python’s `base64` as shown). Don’t forget error handling: the API may return errors if the image is too large or the format unsupported. Respect content guidelines (no disallowed image content). For long-running vision tasks, consider asynchronous calls. Store user images securely and avoid exposing them in logs. Use environment variables for keys and never log sensitive data.

# 4. FAL.ai Kling Video v1.6 (Image-to-Video)

**Installation & Setup:** Use the same FAL.ai Python client. The endpoint is `"fal-ai/kling-video/v1.6/standard/image-to-video"`. Set `FAL_KEY` in your environment as before.

**API Call (Python):** This model generates a video clip from a single image and a prompt. Example:

```python
result = fal_client.subscribe(
    "fal-ai/kling-video/v1.6/standard/image-to-video",
    arguments={
        "prompt": "A car driving through a snowy forest.",
        "image_url": "https://example.com/input.jpg"
    }
)
print("Video URL:", result["video"]["url"])
```

You can supply `image_url` as a link or as a base64 data URI (the playground allowed drag-drop). The response JSON includes `"video": {"url": ...}` with a link to the MP4.

**Handling the Response:** The generation can be slow (the web UI notes \~6 minutes). The synchronous `subscribe` call will block until done. For production, consider using `fal_client.submit()` to get a `request_id`, then poll `fal_client.queue.status()` or set up a webhook so your app can resume when the video is ready. Once complete, fetch the result (client will return it automatically for `subscribe`). For example:

```python
handler = fal_client.submit("fal-ai/kling-video/v1.6/standard/image-to-video", 
                           arguments={"prompt": "A flowing river at sunset.", 
                                      "image_url": "https://.../input.png"})
request_id = handler.request_id
# Poll or webhook...
status = fal_client.queue.status("fal-ai/kling-video/v1.6/standard/image-to-video", {"requestId": request_id})
if status.done:
    res = fal_client.queue.fetch("fal-ai/kling-video/v1.6/standard/image-to-video", {"requestId": request_id})
    print("Video URL:", res["video"]["url"])
```

Always check for errors or rejection in the result.

**Rate Limits & Constraints:** The cost is about **\$0.045 per second of video**. Ensure your prompt and image follow any content policies. Videos may have length limits (the playground example was not long; check docs for max duration). The output is an MP4 link, which you can download or stream.

**Production Tips:** Like before, keep `FAL_KEY` secret and in env vars. Large-generation requests may time out; use queue/webhooks for reliability. Check response status codes and handle timeouts (e.g. retry or alert). Use meaningful prompts, and validate the output URL before sending to users. Monitor usage since video generation is expensive.

# 5. Meta MusicGen on Replicate

**Installation & Setup:** Use Replicate’s API. First install Replicate’s Python client and set your token:

```bash
pip install replicate
export REPLICATE_API_TOKEN="your_replicate_api_token"
```

In Python:

```python
import os, replicate
client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))
```

**API Call (Python):** Meta’s MusicGen is available via Replicate. You can call it either via `replicate.run()` or using the client. For example, using `run()` with the version ID:

```python
version = "671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
output = replicate.run(
    "meta/musicgen:" + version,
    input={"prompt": "A calm piano melody", "length": 8}
)
print("Audio URL:", output)
```

Here, `length` is the duration in seconds (MusicGen’s default model is “melody\_10sec”, approximately 10s of music). The `output` will be a URL or a direct audio file URL (depending on Replicate’s client version). If using the `Client` class:

```python
model = client.models.get("meta/musicgen")
version = model.versions.get(version)
prediction = version.predict(prompt="A calm piano melody", length=8)
audio_url = prediction  # likely returns a URL to an MP3
print("Music URL:", audio_url)
```

**Handling the Response:** The prediction will take on the order of tens of seconds. For synchronous use, you may need to poll until `status == "succeeded"` (or simply wait as above). Once done, Replicate returns an audio file (typically MP3). You can download it or stream it. For example, if `output` is a URL, use `requests` to fetch the audio bytes.

**Rate Limits & Constraints:** MusicGen runs on GPU and costs about \$0.072 per run (around 13 runs per USD). Ensure your `prompt` is within length limits (too long prompts may be truncated or rejected). The model also supports a `model_version` parameter (e.g. `"melody"` or `"large"`) but by default uses `"melody"`. The maximum length of output may be limited (default 10s; some allow up to 30s).

**Production Tips:** Store the `REPLICATE_API_TOKEN` as an env var, not in code. Add error handling: catch HTTP errors or check `prediction.status` for `"failed"`. Consider running these calls asynchronously or in a background task, since each call takes \~1 minute. Validate that the returned URL or file is correct before using it. For scaling, be aware of Replicate’s concurrency limits on your plan. Use secrets management to keep tokens safe.