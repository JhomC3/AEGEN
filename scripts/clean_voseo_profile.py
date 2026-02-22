import json
import sqlite3


def clean_voseo():
    db_path = "storage/aegen_memory.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if profiles table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
        )
        if not cursor.fetchone():
            print("No profiles table found.")
            return

        cursor.execute("SELECT chat_id, data FROM profiles")
        rows = cursor.fetchall()

        updated_count = 0
        for chat_id, data_str in rows:
            try:
                data = json.loads(data_str)
                modified = False

                # Check localization for dialect
                localization = data.get("localization", {})
                if (
                    localization.get("dialect") == "Rioplatense"
                    or localization.get("dialect") == "voseo"
                    or localization.get("dialect") == "argentino"
                ):
                    localization["dialect"] = "neutro"
                    localization["dialect_hint"] = "tuteo neutro"
                    localization["confirmed_by_user"] = False
                    data["localization"] = localization
                    modified = True

                # Check adaptation for preferred_dialect
                adaptation = data.get("personality_adaptation", {})
                if adaptation.get("preferred_dialect") in [
                    "Rioplatense",
                    "voseo",
                    "argentino",
                ]:
                    adaptation["preferred_dialect"] = None
                    data["personality_adaptation"] = adaptation
                    modified = True

                # Check learned preferences for voseo
                learned = adaptation.get("learned_preferences", [])
                new_learned = [
                    p
                    for p in learned
                    if "voseo" not in p.lower() and "rioplatense" not in p.lower()
                ]
                if len(new_learned) != len(learned):
                    adaptation["learned_preferences"] = new_learned
                    data["personality_adaptation"] = adaptation
                    modified = True

                if modified:
                    new_data_str = json.dumps(data)
                    cursor.execute(
                        "UPDATE profiles SET data = ? WHERE chat_id = ?",
                        (new_data_str, chat_id),
                    )
                    updated_count += 1
            except Exception as e:
                print(f"Error processing {chat_id}: {e}")

        conn.commit()
        print(f"Successfully cleaned voseo from {updated_count} profiles.")

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    clean_voseo()
