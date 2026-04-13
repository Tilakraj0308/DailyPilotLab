# Google OAuth Setup Guide

This guide walks you through creating the Google OAuth credentials required for the DailyPilot React Native (Expo) app and the Python (FastAPI) backend.

## 1. Create a Project in Google Cloud

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top left and select **New Project**.
3. Name it `DailyPilot` and click **Create**.
4. Make sure your newly created project is selected in the top-left dropdown.

## 1.1 Enable Required APIs

Before the app can access Google data, you must enable the specific APIs:

1. In the Google Cloud Console, go to **APIs & Services > Library**.
2. Search for and **Enable** the following:
   * **Google Calendar API**
   * **Google Tasks API**
   * **Gmail API**

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
6. On the **Test users** step (or via the **OAuth consent screen** menu later), click **Add Users** and add any Google email addresses you will use for testing. 
   * **Note**: While the app is in "Testing" mode, only these specific users can connect their accounts.

## 3. Create the Web Client ID (Crucial for Expo AuthSession & Backend)

We will create a **Web application** Client ID. Even though we are building a mobile app, Expo's `AuthSession` uses a web-based proxy for maximum compatibility during development, and the Python backend requires a Web Client ID to verify tokens securely.

1. Go to **APIs & Services > Credentials** in the left menu.
2. Click **+ CREATE CREDENTIALS** at the very top and select **OAuth client ID**.
3. For **Application type**, select **Web application**.
4. Name: `DailyPilot Web & Expo Client`
5. Under **Authorized JavaScript origins**, click **ADD URI**:
   * Add: `https://auth.expo.io`
6. Under **Authorized redirect URIs**, click **ADD URI**:
   * **For Frontend (Expo)**: Add `https://auth.expo.io/@your_expo_username/frontend` *(Replace `@your_expo_username` with your actual Expo account username)*.
   * **For Connectors (Backend)**: Add `http://localhost:8000/connectors/google/calendar/callback`.
7. Click **Create**.
8. A modal will pop up with your **Client ID** and **Client Secret**.

## 4. Update the Backend Environment

1. Copy the **Client ID** from the previous step.
2. Open your VSCode and create a new file at `backend/.env`.
3. Paste (or update) the following into the file:

```env
# Frontend Authentication
GOOGLE_CLIENT_ID=your-google-client-id

# Connectors (Google Calendar)
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/connectors/google/calendar/callback
CONNECTOR_TOKEN_ENCRYPTION_KEY=your-generated-key
```

> **Note:** The frontend only needs the Client ID, but the **Connectors** (e.g., Google Calendar) require the **Client Secret**, **Redirect URI**, and an **Encryption Key** to securely manage OAuth tokens.

## 5. Next Steps

Once your `backend/.env` file is saved with the active Client ID, our authentication backend is fully ready to receive tokens from the frontend!
