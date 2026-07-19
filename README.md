# Ledger — Full-Stack Task Management API

A task management application built for the "Full-Stack Task Management API" project brief:
Flask (REST API) backend + JWT authentication + SQLite + a vanilla HTML/JS frontend.

```
task-management-api/
├── backend/
│   ├── app.py              # Flask app: models, auth, task CRUD
│   ├── requirements.txt
│   └── tests/
│       └── test_app.py     # 16 pytest unit tests
├── frontend/
│   └── index.html          # single-page app (HTML/CSS/JS, no build step)
├── .gitignore
└── README.md
```

## Features

- **User auth**: register / login, passwords hashed with Werkzeug, JWT access tokens (24h expiry)
- **Task CRUD**: create, read, update, delete — scoped per user (you only ever see your own tasks)
- **Filtering**: `GET /api/tasks?status=pending` and `GET /api/tasks?q=searchterm`
- **Tests**: 16 pytest tests covering auth and every CRUD path, including the "can't see other users' tasks" case
- **Frontend**: a 3-column board (Pending / In progress / Done) that talks to the API with `fetch`

---

## 1. Run the backend

Requires **Python 3.9+**.

```bash
cd task-management-api/backend

# create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# run the server
python3 app.py
```

The API is now live at **http://localhost:5000**. It creates `tasks.db` (SQLite) automatically
on first run.

Quick check:
```bash
curl http://localhost:5000/api/health
# {"status": "ok"}
```

### Run the tests

```bash
cd task-management-api/backend
pytest -v
```
All 16 tests should pass.

---

## 2. Run the frontend

No build step needed — it's a single static HTML file. Two ways to run it:

**Option A — just open it**
Double-click `frontend/index.html`, or open it in a browser directly.

**Option B — serve it (recommended, avoids some browser file:// quirks)**
```bash
cd task-management-api/frontend
python3 -m http.server 8000
```
Then visit **http://localhost:8000**.

> The frontend is hard-coded to call the API at `http://localhost:5000/api` (see the
> `API_BASE` constant near the top of the `<script>` tag in `index.html`). Change this
> if you deploy the backend elsewhere — see deployment section below.

Make sure the backend (step 1) is running at the same time, then:
1. Create an account
2. Add tasks, drag them mentally between statuses using the dropdown on each card
3. Search, edit, delete

---

## 3. API Reference

| Method | Endpoint                     | Auth? | Description                         |
|--------|-------------------------------|-------|--------------------------------------|
| GET    | `/api/health`                 | No    | Health check                        |
| POST   | `/api/register`               | No    | `{username, password}` → creates user + returns JWT |
| POST   | `/api/login`                  | No    | `{username, password}` → returns JWT |
| GET    | `/api/tasks`                  | Yes   | List your tasks. Optional `?status=` and `?q=` query params |
| POST   | `/api/tasks`                  | Yes   | `{title, description?, status?}` → creates a task |
| GET    | `/api/tasks/<id>`             | Yes   | Get one task |
| PUT    | `/api/tasks/<id>`             | Yes   | Update any of `title`, `description`, `status` |
| DELETE | `/api/tasks/<id>`             | Yes   | Delete a task |

Authenticated requests need an `Authorization: Bearer <token>` header.

---

## 4. Push this project to GitHub

From the `task-management-api` folder:

```bash
git init
git add .
git commit -m "Initial commit: full-stack task management API"

# create a new repo on GitHub first (via github.com/new), then:
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

If you don't have a GitHub repo yet, you can also create one straight from the terminal
with the GitHub CLI:
```bash
gh repo create task-management-api --public --source=. --remote=origin --push
```

---

## 5. Make it live (deployment)

### Backend → Render (free tier, easiest for Flask)
1. Push the code to GitHub (step 4).
2. Go to [render.com](https://render.com) → **New → Web Service** → connect your repo.
3. Settings:
   - **Root directory**: `backend`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app`
4. Add an environment variable `JWT_SECRET_KEY` set to a long random string.
5. Deploy. Render gives you a live URL like `https://your-app.onrender.com`.

> Note: Render's free SQLite storage is ephemeral (resets on redeploy). For a persistent
> free-tier database, swap in Render's free PostgreSQL and point `SQLALCHEMY_DATABASE_URI`
> at it via an environment variable — the app already reads config from environment vars,
> so this is a small change to `app.py`.

Alternatives that work the same way: **Railway**, **Fly.io**, **PythonAnywhere**.

### Frontend → GitHub Pages (free)
1. In `frontend/index.html`, change:
   ```js
   const API_BASE = "http://localhost:5000/api";
   ```
   to your live backend URL, e.g.:
   ```js
   const API_BASE = "https://your-app.onrender.com/api";
   ```
2. Commit and push that change.
3. On GitHub: repo → **Settings → Pages** → Source: **Deploy from a branch** →
   Branch: `main`, folder: `/frontend` (or `/root` if you move `index.html` to the repo root).
4. GitHub gives you a live URL like `https://<your-username>.github.io/<repo-name>/`.

Alternatives: **Netlify** or **Vercel** (drag-and-drop the `frontend` folder, or connect the repo).

### CORS reminder
The backend already has `flask-cors` enabled for all origins, so your GitHub Pages frontend
will be able to call your Render backend without extra config. For production hardening later,
you'd restrict `CORS(app)` to your specific frontend origin.

---

## 6. Why this covers the brief

- **Backend framework**: Flask + Flask-RESTful-style routing ✅
- **Database**: SQLite for dev ✅
- **Auth**: registration + login via JWT ✅
- **Task endpoints**: create, read, update, delete ✅
- **Testing**: pytest unit tests (16 tests, all passing) ✅
- **Git/GitHub**: instructions above to push and deploy ✅
