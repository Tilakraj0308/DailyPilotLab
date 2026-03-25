# DailyPilot — Mobile App

Expo React Native client for DailyPilot. Uses **Supabase Auth** for authentication with an auth-agnostic backend design.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| [Expo Go](https://expo.dev/go) | Install on your Android/iOS device |
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

#### c) Add Redirect URLs (recommended for production)

> By default Supabase allows **all** redirect URLs. Once you add your first entry, it enforces an allowlist. Skip this for local dev; add them before going to production.

1. Go to **Supabase Dashboard → Authentication → URL Configuration**
2. Under **Redirect URLs**, add:
   - `dailypilot://` (for production builds)
   - `exp://*` (for development with Expo Go)

### 3. Environment Variables

Create your `.env` from the example:

```bash
cp .env.example .env
```

Then fill in the values:

| Variable | Where to find it |
|----------|-----------------|
| `EXPO_PUBLIC_API_URL` | Your machine's LAN IP + port 8000 (see note below) |
| `EXPO_PUBLIC_SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API → anon public key |

```ini
# Backend API — must be your machine's local network IP when testing on a physical device
# Find it with: hostname -I | awk '{print $1}'
# Use "localhost" only when testing on web or Android emulator (10.0.2.2)
EXPO_PUBLIC_API_URL=http://<your-machine-ip>:8000

# Supabase (from Dashboard → Settings → API)
EXPO_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

> ⚠️ **`EXPO_PUBLIC_API_URL` must be your machine's LAN IP** (e.g. `http://192.168.1.6:8000`), not `localhost`. On a physical phone, `localhost` refers to the phone itself, not your computer. Run `hostname -I` to find your IP.

> **Never commit `.env`** — it is already listed in `.gitignore`.

---

## Run

Make sure the [backend server](../server/README.md) is running first, then:

```bash
npx expo start
```

- Press **a** to open on a connected Android device
- Press **w** to open in the web browser
- Or scan the QR code with Expo Go on your phone

---

## Auth Flow

```
User taps "Continue with Google"
  → Supabase OAuth URL opens in browser
    → Google authenticates user
      → Google redirects to Supabase callback
        → Supabase redirects back to app via deep link
          → App receives session tokens
            → AuthContext calls GET /auth/profile on backend
              → Backend auto-creates user in public.users
```

All auth state is managed by Supabase. The backend only verifies the JWT and maintains its own `public.users` table via `external_auth_id` (auth-agnostic — no vendor lock-in).

---

## Project Structure

```
app/
├── App.tsx                      # Root — wraps app in AuthProvider
├── src/
│   ├── context/
│   │   └── AuthContext.tsx       # Auth state provider (session, signOut)
│   ├── lib/
│   │   ├── supabase.ts          # Supabase client init
│   │   └── api.ts               # Dynamic API URL resolver
│   └── screens/
│       ├── LoginScreen.tsx      # Google OAuth via Supabase
│       └── HomeScreen.tsx       # Main app screen
├── app.json                     # Expo config (scheme: dailypilot)
└── .env                         # Environment variables (gitignored)
```
