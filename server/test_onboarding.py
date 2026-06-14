import requests
import json

data = {
    "answers": {
        "nickname": "TestUser",
        "study_topic": "AI",
        "date_of_birth": "2000-01-01"
    }
}
# We don't have a valid token, so we can't test it directly unless we mock auth.
