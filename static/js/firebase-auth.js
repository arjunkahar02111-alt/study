/**
 * SYNTRIQ Centralized Firebase Authentication & Real-Time Firestore Sync
 * - Google OAuth Sign-In & Account Switching
 * - Automatic Workspace Creation & Session Restoration
 * - Real-time UID-scoped Firestore listeners (onSnapshot) with clean teardown
 */

import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import { getAnalytics, isSupported as isAnalyticsSupported } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-analytics.js";
import {
    getAuth,
    GoogleAuthProvider,
    signInWithPopup,
    signOut,
    onAuthStateChanged,
    onIdTokenChanged,
    browserLocalPersistence,
    setPersistence
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";
import {
    initializeFirestore,
    getFirestore,
    persistentLocalCache,
    persistentMultipleTabManager,
    collection,
    doc,
    onSnapshot
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";

const cfg = window.SYNTRIQ_AUTH_CONFIG || {};
const state = {
    app: null,
    auth: null,
    db: null,
    unsubscribers: [],
    isLoggingOut: false,
    syncDebounceTimer: null,
    initialSnapshotFlags: {}
};

function showAuthError(message) {
    const box = document.getElementById("authErrorBox");
    const txt = document.getElementById("authErrorText");
    if (box && txt) {
        txt.textContent = message;
        box.style.display = "flex";
    } else {
        console.error("[SYNTRIQ Auth]", message);
    }
}

function setLoginLoading(loading) {
    const btn = document.getElementById("googleSignInBtn");
    const content = document.getElementById("googleBtnContent");
    const loader = document.getElementById("googleBtnLoading");
    if (btn) btn.disabled = loading;
    if (content) content.style.display = loading ? "none" : "inline-flex";
    if (loader) loader.style.display = loading ? "inline-flex" : "none";
}

function stopAllListeners() {
    state.unsubscribers.forEach(unsub => {
        try {
            if (typeof unsub === "function") unsub();
        } catch (e) {}
    });
    state.unsubscribers = [];
    state.initialSnapshotFlags = {};
    if (state.syncDebounceTimer) {
        clearTimeout(state.syncDebounceTimer);
        state.syncDebounceTimer = null;
    }
}

function clearUserClientState(uid) {
    if (window.activeSessionInterval) {
        clearInterval(window.activeSessionInterval);
        window.activeSessionInterval = null;
    }
    if (window.pomoInterval) {
        clearInterval(window.pomoInterval);
        window.pomoInterval = null;
    }
    if (uid) {
        try {
            localStorage.removeItem(`syntriq_${uid}_sound_fx`);
        } catch (e) {}
    }
    try {
        sessionStorage.clear();
    } catch (e) {}
}

function scheduleRemoteSyncRefresh() {
    if (state.isLoggingOut) return;
    if (state.syncDebounceTimer) clearTimeout(state.syncDebounceTimer);
    state.syncDebounceTimer = setTimeout(() => {
        if (typeof window.fetchActiveSession === "function") {
            window.fetchActiveSession();
        }
        if (typeof window.fetchTimeIntelData === "function" && window.location.pathname === "/time-intelligence") {
            window.fetchTimeIntelData();
        }
    }, 500);
}

function attachRealtimeListeners(uid) {
    stopAllListeners();
    if (!state.db || !uid) return;

    const watchCollection = (key, ref, onRemoteChange) => {
        state.initialSnapshotFlags[key] = true;
        const unsub = onSnapshot(
            ref,
            (snapshot) => {
                if (state.initialSnapshotFlags[key]) {
                    state.initialSnapshotFlags[key] = false;
                    return;
                }
                if (snapshot.metadata && snapshot.metadata.hasPendingWrites) return;
                onRemoteChange(snapshot);
            },
            (err) => {
                if (err && err.code === "permission-denied") {
                    console.warn(`[SYNTRIQ Firestore] Access denied on ${key} listener.`);
                }
            }
        );
        state.unsubscribers.push(unsub);
    };

    watchCollection("tasks", collection(state.db, "users", uid, "tasks"), () => {
        scheduleRemoteSyncRefresh();
    });
    watchCollection("routines", collection(state.db, "users", uid, "routines"), () => {
        scheduleRemoteSyncRefresh();
    });
    watchCollection("sessions", collection(state.db, "users", uid, "study_sessions"), () => {
        scheduleRemoteSyncRefresh();
    });

    // Real-time active timer document listener across devices
    state.initialSnapshotFlags["active_session"] = true;
    const activeUnsub = onSnapshot(
        doc(state.db, "users", uid, "active_session", "current"),
        () => {
            if (state.initialSnapshotFlags["active_session"]) {
                state.initialSnapshotFlags["active_session"] = false;
                return;
            }
            if (typeof window.fetchActiveSession === "function") {
                window.fetchActiveSession();
            }
        },
        () => {}
    );
    state.unsubscribers.push(activeUnsub);
}

async function exchangeTokenWithServer(user) {
    const idToken = await user.getIdToken();
    const res = await fetch("/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idToken })
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || "Failed to verify account session.");
    }
    return data;
}

async function signInWithGoogle(forceSelectAccount = false) {
    if (!state.auth) {
        showAuthError("Firebase is not configured yet. Please check FIREBASE_SETUP.md.");
        return;
    }
    const errBox = document.getElementById("authErrorBox");
    if (errBox) errBox.style.display = "none";
    setLoginLoading(true);

    try {
        const provider = new GoogleAuthProvider();
        provider.addScope("email");
        provider.addScope("profile");
        if (forceSelectAccount) {
            provider.setCustomParameters({ prompt: "select_account" });
        }
        const credential = await signInWithPopup(state.auth, provider);
        await exchangeTokenWithServer(credential.user);
        window.location.href = cfg.nextUrl || "/dashboard";
    } catch (err) {
        let msg = err.message || "Google Sign-In failed.";
        if (err.code === "auth/popup-closed-by-user") {
            msg = "Sign-in window was closed before completing authentication.";
        } else if (err.code === "auth/popup-blocked") {
            msg = "Pop-up was blocked by your browser. Please allow pop-ups for this site and try again.";
        } else if (err.code === "auth/unauthorized-domain") {
            msg = "This domain is not yet listed in Firebase Authorized Domains.";
        }
        showAuthError(msg);
        setLoginLoading(false);
    }
}

async function logoutSafely() {
    state.isLoggingOut = true;
    const currentUid = cfg.currentUid;
    stopAllListeners();
    clearUserClientState(currentUid);

    try {
        await fetch("/auth/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
    } catch (e) {}

    if (state.auth) {
        try {
            await signOut(state.auth);
        } catch (e) {}
    }
    window.location.href = "/login";
}

async function switchAccountSafely() {
    state.isLoggingOut = true;
    const currentUid = cfg.currentUid;
    stopAllListeners();
    clearUserClientState(currentUid);

    try {
        await fetch("/auth/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
    } catch (e) {}

    if (state.auth) {
        try {
            await signOut(state.auth);
        } catch (e) {}
    }
    window.location.href = "/login";
}

function initFirebase() {
    if (!cfg.firebaseEnabled || !cfg.firebaseConfig || !cfg.firebaseConfig.apiKey) {
        return;
    }

    state.app = getApps().length ? getApps()[0] : initializeApp(cfg.firebaseConfig);
    if (cfg.firebaseConfig.measurementId) {
        isAnalyticsSupported()
            .then((supported) => {
                if (supported) getAnalytics(state.app);
            })
            .catch(() => {});
    }
    state.auth = getAuth(state.app);
    setPersistence(state.auth, browserLocalPersistence).catch(() => {});

    try {
        state.db = initializeFirestore(state.app, {
            localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() })
        });
    } catch (e) {
        state.db = getFirestore(state.app);
    }

    onAuthStateChanged(state.auth, async (user) => {
        if (state.isLoggingOut) return;

        // Case 1: On /login, restore session automatically if Firebase already has an active user
        if (!cfg.isAuthenticated && window.location.pathname === "/login" && user) {
            const restoring = document.getElementById("authRestoringBox");
            if (restoring) restoring.style.display = "flex";
            try {
                await exchangeTokenWithServer(user);
                window.location.href = cfg.nextUrl || "/dashboard";
                return;
            } catch (e) {
                if (restoring) restoring.style.display = "none";
            }
        }

        // Case 2: Authenticated page — verify Firebase user matches server session UID
        if (cfg.isAuthenticated) {
            if (!user) {
                await logoutSafely();
                return;
            }
            if (cfg.currentUid && user.uid !== cfg.currentUid) {
                // Account switched in another tab -> sync new session cleanly
                stopAllListeners();
                clearUserClientState(cfg.currentUid);
                await exchangeTokenWithServer(user);
                window.location.reload();
                return;
            }
            attachRealtimeListeners(user.uid);
        }
    });

    onIdTokenChanged(state.auth, async (user) => {
        if (state.isLoggingOut || !user || !cfg.isAuthenticated) return;
        if (cfg.currentUid && user.uid === cfg.currentUid) {
            try {
                const idToken = await user.getIdToken();
                await fetch("/auth/refresh-token", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ idToken })
                });
            } catch (e) {}
        }
    });
}

window.SyntriqAuth = {
    signInWithGoogle,
    logoutSafely,
    switchAccountSafely,
    stopAllListeners
};

initFirebase();
