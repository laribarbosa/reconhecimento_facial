TORTOISE_ORM = {
    "connections": {"default": "sqlite://backend/db.sqlite3"},
    "apps": {
        "models": {
            "models": ["backend.models"],
            "default_connection": "default",
        },
    },
}
