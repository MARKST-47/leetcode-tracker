// ==UserScript==
// @name         LeetCode Spaced Repetition Auto-Logger
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Bypasses lockouts, extracts real difficulty and problem topic tags dynamically.
// @author       Mark
// @match        https://leetcode.com/problems/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-end
// ==/UserScript==

(function () {
  "use strict";

  console.log("🚀 DOM Smart-Scraper active. Listening for Accepted status...");

  let submissionLoggedForThisRun = false;
  let lastUrl = location.href;

  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      submissionLoggedForThisRun = false;
    }
  }, 1000);

  const observer = new MutationObserver((mutations) => {
    if (submissionLoggedForThisRun) return;

    const successBadge =
      document.querySelector('[data-e2e-locator="submission-result"]') ||
      document.querySelector(".text-green-s");

    if (successBadge && successBadge.textContent.includes("Accepted")) {
      submissionLoggedForThisRun = true;
      console.log("🎯 Match found! Scraping metadata context...");
      setTimeout(() => {
        processSuccessfulSubmission();
      }, 600);
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
    // Scan for standard link routing patterns matching topics on LeetCode
    document.querySelectorAll('a[href^="/tag/"]').forEach((tagEl) => {
      const tagText = tagEl.textContent.trim();
      if (tagText && !tags.includes(tagText)) {
        tags.push(tagText);
      }
    });
    if (tags.length === 0) {
      tags = ["Algorithms"];
    } // Fallback

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

    const qualityScore =
      parseInt(ratingInput) >= 1 && parseInt(ratingInput) <= 5
        ? parseInt(ratingInput)
        : 3;
    const shortNotes =
      prompt(
        "Enter approach notes, time complexities, or flash observations:",
      ) || "";

    const payload = {
      problem_id: 0, // Backend identifies unique entries via title matching now
      title: titleClean,
      difficulty: difficulty,
      tags: tags,
      runtime_percentile: runtimePercent,
      memory_percentile: memoryPercent,
      lang: "Python/Dynamic",
      notes: shortNotes,
      quality_score: qualityScore,
    };

    GM_xmlhttpRequest({
      method: "POST",
      url: "http://127.0.0.1:8000/log-submission",
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify(payload),
      onload: function (res) {
        console.log("🎯 Synced database updates:", res.responseText);
      },
      onerror: function (err) {
        console.error("❌ Link down to local server.", err);
      },
    });
  }
})();
