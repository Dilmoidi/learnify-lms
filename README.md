# Learnify LMS

Learnify is a modern Learning Management System (LMS) built using Django.
It provides a complete platform for students, instructors, and administrators to manage online learning efficiently.

---

## Features

### Student Module

* Student Registration & Login
* Browse Courses
* Enroll in Courses
* Access Study Materials
* Submit Assignments
* Attempt Quizzes
* Track Progress
* Download Certificates

### Instructor Module

* Instructor Registration & Login
* Create Courses
* Upload Videos & Notes
* Create Assignments
* Create Quizzes
* Track Student Progress

### Admin Module

* Dashboard Analytics
* Manage Students
* Manage Instructors
* Manage Courses
* Reports & Analytics

---

## Tech Stack

* Python
* Django
* HTML
* CSS
* Bootstrap 5
* JavaScript
* SQLite

---

## Installation

Clone repository:

```bash
git clone https://github.com/Dilmoidi/learnify-lms.git
```

Move to project folder:

```bash
cd learnify-lms
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Start server:

```bash
python manage.py runserver
```

---

## Screenshots

Add project screenshots here.

Example:

* Landing Page
* Student Dashboard
* Instructor Dashboard
* Admin Dashboard

---

## CI/CD Pipeline

The project includes an automated CI/CD pipeline powered by **GitHub Actions** (defined in `.github/workflows/ci-cd.yml`). The workflow performs three main jobs sequentially upon any push or pull request to the `main` or `master` branches:

1. **Test (`Run Python Django Tests`)**:
   - Spins up a clean Ubuntu runner, installs dependencies, and executes the unit test suite (`python manage.py test`).
2. **Build (`Build & Push Docker Image`)**:
   - Triggers only on code pushes/merges to primary branches.
   - Logs into **GitHub Container Registry (GHCR)** using repository scopes.
   - Compiles and publishes the production-ready Docker image (`ghcr.io/username/learnify-lms:latest`).
3. **Deploy (`Trigger Render Deployment`)**:
   - Performs a secure trigger hook request to Render to pull the updated Docker container and complete deployment.

### Setup Secrets in GitHub:
To activate automated deployments, go to your GitHub repository `Settings -> Secrets and variables -> Actions` and add:
- **`RENDER_DEPLOY_HOOK_URL`**: The deploy hook URL found under your Render service dashboard (e.g. `https://api.render.com/deploy/srv-...`).

---

## Author

Dilsha Moideen
