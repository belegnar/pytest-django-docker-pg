# pytest-django-docker-pg

Starts a dockerized postgresql instance in pytest hook allowing `pytest_django` tests, for example, to be run against it.

## How to use

```pyproject.toml
[tool.pytest.ini_options]
addopts = "-p pytest_django_docker_pg --django-docker-pg-image=postgres:16-alpine "
```

```python
# settings.py

import os 

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "postgres"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "secret"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

```
