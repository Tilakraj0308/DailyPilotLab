"""
Seed script for DailyPilotLab.

Inserts a set of sample ideas into the `raw_idea` table so the app has
something to work with from day one.

Prerequisites:
    Schema must already be applied via Supabase migrations
    (e.g. `supabase db push` or `supabase migration up`).

Usage:
    python -m db.seed
"""

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# ---------------------------------------------------------------------------
# Seed data – ideas taken directly from ideas_inject.json
# ---------------------------------------------------------------------------

SEED_IDEAS = [
    "We don't actually see objects; we just see the light that failed to pass through them.",
    "Flibber-gasket the mimsy-wobble before the glorp transcends.",
    'The "oldest person on Earth" is a title that has a 100% turnover rate.',
    "Default administrative passwords for many IoT devices are still set to admin or 12345.",
    'My first pet was a goldfish named "Toaster" because he liked to jump toward the light.',
    "A restaurant where the menu is priced based on how much the ingredients cost at the stock market that morning.",
    "Zyzzy-vax the wonky-tonk in a purple skedaddle.",
    '"Save the Planet" campaigns are actually "Save the Humans" campaigns; the planet will be fine without us.',
    "I once spent three hours trying to find my glasses while I was wearing them.",
    "A mirror that shows you what you looked like exactly ten years ago today.",
]

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000000"

INSERT_USER = """
INSERT INTO public.users (auth_id, email)
VALUES (%s, 'seed@dailypilot.dev')
ON CONFLICT (auth_id) DO NOTHING;
"""

INSERT_IDEA = """
INSERT INTO public.raw_idea (user_id, content, raw)
VALUES (%s, %s, TRUE)
RETURNING id;
"""


def run():
    conn = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                print("Ensuring seed user exists ...")
                cur.execute(INSERT_USER, (DEFAULT_USER_ID,))
                
                print("Inserting seed ideas …")
                inserted_ids = []
                for idea_text in SEED_IDEAS:
                    cur.execute(INSERT_IDEA, (DEFAULT_USER_ID, idea_text,))
                    row = cur.fetchone()
                    inserted_ids.append(row[0])

                print(f"  ✓ Inserted {len(inserted_ids)} ideas (ids: {inserted_ids}).")

        print("\nSeed complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
