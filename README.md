# ServeWare

ServeWare is a comprehensive restaurant ordering and table management system built with Django. It streamlines restaurant operations, improves dining floor turnaround, and offers customers a contact-free, QR-code-driven digital dining experience. 🍴

---

## Features

### 1. **Accounts & RBAC Management** 🔒
- Role-based access control (RBAC) separating Restaurant Owners and Customers with strict view decorators.
- Secure email-based One-Time Password (OTP) verification for password resets (using cryptographically secure random tokens and constant-time digest verification).
- *Future Enhancement*: Sign-up OTP verification.

### 2. **Customer App** 📱
- Table-specific QR code scanning and direct menu access.
- Interactive cart management: add items, update quantities, review line items, and place orders.
- Real-time order status tracking (Pending, Cooking, Ready to Serve, Bill Paid).
- *Future Enhancement*: Requesting additional items on open tabs.

### 3. **Restaurant Administration** 🏢
- Full menu CRUD operations with categorized menu items and availability toggles.
- Live restaurant order monitoring and order status progression.
- Table management with automatic QR code generation pointing to table URLs, tracking occupancy and bill-settled states.

---

## Tech Stack 🛠️
- **Backend**: Python 3.13, Django 5.2 LTS
- **Frontend**: HTML5, Vanilla CSS, Bootstrap 5
- **WSGI / Server**: Gunicorn, WhiteNoise
- **Database**: SQLite (pluggable PostgreSQL/MySQL support via `django-environ`)
- **Observability**: `django-prometheus` metrics exporter

---

## Installation & Local Development 🚀

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shlokamdar/serveware.git
   cd serveware
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Navigate to the Django application directory:**
   ```bash
   # manage.py is located in the inner serveware/ directory:
   cd serveware
   ```

5. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Seed demo data (Optional):**
   ```bash
   set DEMO_PASSWORD=YourPassword123!
   python manage.py seed_demo
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   Access the application at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## CI/CD Pipeline & Quality Engineering ⚙️

ServeWare features an enterprise-grade 7-stage Jenkins CI/CD pipeline running automated quality, security, and deployment gates:

1. **Build & Package**: Reproducible builds with pinned dependencies, Django system checks (`manage.py check`, migration dry-run), and single-stage container builds pushed to a local Docker registry (`localhost:5000/serveware`).
2. **Test & Coverage**: Isolated test suites separating unit tests and `@tag("integration")` end-to-end user journeys. JUnit XML reporting and Cobertura code coverage strictly gated at $\ge 60\%$.
3. **Code Quality**: Static code analysis via **SonarQube Community** enforced by a custom Quality Gate, coupled with strict **Ruff** linting.
4. **Security Scanning**: Four-layered DevSecOps scanning:
   - **Bandit**: Static Application Security Testing (SAST).
   - **pip-audit**: Zero-tolerance dependency CVE scanner.
   - **Trivy**: Container image vulnerability analysis.
   - **Gitleaks**: Hardcoded secret and credential detection across code and git history.
5. **Deploy (Staging)**: Automated deployment to Docker Compose staging (`:8000`), validated by an automated smoke test suite (`scripts/smoke_test.py`) with automatic rollback on failure.
6. **Release (Production)**: Automated blue/green release to production (`:8001`) on `main` branch merges, automatic semantic git tagging (`v1.0.X`), and release notes generation.
7. **Monitoring & Alerting**: **Prometheus** metrics collection scraping `django-prometheus` at `/metrics`, custom alert rules (Availability, 5xx Rate, Latency degradation), **Alertmanager** Gmail routing with alert inhibition, and **Grafana** production overview dashboards.

---

## Running Tests & CI / Quality Commands

For development, testing, and CI scanning, install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

From the inner `serveware/` directory:

```bash
# Run unit & integration tests with coverage
coverage run manage.py test --exclude-tag integration --verbosity 2
coverage run -a manage.py test --tag integration --verbosity 2
coverage report

# Linting
ruff check .

# Static Security Testing
bandit -r . -c ../bandit.yaml
```
