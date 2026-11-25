# SYNTRIQ — Firebase Authentication & Multi-User Firestore Setup Guide

This guide explains **exactly what you need to configure in Firebase** and **which environment variables to add** locally (`.env`) and on Vercel.

---

## 1. Create / Open Your Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** (or select your existing project), name it (e.g., `syntriq-study-planner`), and create the project.

---

## 2. Enable Google Sign-In (Firebase Authentication)

1. In the left sidebar, open **Build → Authentication** → click **Get started**.
2. Go to the **Sign-in method** tab.
3. Click **Google** → toggle **Enable**.
4. Choose a **Project support email** (your Gmail) → click **Save**.
5. Go to **Authentication → Settings → Authorized domains** and make sure all of these are listed:
   - `localhost`
   - `127.0.0.1`
   - Your Vercel production domain (e.g., `your-app.vercel.app`)

---

## 3. Create Cloud Firestore & Deploy Security Rules

1. In the left sidebar, open **Build → Firestore Database** → click **Create database**.
2. Choose **Start in production mode** and select your nearest region.
3. Open the **Rules** tab in Firestore Database.
4. Copy the entire contents of [`firestore.rules`](./firestore.rules) from this repository into the Firebase Rules editor and click **Publish**.
   - These rules enforce `request.auth != null && request.auth.uid == uid` on every collection (`profile`, `settings`, `routines`, `subjects`, `tasks`, `study_sessions`, `active_session`, `goals`, `progress`, `analytics`), rejecting all cross-account access at the database layer.

---

## 4. Register a Web App & Copy Your Firebase Config

1. Click the **Gear icon (⚙) → Project settings** → scroll to **Your apps**.
2. Click the **`</>` (Web)** icon, give it a nickname (e.g. `SYNTRIQ Web`), and click **Register app**.
3. Firebase will display a `firebaseConfig` object like:
   ```js
   const firebaseConfig = {
     apiKey: "AIza...",
     authDomain: "your-project.firebaseapp.com",
     projectId: "your-project",
     storageBucket: "your-project.firebasestorage.app",
     messagingSenderId: "1234567890",
     appId: "1:1234567890:web:abcdef..."
   };
   ```
4. Copy those values into a `.env` file in `E:\Aasu\.env` (using `.env.example` as a template):
   ```env
   SECRET_KEY=replace-with-a-long-random-secret-string
   FIREBASE_API_KEY=AIza...
   FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   FIREBASE_PROJECT_ID=your-project
   FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
   FIREBASE_MESSAGING_SENDER_ID=1234567890
   FIREBASE_APP_ID=1:1234567890:web:abcdef...
   ```

---

## 5. Add the Same Environment Variables on Vercel

In your **Vercel Dashboard → Project → Settings → Environment Variables**, add:
- `SECRET_KEY`
- `FIREBASE_API_KEY`
- `FIREBASE_AUTH_DOMAIN`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_MESSAGING_SENDER_ID`
- `FIREBASE_APP_ID`

Then redeploy on Vercel and ensure your Vercel URL (e.g. `https://your-app.vercel.app`) is added under **Firebase Console → Authentication → Settings → Authorized domains**.
