# Project Brief — DailyPilotLab

## The Vibe
An **intelligent idea capture & organization system** — a "second brain" REST API that turns raw, messy thoughts into structured, searchable knowledge and ultimately derives a behavioral profile of the user.

## What Are We Building?
A FastAPI backend that:
1. **Ingests** raw thoughts via REST endpoints
2. **Classifies** them (idea / personal info / secret / gibberish) using LLM
3. **Refines** raw ideas into clean, atomic, third-person statements
4. **Organizes** ideas into topics via a hybrid vector-similarity + LLM pipeline
5. **Enables semantic search** across the entire knowledge base
6. **Extracts user traits** (interests, goals, skills, etc.) from high-signal topics

## Why?
To build a system that doesn't just store ideas — it **understands** them. The end goal is a personal AI that knows what you care about, what you're working on, and can surface relevant past thoughts when you need them.

## Target Users
- Single user (personal tool, no multi-tenancy yet)
- Developers / thinkers who want to capture fleeting thoughts and let AI organize them

## Core Value Proposition
> "Throw thoughts at it. It does the rest."

No manual tagging, no folder hierarchies, no organization burden. The system handles classification, refinement, topic clustering, and trait extraction autonomously.
