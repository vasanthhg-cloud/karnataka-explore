# Getting a working URL where login, booking, payment and admin all work

GitHub Pages **cannot** run this part of the project. Pages serves static files
only; a Flask app needs a Python process, sessions and a writable database. That
is why `https://vasanthhg-cloud.github.io/karnataka-explore/` shows the notice
page on those four flows.

Everything below gives you a real URL where all of it works.

---

## Option 1 - Render, free, about two minutes (recommended)

1. Sign in at <https://render.com> with your GitHub account.
2. **New → Blueprint**, choose the `karnataka-explore` repository, click **Apply**.
   `render.yaml` is already in the repo, so nothing needs configuring.
3. Wait for the build, then open the URL Render gives you
   (`https://karnataka-explore-xxxx.onrender.com`).

Login: `demo@karnatakaexplore.in` / `Demo@1234`
Admin: `https://<your-url>/admin/login` — `admin@karnatakaexplore.in` / `Admin@123`

Free tier notes:

- The service sleeps after ~15 minutes idle; the first request after that takes
  about 30 seconds to wake.
- The filesystem is ephemeral, so the SQLite database is rebuilt on every deploy
  and any bookings made during a demo disappear. Fine for a college demo. For
  permanent data, point `DB_BACKEND` at a managed MySQL (see the README) or add a
  paid Render disk mounted at `/app/instance`.

## Option 2 - Railway

1. <https://railway.app> → **New Project → Deploy from GitHub repo** → pick this repo.
2. Railway reads `railway.json`. Set `SECRET_KEY` in Variables.
3. Generate a domain under Settings → Networking.

## Option 3 - Any Docker host (Fly, Koyeb, Cloud Run, a VPS)

```bash
docker build -t karnataka-explore .
docker run -p 8000:8000 -e SECRET_KEY=change-me karnataka-explore
```

The image seeds its own database at build time.

## Option 4 - PythonAnywhere (free tier, good for college demos)

1. Upload the project or clone it in a Bash console.
2. `pip install --user -r requirements.txt` and `python seed.py`.
3. Web tab → **Add a new web app** → **Manual configuration** → Python 3.12.
4. Edit the WSGI file so it contains:

   ```python
   import sys, os
   path = "/home/<yourusername>/karnataka-explore"
   if path not in sys.path:
       sys.path.insert(0, path)
   os.environ["SECRET_KEY"] = "a-long-random-string"
   from run import app as application
   ```

5. Set the virtualenv path in the Web tab, then **Reload**.

---

## Why not GitHub Pages?

Pages is a static file host. It cannot execute Python, cannot keep a session
cookie, cannot write to a database, and cannot serve a generated PDF from a
running process. No configuration makes Flask run there. The static build in
`docs/` exists so the browsing experience is still viewable at a public URL.

## Regenerating the static preview

```bash
python scripts/export_static.py   # rewrites docs/
git add docs && git commit -m "Update static preview" && git push
```
