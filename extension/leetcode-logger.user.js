// ==UserScript==
// @name         LeetCode Spaced Repetition Auto-Logger
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Logs accepted submissions to local SR backend. Fires exactly once per submission click. Immune to refreshes, SPA navigation, and React re-renders.
// @author       Mark
// @match        https://leetcode.com/problems/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-end
// ==/UserScript==

(function () {
  "use strict";

  console.log("🚀 LeetCode SR Logger v2.0 active.");

  // --- State ---
  // watchForSuccess: armed only after the user physically clicks Submit.
  // submissionInProgress: one-shot lock so the observer doesn't double-fire
  //   within a single mutation burst for the same click.
  let watchForSuccess = false;
  let submissionInProgress = false;
  let currentSlug = getSlug(); // Track slug so we can detect SPA navigation.

  // ─── SessionStorage deduplication key ───────────────────────────────────────
  // After a successful POST we stamp sessionStorage with the slug + a 5-minute
  // window. This is the last-resort guard against any edge case where the two
  // in-memory flags (watchForSuccess, submissionInProgress) could be bypassed
  // (e.g. rapid React re-renders that momentarily re-insert the Accepted badge).
  function dedupKey(slug) {
    return `lc_sr_logged_${slug}`;
  }

  function hasLoggedRecently(slug) {
    const ts = sessionStorage.getItem(dedupKey(slug));
    if (!ts) return false;
    return Date.now() - parseInt(ts, 10) < 5 * 60 * 1000; // 5-minute window
  }

  function markLogged(slug) {
    sessionStorage.setItem(dedupKey(slug), Date.now().toString());
  }

  // ─── SPA navigation detection ────────────────────────────────────────────────
  // LeetCode is a React SPA. Navigating between problems does NOT reload the
  // page, so our module-level variables survive. Without this, submissionInProgress
  // from problem A would block logging for problem B until the user clicks Submit.
  function getSlug() {
    return window.location.pathname.split("/")[2] || "";
  }

  function onUrlChange() {
    const newSlug = getSlug();
    if (newSlug !== currentSlug) {
      console.log(
        `🔄 SPA navigation detected (${currentSlug} → ${newSlug}). Resetting SR logger state.`,
      );
      currentSlug = newSlug;
      watchForSuccess = false;
      submissionInProgress = false;
    }
  }

  // Poll for URL changes (LeetCode doesn't fire popstate reliably for internal nav).
  setInterval(onUrlChange, 750);

  // ─── Submit button listener ──────────────────────────────────────────────────
  document.addEventListener(
    "click",
    function (e) {
      const submitBtn = e.target.closest(
        '[data-e2e-locator="console-submit-button"]',
      );
      if (!submitBtn) return;

      console.log("⚡ Submit clicked — arming Accepted detector.");
      // Refresh slug in case SPA navigation happened between the interval polls.
      currentSlug = getSlug();
      watchForSuccess = true;
      submissionInProgress = false; // Allow a fresh detection for this new attempt.
    },
    true,
  );

  // ─── MutationObserver ────────────────────────────────────────────────────────
  const observer = new MutationObserver(() => {
    // Gate 1: only active after the user clicked Submit.
    if (!watchForSuccess) return;
    // Gate 2: one-shot lock — don't re-enter if we're already handling this result.
    if (submissionInProgress) return;

    const resultBadge =
      document.querySelector('[data-e2e-locator="submission-result"]') ||
      document.querySelector(".text-green-s");

    if (!resultBadge || !resultBadge.textContent.includes("Accepted")) return;

    // Gate 3: sessionStorage dedup — last-resort guard against double-logging.
    if (hasLoggedRecently(currentSlug)) {
      console.log(`⏭️ Already logged "${currentSlug}" recently — skipping.`);
      watchForSuccess = false;
      return;
    }

    // Lock everything before the async timeout so no re-entry can happen.
    submissionInProgress = true;
    watchForSuccess = false;

    console.log("🎯 Fresh Accepted detected — processing in 1 s...");
    // Wait a moment for LeetCode to finish rendering the percentile stats.
    setTimeout(() => processSuccessfulSubmission(currentSlug), 1000);
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // ─── Core processing ─────────────────────────────────────────────────────────
  function processSuccessfulSubmission(slug) {
    // Title from URL slug.
    const titleClean = slug
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

    // 1. Difficulty
    let difficulty = "Medium";
    for (const el of document.querySelectorAll("div")) {
      const txt = el.textContent.trim();
      if (
        (txt === "Easy" || txt === "Medium" || txt === "Hard") &&
        (el.classList.contains("text-green-s") ||
          el.classList.contains("text-yellow") ||
          el.classList.contains("text-brand-orange") ||
          el.classList.contains("text-pink"))
      ) {
        difficulty = txt;
        break;
      }
    }

    // 2. Topic tags
    let tags = [];
    document.querySelectorAll('a[href^="/tag/"]').forEach((el) => {
      const t = el.textContent.trim();
      if (t && !tags.includes(t)) tags.push(t);
    });
    if (tags.length === 0) tags = ["Algorithms"];

    // 3. Runtime / memory percentiles
    let runtimePercent = 0.0;
    let memoryPercent = 0.0;
    document.querySelectorAll("span").forEach((el) => {
      if (el.textContent.includes("Beats")) {
        const match = el.textContent.match(/Beats\s+([\d.]+)%/);
        if (match) {
          if (runtimePercent === 0.0) runtimePercent = parseFloat(match[1]);
          else if (memoryPercent === 0.0) memoryPercent = parseFloat(match[1]);
        }
      }
    });

    // 4. Language — read from the editor language selector button.
    let lang = detectLanguage();

    // 5. Quality rating prompt — user can cancel to abort logging entirely.
    const ratingInput = prompt(
      `✅ "${titleClean}" — Accepted!\n\n` +
        "Rate your solving quality (1–5), or press Cancel to skip logging:\n\n" +
        "5 — Perfect recall, optimal approach, no hints\n" +
        "4 — Solved with minor bugs or brief hesitation\n" +
        "3 — Solved but suboptimal / heavy struggle\n" +
        "2 — Failed, but understood the solution fully\n" +
        "1 — Completely blocked, required deep review",
    );

    // Cancelled rating prompt → abort; don't log this submission.
    if (ratingInput === null) {
      console.log("🚫 Logging cancelled by user (rating prompt dismissed).");
      // Release the lock so the user can re-submit if they want.
      submissionInProgress = false;
      return;
    }

    let qualityScore = 3;
    const parsed = parseInt(ratingInput, 10);
    if (parsed >= 1 && parsed <= 5) qualityScore = parsed;

    const notesInput = prompt(
      "📝 Notes, approach, complexity — or press Cancel to log without notes:",
    );
    // A cancelled notes prompt is fine — just log with empty notes.
    const shortNotes = notesInput !== null ? notesInput : "";

    const payload = {
      problem_id: 0,
      title: titleClean,
      difficulty,
      tags,
      runtime_percentile: runtimePercent,
      memory_percentile: memoryPercent,
      lang,
      notes: shortNotes,
      quality_score: qualityScore,
    };

    console.log("📤 Sending SR payload:", payload);

    GM_xmlhttpRequest({
      method: "POST",
      url: "http://127.0.0.1:8000/log-submission",
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify(payload),
      onload(res) {
        console.log("✅ SR backend acknowledged:", res.responseText);
        // Stamp sessionStorage ONLY after a confirmed successful POST.
        markLogged(slug);
      },
      onerror(err) {
        console.error(
          "❌ SR backend unreachable. Is the FastAPI server running?",
          err,
        );
        // Release the lock on failure so the user can try again without resubmitting.
        submissionInProgress = false;
      },
    });
  }

  // ─── Language detection ───────────────────────────────────────────────────────
  function detectLanguage() {
    // LeetCode renders the active language on the editor toolbar button.
    const langBtn = document.querySelector(
      '[data-e2e-locator="console-lang-select-btn"]',
    );
    if (langBtn) {
      const txt = langBtn.textContent.trim();
      if (txt) return txt;
    }

    // Fallback: scan visible text for a known language name near the code area.
    const knownLangs = [
      "Python3",
      "Python",
      "JavaScript",
      "TypeScript",
      "Java",
      "C++",
      "C",
      "Go",
      "Ruby",
      "Swift",
      "Kotlin",
      "Rust",
      "Scala",
      "PHP",
      "C#",
      "Dart",
      "Elixir",
      "Erlang",
      "Racket",
    ];
    for (const el of document.querySelectorAll("button, span, div")) {
      const txt = el.textContent.trim();
      if (knownLangs.includes(txt)) return txt;
    }

    return "Unknown";
  }
})();
