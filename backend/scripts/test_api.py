import requests

def test_recommend():
    url = "http://localhost:8000/recommend"
    params = {"q": "space travel"}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"✅ Received {len(results)} results.")
            if results:
                print("First result sample:")
                print(f"  Title: {results[0].get('title')}")
                print(f"  Poster: {results[0].get('poster_path')}")
        else:
            print(f"❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_recommend()
