"""Manual debug script: print connector status for a user. Not a pytest module.

Run from repo `server/` root, e.g. `python scripts/db_list_connectors_status.py`.
"""

from connectors import db
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    print(db.list_connectors_status("some-user-id"))
