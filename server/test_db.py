from connectors import db
from dotenv import load_dotenv
load_dotenv()
print(db.list_connectors_status('some-user-id'))
