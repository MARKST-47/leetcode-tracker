// ==UserScript==
// @name         LeetCode Spaced Repetition Auto-Logger
// @namespace    http://tampermonkey.net/
// @version      1.5
// @description  Triggers ONLY on real code submissions, ignoring page refreshes.
// @author       Mark
// @match        https://leetcode.com/problems/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-end
// ==/UserScript==

(function () {
  "use strict";

  console.log(
    "🚀 DOM Smart-Scraper v1.5 active. Arming submission listeners...",
  );

  let watchForSuccess = false;
  let submissionInProgress = false;

  // Listen for clicks on LeetCode's Submit button
  document.addEventListener(
    "click",
    function (e) {
      // Target LeetCode's explicit submission button attribute
      const submitBtn = e.target.closest(
        '[data-e2e-locator="console-submit-button"]',
      );
      if (submitBtn) {
        console.log("⚡ Submit button clicked! Arming success detector...");
        watchForSuccess = true;
        submissionInProgress = false; // Reset lock for this fresh run
      }
    },
    true,
  );

  const observer = new MutationObserver((mutations) => {
    // ONLY check the DOM if the user actually clicked "Submit" first
    if (!watchForSuccess || submissionInProgress) return;

    const successBadge =
      document.querySelector('[data-e2e-locator="submission-result"]') ||
      document.querySelector(".text-green-s");

    if (successBadge && successBadge.textContent.includes("Accepted")) {
      submissionInProgress = true; // Set lock
      watchForSuccess = false; // Disarm detector until next button click

      console.log("🎯 Fresh 'Accepted' status detected! Processing...");

      // Delay slightly to let performance percentiles finish rendering on screen
      setTimeout(() => {
        processSuccessfulSubmission();
      }, 1000);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  function processSuccessfulSubmission() {
    const pathSegments = window.location.pathname.split("/");
    const slug = pathSegments[2];
    const titleClean = slug
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");

    // 1. Precise Difficulty Extraction
    let difficulty = "Medium";
    const diffElements = document.querySelectorAll("div");
    for (let el of diffElements) {
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

    // 2. Precise Topic Tags Extraction
    let tags = [];
    document.querySelectorAll('a[href^="/tag/"]').forEach((tagEl) => {
      const tagText = tagEl.textContent.trim();
      if (tagText && !tags.includes(tagText)) {
        tags.push(tagText);
      }
    });
    if (tags.length === 0) {
      tags = ["Algorithms"];
    }

    // 3. Runtime Percentiles
    let runtimePercent = 0.0;
    let memoryPercent = 0.0;
    document.querySelectorAll("span").forEach((el) => {
      if (el.textContent.includes("Beats")) {
        const match = el.textContent.match(/Beats\s+([\d.]+)\%/);
        if (match && match[1]) {
          if (runtimePercent === 0.0) runtimePercent = parseFloat(match[1]);
          else if (memoryPercent === 0.0) memoryPercent = parseFloat(match[1]);
        }
      }
    });

    const ratingInput = prompt(
      `"${titleClean}" Successfully Logged!\n\n` +
        "Rate your solving performance quality (1 to 5):\n" +
        "5 - Perfect execution (Optimal strategy, no hints, fast)\n" +
        "4 - Solved with minor bugs or hesitation\n" +
        "3 - Solved suboptimal approach / heavy struggling\n" +
        "2 - Failed, but understood solution completely\n" +
        "1 - Blocked entirely, required deep review",
    );

    let qualityScore = 3;
    if (ratingInput !== null) {
      const parsed = parseInt(ratingInput);
      if (parsed >= 1 && parsed <= 5) qualityScore = parsed;
    }

    const notesInput = prompt(
      "Enter approach notes, time complexities, or flash observations:",
    );
    const shortNotes = notesInput !== null ? notesInput : "";

    const payload = {
      problem_id: 0,
      title: titleClean,
      difficulty: difficulty,
      tags: tags,
      runtime_percentile: runtimePercent,
      memory_percentile: memoryPercent,
      lang: "Python/Dynamic",
      notes: shortNotes,
      quality_score: qualityScore,
    };

    console.log("📤 Sending payload:", payload);

    GM_xmlhttpRequest({
      method: "POST",
      url: "http://127.0.0.1:8000/log-submission",
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify(payload),
      onload: function (res) {
        console.log("🎯 Backend response received:", res.responseText);
      },
      onerror: function (err) {
        console.error("❌ Link down to local FastAPI server.", err);
      },
    });
  }
})();
