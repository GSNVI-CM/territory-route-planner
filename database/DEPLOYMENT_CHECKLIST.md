# Deployment Checklist

## Best free option
Use Streamlit Community Cloud.

Streamlit Community Cloud is free and deploys directly from GitHub.

## Repository setup
Create a GitHub repo named something neutral, such as:

- territory-route-planner
- field-visit-planner
- practice-route-planner
- tms-route-planner

Do not use a personal name.

## Upload these files
- app.py
- requirements.txt
- .streamlit/config.toml
- README.md

## Streamlit setup
1. Go to share.streamlit.io
2. Sign in with GitHub
3. Create app
4. Select the repo
5. Main file path: app.py
6. Choose a neutral subdomain
7. Deploy

## After deployment
Open the new streamlit.app URL, upload the current visit report, and generate the month.
