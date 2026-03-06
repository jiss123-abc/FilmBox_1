import socket
import requests
import time

def check_tmdb():
    print("🔍 Diagnosing TMDB Connection...")
    
    # 1. DNS Check
    try:
        host = "api.themoviedb.org"
        ip = socket.gethostbyname(host)
        print(f"✅ DNS Resolved: {host} -> {ip}")
    except Exception as e:
        print(f"❌ DNS Resolution Failed: {e}")
        return

    # 2. Port 443 Check
    try:
        s = socket.create_connection((host, 443), timeout=5)
        print(f"✅ Port 443 is open/reachable.")
        s.close()
    except Exception as e:
        print(f"❌ Port 443 Connection Failed: {e}")
        return

    # 3. Simple Request Check
    try:
        print("📡 Attempting simple HTTPS GET (5s timeout)...")
        start = time.time()
        response = requests.get("https://api.themoviedb.org/3/configuration", params={"api_key": "any"}, timeout=5)
        print(f"✅ HTTPS Request Successful (Status: {response.status_code})")
        print(f"⏱️ Latency: {round(time.time() - start, 2)}s")
    except Exception as e:
        print(f"❌ HTTPS Request Failed: {e}")

if __name__ == "__main__":
    check_tmdb()
