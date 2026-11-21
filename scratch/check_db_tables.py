import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.database import get_engine, init_db
from sqlalchemy import inspect

print("Initializing DB...")
ok, msg = init_db()
print(f"init_db result: {ok}, {msg}")

engine = get_engine()
inspector = inspect(engine)
print("Updated tables in Neon:", inspector.get_table_names())
