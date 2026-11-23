/**
 * Smart Study Planner - Client-side Interactive Application Script
 * Features:
 * - Live Priority Calculation Preview
 * - Focus Kitchen Pomodoro Timer with Circular SVG Progress
 * - Web Audio API Soundscapes & Chimes (100% Offline / No Assets Needed)
 * - Canvas Confetti Physics Engine
 * - Subtasks Real-Time Checklist Manager
 * - What-If Priority Simulator
 * - Smart Due Date Quick Chips
 * - Pro-Student Keyboard Shortcuts
 */

document.addEventListener("DOMContentLoaded", () => {
    initPriorityPreview();
    initAlertAutoDismiss();
    initKeyboardShortcuts();
    initConfettiCanvas();
    initSoundSystem();
    initMobileNav();
    animateNumberCounters();
});

/* ==========================================================================
   0. Mobile Navigation Drawer Controller
   ========================================================================== */

function initMobileNav() {
    const overlay = document.getElementById("mobileDrawerOverlay");
    const drawer = document.getElementById("mobileNavDrawer");
    if (!overlay || !drawer) return;

    window.addEventListener("resize", () => {
        if (window.innerWidth > 768 && drawer.classList.contains("drawer-open")) {
            closeMobileNav();
        }
    });
}

function toggleMobileNav() {
    const drawer = document.getElementById("mobileNavDrawer");
    if (!drawer) return;
    if (drawer.classList.contains("drawer-open")) {
        closeMobileNav();
    } else {
        openMobileNav();
    }
}

function openMobileNav() {
    const drawer = document.getElementById("mobileNavDrawer");
    const overlay = document.getElementById("mobileDrawerOverlay");
    const hamburger = document.getElementById("mobileMenuBtn");
    if (!drawer || !overlay) return;

    drawer.classList.add("drawer-open");
    overlay.classList.add("overlay-visible");
    if (hamburger) hamburger.classList.add("btn-active");
    document.body.classList.add("nav-locked");
    playPopSound();
}

function closeMobileNav() {
    const drawer = document.getElementById("mobileNavDrawer");
    const overlay = document.getElementById("mobileDrawerOverlay");
    const hamburger = document.getElementById("mobileMenuBtn");
    if (!drawer || !overlay) return;

    drawer.classList.remove("drawer-open");
    overlay.classList.remove("overlay-visible");
    if (hamburger) hamburger.classList.remove("btn-active");
    document.body.classList.remove("nav-locked");
}

/**
 * Animated Number Counters for Statistics & Metrics
 */
function animateNumberCounters() {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const counters = document.querySelectorAll("[data-counter]");
    if (!counters.length) return;

    counters.forEach(counter => {
        const target = parseFloat(counter.getAttribute("data-counter"));
        if (isNaN(target)) return;

        if (prefersReducedMotion || target === 0) {
            counter.textContent = target;
            return;
        }

        const duration = 650; // ms
        const startTime = performance.now();

        function updateCount(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out cubic curve
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const currentVal = Math.round(easeOut * target);
            counter.textContent = currentVal;

            if (progress < 1) {
                requestAnimationFrame(updateCount);
            } else {
                counter.textContent = target;
            }
        }

        requestAnimationFrame(updateCount);
    });
}

/* ==========================================================================
   1. Live Dynamic Priority Preview (Add & Edit Task Pages)
   ========================================================================== */

function initPriorityPreview() {
    const form = document.getElementById("taskForm");
    if (!form) return;

    const deadlineInput = document.getElementById("deadline");
    const difficultyInput = document.getElementById("difficulty");
    const importanceInput = document.getElementById("importance");
    const hoursInput = document.getElementById("estimated_hours");

    const scoreDisplay = document.getElementById("previewScore");
    const categoryDisplay = document.getElementById("previewCategory");
    const urgencyDisplay = document.getElementById("previewUrgency");
    const importanceDisplay = document.getElementById("previewImportance");
    const difficultyDisplay = document.getElementById("previewDifficulty");
    const workloadDisplay = document.getElementById("previewWorkload");

    if (!scoreDisplay) return;

    function updatePreview() {
        const deadlineVal = deadlineInput.value;
        const diffVal = parseInt(difficultyInput.value, 10);
        const impVal = parseInt(importanceInput.value, 10);
        const hoursVal = parseFloat(hoursInput.value);

        if (!deadlineVal || isNaN(diffVal) || isNaN(impVal) || isNaN(hoursVal) || hoursVal <= 0) {
            scoreDisplay.textContent = "--";
            categoryDisplay.textContent = "Fill in details to calculate";
            categoryDisplay.className = "score-category text-muted";
            if (urgencyDisplay) urgencyDisplay.textContent = "--";
            if (importanceDisplay) importanceDisplay.textContent = isNaN(impVal) ? "--" : `${impVal}/5`;
            if (difficultyDisplay) difficultyDisplay.textContent = isNaN(diffVal) ? "--" : `${diffVal}/5`;
            if (workloadDisplay) workloadDisplay.textContent = "--";
            return;
        }

        // Calculate days remaining
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const [year, month, day] = deadlineVal.split("-").map(Number);
        const targetDate = new Date(year, month - 1, day);
        targetDate.setHours(0, 0, 0, 0);

        const diffTime = targetDate - today;
        const daysRemaining = Math.round(diffTime / (1000 * 60 * 60 * 24));

        // Urgency algorithm matching pseudocode
        let urgency = 1;
        if (daysRemaining <= 1) urgency = 5;
        else if (daysRemaining <= 3) urgency = 4;
        else if (daysRemaining <= 7) urgency = 3;
        else if (daysRemaining <= 14) urgency = 2;
        else urgency = 1;

        // Workload algorithm matching pseudocode
        let workload = 1;
        if (hoursVal >= 6.0) workload = 5;
        else if (hoursVal >= 4.0) workload = 4;
        else if (hoursVal >= 2.0) workload = 3;
        else if (hoursVal >= 1.0) workload = 2;
        else workload = 1;

        // Composite priority score formula
        const priorityScore = (0.4 * urgency) + (0.3 * impVal) + (0.2 * diffVal) + (0.1 * workload);
        const roundedScore = priorityScore.toFixed(2);

        scoreDisplay.textContent = roundedScore;

        if (urgencyDisplay) {
            const overdueText = daysRemaining < 0 ? ` (${Math.abs(daysRemaining)}d overdue)` : ` (${daysRemaining}d left)`;
            urgencyDisplay.textContent = `${urgency}/5${overdueText}`;
        }
        if (importanceDisplay) importanceDisplay.textContent = `${impVal}/5`;
        if (difficultyDisplay) difficultyDisplay.textContent = `${diffVal}/5`;
        if (workloadDisplay) workloadDisplay.textContent = `${workload}/5 (${hoursVal}h)`;

        // Category style
        if (priorityScore >= 4.0) {
            categoryDisplay.textContent = "Urgent / High Priority";
            categoryDisplay.className = "score-category text-danger";
            scoreDisplay.style.color = "var(--primary)";
        } else if (priorityScore >= 3.0) {
            categoryDisplay.textContent = "Moderate Priority";
            categoryDisplay.className = "score-category text-warning";
            scoreDisplay.style.color = "var(--primary-hover)";
        } else {
            categoryDisplay.textContent = "Low Priority";
            categoryDisplay.className = "score-category text-primary";
            scoreDisplay.style.color = "var(--text-secondary)";
        }
    }

    // Attach listeners
    [deadlineInput, difficultyInput, importanceInput, hoursInput].forEach(elem => {
        if (elem) {
            elem.addEventListener("input", updatePreview);
            elem.addEventListener("change", updatePreview);
        }
    });

    // Run initial update on page load
    updatePreview();
}

/**
 * Smart Date Chips: sets date input relative to today
 */
function setSmartDate(daysToAdd) {
    const deadlineInput = document.getElementById("deadline");
    if (!deadlineInput) return;

    const target = new Date();
    target.setDate(target.getDate() + daysToAdd);
    const yyyy = target.getFullYear();
    const mm = String(target.getMonth() + 1).padStart(2, "0");
    const dd = String(target.getDate()).padStart(2, "0");

    deadlineInput.value = `${yyyy}-${mm}-${dd}`;
    deadlineInput.dispatchEvent(new Event("change"));
}

/* ==========================================================================
   2. Focus Kitchen Pomodoro Timer (Drift-Free Timestamp Engine)
   ========================================================================== */

let pomoInterval = null;
let pomoTimeLeft = 25 * 60;
let pomoTotalTime = 25 * 60;
let pomoIsRunning = false;
let pomoCurrentTaskId = null;
let pomoEndTime = null;

const CIRCLE_CIRCUMFERENCE = 2 * Math.PI * 100; // r = 100

function openPomodoroModal() {
    const modal = document.getElementById("pomodoroModal");
    if (!modal) return;
    modal.style.display = "flex";
    updatePomoDisplay();
}

function closePomodoroModal() {
    const modal = document.getElementById("pomodoroModal");
    if (!modal) return;
    modal.style.display = "none";
    stopAmbientSound();
}

function openPomodoroForTask(taskTitle, taskSubject, taskId) {
    pomoCurrentTaskId = taskId;
    const titleElem = document.getElementById("pomoTaskTitle");
    const subElem = document.getElementById("pomoTaskSubject");
    if (titleElem) titleElem.textContent = taskTitle;
    if (subElem) subElem.textContent = `${taskSubject} • Focus Session`;
    openPomodoroModal();
}

function setPomoDuration(minutes, buttonElem) {
    if (pomoIsRunning) togglePomodoro();
    pomoTotalTime = minutes * 60;
    pomoTimeLeft = pomoTotalTime;
    pomoEndTime = null;
    
    document.querySelectorAll(".pomo-mode-btn").forEach(btn => btn.classList.remove("active"));
    if (buttonElem) buttonElem.classList.add("active");
    
    const statusText = document.getElementById("pomoStatusText");
    if (statusText) statusText.textContent = `${minutes}m Session Selected`;

    updatePomoDisplay();
}

function togglePomodoro() {
    const startBtn = document.getElementById("pomoStartBtn");
    const statusText = document.getElementById("pomoStatusText");

    if (pomoIsRunning) {
        // Pause session: calculate exact time remaining and freeze
        if (pomoInterval) clearInterval(pomoInterval);
        pomoInterval = null;
        pomoIsRunning = false;
        if (pomoEndTime) {
            pomoTimeLeft = Math.max(0, Math.round((pomoEndTime - Date.now()) / 1000));
            pomoEndTime = null;
        }
        if (startBtn) startBtn.innerHTML = "▶ Resume Session";
        if (statusText) statusText.textContent = "Paused";
        updatePomoDisplay();
    } else {
        // Start or resume session: anchor target completion timestamp
        pomoIsRunning = true;
        pomoEndTime = Date.now() + pomoTimeLeft * 1000;
        playStartSound();
        if (startBtn) startBtn.innerHTML = "⏸ Pause Session";
        if (statusText) statusText.textContent = "Focusing...";

        // Initial tick immediate sync
        updatePomoDisplay();

        pomoInterval = setInterval(() => {
            if (!pomoEndTime) return;
            const remaining = Math.max(0, Math.round((pomoEndTime - Date.now()) / 1000));
            pomoTimeLeft = remaining;
            updatePomoDisplay();
            if (tickingEnabled) {
                playTickSound();
            }

            if (pomoTimeLeft <= 0) {
                clearInterval(pomoInterval);
                pomoInterval = null;
                pomoIsRunning = false;
                pomoEndTime = null;
                onPomodoroFinished();
            }
        }, 1000);
    }
}

function resetPomodoro() {
    if (pomoInterval) clearInterval(pomoInterval);
    pomoInterval = null;
    pomoIsRunning = false;
    pomoEndTime = null;
    pomoTimeLeft = pomoTotalTime;
    
    const startBtn = document.getElementById("pomoStartBtn");
    const statusText = document.getElementById("pomoStatusText");
    if (startBtn) startBtn.innerHTML = "▶ Start Session";
    if (statusText) statusText.textContent = "Ready to Start";
    
    updatePomoDisplay();
}

// Background Tab Sync using Page Visibility API (prevents browser timer throttling drift)
document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && pomoIsRunning && pomoEndTime) {
        const remaining = Math.max(0, Math.round((pomoEndTime - Date.now()) / 1000));
        pomoTimeLeft = remaining;
        updatePomoDisplay();
        if (pomoTimeLeft <= 0) {
            if (pomoInterval) clearInterval(pomoInterval);
            pomoInterval = null;
            pomoIsRunning = false;
            pomoEndTime = null;
            onPomodoroFinished();
        }
    }
});

function updatePomoDisplay() {
    const timerText = document.getElementById("pomoTimerText");
    const progressCircle = document.getElementById("timerProgress");

    const minutes = Math.floor(pomoTimeLeft / 60);
    const seconds = pomoTimeLeft % 60;
    const formatted = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    if (timerText) timerText.textContent = formatted;

    if (progressCircle) {
        const offset = CIRCLE_CIRCUMFERENCE - (pomoTimeLeft / pomoTotalTime) * CIRCLE_CIRCUMFERENCE;
        progressCircle.style.strokeDashoffset = offset;
    }
}

function onPomodoroFinished() {
    playZenBell();
    triggerConfetti();

    const statusText = document.getElementById("pomoStatusText");
    const startBtn = document.getElementById("pomoStartBtn");
    if (statusText) statusText.textContent = "🎉 Great Focus! Session Completed";
    if (startBtn) startBtn.innerHTML = "↺ Start Another";

    // Log focus session to backend
    const minutesSpent = Math.round(pomoTotalTime / 60);
    fetch("/api/log-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: pomoCurrentTaskId, minutes: minutesSpent })
    }).catch(err => console.warn("Session logging note:", err));
}

/* ==========================================================================
   3. Web Audio API Acoustic Sound Suite (100% Offline / Synthesized)
   ========================================================================== */

let audioCtx = null;
let ambientSource = null;
let ambientGain = null;
let soundEffectsEnabled = localStorage.getItem("planner_sound_fx") !== "false";
let tickingEnabled = false;

function initSoundSystem() {
    updateSoundButtonUI();

    // Attach tactile pop sound to buttons and interactive controls
    document.addEventListener("click", (e) => {
        const target = e.target.closest("button, .btn, .date-chip, .tab-item, .heatmap-day-chip");
        if (target && !target.classList.contains("ambient-chip") && !target.classList.contains("sound-toggle-btn")) {
            playPopSound();
        }
    });
}

function updateSoundButtonUI() {
    const btns = [document.getElementById("soundToggleBtn"), document.getElementById("mobileSoundToggleBtn")];
    btns.forEach(btn => {
        if (btn) {
            btn.innerHTML = soundEffectsEnabled 
                ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>'
                : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>';
            btn.title = soundEffectsEnabled ? "Sound Effects: ON (Click to Mute)" : "Sound Effects: MUTED (Click to Enable)";
            btn.setAttribute("aria-label", soundEffectsEnabled ? "Mute sound effects" : "Enable sound effects");
            btn.classList.toggle("sound-muted", !soundEffectsEnabled);
        }
    });
}

function toggleSoundMute() {
    soundEffectsEnabled = !soundEffectsEnabled;
    localStorage.setItem("planner_sound_fx", soundEffectsEnabled ? "true" : "false");
    updateSoundButtonUI();
    if (soundEffectsEnabled) {
        playPopSound();
    }
}

function toggleClockTick(chipBtn) {
    tickingEnabled = !tickingEnabled;
    if (chipBtn) {
        chipBtn.textContent = tickingEnabled ? "Ticking: ON" : "Ticking: OFF";
        chipBtn.classList.toggle("active", tickingEnabled);
    }
    if (tickingEnabled) {
        playTickSound();
    }
}

function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === "suspended") {
        audioCtx.resume();
    }
    return audioCtx;
}

/**
 * Triumphant 4-note celebration arpeggio (C5 -> E5 -> G5 -> C6)
 */
function playSuccessChime() {
    if (!soundEffectsEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        const notes = [523.25, 659.25, 783.99, 1046.50];
        notes.forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);
            gain.gain.setValueAtTime(0.18, now + idx * 0.08);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.65);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.65);
        });
    } catch (e) {
        console.warn("Chime note:", e);
    }
}

/**
 * Tactile bubble/pop sound for interactive UI feedback
 */
function playPopSound() {
    if (!soundEffectsEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(460, now);
        osc.frequency.exponentialRampToValueAtTime(170, now + 0.035);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.035);
    } catch (e) {}
}

/**
 * Satisfying subtask completion check sound
 */
function playSubtaskSound() {
    if (!soundEffectsEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(1320, now + 0.09);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.1);
    } catch (e) {}
}

/**
 * Ascending focus session launch chime
 */
function playStartSound() {
    if (!soundEffectsEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        [330, 440, 660].forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.09);
            gain.gain.setValueAtTime(0.14, now + idx * 0.09);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.09 + 0.28);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now + idx * 0.09);
            osc.stop(now + idx * 0.09 + 0.28);
        });
    } catch (e) {}
}

/**
 * Resonant Tibetan singing bowl bell for completed focus session
 */
function playZenBell() {
    if (!soundEffectsEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        [432, 864, 1296].forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now);
            const vol = 0.22 / (idx + 1);
            gain.gain.setValueAtTime(vol, now);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 2.8);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now);
            osc.stop(now + 2.8);
        });
    } catch (e) {}
}

/**
 * Soft swoosh tone on task deletion
 */
function playTrashSound() {
    if (!soundEffectsEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(260, now);
        osc.frequency.exponentialRampToValueAtTime(90, now + 0.12);
        gain.gain.setValueAtTime(0.14, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.12);
    } catch (e) {}
}

/**
 * Clock tick pulse for Pomodoro timer
 */
function playTickSound() {
    if (!soundEffectsEnabled || !tickingEnabled) return;
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "square";
        osc.frequency.setValueAtTime(1100, now);
        gain.gain.setValueAtTime(0.025, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.012);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.012);
    } catch (e) {}
}

/**
 * Ambient Synthesizers (Rain, White Noise, Café Waves)
 */
function setAmbientSound(type, chipBtn) {
    document.querySelectorAll(".ambient-chip:not(#tickSoundChip)").forEach(c => c.classList.remove("active"));
    if (chipBtn) chipBtn.classList.add("active");

    stopAmbientSound();
    if (type === "none") return;

    try {
        const ctx = getAudioContext();
        const bufferSize = 2 * ctx.sampleRate;
        const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const output = noiseBuffer.getChannelData(0);

        let b0 = 0, b1 = 0;
        for (let i = 0; i < bufferSize; i++) {
            const white = Math.random() * 2 - 1;
            if (type === "rain") {
                // Pink noise filter (rain drops)
                b0 = 0.99886 * b0 + white * 0.0555;
                b1 = 0.99332 * b1 + white * 0.075;
                output[i] = (b0 + b1) * 0.15;
            } else if (type === "cafe") {
                // Brown noise filter (warm waves)
                b0 = (b0 + (0.02 * white)) / 1.02;
                output[i] = b0 * 0.38;
            } else {
                // White noise
                output[i] = white * 0.04;
            }
        }

        ambientSource = ctx.createBufferSource();
        ambientSource.buffer = noiseBuffer;
        ambientSource.loop = true;

        ambientGain = ctx.createGain();
        ambientGain.gain.setValueAtTime(0.14, ctx.currentTime);

        ambientSource.connect(ambientGain);
        ambientGain.connect(ctx.destination);
        ambientSource.start();
    } catch (e) {
        console.warn("Ambient generator note:", e);
    }
}

function stopAmbientSound() {
    if (ambientSource) {
        try { ambientSource.stop(); } catch (e) {}
        ambientSource = null;
    }
}

/* ==========================================================================
   4. Canvas Confetti Particle Celebration Engine
   ========================================================================== */

let confettiParticles = [];
let confettiAnimId = null;

function initConfettiCanvas() {
    const canvas = document.getElementById("confettiCanvas");
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    window.addEventListener("resize", () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

function triggerConfetti() {
    playSuccessChime();
    const canvas = document.getElementById("confettiCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const colors = ["#FF6B00", "#FFA94D", "#10B981", "#3B82F6", "#F59E0B", "#111111"];
    confettiParticles = [];

    for (let i = 0; i < 90; i++) {
        confettiParticles.push({
            x: canvas.width / 2 + (Math.random() * 200 - 100),
            y: canvas.height * 0.6,
            vx: (Math.random() - 0.5) * 16,
            vy: (Math.random() * -14) - 7,
            size: Math.random() * 9 + 4,
            color: colors[Math.floor(Math.random() * colors.length)],
            rotation: Math.random() * 360,
            rotSpeed: (Math.random() - 0.5) * 10,
            opacity: 1
        });
    }

    if (confettiAnimId) cancelAnimationFrame(confettiAnimId);

    function renderConfetti() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        let activeCount = 0;

        confettiParticles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.35; // Gravity
            p.rotation += p.rotSpeed;
            p.opacity -= 0.009;

            if (p.opacity > 0) {
                activeCount++;
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate((p.rotation * Math.PI) / 180);
                ctx.fillStyle = p.color;
                ctx.globalAlpha = Math.max(0, p.opacity);
                ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.7);
                ctx.restore();
            }
        });

        if (activeCount > 0) {
            confettiAnimId = requestAnimationFrame(renderConfetti);
        } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }

    renderConfetti();
}

/* ==========================================================================
   5. Subtasks Real-Time Checklist Manager
   ========================================================================== */

function toggleSubtasksView(taskId) {
    const body = document.getElementById(`subtasksBody-${taskId}`);
    const arrow = document.getElementById(`subtaskArrow-${taskId}`);
    if (!body) return;

    if (body.style.display === "none" || !body.style.display) {
        body.style.display = "block";
        if (arrow) arrow.textContent = "▲";
    } else {
        body.style.display = "none";
        if (arrow) arrow.textContent = "▼";
    }
}

function createSubtask(taskId) {
    const input = document.getElementById(`newSubtaskInput-${taskId}`);
    if (!input || !input.value.trim()) return;

    const title = input.value.trim();
    fetch(`/api/tasks/${taskId}/subtasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            input.value = "";
            const list = document.getElementById(`subtasksList-${taskId}`);
            if (list) {
                const li = document.createElement("li");
                li.className = "subtask-item";
                li.id = `subtaskItem-${data.subtask_id}`;
                li.innerHTML = `
                    <label class="subtask-checkbox-label">
                        <input type="checkbox" onchange="toggleSubtaskStatus(${data.subtask_id}, ${taskId});">
                        <span class="subtask-text">${data.title}</span>
                    </label>
                    <button type="button" class="subtask-del-btn" onclick="deleteSubtaskItem(${data.subtask_id}, ${taskId});">&times;</button>
                `;
                list.appendChild(li);
            }
            updateSubtaskCounter(taskId);
        }
    })
    .catch(err => console.error("Error creating subtask:", err));
}

function toggleSubtaskStatus(subtaskId, taskId) {
    fetch(`/api/subtasks/${subtaskId}/toggle`, { method: "POST" })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const item = document.getElementById(`subtaskItem-${subtaskId}`);
            if (item) {
                item.classList.toggle("subtask-done");
                if (item.classList.contains("subtask-done")) {
                    playSubtaskSound();
                    triggerConfetti();
                } else {
                    playPopSound();
                }
            }
            updateSubtaskCounter(taskId);
        }
    })
    .catch(err => console.error("Error toggling subtask:", err));
}

function deleteSubtaskItem(subtaskId, taskId) {
    fetch(`/api/subtasks/${subtaskId}/delete`, { method: "POST" })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            playTrashSound();
            const item = document.getElementById(`subtaskItem-${subtaskId}`);
            if (item) item.remove();
            updateSubtaskCounter(taskId);
        }
    })
    .catch(err => console.error("Error deleting subtask:", err));
}

function updateSubtaskCounter(taskId) {
    const list = document.getElementById(`subtasksList-${taskId}`);
    const counter = document.getElementById(`subtaskCounter-${taskId}`);
    if (!list || !counter) return;

    const total = list.querySelectorAll(".subtask-item").length;
    const completed = list.querySelectorAll(".subtask-item.subtask-done").length;
    counter.textContent = `(${completed}/${total})`;
}

/* ==========================================================================
   6. What-If Priority Simulator
   ========================================================================== */

function openSimulatorModal() {
    const modal = document.getElementById("simulatorModal");
    if (!modal) return;
    modal.style.display = "flex";
    loadSimTaskDetails();
}

function closeSimulatorModal() {
    const modal = document.getElementById("simulatorModal");
    if (!modal) return;
    modal.style.display = "none";
}

function loadSimTaskDetails() {
    const select = document.getElementById("simTaskSelect");
    if (!select || !select.selectedOptions.length) return;

    const opt = select.selectedOptions[0];
    const score = parseFloat(opt.dataset.score);
    const scoreElem = document.getElementById("simCurrentScore");
    if (scoreElem) scoreElem.textContent = `★ ${score.toFixed(2)}`;

    // Reset sliders
    const daysSlider = document.getElementById("simDaysShift");
    const hoursSlider = document.getElementById("simHoursShift");
    if (daysSlider) daysSlider.value = 0;
    if (hoursSlider) hoursSlider.value = 0;

    runPrioritySimulation();
}

function runPrioritySimulation() {
    const select = document.getElementById("simTaskSelect");
    if (!select || !select.selectedOptions.length) return;

    const opt = select.selectedOptions[0];
    const deadline = opt.dataset.deadline;
    const difficulty = parseInt(opt.dataset.difficulty, 10);
    const importance = parseInt(opt.dataset.importance, 10);
    const estimatedHours = parseFloat(opt.dataset.hours);

    const daysShift = parseInt(document.getElementById("simDaysShift").value, 10);
    const hoursShift = parseFloat(document.getElementById("simHoursShift").value);

    // Update labels
    const daysLabel = document.getElementById("simDaysShiftLabel");
    const hoursLabel = document.getElementById("simHoursShiftLabel");
    if (daysLabel) {
        daysLabel.textContent = daysShift > 0 ? `+${daysShift} days (Postponed)` : (daysShift < 0 ? `${daysShift} days (Closer)` : "0 days");
    }
    if (hoursLabel) {
        hoursLabel.textContent = hoursShift > 0 ? `+${hoursShift.toFixed(1)} hrs` : `${hoursShift.toFixed(1)} hrs`;
    }

    fetch("/api/simulate-priority", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            deadline: deadline,
            difficulty: difficulty,
            importance: importance,
            estimated_hours: estimatedHours,
            days_shift: daysShift,
            hours_shift: hoursShift
        })
    })
    .then(res => res.json())
    .then(data => {
        const projScoreElem = document.getElementById("simProjectedScore");
        const diffPill = document.getElementById("simDiffPill");
        const detailsText = document.getElementById("simDetailsText");

        if (projScoreElem) projScoreElem.textContent = `★ ${data.simulated_score.toFixed(2)}`;
        if (diffPill) {
            const diff = data.score_diff;
            if (diff > 0) {
                diffPill.textContent = `+${diff.toFixed(2)} Urgency Increase`;
                diffPill.className = "sim-diff-pill text-danger";
            } else if (diff < 0) {
                diffPill.textContent = `${diff.toFixed(2)} Priority Reduction`;
                diffPill.className = "sim-diff-pill text-success";
            } else {
                diffPill.textContent = "0.00 No Rank Change";
                diffPill.className = "sim-diff-pill text-muted";
            }
        }
        if (detailsText) {
            detailsText.innerHTML = `Simulated deadline is <strong>${data.simulated_deadline}</strong> with <strong>${data.simulated_hours}h</strong> workload.`;
        }
    })
    .catch(err => console.error("Simulation error:", err));
}

/* ==========================================================================
   7. Keyboard Shortcuts
   ========================================================================== */

function toggleKeyboardModal() {
    const modal = document.getElementById("keyboardModal");
    if (!modal) return;
    modal.style.display = modal.style.display === "flex" ? "none" : "flex";
}

function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        // Ignore if user is typing in form inputs
        const tag = e.target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") return;

        if (e.key === "Escape") {
            closeMobileNav();
            closePomodoroModal();
            closeSimulatorModal();
            const kbModal = document.getElementById("keyboardModal");
            if (kbModal) kbModal.style.display = "none";
        } else if (e.key === "n" || e.key === "N") {
            window.location.href = "/add-task";
        } else if (e.key === "d" || e.key === "D") {
            window.location.href = "/dashboard";
        } else if (e.key === "s" || e.key === "S") {
            window.location.href = "/study-plan";
        } else if (e.key === "p" || e.key === "P") {
            openPomodoroModal();
        } else if (e.key === " ") {
            // Space bar toggles pomodoro if modal is visible
            const pomoModal = document.getElementById("pomodoroModal");
            if (pomoModal && pomoModal.style.display === "flex") {
                e.preventDefault();
                togglePomodoro();
            }
        }
    });
}

function initAlertAutoDismiss() {
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-6px)";
            setTimeout(() => alert.remove(), 400);
        }, 5500);
    });
}
