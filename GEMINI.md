
# Project Overview

This is a Django-based web application named **Sys_TDM** (Sistema de Gestão Técnica para Dados Complexos). It's designed for managing budgets, products, and consumption, making it a technical data management system. The project is containerized using Docker and uses a PostgreSQL database.

**Key Technologies:**

*   **Backend:** Django (Python)
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
*   **Database:** PostgreSQL
*   **Containerization:** Docker, Docker Compose
*   **Other Libraries:**
    *   `psycopg2-binary`: PostgreSQL adapter for Python.
    *   `openpyxl`: A Python library to read/write Excel 2010 xlsx/xlsm/xltx/xltm files.
    *   `django-crispy-forms`: A Django application that lets you control the rendering of your forms in a very elegant and DRY way.
    *   `crispy-bootstrap5`: Bootstrap 5 template pack for django-crispy-forms.

# Building and Running

The project is designed to be run with Docker Compose.

**1. Build and Start Containers:**

```bash
docker-compose up --build -d
```

**2. Apply Database Migrations:**

```bash
docker-compose exec web python sys_tdm/manage.py migrate
```

**3. Create a Superuser (optional):**

```bash
docker-compose exec web python sys_tdm/manage.py createsuperuser
```

**4. Accessing the Application:**

*   **Web Application:** [http://localhost:8000](http://localhost:8000)
*   **Admin Interface:** [http://localhost:8000/admin](http://localhost:8000/admin)

# Development Conventions

*   The project follows a standard Django project structure.
*   The main application logic is within the `sys_tdm` directory.
*   The project is divided into several Django apps: `consumos`, `contas`, `estoque`, `orcamentos`, and `produtos`.
*   Templates are located in the `templates` directory of each application.
*   Static files are located in the `static` directory.
