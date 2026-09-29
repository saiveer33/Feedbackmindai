# FeedbackMind — 3-Minute Demo Script (video + live judging)

Rehearse twice. Record at 1080p (OBS / Loom). Bump VS Code + browser font size.
Close notifications. If anything fails LIVE: switch to a pre-recorded clip. Never debug on stage.

## Scene 0 — Intro (0:00–0:20)
SHOW: app home, title.
SAY: "Hi, I'm Sujith. FeedbackMind is an AI product analyst that remembers every
piece of customer feedback across channels and time — built on Hindsight memory
and Groq. Let me show you why memory changes everything."

## Scene 1 — The problem: no memory (0:20–0:50)
CLICK: ⚖️ Before/After tab → Run comparison (default question:
"Has dashboard performance improved after the v2.4 release?")
SHOW: LEFT side (plain LLM): vague guess, admits it has no data.
SAY: "A stateless LLM — even a smart one — can only guess. It has never seen our
users. This is every chatbot you've used."

## Scene 2 — The memory answer (0:50–1:20)
SHOW: RIGHT side: cites dates, channels, the v2.4 release; open Evidence expander.
SAY: "Same model. One difference: Hindsight memory. It recalls 8 weeks of feedback
AND the release log, and cites its sources. Memory didn't improve the model —
it gave the model a history."

## Scene 3 — Dashboard from memory (1:20–1:40)
CLICK: 📊 Dashboard. Point at 🔴 search alert + theme bars + sentiment dip.
SAY: "These numbers are computed live from memory metadata — there is no database
in this project. The memory IS the database."

## Scene 4 — The learning loop (1:40–2:10)  ← the judge-winner
CLICK: 📰 Digests. Open Week 2 (generic) vs Week 6 (focused, 2 recommendations).
SAY: "Week 2's digest listed everything, including noise. Then the PM typed one
correction — retained as an experience fact. Week 6 obeys it. No fine-tuning,
no retraining. Just memory."
LIVE BONUS: type a new correction → Generate week 7 → it obeys on screen.

## Scene 5 — Inside the brain (2:10–2:30)
CLICK: 🧠 Memory Explorer → filters: Releases, PM corrections. Show ~424 memories.
SAY: "This is what agent memory looks like from inside: dated facts, releases,
the agent's own digests, and its boss's corrections — all retrievable."

## Scene 6 — Cross-channel recall (2:30–2:50)
CLICK: 💬 Ask → "Which customer complained about checkout across multiple channels?"
SHOW: Rohit Sharma (user_101): app review → ticket → tweet → ticket.
SAY: "One angry customer, four channels, eight weeks. Humans miss this. Memory doesn't."

## Scene 7 — Close (2:50–3:00)
SAY: "Interaction 1 was generic. Interaction 20 feels like a colleague who's been
here for months. That's what Hindsight memory buys you. Thank you."

## After recording
- Thumbnail via Nano Banana (Content Guide Prompt 6), post public on YouTube
- Article + LinkedIn post per team member (Content Guide prompts) — NO word "hackathon"!