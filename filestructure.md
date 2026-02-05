network-db/
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── Dockerfile
├── requirements.txt
│
├── api/
│ ├── app/
│ │ ├── main.py
│ │ │
│ │ ├── core/ # Config, database session
│ │ │ ├── config.py
│ │ │ └── database.py
│ │ │
│ │ ├── models/ # SQLAlchemy models
│ │ │ ├── network.py
│ │ │ ├── unit.py
│ │ │ └── opening.py
│ │ │
│ │ ├── schemas/ # Pydantic schemas (API contracts)
│ │ │ ├── network.py
│ │ │ ├── unit.py
│ │ │ └── opening.py
│ │ │
│ │ ├── services/ # Business logic
│ │ │ ├── ogr_service.py
│ │ │ ├── network_service.py
│ │ │ └── geometry_service.py
│ │ │
│ │ ├── routes/ # FastAPI routers
│ │ │ ├── import_routes.py
│ │ │ ├── export_routes.py
│ │ │ └── network_routes.py
│ │ │
│ │ └── utils/ # Helpers
│ │ ├── projection.py
│ │ └── file_utils.py
│ │
│ └── tests/
│
└── data/ # Optional bind mount for uploads

#### primary key requirement####

100% immutable?
Never renamed?
Never localized?
Never reformatted?
Never merged/split in the future?
If the answer is even slightly “maybe”, then don’t use it as your primary key.

Best Practices Summary for primary key

Always use immutable ID for internal operations
Use UNIQUE constraint on name field
Implement two-step operations for user-facing actions:

Step 1: Resolve name to ID
Step 2: Perform operation using ID
Add proper indexes for search performance
Consider implementing an audit trail for sensitive fields
Use transactions for multi-step operations
For web applications, consider exposing IDs in UI once user selects a record
This approach gives you the flexibility to allow name changes while maintaining data integrity and providing good search functionality.

example:

```update

# Example using Python/SQL
def update_user(old_name: str, new_name: str):
    # First, verify the user exists
    user = db.execute("SELECT id FROM users WHERE name = ?", old_name).fetchone()

    if not user:
        raise ValueError("User not found")

    # Check if new_name already exists (to maintain uniqueness)
    existing = db.execute("SELECT id FROM users WHERE name = ?", new_name).fetchone()
    if existing:
        raise ValueError("Username already taken")

    # Update using the immutable ID
    db.execute("UPDATE users SET name = ? WHERE id = ?",
               new_name, user['id'])
    db.commit()

```

```create
def create_user(name: str, email: str):
    # Check uniqueness first
    existing = db.execute(
        "SELECT id FROM users WHERE name = ? OR email = ?",
        name, email
    ).fetchone()

    if existing:
        raise ValueError("Username or email already exists")

    # Insert (ID is auto-generated)
    db.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        name, email
    )
    db.commit()
```
