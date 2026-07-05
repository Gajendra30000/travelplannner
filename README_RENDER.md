Render deployment steps

1) Backend service (FastAPI)
- Create a new Web Service in Render, connect to this repo.
- Root directory: `.`
- Environment: `Python`
- Build Command:
```
pip install -r requirements.txt
```
- Start Command:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
- Environment variables: add all provider keys from your local `.env` (do NOT commit `.env`). Use the names shown in `.env.sample`.

2) Frontend service (Streamlit)
- Create a new Web Service in Render, connect to this repo.
- Root directory: `.`
- Environment: `Python`
- Build Command:
```
pip install -r requirements.txt
```
- Start Command:
```
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true --server.enableCORS false
```
- Environment variables:
  - `BASE_URL`: set to the public URL of the backend (e.g. https://travelplannner.onrender.com)
  - `API_TIMEOUT` (optional): `120`
  - Any other non-secret UI settings you want.

3) Security & notes
- Rotate any API keys you accidentally exposed in the repo or screenshots immediately.
- Do NOT store secrets in the repository. Use Render's Environment settings.
- If you previously committed secrets, consider invalidating them and rewriting history if necessary.

4) Testing
- After both services are deployed, open the Streamlit URL and submit a request.
- If you see JS asset fetch errors, open browser DevTools → Network and check failing requests; then check Render logs for matching errors.

5) Helpful files added to this repo
- `.env.sample` — template of env variable names
- `render.yaml` — manifest added to create both services automatically
- `scripts/print_envs.py` — prints required env var names

If you'd like, I can also prepare a `curl`-based smoke-test script to POST a sample query to the backend once you set env vars and the backend is live.
