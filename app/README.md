# DailyPilot — App (Mobile + Web)

Expo React Native client for DailyPilot. Runs as a **native mobile app** (iOS/Android) and as a **Progressive Web App (PWA)** in the browser — all from the same codebase. Uses **Supabase Auth** for authentication with an auth-agnostic backend design.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| [Expo Go](https://expo.dev/go) | Install on your Android/iOS device (for native dev) |
| A modern browser | Chrome, Firefox, Edge (for web dev) |
| A Supabase project | free tier is fine |

---

## Setup

### 1. Install Dependencies

```bash
cd app
npm install
```

### 2. Supabase Auth Configuration

#### a) Google OAuth Client (Google Cloud Console)

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Create an **OAuth 2.0 Client ID** → type: **Web application**
   > Only a **Web application** type is needed. The OAuth flow goes entirely through Supabase's hosted callback — no Android/iOS client IDs required.
3. Under **Authorized redirect URIs**, add the Supabase callback URL:
   ```
   https://<your-project-ref>.supabase.co/auth/v1/callback
   ```
   > You'll get this exact URL from Supabase (see step b below).
4. Note down the **Client ID** and **Client Secret**.

#### b) Enable Google Provider in Supabase

1. Go to **Supabase Dashboard → Authentication → Providers → Google**
2. Toggle **Enable**
3. Paste the **Client ID** and **Client Secret** from step (a)
4. Copy the **Callback URL** shown — this is what you added to Google Console in step (a)
5. Save

#### c) Configure Redirect URLs in Supabase

Go to **Supabase Dashboard → Authentication → URL Configuration**.

**Redirect URLs** — Add **all** of the following entries. Wildcards (`*`) survive dynamic IP changes.

For **Mobile / Expo Go**:
- `dailypilot://*`
- `exp://*`
- `https://auth.expo.io/*`

For **Web browser (local development)**:
- `http://localhost:8081/*`
- `http://<your-machine-ip>:8081/*` — replace with your LAN IP (find it: `hostname -I`)

> ⚠️ **Important:** Once you add your first Redirect URL entry, Supabase enforces a strict allowlist. If your web login gets stuck or tries to open `xdg-open`, the URL your browser is running on is not in the list. Add it and retry.

### 3. Environment Variables

Create your `.env` from the example:

```bash
cp .env.example .env
```

Fill in the values:

| Variable | Where to find it |
|----------|--------------------|
| `EXPO_PUBLIC_API_URL` | Your machine's LAN IP + port 8000 |
| `EXPO_PUBLIC_SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API → anon public key |

```ini
# Backend API — use your machine's LAN IP so that native devices AND
# the web browser (on the same machine) can both reach the backend.
# Find your IP with: hostname -I | awk '{print $1}'
EXPO_PUBLIC_API_URL=http://<your-machine-ip>:8000

# Supabase (from Dashboard → Settings → API)
EXPO_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

> ⚠️ **Use your LAN IP, not `localhost`**, for `EXPO_PUBLIC_API_URL`. A LAN IP works for browsers, simulators, and physical devices simultaneously. `localhost` only works for the current machine.

> **Never commit `.env`** — it is already in `.gitignore`.

---

## Run

Start the [backend server](../server/README.md) first, then:

### Mobile (Expo Go / Simulator)

```bash
npx expo start
```

- Press **a** → Android device/emulator
- Press **i** → iOS simulator
- Scan the QR code with **Expo Go** on your phone

### Web Browser (PWA)

```bash
# Option 1: Start all platforms, then press W in the terminal
npx expo start

# Option 2: Launch web directly
npx expo start --web

# Option 3: npm script shortcut
npm run web
```

The app will open at **`http://localhost:8081`**.

> 💡 **Web-specific notes:**
> - The app is centered at a max-width of **480px** on desktop — preserving the mobile-first design.
> - Voice recording via the mic button uses the browser's native `MediaRecorder` API. **Chrome** is recommended for the best audio support.
> - The browser will request microphone permission on first use of voice chat.
> - On Google login, you will be redirected to `http://localhost:8081` after authentication — make sure this URL is in your Supabase Redirect URLs list (see Setup § c above).

---

## Auth Flow

### Mobile (Native Deep Link)
```
User taps "Continue with Google"
  → Supabase OAuth URL opens in in-app browser
    → Google authenticates user
      → Google redirects to Supabase callback
        → Supabase redirects back to app via deep link (exp:// or dailypilot://)
          → App parses tokens from URL and sets session
            → AuthContext calls GET /auth/profile on backend
```

### Web Browser
```
User clicks "Continue with Google"
  → Browser navigates to Supabase OAuth URL
    → Google authenticates user
      → Google redirects to Supabase callback
        → Supabase redirects back to http://localhost:8081
          → Supabase JS SDK auto-detects token in URL hash (detectSessionInUrl: true)
            → onAuthStateChange fires → session is set
              → AuthContext calls GET /auth/profile on backend
```

All auth state is managed by Supabase. The backend only verifies the JWT and maintains its own `public.users` table via `external_auth_id` (auth-agnostic — no vendor lock-in).

---

## Connectors (Google Calendar, Google Tasks, Gmail, Notion)

Sign-in uses **Supabase + Google** for account auth. **Google Calendar**, **Google Tasks**, and **Gmail** share a **separate Google OAuth Web client** on the backend (`GOOGLE_CONNECTOR_*` and per-product redirect env vars in server `.env`). **Notion** uses its own public integration OAuth (`NOTION_CLIENT_*`, `NOTION_CONNECTOR_REDIRECT_URI` — see [`server/.env.example`](../server/.env.example) and [`server/README.md`](../server/README.md)).

Flow (all connectors):

1. User opens **Profile** (Me tab or avatar menu) and taps a connector under Integrations.
2. App calls `POST /connectors/{provider}/start` (`google_calendar`, `google_tasks`, `gmail`, or `notion`) with the Supabase JWT and a `return_to` URL (where the backend redirects after OAuth).
3. User completes provider consent; the provider hits the **server** callback `GET /connectors/{provider}/callback`.
4. Server exchanges the code (Google: PKCE; Notion: Basic-auth token endpoint per Notion docs), encrypts tokens, stores them, then redirects the browser/app to `return_to?connector_status=success|error&provider=...`.

**Consent UX:** Calendar, Tasks, and Gmail are **separate** connector providers but use the **same** Google OAuth Web client. The API usually **does not** send `prompt=consent` so Google can use **incremental authorization** when you connect another Google product (often a shorter step). It **does** send `prompt=consent` when that connector is already in `reauth_required` or `error` so you get a full re-approval. Google still hosts the consent screen; it cannot be replaced for these APIs.

**Google Cloud:** Enable **Google Calendar API**, **Google Tasks API**, and **Gmail API** for the project. Under the OAuth client’s **Authorized redirect URIs**, add every URI you use:

- `GOOGLE_CONNECTOR_REDIRECT_URI` — e.g. `http://127.0.0.1:8000/connectors/google_calendar/callback`
- `GOOGLE_TASKS_CONNECTOR_REDIRECT_URI` — required; e.g. `http://127.0.0.1:8000/connectors/google_tasks/callback` (must not reuse the Calendar callback path — Google hits that exact URL and the server routes by path)
- `GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI` — e.g. `http://127.0.0.1:8000/connectors/gmail/callback` (same pattern; register explicitly unless you rely on derivation from the Calendar URI — see server `.env.example`)

Ensure `EXPO_PUBLIC_API_URL` points at your API for device testing.

**Notion:** Create a **public** integration in the Notion developer dashboard and add the same redirect URI as `NOTION_CONNECTOR_REDIRECT_URI` on the server. Secrets stay in `server/.env` only.

**Google Tasks (v1):** After connecting, choose **one** task list; the app stores it server-side (`user_connector_resources`). Profile shows a short preview and quick-add for that list.

**Gmail:** Provider key `gmail`. **Tool Access** ([`ToolAccessScreen.tsx`](src/connectors/ToolAccessScreen.tsx)) is used for tool permissions and connector history for `gmail`, the same pattern as Calendar / Tasks / Notion (`GET` / `PUT /connectors/gmail/permissions`, `GET /connectors/gmail/history`). The dedicated inbox UI is **`GmailConnectorScreen`** (stack route name **`GmailConnector`** in the navigation plan); wire it in `App.tsx` when the screen lands. Those flows call the backend with `getApiUrl()` and `Authorization: Bearer <Supabase access token>`:

| Endpoint | Role |
|----------|------|
| `GET /connectors` | Connector status row for `gmail` (with other providers) |
| `POST /connectors/gmail/start` | Start Gmail OAuth (same JSON body as other `…/start` routes) |
| `GET /connectors/gmail/priority` | Priority thread list for the inbox UI |
| `GET /connectors/gmail/threads/{thread_id}` | Thread detail for read / draft context |
| `POST /connectors/gmail/drafts` | Create a draft |
| `POST /connectors/gmail/drafts/{draft_id}/send` | Send a draft after explicit confirmation |
| `GET` / `PUT /connectors/gmail/permissions` | Tool permission toggles (shared connector route shape) |
| `GET /connectors/gmail/history` | Activity feed for Gmail tool / UI actions |

If you see **`Invalid token`** when connecting, the backend cannot verify your Supabase session JWT (this happens **before** any Google redirect). Add **`SUPABASE_URL`** to `server/.env` (same as `EXPO_PUBLIC_SUPABASE_URL`) if your project uses **JWT Signing Keys / ES256**; otherwise set **`SUPABASE_JWT_SECRET`** to the **JWT Secret** from Supabase → Project Settings → API. Restart the API.

---

## Project Structure

```
app/
├── App.tsx                         # Root — AuthProvider, NavigationContainer ref, OAuth → Profile on web
├── src/
│   ├── context/
│   │   └── AuthContext.tsx         # Auth state provider (session, signOut)
│   ├── lib/
│   │   ├── api.ts                  # getApiUrl() — backend base URL (LAN / emulator rules)
│   │   ├── supabase.ts             # Supabase client (detectSessionInUrl: true on web)
│   │   └── alerts.ts               # Cross-platform alert helper (window.alert on web)
│   ├── connectors/                 # Integrations UI + connector API client (Calendar, Tasks, Gmail, Notion)
│   │   ├── api.ts
│   │   ├── ConnectorsSection.tsx
│   │   ├── oauthFlow.ts
│   │   ├── ToolAccessScreen.tsx
│   │   ├── GmailConnectorScreen.tsx  # (when added) Gmail priority inbox + drafts — stack: GmailConnector
│   │   └── …
│   ├── hooks/
│   │   └── useChat.ts              # Chat state, SSE streaming, web-compatible audio upload
│   ├── components/
│   │   ├── MainBottomNav.tsx       # Shared bottom bar (Home / Chat / Me → Profile)
│   │   └── SoundBarsEqualizer.tsx  # Reanimated audio visualizer (native only)
│   └── screens/
│       ├── LoginScreen.tsx         # Google OAuth (web redirect vs native in-app browser)
│       ├── HomeScreen.tsx          # Main dashboard
│       ├── ChatScreen.tsx          # Chat UI with voice recording (web + native)
│       ├── ProfileScreen.tsx       # Account, integrations, sign out (Me tab)
│       └── SettingsScreen.tsx      # App preferences placeholder; connectors live on Profile
├── app.json                        # Expo config (scheme: dailypilot, web: favicon)
└── .env                            # Environment variables (gitignored)
```
