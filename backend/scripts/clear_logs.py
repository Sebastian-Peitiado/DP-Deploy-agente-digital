import sys
import os

# Ensure the backend directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_supabase_client

def clear_all_logs():
    client = get_supabase_client()
    try:
        # We can use .neq("user_message", "___IMPOSSIBLE___") to delete all rows
        res = client.table("chat_logs").delete().neq("user_message", "___IMPOSSIBLE___").execute()
        print(f"✅ All chat logs have been deleted successfully. Count: {len(res.data)}")
    except Exception as e:
        print(f"❌ Error deleting chat logs: {e}")

if __name__ == "__main__":
    clear_all_logs()
