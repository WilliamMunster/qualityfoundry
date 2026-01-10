
import httpx
import json
import asyncio

url = "http://localhost:8000/api/v1/scenarios/generate"
headers = {"Content-Type": "application/json"}
data = {
    "requirement_id": "e43f57bb-c0ef-4b3a-aa05-acd121cfba47",
    "auto_approve": False
}

async def main():
    try:
        print(f"Sending POST to {url}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=60.0)
            print(f"Status Code: {response.status_code}")
            try:
                print("Response JSON:")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            except:
                print("Response Text:")
                print(response.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
