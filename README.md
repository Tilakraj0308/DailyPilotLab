# DailyPilotLab

Welcome to **DailyPilot**, your intelligent personal assistant application.

DailyPilot is designed to help you manage your daily chores, remember your choices, track your habits, and stay aligned with your goals. By learning what matters to you, it uniquely curates every day to help you stay productive and balanced.

---

## 🛠 For Developers & Contributors

The project is split into two main components. If you are a developer looking to set up the project locally or contribute, please refer to the individual component setups:

**AI / agent tooling:** [AGENTS.md](AGENTS.md) (repo map, commands, links to `.notes/`), [`.cursor/rules/`](.cursor/rules/) (Cursor project rules), and nested `AGENTS.md` files under `server/` and `app/`.

### 📚 Design & Architecture Decisions (`docx/`)

Key design and architectural decisions are documented in the [`docx/`](./docx/) directory at the root level of the repository. This directory stores decision records detailing architectural choices, trade-offs, and implementation strategies, for example:
- **Audio Provider Choice:** Rationale for using Deepgram over OpenAI TTS.
- **API Key Model:** Strategy around introducing user API keys for usage tracking rather than application-managed keys.

---

### 1. [Server (Backend)](./server/README.md)
The backend is a FastAPI service powered by a Supabase Postgres database with the `pgvector` extension. It handles semantic search, AI-driven topic extraction (via OpenAI), and data persistence.

👉 **[View Server Setup Guide](./server/README.md)**

### 2. [App (Mobile Client)](./app/README.md)
The mobile client is an Expo React Native application. It features Supabase Auth for seamless authentication (Google OAuth) and connects your mobile device directly to your personalized daily assistant.

👉 **[View App Setup Guide](./app/README.md)**

### 3. EAS Android Test Builds

The project is configured to create a standalone Android APK through Expo Application Services (EAS). The Preview build uses the FastAPI server already hosted at `https://dailypilotlab-2.onrender.com`, so the installed APK does not depend on a local development server or Expo Go.

From the repository root, create a new downloadable APK in one command:

```bash
cd app && npx eas-cli@latest build --platform android --profile preview --non-interactive
```

EAS prints the build page and APK download link after the cloud build completes. Open that link on an Android phone to install the test build. This is private development distribution; it does not publish the app to Google Play.

👉 **[View the complete hosted-server and EAS setup guide](./eas_setup_doc.md)**

---

## 🤝 Contributing

We welcome contributions! If you're looking to help out or want to see exactly how to structure your branches, commit messages, and what we look for in Pull Requests, please read our contributing guidelines.

👉 **[View Contribution Guidelines](./CONTRIBUTING.md)**
