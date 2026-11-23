# SYNTRIQ — Creative Experience & Micro-Interaction Guide (CREATIVITY.md)

**Product**: SYNTRIQ — Think Smarter. Study Better.  
**Concept**: The Academic Kitchen & Algorithmic Study Engine  
**Status**: Implemented & Approved  

---

## 1. Brand Personality & Creative Narrative

SYNTRIQ transforms the stress of academic overwhelm into the satisfaction of a master chef executing a culinary recipe. Tasks are "ingredients" to be "cooked," priorities are calculated with algorithmic rigor, and focus sessions ("Focus Kitchen") provide clear milestones.

* **Tone**: Empowering, energetic, disciplined, yet playfully warm.
* **Signature Vocabulary**: "Cook Task", "Focus Kitchen", "Priority Recipe", "Study Milestones", "Workload Capacity".

---

## 2. Implemented Creative Micro-Interactions

### 2.1 Live Dynamic Priority Preview
* **Location**: Add Task ([templates/add_task.html](file:///E:/Aasu/templates/add_task.html)) and Edit Task ([templates/edit_task.html](file:///E:/Aasu/templates/edit_task.html)).
* **Experience**: As the student enters deadlines, difficulty, importance, or hours, the preview card instantly calculates days remaining, workload score, and final priority score with zero latency.
* **Benefit**: Eliminates guesswork; teaches students how deadlines impact urgency.

### 2.2 Dynamic Priority Glow on Top Task
* **Location**: Study Plan ([templates/study_plan.html](file:///E:/Aasu/templates/study_plan.html)).
* **Experience**: The `#1` ranked study task card displays an ambient breathing aura glow (`@keyframes syntriqPriorityPulse`), signaling to the user exactly where their focus belongs.

### 2.3 Acoustic Web Audio Synthesizer Suite (100% Offline)
* **Location**: Focus Kitchen Modal ([templates/base.html](file:///E:/Aasu/templates/base.html)) & Global App Interactions.
* **Technology**: Synthesized via HTML5 `AudioContext` without downloading external audio files (works completely offline).
* **Soundscapes & Tones**:
  - `playPopSound()`: Tactile bubble pop on button clicks and chip selection.
  - `playSuccessChime()`: Ascending 4-note celebration arpeggio (C5 &rarr; E5 &rarr; G5 &rarr; C6) upon task completion.
  - `playSubtaskSound()`: Crisp triangle chime when ticking off a study milestone.
  - `playStartSound()`: Gentle 3-note chime when launching a Pomodoro deep work session.
  - `playZenBell()`: Resonant Tibetan singing bowl bell on focus session finish.
  - Ambient Focus Generators: Pink noise filter (Rain), Brown noise filter (Warm Café Waves), and Pure White Noise.
* **User Control**: Opt-in toggle in the header navigation (🔊 / 🔇), persisted in `localStorage`.

### 2.4 Physics-Based Canvas Confetti Celebration
* **Location**: Task completion, subtask milestone completion, and focus session completion.
* **Experience**: 90 colorful confetti rectangles launch from the center of the viewport with realistic gravity, rotation speed, and fading opacity. Zero external library dependencies.

### 2.5 What-If Ripple Simulator
* **Location**: Study Plan modal ([templates/study_plan.html](file:///E:/Aasu/templates/study_plan.html)).
* **Experience**: Dual interactive range sliders allow students to test hypothetical schedule adjustments (e.g., postponing a deadline by 3 days, adding 2 hours) to simulate how priority scores shift before making real edits.

### 2.6 Subtask Decomposition Checklist
* **Location**: Individual priority cards.
* **Experience**: Allows breaking large assignments into bite-sized milestones. Ticking a milestone plays a sound, updates the fraction badge (`(2/4)`), and provides instant momentum.

---

## 3. Creative Feature Evaluation Matrix

| Creative Feature | User Benefit | Technical Complexity | Performance Impact | Status |
|---|---|---|---|---|
| **Live Priority Preview** | Transparent algorithm feedback | Low | $\approx 0\text{ms}$ (instant event listener) | **Active** |
| **Top Priority Pulse** | Unambiguous focus indicator | Low | GPU compositor only | **Active** |
| **Offline Audio Synthesizer** | Auditory tactile feedback | Medium | AudioContext native thread | **Active** (Muteable) |
| **Canvas Confetti** | Dopamine completion loop | Medium | 60 FPS requestAnimationFrame | **Active** |
| **What-If Simulator** | Strategic time management | Medium | Fast JSON micro-API | **Active** |
| **Subtask Decomposer** | Lowers task resistance | Medium | In-memory DOM + SQLite | **Active** |
