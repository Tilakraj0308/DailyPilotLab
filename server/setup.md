# Google OAuth Setup Guide

This guide walks you through creating the Google OAuth credentials required for the DailyPilot React Native (Expo) app and the Python (FastAPI) backend.

## 1. Create a Project in Google Cloud
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top left and select **New Project**.
3. Name it `DailyPilot` and click **Create**.
4. Make sure your newly created project is selected in the top-left dropdown.

## 2. Configure the OAuth Consent Screen
Before creating credentials, you must set up the consent screen (the screen users see when they click "Continue with Google").

1. In the left sidebar menu, go to **APIs & Services > OAuth consent screen**.
2. Choose **External** (unless you have a Google Workspace org and only want internal users). Click **Create**.
3. Fill in the required fields:
   * **App name**: `DailyPilot`
   * **User support email**: *Your email*
   * **Developer contact info**: *Your email*
4. Click **Save and Continue**.
5. On the **Scopes** step, just click **Save and Continue** (the default basic profile/email scopes are enough).
6. On the **Test users** step, click **Add Users** and add your own Google email address so you can test it while the app is unpublished. Click **Save and Continue**.

## 3. Create the Web Client ID (Crucial for Expo AuthSession & Backend)
We will create a **Web application** Client ID. Even though we are building a mobile app, Expo's `AuthSession` uses a web-based proxy for maximum compatibility during development, and the Python backend requires a Web Client ID to verify tokens securely.

1. Go to **APIs & Services > Credentials** in the left menu.
2. Click **+ CREATE CREDENTIALS** at the very top and select **OAuth client ID**.
3. For **Application type**, select **Web application**.
4. Name: `DailyPilot Web & Expo Client`
5. Under **Authorized JavaScript origins**, click **ADD URI**:
   * Add: `https://auth.expo.io`
6. Under **Authorized redirect URIs**, click **ADD URI**:
   * Add: `https://auth.expo.io/@your_expo_username/frontend` *(Replace `@your_expo_username` with your actual Expo account username if you have one linked, otherwise leave it as `https://auth.expo.io`)*.
7. Click **Create**.
8. A modal will pop up with your **Client ID** and **Client Secret**.

## 4. Update the Backend Environment
1. Copy the **Client ID** from the previous step.
2. Open your VSCode and create a new file at `backend/.env`.
3. Paste the following into the file:

```env
GOOGLE_CLIENT_ID=your-copied-client-id.apps.googleusercontent.com
JWT_SECRET_KEY=generate_a_random_long_string_here_like_dj73nd8q3id91k
```

> **Note:** The backend only needs the Client ID, not the Secret, because it only verifies incoming ID tokens.

## 5. Next Steps
Once your `backend/.env` file is saved with the active Client ID, our authentication backend is fully ready to receive tokens from the frontend!
