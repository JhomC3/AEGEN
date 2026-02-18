import urllib.request
from pathlib import Path


def load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with env_path.open() as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                import os

                os.environ[k] = v


def main() -> None:
    load_env()
    print("Testing API...")
    try:
        url = "http://127.0.0.1:8000/system/health"
        resp = urllib.request.urlopen(url, timeout=5)
        print(f"Status: {resp.status}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
