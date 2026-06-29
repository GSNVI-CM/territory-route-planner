# Territory Route Planner

A free-hostable Streamlit web app for territory visit planning.

## What it does

- Uploads the current visit report Excel file
- Saves upload history
- Reads Doctors and Visits data
- Enforces visit cadence rules
- Excludes non-routable / do-not-visit accounts
- Generates a full-month schedule
- Gives calendar control for blocked dates and locked visits
- Uses smart grouping and visit priority, not maps
- Exports a clean Excel schedule with note/update columns

## App name

The app is intentionally neutral: **Territory Route Planner**.

## Free website deployment

This is ready for Streamlit Community Cloud.

### Files required for deployment

- `app.py`
- `requirements.txt`
- `.streamlit/config.toml`

### Deploy steps

1. Create a GitHub account or use an existing one.
2. Create a new GitHub repository, for example `territory-route-planner`.
3. Upload these files to that repository.
4. Go to Streamlit Community Cloud: `share.streamlit.io`
5. Sign in with GitHub.
6. Click **Create app**.
7. Choose the repository, branch, and `app.py`.
8. Pick a neutral URL, for example:
   - `territory-route-planner.streamlit.app`
   - `practice-route-planner.streamlit.app`
   - `field-visit-planner.streamlit.app`
9. Click **Deploy**.

## Important note about free hosting

Free Streamlit hosting can store files while the app is running, but long-term file persistence is not guaranteed. The app includes a backup download for upload history. For a future version, use a small database service if permanent cloud storage is required.

## Local test option

You can also run it locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```
