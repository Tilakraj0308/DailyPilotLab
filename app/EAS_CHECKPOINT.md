# EAS Android Test Checkpoint

This guide creates a standalone Android APK for private testing. It uses the deployed Render API and does not require Expo Go, a local Metro server, or a Google Play Console account.

## Runtime topology

- API: `https://dailypilotlab-2.onrender.com`
- Android package: `com.bharat948.dailypilot`
- Native URL scheme: `dailypilot`
- EAS build profile: `preview`
- EAS environment: `preview`

The build uses the existing Supabase project and database. Use designated test accounts.

## 1. Confirm Expo project access

From this directory:

```bash
npx eas-cli@latest login
npx eas-cli@latest whoami
npx eas-cli@latest project:info
```

The account must own or have access to project ID `3252f4f9-e2ed-4b83-b5e2-c8dd68076d4a`. Do not run `eas init --force` if access fails; first confirm which Expo account owns the existing project.

## 2. Configure the Expo Preview environment

In the Expo dashboard, open the project, then **Project settings → Environment variables**. Add these variables to the **Preview** environment:

| Variable | Value |
| --- | --- |
| `EXPO_PUBLIC_API_URL` | `https://dailypilotlab-2.onrender.com` |
| `EXPO_PUBLIC_SUPABASE_URL` | Copy the value from the ignored local `.env` |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Copy the value from the ignored local `.env` |

Alternatively, use `eas env:create` for each value. Do not place server secrets in an `EXPO_PUBLIC_*` variable; these values are embedded in the APK.

Verify the variable names without printing sensitive values:

```bash
npx eas-cli@latest env:list --environment preview
```

## 3. Configure Supabase login redirects

In **Supabase Dashboard → Authentication → URL Configuration**, retain the existing URLs and add the native app redirect pattern:

```text
dailypilot://**
```

The EAS APK uses the custom `dailypilot` scheme instead of an Expo Go `exp://` return URL.

## 4. Configure connector callbacks in Google Cloud

In the connector OAuth Web client, add these exact **Authorized redirect URIs**:

```text
https://dailypilotlab-2.onrender.com/connectors/google_calendar/callback
https://dailypilotlab-2.onrender.com/connectors/google_tasks/callback
https://dailypilotlab-2.onrender.com/connectors/gmail/callback
```

Enable the Google Calendar API, Google Tasks API, and Gmail API. If the consent screen is in Testing mode, add every tester's Google account under **OAuth consent screen → Test users**.

The connector OAuth client is separate from the Google client used by Supabase login.

## 5. Configure matching Render variables

In the Render service environment, set:

```text
GOOGLE_CONNECTOR_REDIRECT_URI=https://dailypilotlab-2.onrender.com/connectors/google_calendar/callback
GOOGLE_TASKS_CONNECTOR_REDIRECT_URI=https://dailypilotlab-2.onrender.com/connectors/google_tasks/callback
GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI=https://dailypilotlab-2.onrender.com/connectors/gmail/callback
```

Retain the existing connector client ID, client secret, token-encryption secret, Supabase verification configuration, database values, and AI-provider credentials. Save the environment and allow Render to redeploy.

## 6. Validate locally

```bash
npm install
npx tsc --noEmit
npx expo config --type public
```

The public Expo configuration must show the `dailypilot` scheme, the Android package, and the EAS project ID.

## 7. Build the APK

```bash
npx eas-cli@latest build --platform android --profile preview
```

For the first Android build, allow EAS to generate and manage the keystore unless the package already has an established release keystore. Preserve that credential for future builds.

When the job finishes, open the build URL or scan its QR code on an Android phone. Download and install the APK, allowing installation from the browser when Android asks.

## 8. Device acceptance test

1. Launch from a cold state.
2. Sign in with Google and finish onboarding.
3. Relaunch and confirm the session persists.
4. Send a text chat message and receive streamed output.
5. Record and upload an audio message.
6. Create, modify, complete, and delete a DailyPilot task.
7. Exercise memories, settings, and token usage.
8. Connect Calendar and verify its allowed tools.
9. Connect Google Tasks, select a list, and exercise its operations.
10. Connect Gmail, read a safe test thread, create a draft, and send only a safe test message.
11. Disconnect and reconnect each connector.
12. Sign out and sign in again.

Test both successful consent and denied consent for every connector. A connector callback must return to `dailypilot://connectors/callback` and reopen the installed app.

## Troubleshooting

- **EAS project permission error:** sign in to the Expo account that owns the project; do not overwrite the project ID.
- **App calls localhost or a LAN IP:** the Preview EAS variables were not selected or configured; rebuild after correcting them.
- **Supabase login stays in the browser:** confirm `dailypilot://**` is in the Supabase redirect allowlist.
- **Google reports `redirect_uri_mismatch`:** compare the Google Cloud URI with the Render variable character-for-character.
- **Google says access is blocked:** add the tester under Google OAuth test users and confirm the requested scopes are declared.
- **First API call is slow:** allow for a Render cold start, then retry once.
- **Connector returns `Invalid token`:** verify Render's `SUPABASE_URL` or legacy JWT-secret configuration.
