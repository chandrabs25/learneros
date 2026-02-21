import { initializeApp, getApps } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyDZtH1igFr6mKXjzrKcYbCQJQK3YdDjBAk",
    authDomain: "teacher-b2cd9.firebaseapp.com",
    projectId: "teacher-b2cd9",
    storageBucket: "teacher-b2cd9.firebasestorage.app",
    messagingSenderId: "980173916496",
    appId: "1:980173916496:web:6213a4fdd5bea3f1c08455",
    measurementId: "G-Z7Q570H1ZY",
};

// Initialize Firebase (singleton — safe for HMR)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const auth = getAuth(app);

export { app, auth };
