# Contributing to DailyPilot

First off, thank you for taking the time to contribute to DailyPilot! 🎉 

This document outlines the guidelines for contributing to this project. By participating in this project, you agree to abide by these guidelines.

## 🌿 Branching Guidelines

When creating a new branch, please use one of the following prefixes to clearly indicate the purpose of your work:

- **`feat/`** — New features or significant additions (`feat/add-voice-transcription`)
- **`fix/`** — Bug fixes (`fix/oauth-redirect-loop`)
- **`refactor/`** — Code changes that neither fix a bug nor add a feature (`refactor/topic-service-cleanup`)
- **`chore/`** — Routine tasks, dependency updates, or tool configurations (`chore/update-expo-sdk`)
- **`docs/`** — Documentation changes only (`docs/guidelines` or `docs/api-readme-update`)

Please keep branch names lowercase and use hyphens `-` to separate words.

## 📝 Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for our commit messages. This leads to more readable messages that are easy to follow when looking through the project history.

**Format:**
```
<type>(<optional scope>): <description>
```

**Examples:**
- `feat(app): add dark mode toggle to settings schema`
- `fix(server): resolve duplicate topic assignment bug`
- `docs: update setup documentation for supabase cli`
- `chore(deps): bump react-native version`

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries

## ✔️ Pull Request Checklist

Before submitting a Pull Request, please make sure the following checks are complete. You will be asked to check these off in your PR description:

- [ ] I have self-reviewed my code and verified the app runs locally.
- [ ] I have commented my code and updated docs (if applicable).
- [ ] My branch follows the `prefix/branch-name` naming convention.
- [ ] My commit messages follow the Conventional Commits format.
- [ ] I have checked the chat response.
- [ ] I have checked the audio response.
- [ ] I have added checklist for any major feature.

---

Once again, thank you for your contributions!
