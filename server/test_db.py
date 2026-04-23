from db.dbConnection import get_dict_cursor
with get_dict_cursor() as cur:
    cur.execute("SELECT * FROM public.users LIMIT 1")
    print(cur.fetchall())
