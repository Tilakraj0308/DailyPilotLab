# DailyPilot: End-to-End EAS Setup with Hosted Render Server

This document records the complete setup used to produce a private, installable Android APK for DailyPilot.

It covers:

- the Expo/EAS project;
- the FastAPI server hosted on Render;
- Supabase authentication and database access;
- Google Calendar, Google Tasks, and Gmail connectors;
- building and installing the APK;
- testing the complete mobile flow.

This is a development/testing release. It does not publish the app to Google Play and does not require a Play Console account or the Play closed-testing requirement.

## 1. Final architecture

```text
Android APK built by EAS
  |
  |-- Supabase Auth and database
  |     `-- Google login returns to dailypilot://
  |
  `-- FastAPI server on Render
        https://dailypilotlab-2.onrender.com
        |-- profile, onboarding, chat, tasks, memories, token APIs
        `-- Google connector OAuth callbacks
              `-- returns to dailypilot://connectors/callback
```

The APK must not use a laptop-only URL such as `localhost` or `192.168.x.x`. Those addresses work only on a local network. The Preview build embeds the public Render URL instead.

## 2. Project identity

These values must remain stable:

| Setting | Value |
| --- | --- |
| Expo project | `@bharat948/dailypilot` |
| EAS project ID | `3252f4f9-e2ed-4b83-b5e2-c8dd68076d4a` |
| Android package | `com.bharat948.dailypilot` |
| Native URL scheme | `dailypilot` |
| Render API | `https://dailypilotlab-2.onrender.com` |
| EAS test profile | `preview` |
| EAS test artifact | Android APK (`.apk`) |

Changing the Android package can break signing continuity. Changing the scheme can break Supabase login and connector returns.

## 3. Branch and repository configuration

The EAS work is on:

```text
codex/eas-development
```

Important files:

- [app/app.json](app/app.json): app identity, package, scheme, icons, and EAS project ID.
- [app/eas.json](app/eas.json): EAS profiles.
- [app/src/lib/env.ts](app/src/lib/env.ts): required public client configuration.
- [app/src/lib/api.ts](app/src/lib/api.ts): shared API URL helper.
- This file is the single source of truth for the EAS checkpoint and hosted-server setup.

The canonical preview profile is:

```json
{
  "preview": {
    "distribution": "internal",
    "environment": "preview",
    "env": {
      "EXPO_PUBLIC_API_URL": "https://dailypilotlab-2.onrender.com"
    },
    "android": { "buildType": "apk" }
  }
}
```

The production profile remains an Android App Bundle profile for a future Play Store release.

## 4. Render server prerequisites

The FastAPI server must be deployed and reachable over HTTPS before creating the shared APK. Verify it from a terminal:

```bash
curl -fsS https://dailypilotlab-2.onrender.com/openapi.json > /tmp/dailypilot-openapi.json
```

The server must have its existing database, Supabase, AI, encryption, and connector secrets configured in Render. Do not put any of those server-only secrets in the mobile app or in an `EXPO_PUBLIC_*` variable.

### Render connector variables

Set these variables in the Render service environment. The values must match Google Cloud exactly:

```text
GOOGLE_CONNECTOR_REDIRECT_URI=https://dailypilotlab-2.onrender.com/connectors/google_calendar/callback
GOOGLE_TASKS_CONNECTOR_REDIRECT_URI=https://dailypilotlab-2.onrender.com/connectors/google_tasks/callback
GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI=https://dailypilotlab-2.onrender.com/connectors/gmail/callback
```

Retain the existing values for:

- database connection;
- `SUPABASE_URL` or the legacy `SUPABASE_JWT_SECRET`;
- Google connector client ID and client secret;
- connector encryption secret;
- OpenAI/AI provider credentials;
- AWS KMS credentials, if used by the server.

After changing Render variables, save and wait for the service redeploy to finish.

Render free/sleeping instances can be slow on the first request. Allow one cold-start delay before treating the request as failed.

## 5. Expo account and EAS access

Create or use an Expo account, then run from `app/`:

```bash
npx eas-cli@latest login
npx eas-cli@latest whoami
npx eas-cli@latest project:info
```

The project must resolve to `@bharat948/dailypilot` and the EAS project ID above. If the account does not have access, sign in to the account that owns the project. Do not run `eas init --force`, because it can replace the existing project linkage.

EAS stores Android signing credentials remotely. On the first build, allow EAS to generate and manage the keystore. Keep using that credential for future builds of this Android package.

## 6. EAS Preview environment variables

In the Expo project dashboard, open **Project settings → Environment variables**, select **Preview**, and add:

| Name | Value | Visibility |
| --- | --- | --- |
| `EXPO_PUBLIC_API_URL` | `https://dailypilotlab-2.onrender.com` | Plain text |
| `EXPO_PUBLIC_SUPABASE_URL` | The value from the local ignored `app/.env` | Plain text |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | The value from the local ignored `app/.env` | Sensitive |

The Supabase anon/publishable key is a client-side value, but it is still embedded in the APK. Never add a Supabase service-role key, database password, OAuth client secret, OpenAI key, KMS key, or encryption secret here.

Verify only the variable names:

```bash
npx eas-cli@latest env:list --environment preview
```

Do not commit `app/.env`; it is intentionally ignored by Git.

## 7. Supabase authentication setup

In **Supabase Dashboard → Authentication → URL Configuration**:

1. Keep the existing web, localhost, and Expo Go redirect URLs used for development.
2. Add the native application pattern:

```text
dailypilot://**
```

The installed APK uses `dailypilot://` for Google/Supabase login. Expo Go uses a different `exp://` URL, so both forms may be needed during development.

Login acceptance flow:

```text
APK → Supabase Google OAuth → Google → Supabase callback
    → dailypilot:// → APK → GET /auth/profile on Render
```

## 8. Google Cloud connector setup

The Google connector OAuth client is separate from the Google OAuth client used by Supabase login.

In the connector OAuth Web client, add these exact **Authorized redirect URIs**:

```text
https://dailypilotlab-2.onrender.com/connectors/google_calendar/callback
https://dailypilotlab-2.onrender.com/connectors/google_tasks/callback
https://dailypilotlab-2.onrender.com/connectors/gmail/callback
```

Enable these APIs in Google Cloud:

- Google Calendar API;
- Google Tasks API;
- Gmail API.

If the consent screen is in Testing mode, add every tester's Google account under **OAuth consent screen → Test users**. Otherwise Google may show an access-blocked message even when the redirect URL is correct.

The connector flow is:

```text
APK → POST /connectors/{provider}/start on Render
    → Google consent
    → Render callback
    → dailypilot://connectors/callback
    → APK refreshes connector status
```

## 9. Validate before building

From the `app/` directory:

```bash
npm install
npx expo config --type public
npx tsc --noEmit --skipLibCheck --jsx react-jsx \
  --module preserve --moduleResolution bundler --target es2022 \
  --allowSyntheticDefaultImports \
  src/lib/env.ts src/lib/api.ts src/lib/supabase.ts src/components/DebugInfo.tsx
```

The Expo config should show:

- scheme `dailypilot`;
- Android package `com.bharat948.dailypilot`;
- EAS project ID `3252f4f9-e2ed-4b83-b5e2-c8dd68076d4a`.

## 10. Create the EAS APK

Run:

```bash
cd app
npx eas-cli@latest config --platform android --profile preview
npx eas-cli@latest build --platform android --profile preview
```

The resolved profile must show:

```text
distribution: internal
environment: preview
buildType: apk
```

The build runs on Expo's servers. It bundles the JavaScript code and Preview environment variables, compiles the native Android project, signs the APK, and publishes a build page and download link.

The APK does not require Expo Go or a running Metro server.

## 11. Download and install

Use the **Install** or **Download** button on the EAS build page, or open the APK link directly in Chrome on Android.

From a development computer, the official CLI download is more reliable than an in-app browser:

```bash
cd app
npx eas-cli@latest build:download \
  --build-id <EAS_BUILD_ID>
```

To install over USB with Android Debug Bridge:

```bash
adb install -r path/to/application.apk
```

For browser installation, Android may ask you to allow **Install unknown apps** for Chrome or the file manager. Revoke that permission afterward if desired.

## 12. Complete mobile acceptance test

Use designated test accounts because the APK connects to the existing Supabase database and Render service.

### Authentication and account

1. Launch the APK from a cold state.
2. Tap **Continue with Google**.
3. Complete Google consent.
4. Confirm the browser returns to the DailyPilot app.
5. Complete onboarding.
6. Close and reopen the app; confirm the session persists.
7. Sign out and sign in again.

### Core application

1. Load Home and Profile.
2. Send a text chat message and wait for streamed output.
3. Record and upload an audio message.
4. Create, update, complete, and delete a task.
5. Open memories and token usage.
6. Confirm errors are visible instead of causing a crash.

### Google connectors

For each connector, test both approval and denial:

1. Open Profile → Integrations.
2. Connect Google Calendar.
3. Connect Google Tasks and select a task list.
4. Connect Gmail.
5. Exercise read operations.
6. Create a safe Gmail draft.
7. Send only a safe test message after explicit confirmation.
8. Disconnect and reconnect each connector.

Every callback should reopen the APK through `dailypilot://connectors/callback` and return the user to the appropriate connector screen.

## 13. Troubleshooting

### The app calls localhost or a LAN IP

The APK was built without the EAS Preview variables or with the wrong EAS environment. Correct the Preview variables and create a new build. Environment values are embedded at build time; changing them later does not change an already-installed APK.

### Supabase login does not return to the app

Confirm `dailypilot://**` is in Supabase's redirect allowlist and that the APK was built from the current `app.json` scheme.

### Google reports `redirect_uri_mismatch`

Compare the Google Cloud Authorized redirect URI with the Render variable character-for-character. The provider path must be correct for Calendar, Tasks, and Gmail.

### Google reports access blocked

Add the Google account as an OAuth consent-screen test user and confirm the required APIs/scopes are enabled.

### Connector reports `Invalid token`

Verify Render has the same `SUPABASE_URL` as the mobile project's Supabase URL, or the correct legacy JWT secret when the project uses HS256. Restart/redeploy the Render service after changing it.

### The first API request is slow

Render may be waking from sleep. Wait for the first request to complete and retry once before diagnosing authentication.

### The APK link does not download

Open the link in Chrome rather than an embedded browser, use the EAS build page's Download button, or use `eas build:download` from the project directory.

## 14. Future Play Store release

The same project retains a `production` EAS profile that produces an Android App Bundle:

```bash
npx eas-cli@latest build --platform android --profile production
```

That AAB is for Google Play. A future Play Store release will additionally require Play Console registration, store listing/policy forms, privacy and account-deletion resources, and—in a new personal account—the required closed test before production access.
