import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.profile_manager import user_profile_manager


async def main() -> None:
    chat_ids = await user_profile_manager.list_all_profiles()
    for chat_id in chat_ids:
        profile = await user_profile_manager.load_profile(chat_id)
        loc = profile.get("localization", {})
        ada = profile.get("personality_adaptation", {})
        if loc.get("confirmed_by_user") and not ada.get("preferred_dialect"):
            ada["preferred_dialect"] = loc.get("dialect")
            await user_profile_manager.save_profile(chat_id, profile)
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
