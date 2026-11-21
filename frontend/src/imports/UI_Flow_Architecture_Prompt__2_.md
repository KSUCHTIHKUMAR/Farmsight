# Project Prompt — UI Flow & Architecture
### FarmSight — AI-powered crop disease diagnosis and produce quality grading

Use this as a copy-paste brief for a design tool (Figma AI, v0, Bolt), or as a reference for building the UI yourself.

**Status:** Landing, Task Picker, and Input Method (both tasks) are designed and built. Loading, Results, and Error states are still needed.

---

## Project One-Liner
A mobile-friendly web app that helps farmers diagnose leaf disease in tomato and potato crops, and helps vendors grade apples, bananas, and oranges as fresh or rotten — using photo upload or live camera capture, with an AI explanation (Grad-CAM heatmap) for every result.

## Design Direction
- **Style:** Clean, modern, agri-tech — not clinical/sterile, not overly playful. Think "trustworthy field tool," similar to modern fintech or health apps: generous whitespace, rounded cards, soft shadows, one confident accent color (green fits the domain naturally without being a cliché farm theme).
- **Typography:** A clean sans-serif (Inter, Manrope, or similar), strong hierarchy between headline/result text and supporting body text.
- **Tone:** Reassuring and clear, not alarming — even when the result is "diseased" or "rotten," the UI should feel helpful, not punitive.
- **Mobile-first:** primary usage is a farmer/vendor on a phone in the field or at a stall, not a desktop user.

## Desktop Layout (Task Switcher)

The mobile flow above (Landing → Task Picker → back-and-forth) is right for a phone, but wastes a desktop's screen width and adds unnecessary navigation. For desktop, use a **persistent sidebar + working panel** layout instead:

```
┌─────────────┬───────────────────────────────┐
│  Sidebar    │  Working panel                 │
│  (always    │  (updates based on sidebar     │
│  visible)   │   selection — no page nav)     │
│             │                                │
│ FarmSight   │  Input / Loading / Results /   │
│ ○ Diagnose  │  Error state for whichever     │
│   Leaf      │  task is selected              │
│ ○ Grade     │                                │
│   Produce   │                                │
└─────────────┴───────────────────────────────┘
```

**Behavior:**
- Sidebar shows both tasks at all times, each with a short subtitle (crop/fruit types covered) — clicking instantly swaps the working panel's content, no route change or back button needed
- The currently active task is visually highlighted (accent background)
- The working panel itself still moves through the same states as mobile — Input → Loading → Results/Error — just rendered in place rather than as a separate full-screen step
- Same components (upload card, camera button, results card, Grad-CAM overlay, treatment card) are reused between mobile and desktop — only the shell layout differs
- Breakpoint: below ~768px width, collapse to the mobile flow (Task Picker screen instead of sidebar); above that, use the sidebar layout

This keeps one shared component library for both layouts — you're not building two separate apps, just two shells around the same working panel content.

## Full UI Flow

```
Landing
  → Task Picker (Diagnose Leaf | Grade Produce)
      → Input Method (Upload Photo | Take Photo)
          → Loading / Processing state
              → Results screen
                  ├─ Prediction label + confidence score
                  ├─ Grad-CAM heatmap overlay on the image
                  ├─ (Leaf task only) Suggested treatment card
                  └─ "Try another" → back to Input Method
              → Error state (bad file / low confidence) → back to Input Method
```

## Screens to Design

**1. Landing** ✅ Done
One-line app description, two clear entry points (or a single "Get Started" leading into the Task Picker). Should communicate what the app does in under 5 seconds.

**2. Task Picker** ✅ Done
Two large, tappable cards: "Diagnose Leaf" and "Grade Produce." Icon + one-line description each. This is the fork point that determines which model runs later.
*Fix needed:* the "AI heatmap explanations" chip is currently using a music-note icon — swap for a scan/target/eye icon to match the Grad-CAM concept.

**3. Input Method** ✅ Done
Two options: "Upload Photo" (file picker) and "Take Photo" (camera capture). Show a brief instruction relevant to the chosen task (e.g., "Photograph the affected leaf area in good light" vs. "Photograph the whole fruit").

**4. Loading/Processing** — Not yet designed
Simple, short-duration state — spinner or subtle animation, no more than a couple seconds expected. Avoid making this feel like a long wait.

**5. Results** — Not yet designed
- Predicted class + confidence percentage, prominent
- Grad-CAM overlay on the submitted image (heatmap highlighting the region the model focused on)
- For leaf disease results: a "Suggested Treatment" card showing the general treatment category (fungicide/pesticide/fertilizer) with a caveat line: *"General guidance only — consult your local agricultural extension office."*
- "Try Another" action to loop back

**6. Error State** — Not yet designed
Friendly, non-technical message ("Couldn't read that image — try another photo"), single "Retry" action back to Input Method. Never a raw error code or crash.

## Architecture (Frontend ↔ Model)

```
[Browser / Mobile Web UI]
        │  (image upload or camera capture)
        ▼
[Streamlit app hosted on Hugging Face Spaces]
        │
        ├─ Task = Leaf  → [Leaf Disease Model: MobileNetV2, fine-tuned on
        │                   PlantVillage Tomato+Potato subset]
        │                   → prediction + Grad-CAM + treatment lookup table
        │
        └─ Task = Produce → [Ripeness Model: MobileNetV2, fine-tuned on
                              Kaggle fresh/rotten apple/banana/orange]
                              → prediction + Grad-CAM
        │
        ▼
[Results rendered back in the same UI component, parameterized by task type]
```

**Key architecture notes:**
- One shared results-screen component, parameterized by task (label text and treatment card only appear for the leaf task)
- Two independently trained models, loaded conditionally based on task selection — not a single multi-task model
- Treatment suggestions are a static lookup table (disease class → treatment category), not model output
- No backend database needed — this is a stateless, single-request-response app; no user accounts or history required for v1

## Tech Constraints for the Design/Build
- Framework: Streamlit (fast to build, sufficient for this scope)
- Hosting: Hugging Face Spaces (free GPU tier)
- Must work on both mobile browsers and desktop
- Camera capture uses `st.camera_input()` (single-shot capture, not continuous video)
- No login/auth required
