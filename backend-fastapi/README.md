# Folder Structure

project/
│── alembic/ # Migrasi database PostgreSQL
│── app/
│ ├── api/ # Routing / Endpoint
│ │ ├── v1/
│ │ │ ├── endpoints/
│ │ │ │ ├── users.py
│ │ │ │ ├── items.py
│ │ │ │ └── logs.py
│ │ │ └── **init**.py
│ │ └── **init**.py
│ │
│ ├── core/ # Konfigurasi inti aplikasi
│ │ ├── config.py # Settings (ENV, secret key, DB URL)
│ │ ├── security.py # Auth & JWT
│ │ └── **init**.py
│ │
│ ├── db/ # Database setup
│ │ ├── postgres/ # PostgreSQL
│ │ │ ├── session.py # SQLAlchemy session/engine
│ │ │ ├── base.py # Base class SQLAlchemy
│ │ │ └── **init**.py
│ │ ├── mongo/ # MongoDB
│ │ │ ├── connection.py # Motor/Mongo client setup
│ │ │ └── **init**.py
│ │ └── **init**.py
│ │
│ ├── models/ # Models
│ │ ├── postgres/ # Relational models
│ │ │ ├── user.py
│ │ │ ├── item.py
│ │ │ └── **init**.py
│ │ ├── mongo/ # Document-based models (schema MongoDB)
│ │ │ ├── log.py
│ │ │ └── **init**.py
│ │ └── **init**.py
│ │
│ ├── schemas/ # Pydantic schemas
│ │ ├── user.py
│ │ ├── item.py
│ │ ├── log.py
│ │ └── **init**.py
│ │
│ ├── repositories/ # Repository layer (abstraksi query)
│ │ ├── postgres/ # Query untuk PostgreSQL
│ │ │ ├── user_repo.py
│ │ │ └── item_repo.py
│ │ ├── mongo/ # Query untuk MongoDB
│ │ │ ├── log_repo.py
│ │ │ └── **init**.py
│ │ └── **init**.py
│ │
│ ├── services/ # Business logic
│ │ ├── user_service.py
│ │ ├── item_service.py
│ │ ├── log_service.py
│ │ └── **init**.py
│ │
│ ├── utils/ # Helper
│ │ ├── email.py
│ │ ├── logger.py
│ │ └── **init**.py
│ │
│ ├── main.py # Entry point FastAPI
│ └── **init**.py
│
│── tests/ # Unit & integration tests
│ ├── test_users.py
│ ├── test_logs.py
│ └── conftest.py
│
│── .env # Environment variables
│── requirements.txt # Dependencies
│── alembic.ini # Konfigurasi migrasi Postgres
│── README.md
