# Deploy ShaadiGlow (Render free web service)

The testing link must stay up **until 20 Nov 2026**. Total time: about 20 minutes.

The API key is a secret. Never paste it into the repo, a commit, an issue, a chat or the Devpost form. It only goes
into Render's environment settings and your own terminal.

## 0. Before you start

- A GitHub account (yours: `rounak251`) with this project pushed to a repository:
  ```bash
  cd ~/Desktop/datascience/hackathons/youcam-shaadiglow
  gh repo create shaadiglow --public --source . --push      # or create it on github.com and `git push`
  ```
  Public with the MIT `LICENSE` satisfies the rules (alternative: private and shared with
  contact_event@PerfectCorp.com).
- Your YouCam API key from the India console (step 1 of NOTES.md).
- Optional but recommended first: run `scripts/live_smoke.py --prewarm core` locally and commit `cache_seed/`, so the
  deployed sample journeys cost 0 units (see NOTES.md).

## 1. Create a Render account

1. Go to https://render.com and click **Get Started**.
2. Choose **Sign up with GitHub** and authorise Render. Verify your email if asked.
3. The free plan needs no card for a free web service. If Render asks for a card, it is only for verification.

## 2. Create the service from the blueprint

1. In the Render dashboard click **New +** → **Blueprint**.
2. Connect the GitHub repository `shaadiglow` (grant access to that repo only).
3. Render reads `render.yaml`: one **free Docker web service** named `shaadiglow` in **Singapore** (closest region
   to India), health check `/api/health`.
4. Render asks for the value of **`YOUCAM_API_KEY`** (it is marked `sync: false`). Paste the key there. It is stored
   as an encrypted environment variable and never appears in the repo.
5. Leave the other values as they are: `YOUCAM_REGION=india`, `SG_RESERVE_UNITS=60`, `SG_CLIENT_DAILY_UNITS=60`,
   `SG_ALLOW_LIVE_UPLOADS=true`.
6. Click **Apply**. The first build takes about 3–5 minutes.

If you prefer not to use the blueprint: **New +** → **Web Service** → pick the repo → Runtime **Docker** →
Instance type **Free** → Region **Singapore** → **Advanced** → add the environment variables above (mark
`YOUCAM_API_KEY` as secret) → Health check path `/api/health` → **Create Web Service**.

## 3. Test the deployment

1. Open `https://shaadiglow.onrender.com/api/health` (Render shows your exact URL). Expect
   `{"ok":true,"mode":"live",...}`. If it says `"mode":"mock"`, the key is missing: check **Environment**.
2. Open the root URL on your phone. The top pill should read **Live AI**.
3. Tap **Ananya** → **Continue**. The scan tag should say **cached · 0 units** if you committed the pre-warmed
   `cache_seed/`; otherwise it spends 14 units once and caches it.
4. Tap ⓘ: check **Units left** matches your YouCam console balance (it reads the real balance from the Unit API).
5. Try one upload of your own photo to confirm the live path end to end.

## 4. Keep it up until 20 Nov

- Free Render services **sleep after 15 minutes without traffic**; the next visit takes ~30–60 s to wake. Mention
  this in the Devpost testing instructions, or keep it awake with a free uptime monitor (e.g. UptimeRobot, HTTP
  check of `/api/health` every 10 minutes). A 31-day month of uptime is 744 hours, within Render's 750 free hours.
- Render's free disk is ephemeral: runtime cache, uploads and the ledger reset on each deploy/restart. That is fine:
  the sample journeys come from the committed `cache_seed/`, and the budget guard reads the real balance from YouCam
  (so a restart cannot overspend).
- Do not push changes after the deadline that alter the submitted behaviour; only fixes for availability.

## 5. Updating

Every `git push` to the default branch redeploys automatically (`autoDeploy: true`). To rotate the key: Render →
service → **Environment** → edit `YOUCAM_API_KEY` → **Save, rebuild and deploy**.

## Local Docker (optional)

```bash
docker build -t shaadiglow .
docker run -p 10000:10000 -e YOUCAM_API_KEY="$YOUCAM_API_KEY" shaadiglow   # omit the key for demo mode
open http://localhost:10000
```
