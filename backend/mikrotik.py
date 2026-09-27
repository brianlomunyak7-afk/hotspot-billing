import os
from librouteros import connect
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return connect(
        username=os.getenv("MIKROTIK_USER"),
        password=os.getenv("MIKROTIK_PASSWORD"),
        host=os.getenv("MIKROTIK_HOST"),
        port=int(os.getenv("MIKROTIK_PORT", 8728)),
    )

def duration_to_uptime_limit(duration: int, duration_type: str) -> str:
    """Converts package duration into MikroTik's limit-uptime format (e.g. '15m', '2d')."""
    if duration_type == "minutes":
        return f"{duration}m"
    return f"{duration}d"

def grant_hotspot_user(username: str, password: str, duration: int, duration_type: str, profile: str = "default"):
    """
    Creates (or refreshes) a hotspot user on MikroTik with a time limit.
    username: usually the tenant's phone number
    password: tenant's hotspot password
    duration/duration_type: from the purchased package
    """
    try:
        api = get_connection()
        limit_uptime = duration_to_uptime_limit(duration, duration_type)

        existing = list(api.path("ip", "hotspot", "user").select("name", ".id"))
        match = next((u for u in existing if u.get("name") == username), None)

        if match:
            api.path("ip", "hotspot", "user").update(
                **{".id": match[".id"], "password": password, "limit-uptime": limit_uptime, "profile": profile}
            )
        else:
            api.path("ip", "hotspot", "user").add(
                name=username, password=password, profile=profile, **{"limit-uptime": limit_uptime}
            )

        return True
    except Exception as e:
        print(f"MIKROTIK ERROR: {e}")
        return False