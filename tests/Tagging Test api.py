import requests

resp = requests.post(
    "http://localhost:8000/tag-json",
    json={"image_url": "https://www.gstatic.com/webp/gallery3/1_webp_a.sm.png"}
)
print(resp.json())