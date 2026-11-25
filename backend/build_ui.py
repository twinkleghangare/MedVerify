# -*- coding: utf-8 -*-
"""
Builder script for MedVerify AI frontend.
Styled after the uploaded reference screens & 16px spacing spec:
  - 16px rounded white cards (border-radius: 16px, padding: 16px) on soft neutral off-white canvas
  - Dark Charcoal-Forest header card (#252A26) for result hero (inspired by "Amoxiciline DX2")
  - Vibrant Lime-Green primary accent (#82D616) with high-contrast dark forest ink (#161E13)
  - Coral Red alert (#E5484D) & Soft Violet (#7C5CFA) secondary tags
  - Focused 3-mode verification: Upload | Live Scan | Text
  - Conditional Government Complaint redirect: ONLY shown when Counterfeit, Banned, Suspicious, or Expired
"""
import os

UI_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="MedVerify AI: Medicine authentication via packaging upload, live camera scan, or text registry lookup.">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; connect-src *; img-src 'self' data: blob:; media-src 'self' blob:;">
<title>MedVerify AI: Medicine Verification</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
<style>
/* Hallmark · theme: dose · genre: modern-minimal · shape: app screen · scope: app · v5.0.0
 * critique: 16px-rounded white cards, dark charcoal-forest result hero, vibrant lime-green primary CTA, coral hazard alerts
 * waive: none
 * answered: none */

:root {
  /* Frosted Glass & Pastel-Mist Reference Palette (from uploaded UI texture reference) */
  --color-charcoal-hero: oklch(23% 0.02 265);   /* #1E222E Deep Ink Slate */
  --color-lime: oklch(25% 0.025 265);           /* #242936 Sleek Dark-Ink Primary CTA */
  --color-lime-hover: oklch(19% 0.025 265);
  --color-lime-ink: oklch(99% 0.002 260);       /* Crisp White text on Dark-Ink CTA */
  --color-lime-soft: oklch(94% 0.025 260);      /* Soft Frosted Tint */
  --color-lime-text: oklch(34% 0.03 265);

  --color-violet: oklch(58% 0.14 280);
  --color-violet-soft: oklch(93% 0.03 280);

  --status-verified-bg: oklch(92% 0.055 155);   /* Soft Sage-Mint Pill */
  --status-verified-text: oklch(40% 0.11 160);

  --status-suspicious-bg: oklch(92% 0.045 15);  /* Soft Rose-Blush Pill */
  --status-suspicious-text: oklch(48% 0.17 18);

  --status-inconclusive-bg: oklch(92% 0.045 78);
  --status-inconclusive-text: oklch(46% 0.11 65);

  /* Ambient Pastel-Mist Canvas & Translucent Frosted Surfaces */
  --color-canvas: oklch(93% 0.015 265);
  --bg-ambient-mesh: radial-gradient(at 12% 18%, oklch(92% 0.035 235) 0px, transparent 52%),
                     radial-gradient(at 88% 15%, oklch(91% 0.038 295) 0px, transparent 50%),
                     radial-gradient(at 25% 88%, oklch(92% 0.042 155) 0px, transparent 55%),
                     radial-gradient(at 82% 85%, oklch(90% 0.035 280) 0px, transparent 52%);
  --color-panel: oklch(98.5% 0.004 260 / 0.72);       /* Frosted Glass Panel */
  --color-surface-tint: oklch(99% 0.003 260 / 0.56);  /* Inner Translucent Layer */
  --color-bright: oklch(99.5% 0.002 260);
  --color-charcoal: oklch(23% 0.02 265);
  --color-slate: oklch(51% 0.02 260);
  --color-border: oklch(99% 0.002 260 / 0.7);         /* Delicate Frosted Edge */
  --color-border-strong: oklch(82% 0.015 260 / 0.8);
  --color-emerald-dot: oklch(62% 0.15 155);
  --color-reticle: oklch(99% 0.002 260);
  --backdrop-scrim: oklch(20% 0.025 265 / 0.45);

  --font-heading: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
  --font-body: "Inter", system-ui, -apple-system, sans-serif;
  --font-mono: "DM Mono", ui-monospace, monospace;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-pill: 9999px;

  --space-4: 4px;
  --space-8: 8px;
  --space-12: 12px;
  --space-16: 16px;
  --space-20: 20px;
  --space-24: 24px;

  --shadow-card: 0 8px 32px oklch(25% 0.03 265 / 0.06);
  --shadow-pill: 0 2px 10px oklch(25% 0.03 265 / 0.07);
  --shadow-modal: 0 24px 60px oklch(20% 0.03 265 / 0.22);
  --dur-fast: 160ms;
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
}

*, *::before, *::after {
  box-sizing: border-box;
}

html, body {
  overflow-x: clip;
}

body {
  margin: 0;
  font-family: var(--font-body);
  background-color: var(--color-canvas);
  background-image: var(--bg-ambient-mesh);
  background-attachment: fixed;
  color: var(--color-charcoal);
  -webkit-font-smoothing: antialiased;
  line-height: 1.5;
  min-height: 100vh;
}

button, input, textarea, select {
  font-family: inherit;
}

button:active {
  transform: scale(0.98);
}

/* Top Compact Header */
.top-header {
  background-color: var(--color-panel);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-12) var(--space-24);
  position: sticky;
  top: 0;
  z-index: 40;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-16);
  flex-wrap: wrap;
}

.brand-group {
  display: flex;
  align-items: center;
  gap: var(--space-12);
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background-color: var(--color-charcoal-hero);
  display: grid;
  place-items: center;
  color: var(--color-bright);
  flex-shrink: 0;
}

.brand-mark svg {
  width: 18px;
  height: 18px;
}

.brand-name {
  font-family: var(--font-heading);
  font-size: 17px;
  font-weight: 800;
  color: var(--color-charcoal-hero);
  letter-spacing: -0.02em;
  margin: 0;
}

.brand-sub {
  font-size: 11px;
  color: var(--color-slate);
  margin: 0;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex-wrap: wrap;
}

.api-status-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-4) var(--space-12);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border-strong);
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-charcoal);
  cursor: pointer;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-emerald-dot);
}

.status-dot.is-down {
  background-color: var(--status-suspicious-text);
}

.lang-group {
  display: inline-flex;
  padding: var(--space-4);
  background-color: var(--color-surface-tint);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  gap: var(--space-4);
}

.lang-btn {
  border: none;
  background: transparent;
  padding: var(--space-4) var(--space-12);
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-slate);
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}

.lang-btn.is-active {
  background-color: var(--color-charcoal-hero);
  color: var(--color-bright);
}

/* Main 2-Column 16px-Rounded Card Layout */
.workspace-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-24);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
  gap: var(--space-20);
  align-items: start;
}

.card-panel {
  background-color: var(--color-panel);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.card-pad {
  padding: var(--space-16);
}

.panel-heading {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 800;
  color: var(--color-charcoal-hero);
  letter-spacing: -0.02em;
  margin: 0 0 var(--space-4);
}

.panel-subtitle {
  font-size: 13px;
  color: var(--color-slate);
  margin: 0 0 var(--space-16);
}

/* 3-Mode Pill Tabs */
.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-8);
  background-color: var(--color-surface-tint);
  padding: var(--space-4);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-16);
}

.mode-tab-btn {
  border: none;
  background: transparent;
  padding: var(--space-8) var(--space-12);
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-slate);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  transition: background-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}

.mode-tab-btn svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.mode-tab-btn.is-active {
  background-color: var(--color-bright);
  color: var(--color-charcoal);
  box-shadow: var(--shadow-pill);
}

.mode-pane {
  display: none;
}

.mode-pane.is-active {
  display: block;
}

/* Upload Drop Zone */
.drop-zone {
  border: 1.5px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background-color: var(--color-surface-tint);
  padding: var(--space-24) var(--space-16);
  text-align: center;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-out), background-color var(--dur-fast) var(--ease-out);
}

.drop-zone:hover, .drop-zone.is-dragover {
  border-color: var(--color-lime-text);
  background-color: var(--color-lime-soft);
}

.drop-icon-plain {
  display: inline-flex;
  margin-bottom: var(--space-8);
  color: var(--color-charcoal-hero);
}

.drop-icon-plain svg {
  width: 24px;
  height: 24px;
}

.drop-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-charcoal);
  margin: 0 0 var(--space-4);
}

.drop-hint {
  font-size: 12px;
  color: var(--color-slate);
  margin: 0;
}

/* Preview Box */
.preview-card {
  display: none;
  margin-top: var(--space-12);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-12);
  background-color: var(--color-panel);
}

.preview-card.is-visible {
  display: block;
}

.preview-img-wrap {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  background-color: var(--color-charcoal-hero);
  height: 200px;
  margin-bottom: var(--space-12);
}

.preview-img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.preview-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-12);
}

.preview-filename {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-charcoal);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-filesize {
  font-size: 11px;
  color: var(--color-slate);
  margin: 0;
}

/* Live Camera Viewfinder (inspired by green capsule scan screen) */
.camera-frame {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-color: var(--color-charcoal-hero);
  aspect-ratio: 16 / 10;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-12);
}

.camera-frame video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-placeholder {
  color: var(--color-bright);
  text-align: center;
  padding: var(--space-16);
}

.camera-placeholder p {
  margin: var(--space-8) 0 0;
  font-size: 13px;
  opacity: 0.85;
}

.reticle-box {
  position: absolute;
  inset: 16px;
  pointer-events: none;
}

.reticle-corner {
  position: absolute;
  width: 22px;
  height: 22px;
  border-color: var(--color-reticle);
  border-style: solid;
}

.reticle-corner.tl { top: 0; left: 0; border-width: 3px 0 0 3px; border-top-left-radius: 8px; }
.reticle-corner.tr { top: 0; right: 0; border-width: 3px 3px 0 0; border-top-right-radius: 8px; }
.reticle-corner.bl { bottom: 0; left: 0; border-width: 0 0 3px 3px; border-bottom-left-radius: 8px; }
.reticle-corner.br { bottom: 0; right: 0; border-width: 0 3px 3px 0; border-bottom-right-radius: 8px; }

.camera-controls {
  display: flex;
  gap: var(--space-8);
  flex-wrap: wrap;
}

/* Text Lookup Form */
.field-group {
  margin-bottom: var(--space-12);
}

.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-charcoal);
  margin-bottom: var(--space-4);
}

.field-input {
  width: 100%;
  height: 40px;
  padding: 0 var(--space-12);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-strong);
  background-color: var(--color-surface-tint);
  font-size: 13px;
  color: var(--color-charcoal);
  outline: none;
  transition: background-color var(--dur-fast) var(--ease-out);
}

.field-input:focus {
  background-color: var(--color-panel);
  outline: 2px solid var(--color-lime-text);
  outline-offset: -1px;
}

.field-row-2 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-12);
}

/* Vibrant Lime Primary Button (from "See Details ->" reference) */
.btn-primary {
  width: 100%;
  min-height: 46px;
  margin-top: var(--space-16);
  background-color: var(--color-lime);
  color: var(--color-lime-ink);
  border: none;
  border-radius: var(--radius-pill);
  padding: 0 var(--space-20);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  transition: background-color var(--dur-fast) var(--ease-out);
}

.btn-primary:hover {
  background-color: var(--color-lime-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ghost-btn {
  min-height: 36px;
  padding: 0 var(--space-12);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border-strong);
  background: transparent;
  color: var(--color-charcoal);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  transition: background-color var(--dur-fast) var(--ease-out);
}

.ghost-btn:hover {
  background-color: var(--color-surface-tint);
}

/* Results Column */
.empty-result-state {
  padding: var(--space-24) var(--space-16);
  text-align: center;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background-color: var(--color-surface-tint);
}

.empty-result-icon {
  display: inline-flex;
  margin-bottom: var(--space-8);
  color: var(--color-charcoal-hero);
}

.empty-result-icon svg {
  width: 28px;
  height: 28px;
}

.empty-result-title {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-charcoal-hero);
  margin: 0 0 var(--space-4);
}

.empty-result-desc {
  font-size: 13px;
  color: var(--color-slate);
  margin: 0;
}

.result-content {
  display: none;
}

.result-content.is-visible {
  display: block;
}

/* Frosted Glass Result Header */
.dark-hero-header {
  background-color: var(--color-surface-tint);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-charcoal);
  padding: var(--space-20) var(--space-16);
}

.dark-hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-12);
}

.result-med-name {
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 800;
  color: var(--color-charcoal);
  margin: 0 0 var(--space-4);
}

.result-med-sub {
  font-size: 13px;
  color: var(--color-slate);
  margin: 0 0 var(--space-12);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: var(--space-4) var(--space-12);
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 700;
}

.status-pill.verified {
  background-color: var(--status-verified-bg);
  color: var(--status-verified-text);
}

.status-pill.suspicious {
  background-color: var(--status-suspicious-bg);
  color: var(--status-suspicious-text);
}

.status-pill.inconclusive {
  background-color: var(--status-inconclusive-bg);
  color: var(--status-inconclusive-text);
}

.hero-listen-btn {
  border: 1px solid var(--color-border-strong);
  background: transparent;
  color: var(--color-charcoal);
  border-radius: var(--radius-pill);
  padding: var(--space-4) var(--space-12);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  flex-shrink: 0;
}

/* Conditional Counterfeit / Hazard Complaint Alert (HIDDEN when Genuine) */
.complaint-redirect-box {
  display: none;
  margin-bottom: var(--space-16);
  padding: var(--space-16);
  border-radius: var(--radius-lg);
  background-color: var(--status-suspicious-bg);
  border: 1px solid var(--status-suspicious-text);
}

.complaint-redirect-box.is-visible {
  display: block;
}

.complaint-alert-title {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 800;
  color: var(--status-suspicious-text);
  margin: 0 0 var(--space-4);
}

.complaint-alert-desc {
  font-size: 12px;
  color: var(--color-charcoal);
  margin: 0 0 var(--space-12);
}

.complaint-action-btn {
  border: 1.5px solid var(--status-suspicious-text);
  background: transparent;
  color: var(--status-suspicious-text);
  border-radius: var(--radius-pill);
  padding: var(--space-8) var(--space-16);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
}

.complaint-action-btn:hover {
  background-color: var(--color-panel);
}

/* Diagnostics Key-Value Table */
.diag-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.diag-table tr {
  border-bottom: 1px solid var(--color-border);
}

.diag-table tr:last-child {
  border-bottom: none;
}

.diag-table td {
  padding: var(--space-8) 0;
}

.diag-key {
  color: var(--color-slate);
  width: 42%;
}

.diag-val {
  font-weight: 600;
  color: var(--color-charcoal);
  text-align: right;
}

.diag-val.is-mono {
  font-family: var(--font-mono);
}

/* AI Assistant Box inside Result */
.ai-followup-box {
  margin-top: var(--space-16);
  padding-top: var(--space-16);
  border-top: 1px solid var(--color-border);
}

.ai-followup-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-charcoal-hero);
  margin: 0 0 var(--space-8);
}

.chat-log {
  max-height: 180px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  margin-bottom: var(--space-8);
}

.chat-bubble {
  font-size: 12px;
  padding: var(--space-8) var(--space-12);
  border-radius: var(--radius-md);
  line-height: 1.45;
}

.chat-bubble.assistant {
  background-color: var(--color-surface-tint);
  border: 1px solid var(--color-border);
  color: var(--color-charcoal);
}

.chat-bubble.user {
  background-color: var(--color-charcoal-hero);
  color: var(--color-bright);
  align-self: flex-end;
}

.chat-form-row {
  display: flex;
  gap: var(--space-8);
}

/* Recent History List */
.history-card {
  margin-top: var(--space-20);
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-8);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

.history-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
  padding: var(--space-8) var(--space-12);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background-color: var(--color-surface-tint);
  cursor: pointer;
}

.history-row-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-charcoal);
  margin: 0;
}

.history-row-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-slate);
  margin: 0;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--backdrop-scrim);
  z-index: 100;
  display: none;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
}

.modal-backdrop.is-open {
  display: flex;
}

.modal-box {
  background-color: var(--color-panel);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 560px;
  padding: var(--space-24);
  box-shadow: var(--shadow-modal);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-16);
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 17px;
  font-weight: 800;
  color: var(--color-charcoal-hero);
  margin: 0;
}

.authority-pills {
  display: flex;
  gap: var(--space-8);
  flex-wrap: wrap;
  margin-bottom: var(--space-12);
}

.auth-pill {
  padding: var(--space-4) var(--space-12);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border-strong);
  background-color: var(--color-surface-tint);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-charcoal);
  cursor: pointer;
}

.auth-pill.is-active {
  background-color: var(--color-charcoal-hero);
  border-color: var(--color-charcoal-hero);
  color: var(--color-bright);
}

.dossier-textarea {
  width: 100%;
  min-height: 170px;
  padding: var(--space-12);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-strong);
  background-color: var(--color-surface-tint);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-charcoal);
  resize: vertical;
  margin-bottom: var(--space-12);
}

.consent-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-8);
  font-size: 12px;
  color: var(--color-slate);
  margin-bottom: var(--space-16);
}

.modal-footer-btns {
  display: flex;
  gap: var(--space-8);
  justify-content: flex-end;
  flex-wrap: wrap;
}

.toast-bar {
  position: fixed;
  bottom: var(--space-20);
  right: var(--space-20);
  background-color: var(--color-charcoal-hero);
  color: var(--color-bright);
  padding: var(--space-8) var(--space-16);
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  z-index: 200;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--dur-fast) var(--ease-out);
}

.toast-bar.is-visible {
  opacity: 1;
}

@media (max-width: 900px) {
  .workspace-container {
    grid-template-columns: minmax(0, 1fr);
    padding: var(--space-16);
  }
  .field-row-2 {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
</head>
<body>

<header class="top-header">
  <div class="header-inner">
    <div class="brand-group">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v8M8 12h8"/></svg>
      </div>
      <div>
        <h1 class="brand-name">MedVerify AI</h1>
        <p class="brand-sub" id="brandSubText">Medicine Authentication &amp; Screening</p>
      </div>
    </div>

    <div class="header-controls">
      <button type="button" class="api-status-pill" id="apiStatusPill" onclick="openHostModal()">
        <span class="status-dot" id="apiDot"></span>
        <span id="apiStatusText">Connecting…</span>
      </button>

      <div class="lang-group" role="group" aria-label="Language">
        <button type="button" class="lang-btn is-active" id="lang-en" onclick="setLanguage('en')">EN</button>
        <button type="button" class="lang-btn" id="lang-hi" onclick="setLanguage('hi')">हिंदी</button>
        <button type="button" class="lang-btn" id="lang-mr" onclick="setLanguage('mr')">मराठी</button>
      </div>
    </div>
  </div>
</header>

<main class="workspace-container">
  <!-- LEFT COLUMN: VERIFICATION STATION -->
  <section class="card-panel" aria-label="Verification Station">
    <div class="card-pad">
      <h2 class="panel-heading" id="stationTitle">Verify Medicine</h2>
      <p class="panel-subtitle" id="stationSubtitle">Upload a packaging photo, scan with live camera, or search by medicine name.</p>

      <div class="mode-tabs" role="tablist">
        <button type="button" class="mode-tab-btn is-active" id="tabUpload" onclick="switchMode('upload')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <span id="lblTabUpload">Upload</span>
        </button>
        <button type="button" class="mode-tab-btn" id="tabCamera" onclick="switchMode('camera')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          <span id="lblTabCamera">Live Scan</span>
        </button>
        <button type="button" class="mode-tab-btn" id="tabText" onclick="switchMode('text')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <span id="lblTabText">Text</span>
        </button>
      </div>

      <!-- MODE 1: UPLOAD PHOTO -->
      <div class="mode-pane is-active" id="paneUpload">
        <div class="drop-zone" id="dropZone" onclick="triggerFileSelect()">
          <div class="drop-icon-plain" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          </div>
          <p class="drop-title" id="dropTitleText">Drop medicine packaging photo or click to browse</p>
          <p class="drop-hint">JPG, PNG, WEBP up to 8 MB · OCR &amp; QR/Barcode supported</p>
        </div>
        <input type="file" id="fileInput" accept="image/*" style="display:none;">

        <div class="preview-card" id="previewCard">
          <div class="preview-img-wrap">
            <img id="previewImg" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1' height='1'/%3E" alt="Selected medicine packaging">
          </div>
          <div class="preview-meta-row">
            <div style="min-width:0;">
              <p class="preview-filename" id="previewName">image.jpg</p>
              <p class="preview-filesize" id="previewSize">0 KB</p>
            </div>
            <div style="display:flex; gap:6px; flex-shrink:0;">
              <button type="button" class="ghost-btn" onclick="triggerFileSelect()">Replace</button>
              <button type="button" class="ghost-btn" onclick="clearSelectedFile()">Remove</button>
            </div>
          </div>
        </div>
      </div>

      <!-- MODE 2: LIVE CAMERA SCAN -->
      <div class="mode-pane" id="paneCamera">
        <div class="camera-frame">
          <video id="cameraVideo" autoplay playsinline muted poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='400'/%3E" style="display:none;"></video>
          <div class="camera-placeholder" id="cameraPlaceholder">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            <p id="camPlaceholderText">Tap “Start Camera” to scan blister pack or label</p>
          </div>
          <div class="reticle-box" aria-hidden="true">
            <div class="reticle-corner tl"></div>
            <div class="reticle-corner tr"></div>
            <div class="reticle-corner bl"></div>
            <div class="reticle-corner br"></div>
          </div>
        </div>
        <div class="camera-controls">
          <button type="button" class="ghost-btn" id="btnStartCam" onclick="startLiveCamera()">Start Camera</button>
          <button type="button" class="ghost-btn" id="btnSwitchCam" onclick="switchCamera()" style="display:none;">Flip Camera</button>
          <button type="button" class="ghost-btn" id="btnStopCam" onclick="stopLiveCamera()" style="display:none;">Stop</button>
        </div>
        <canvas id="cameraCanvas" style="display:none;"></canvas>
      </div>

      <!-- MODE 3: TEXT / REGISTRY LOOKUP -->
      <div class="mode-pane" id="paneText">
        <div class="field-group">
          <label class="field-label" for="txtMedName" id="lblMedName">Medicine / Brand Name *</label>
          <input type="text" class="field-input" id="txtMedName" placeholder="e.g. Dolo 650, Augmentin 625, Crocin">
        </div>
        <div class="field-row-2">
          <div class="field-group">
            <label class="field-label" for="txtBatch">Batch / Lot Number (optional)</label>
            <input type="text" class="field-input" id="txtBatch" placeholder="e.g. DL2024">
          </div>
          <div class="field-group">
            <label class="field-label" for="txtExpiry">Expiry Date (optional)</label>
            <input type="text" class="field-input" id="txtExpiry" placeholder="MM/YYYY">
          </div>
        </div>
      </div>

      <button type="button" class="btn-primary" id="btnVerifyMain" onclick="handlePrimaryVerify()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
        <span id="btnVerifyText">Verify Medicine</span>
      </button>

      <!-- RECENT CHECKS -->
      <div class="history-card">
        <div class="history-header">
          <span style="font-size:13px; font-weight:700; color:var(--color-charcoal-hero);" id="lblRecentScans">Recent Checks</span>
          <button type="button" class="ghost-btn" style="min-height:26px; font-size:11px;" onclick="clearHistoryList()">Clear</button>
        </div>
        <div class="history-list" id="historyFeed"></div>
      </div>
    </div>
  </section>

  <!-- RIGHT COLUMN: VERIFICATION RESULT & DIAGNOSTICS -->
  <section class="card-panel" aria-label="Verification Result">
    <!-- Empty Initial State -->
    <div class="card-pad" id="emptyWrap">
      <div class="empty-result-state" id="emptyResultState">
        <div class="empty-result-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
        </div>
        <p class="empty-result-title" id="emptyTitle">Ready for Verification</p>
        <p class="empty-result-desc" id="emptyDesc">Upload a medicine photo, capture using Live Scan, or enter the medicine name to check authenticity against the CDSCO/NPPA database.</p>
      </div>
    </div>

    <!-- Real Verification Result Content -->
    <div class="result-content" id="resultContent">
      <!-- Dark Charcoal-Forest Header Card (from Amoxiciline DX2 screen) -->
      <div class="dark-hero-header">
        <div class="dark-hero-top">
          <div>
            <h2 class="result-med-name" id="resMedName">Medicine</h2>
            <p class="result-med-sub" id="resMedSub">Manufacturer details</p>
            <span class="status-pill verified" id="resStatusPill">Genuine · Verified</span>
          </div>
          <button type="button" class="hero-listen-btn" onclick="speakResult()" title="Listen to verification result">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            <span id="lblSpeakBtn">Listen</span>
          </button>
        </div>
      </div>

      <div class="card-pad">
        <!-- CONDITIONAL COMPLAINT REDIRECT: ONLY SHOWN WHEN COUNTERFEIT / BANNED / EXPIRED / SUSPICIOUS -->
        <div class="complaint-redirect-box" id="counterfeitComplaintAlert">
          <p class="complaint-alert-title" id="alertTitleText">Counterfeit or Hazard Detected</p>
          <p class="complaint-alert-desc" id="alertDescText">This medicine failed verification or is expired. Report this batch to regulatory authorities.</p>
          <button type="button" class="complaint-action-btn" id="btnOpenComplaint" onclick="openComplaintModal()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>File Official Complaint</span>
          </button>
        </div>

        <!-- Structured Diagnostics Table -->
        <table class="diag-table">
          <tbody>
            <tr><td class="diag-key">Status Reason</td><td class="diag-val" id="tblReason">-</td></tr>
            <tr><td class="diag-key">Manufacturer</td><td class="diag-val" id="tblManufacturer">-</td></tr>
            <tr><td class="diag-key">Composition</td><td class="diag-val" id="tblComposition">-</td></tr>
            <tr><td class="diag-key">Batch / Lot No.</td><td class="diag-val is-mono" id="tblBatch">-</td></tr>
            <tr><td class="diag-key">Mfg Date</td><td class="diag-val is-mono" id="tblMfg">-</td></tr>
            <tr><td class="diag-key">Expiry Date</td><td class="diag-val is-mono" id="tblExp">-</td></tr>
            <tr><td class="diag-key">Detection Method</td><td class="diag-val" id="tblMethod">-</td></tr>
          </tbody>
        </table>

        <!-- AI Follow-up Q&A -->
        <div class="ai-followup-box">
          <p class="ai-followup-title">Tips, Notes &amp; AI Assistant</p>
          <div class="chat-log" id="chatLog"></div>
          <div class="chat-form-row">
            <input type="text" class="field-input" id="chatInputField" placeholder="Ask about dosage, side effects, or safety…">
            <button type="button" class="ghost-btn" id="chatSendBtn" onclick="submitChat()">Ask</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>

<!-- GOVERNMENT COMPLAINT MODAL (Triggered ONLY from Counterfeit/Hazard Alert) -->
<div class="modal-backdrop" id="complaintModal">
  <div class="modal-box">
    <div class="modal-top">
      <h3 class="modal-title">Report to Government Authority</h3>
      <button type="button" class="ghost-btn" onclick="closeComplaintModal()">Close</button>
    </div>

    <div class="authority-pills">
      <button type="button" class="auth-pill is-active" onclick="setAuthority('Maha FDA', this)">Maharashtra FDA</button>
      <button type="button" class="auth-pill" onclick="setAuthority('CDSCO', this)">Central Drugs (CDSCO)</button>
      <button type="button" class="auth-pill" onclick="setAuthority('CPGRAMS', this)">Public Grievance</button>
      <button type="button" class="auth-pill" onclick="setAuthority('NPPA', this)">Pharma Samadhan</button>
    </div>

    <textarea class="dossier-textarea" id="complaintDossierText"></textarea>

    <label class="consent-row">
      <input type="checkbox" id="consentCheck" onchange="togglePortalBtn()">
      <span>I confirm these findings are accurate and want to proceed to the official government portal.</span>
    </label>

    <div class="modal-footer-btns">
      <button type="button" class="ghost-btn" onclick="copyDossier()">Copy Dossier</button>
      <button type="button" class="ghost-btn" id="btnLaunchPortal" disabled style="opacity:0.5;" onclick="launchOfficialPortal()">Open Official Portal ↗</button>
    </div>
  </div>
</div>

<!-- API HOST CONFIG MODAL -->
<div class="modal-backdrop" id="hostModal">
  <div class="modal-box" style="max-width:420px;">
    <div class="modal-top">
      <h3 class="modal-title">Backend API Host</h3>
      <button type="button" class="ghost-btn" onclick="closeHostModal()">Close</button>
    </div>
    <div class="field-group">
      <label class="field-label" for="hostUrlInput">FastAPI Endpoint URL</label>
      <input type="text" class="field-input" id="hostUrlInput" placeholder="http://localhost:8000">
    </div>
    <div class="modal-footer-btns">
      <button type="button" class="ghost-btn" onclick="saveHostConfig()">Save &amp; Reconnect</button>
    </div>
  </div>
</div>

<div class="toast-bar" id="toastBar"></div>

<script>
(() => {
  const DEFAULT_API = (window.location.protocol === 'http:' || window.location.protocol === 'https:')
    ? window.location.origin
    : 'http://localhost:8000';
  let API_BASE = localStorage.getItem('medverify_api_base') || DEFAULT_API;
  if (API_BASE.includes('localhost:8000') && window.location.hostname && window.location.hostname !== 'localhost') {
    API_BASE = window.location.origin;
  }

  let currentMode = 'upload';
  let currentLang = 'en';
  let selectedFile = null;
  let lastResult = null;
  let cameraStream = null;
  let facingMode = 'environment';
  let activeAuthority = 'Maha FDA';

  const AUTHORITIES = {
    'Maha FDA': { name: 'Maharashtra FDA', url: 'https://complaints.mahafda.in/' },
    'CDSCO': { name: 'CDSCO (Central Drugs Standard Control Organization)', url: 'https://cdsco.gov.in/' },
    'CPGRAMS': { name: 'CPGRAMS Public Grievance Portal', url: 'https://pgportal.gov.in/' },
    'NPPA': { name: 'NPPA Pharma Jan Samadhan', url: 'https://nppapricechetti.gov.in/' }
  };

  const I18N = {
    en: {
      brandSub: 'Medicine Authentication & Screening',
      stationTitle: 'Verify Medicine',
      stationSubtitle: 'Upload a packaging photo, scan with live camera, or search by medicine name.',
      tabUpload: 'Upload',
      tabCamera: 'Live Scan',
      tabText: 'Text',
      dropTitle: 'Drop medicine packaging photo or click to browse',
      verifyBtn: 'Verify Medicine',
      recent: 'Recent Checks',
      emptyTitle: 'Ready for Verification',
      emptyDesc: 'Upload a medicine photo, capture using Live Scan, or enter the medicine name to check authenticity against the CDSCO/NPPA database.',
      speak: 'Listen'
    },
    hi: {
      brandSub: 'दवा प्रमाणीकरण और जांच प्रणाली',
      stationTitle: 'दवा की जांच करें',
      stationSubtitle: 'पैकेजिंग की फोटो अपलोड करें, लाइव कैमरे से स्कैन करें, या दवा का नाम लिखें।',
      tabUpload: 'अपलोड',
      tabCamera: 'लाइव स्कैन',
      tabText: 'टेक्स्ट',
      dropTitle: 'दवा की फोटो यहाँ डालें या चुनने के लिए क्लिक करें',
      verifyBtn: 'दवा सत्यापित करें',
      recent: 'हाल की जांच',
      emptyTitle: 'जांच के लिए तैयार',
      emptyDesc: 'असली या नकली दवा की जांच के लिए फोटो अपलोड करें, कैमरा स्कैन करें, या दवा का नाम दर्ज करें।',
      speak: 'सुनें'
    },
    mr: {
      brandSub: 'औषध पडताळणी आणि तपासणी प्रणाली',
      stationTitle: 'औषध तपासा',
      stationSubtitle: 'औषधाचा फोटो अपलोड करा, थेट कॅमेऱ्याने स्कॅन करा किंवा औषधाचे नाव लिहा.',
      tabUpload: 'अपलोड',
      tabCamera: 'लाइव्ह स्कॅन',
      tabText: 'मजकूर',
      dropTitle: 'औषधाचा फोटो येथे टाका किंवा निवडण्यासाठी क्लिक करा',
      verifyBtn: 'औषध तपासा',
      recent: 'मागील तपासण्या',
      emptyTitle: 'तपासणीसाठी सज्ज',
      emptyDesc: 'औषधाची सत्यता तपासण्यासाठी फोटो अपलोड करा, कॅमेरा वापरा किंवा औषधाचे नाव लिहा.',
      speak: 'ऐका'
    }
  };

  const $ = (id) => document.getElementById(id);

  function showToast(msg) {
    const t = $('toastBar');
    t.textContent = msg;
    t.classList.add('is-visible');
    setTimeout(() => t.classList.remove('is-visible'), 3000);
  }

  async function checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        $('apiDot').classList.remove('is-down');
        $('apiStatusText').textContent = 'API Connected';
      } else {
        throw new Error();
      }
    } catch {
      $('apiDot').classList.add('is-down');
      $('apiStatusText').textContent = 'API Offline';
    }
  }

  function setLanguage(lang) {
    currentLang = lang;
    ['en', 'hi', 'mr'].forEach((l) => {
      $('lang-' + l).classList.toggle('is-active', l === lang);
    });
    const t = I18N[lang];
    $('brandSubText').textContent = t.brandSub;
    $('stationTitle').textContent = t.stationTitle;
    $('stationSubtitle').textContent = t.stationSubtitle;
    $('lblTabUpload').textContent = t.tabUpload;
    $('lblTabCamera').textContent = t.tabCamera;
    $('lblTabText').textContent = t.tabText;
    $('dropTitleText').textContent = t.dropTitle;
    $('btnVerifyText').textContent = t.verifyBtn;
    $('lblRecentScans').textContent = t.recent;
    $('emptyTitle').textContent = t.emptyTitle;
    $('emptyDesc').textContent = t.emptyDesc;
    $('lblSpeakBtn').textContent = t.speak;
  }

  function switchMode(mode) {
    currentMode = mode;
    $('tabUpload').classList.toggle('is-active', mode === 'upload');
    $('tabCamera').classList.toggle('is-active', mode === 'camera');
    $('tabText').classList.toggle('is-active', mode === 'text');

    $('paneUpload').classList.toggle('is-active', mode === 'upload');
    $('paneCamera').classList.toggle('is-active', mode === 'camera');
    $('paneText').classList.toggle('is-active', mode === 'text');

    if (mode !== 'camera') {
      stopLiveCamera();
    }
  }

  function triggerFileSelect() {
    $('fileInput').click();
  }

  function handleSelectedFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      showToast('Please select a valid image file.');
      return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      $('previewImg').src = e.target.result;
      $('previewName').textContent = file.name;
      $('previewSize').textContent = `${(file.size / 1024).toFixed(1)} KB`;
      $('previewCard').classList.add('is-visible');
    };
    reader.readAsDataURL(file);
  }

  function clearSelectedFile() {
    selectedFile = null;
    $('fileInput').value = '';
    $('previewCard').classList.remove('is-visible');
  }

  const dz = $('dropZone');
  dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('is-dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('is-dragover'));
  dz.addEventListener('drop', (e) => {
    e.preventDefault();
    dz.classList.remove('is-dragover');
    if (e.dataTransfer.files[0]) handleSelectedFile(e.dataTransfer.files[0]);
  });
  $('fileInput').addEventListener('change', (e) => {
    if (e.target.files[0]) handleSelectedFile(e.target.files[0]);
  });

  async function startLiveCamera() {
    try {
      if (cameraStream) stopLiveCamera();
      cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode } });
      const video = $('cameraVideo');
      video.srcObject = cameraStream;
      video.style.display = 'block';
      $('cameraPlaceholder').style.display = 'none';
      $('btnSwitchCam').style.display = 'inline-flex';
      $('btnStopCam').style.display = 'inline-flex';
      $('btnStartCam').textContent = 'Restart Camera';
    } catch {
      showToast('Camera permission denied or unavailable.');
    }
  }

  function stopLiveCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach((t) => t.stop());
      cameraStream = null;
    }
    $('cameraVideo').style.display = 'none';
    $('cameraPlaceholder').style.display = 'block';
    $('btnSwitchCam').style.display = 'none';
    $('btnStopCam').style.display = 'none';
    $('btnStartCam').textContent = 'Start Camera';
  }

  function switchCamera() {
    facingMode = facingMode === 'environment' ? 'user' : 'environment';
    startLiveCamera();
  }

  async function handlePrimaryVerify() {
    if (currentMode === 'text') {
      await executeTextLookup();
      return;
    }

    if (currentMode === 'camera') {
      if (!cameraStream) {
        await startLiveCamera();
        return;
      }
      const video = $('cameraVideo');
      const canvas = $('cameraCanvas');
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      canvas.getContext('2d').drawImage(video, 0, 0);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
      selectedFile = new File([blob], 'live_camera_scan.jpg', { type: 'image/jpeg' });
    }

    if (!selectedFile) {
      showToast('Please upload a photo or capture via Live Scan.');
      return;
    }

    await executeImageVerification(selectedFile);
  }

  async function executeImageVerification(file) {
    const btn = $('btnVerifyMain');
    btn.disabled = true;
    $('btnVerifyText').textContent = 'Scanning…';

    const fd = new FormData();
    fd.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/verify/image?explain=true`, {
        method: 'POST',
        body: fd
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Verification failed');
      renderResult(data);
    } catch (err) {
      showToast('Error: ' + err.message);
    } finally {
      btn.disabled = false;
      $('btnVerifyText').textContent = I18N[currentLang].verifyBtn;
    }
  }

  async function executeTextLookup(overrideName, overrideBatch) {
    const medName = overrideName || $('txtMedName').value.trim();
    const batch = overrideBatch !== undefined ? overrideBatch : $('txtBatch').value.trim();
    const exp = $('txtExpiry').value.trim();

    if (!medName) {
      showToast('Please enter a medicine name.');
      return;
    }

    const btn = $('btnVerifyMain');
    btn.disabled = true;
    $('btnVerifyText').textContent = 'Checking Registry…';

    try {
      const res = await fetch(`${API_BASE}/verify/text?explain=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medicine_name: medName,
          batch_number: batch || null,
          expiry_date: exp || null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Lookup failed');
      renderResult({ database_verification: data });
    } catch (err) {
      showToast('Lookup error: ' + err.message);
    } finally {
      btn.disabled = false;
      $('btnVerifyText').textContent = I18N[currentLang].verifyBtn;
    }
  }

  function renderResult(data) {
    lastResult = data;
    const dbr = data.database_verification || data;
    const rawStatus = (dbr.status || 'UNVERIFIED').toUpperCase();
    const isExpired = Boolean(dbr.is_expired);

    const isGenuine = rawStatus === 'GENUINE' && !isExpired;
    const isCounterfeitOrHazard = rawStatus === 'COUNTERFEIT' || rawStatus === 'BANNED' || rawStatus === 'SUSPICIOUS' || isExpired;

    $('emptyWrap').style.display = 'none';
    $('resultContent').classList.add('is-visible');

    const pill = $('resStatusPill');
    if (isGenuine) {
      pill.className = 'status-pill verified';
      pill.textContent = 'Genuine · Verified';
    } else if (isCounterfeitOrHazard) {
      pill.className = 'status-pill suspicious';
      pill.textContent = isExpired ? 'Expired · Do Not Consume' : `${rawStatus} · Alert`;
    } else {
      pill.className = 'status-pill inconclusive';
      pill.textContent = 'Unverified · Insufficient Records';
    }

    const medName = dbr.matched_name || dbr.medicine || 'Unknown Medicine';
    $('resMedName').textContent = medName;
    $('resMedSub').textContent = dbr.company ? `Manufacturer: ${dbr.company}` : 'Manufacturer not found in registry';

    // Show Government Complaint redirect ONLY IF Counterfeit / Banned / Suspicious / Expired
    const alertBox = $('counterfeitComplaintAlert');
    if (isCounterfeitOrHazard) {
      alertBox.classList.add('is-visible');
      $('alertTitleText').textContent = isExpired
        ? 'Expired Medicine Hazard Detected'
        : 'Counterfeit or Banned Medicine Detected';
      $('alertDescText').textContent = dbr.expiry_warning || dbr.reason || 'This medicine failed verification. Report this batch directly to government authorities.';
    } else {
      alertBox.classList.remove('is-visible');
    }

    $('tblReason').textContent = dbr.reason || '-';
    $('tblManufacturer').textContent = dbr.company || 'Not detected';
    $('tblComposition').textContent = (dbr.details && dbr.details.composition) ? dbr.details.composition : 'Not listed';
    $('tblBatch').textContent = dbr.batch_number || 'Not detected';
    $('tblMfg').textContent = dbr.mfg_date || 'Not detected';
    $('tblExp').textContent = dbr.expiry_status || dbr.expiry_date || 'Not detected';
    $('tblMethod').textContent = dbr.method || 'Database Match';

    const chatLog = $('chatLog');
    chatLog.innerHTML = '';
    if (dbr.ai_explanation && dbr.ai_explanation.explanation) {
      appendChat('assistant', dbr.ai_explanation.explanation);
    }

    addHistoryRecord({
      name: medName,
      batch: dbr.batch_number || 'No Batch',
      status: isExpired ? 'Expired' : (isGenuine ? 'Genuine' : rawStatus),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });

    refreshDossierText();
  }

  function speakResult() {
    if (!lastResult || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const dbr = lastResult.database_verification || lastResult;
    const med = dbr.matched_name || dbr.medicine || 'Medicine';
    const status = dbr.is_expired ? 'Expired' : (dbr.status || 'Unverified');
    const text = currentLang === 'hi'
      ? `${med} की जांच परिणाम: ${status}। ${dbr.reason || ''}`
      : currentLang === 'mr'
        ? `${med} तपासणी निकाल: ${status}. ${dbr.reason || ''}`
        : `Verification result for ${med}: ${status}. ${dbr.reason || ''}`;
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = currentLang === 'hi' ? 'hi-IN' : (currentLang === 'mr' ? 'mr-IN' : 'en-IN');
    window.speechSynthesis.speak(utt);
  }

  function appendChat(role, text) {
    const log = $('chatLog');
    const div = document.createElement('div');
    div.className = `chat-bubble ${role}`;
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  async function submitChat() {
    const inp = $('chatInputField');
    const q = inp.value.trim();
    if (!q) return;
    inp.value = '';
    appendChat('user', q);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: lastResult ? (lastResult.database_verification || lastResult) : {},
          question: q,
          language: currentLang
        })
      });
      const data = await res.json();
      appendChat('assistant', data.answer || data.response || 'No response available.');
    } catch {
      appendChat('assistant', 'Unable to reach AI assistant.');
    }
  }

  function addHistoryRecord(item) {
    let list = [];
    try { list = JSON.parse(localStorage.getItem('medverify_history_v3') || '[]'); } catch { list = []; }
    list.unshift(item);
    list = list.slice(0, 6);
    localStorage.setItem('medverify_history_v3', JSON.stringify(list));
    renderHistoryFeed();
  }

  function renderHistoryFeed() {
    const feed = $('historyFeed');
    let list = [];
    try { list = JSON.parse(localStorage.getItem('medverify_history_v3') || '[]'); } catch { list = []; }

    if (!list.length) {
      feed.innerHTML = '<p style="font-size:12px; color:var(--color-slate); margin:0;">No recent checks yet.</p>';
      return;
    }

    feed.innerHTML = list.map((it) => {
      const st = String(it.status).toUpperCase();
      const cls = st === 'GENUINE' ? 'verified'
        : (st === 'COUNTERFEIT' || st === 'BANNED' || st === 'EXPIRED' ? 'suspicious' : 'inconclusive');
      const safeName = String(it.name).replace(/'/g, "\\'");
      const safeBatch = it.batch !== 'No Batch' ? String(it.batch).replace(/'/g, "\\'") : '';
      return `
        <div class="history-row" onclick="executeTextLookup('${safeName}', '${safeBatch}')">
          <div>
            <p class="history-row-name">${it.name}</p>
            <p class="history-row-meta">${it.batch} &middot; ${it.time}</p>
          </div>
          <span class="status-pill ${cls}" style="font-size:10px; padding:2px 8px;">${it.status}</span>
        </div>`;
    }).join('');
  }

  function clearHistoryList() {
    localStorage.removeItem('medverify_history_v3');
    renderHistoryFeed();
  }

  function openComplaintModal() {
    refreshDossierText();
    $('complaintModal').classList.add('is-open');
  }

  function closeComplaintModal() {
    $('complaintModal').classList.remove('is-open');
  }

  function setAuthority(key, btn) {
    activeAuthority = key;
    document.querySelectorAll('.auth-pill').forEach((p) => p.classList.remove('is-active'));
    btn.classList.add('is-active');
    refreshDossierText();
  }

  function refreshDossierText() {
    const dbr = lastResult ? (lastResult.database_verification || lastResult) : {};
    const auth = AUTHORITIES[activeAuthority];
    const text = [
      `REGULATORY COMPLAINT DOSSIER: MEDVERIFY AI`,
      `Authority: ${auth.name} (${auth.url})`,
      `Date: ${new Date().toLocaleString()}`,
      ``,
      `1. MEDICINE DETAILS`,
      `- Medicine Name: ${dbr.matched_name || dbr.medicine || 'Unknown'}`,
      `- Manufacturer: ${dbr.company || 'Unknown'}`,
      `- Batch / Lot No.: ${dbr.batch_number || 'Not detected'}`,
      `- Expiry Date: ${dbr.expiry_status || dbr.expiry_date || 'Not detected'}`,
      `- Status: ${dbr.is_expired ? 'EXPIRED HAZARD' : (dbr.status || 'COUNTERFEIT')}`,
      ``,
      `2. EVIDENCE & REASON`,
      `- Reason: ${dbr.reason || 'Failed authenticity verification'}`,
      `- Attached File: ${selectedFile ? selectedFile.name : 'Text/OCR Check'}`,
      `- Optical Text: ${dbr.optical_text_extracted || 'N/A'}`
    ].join('\n');
    $('complaintDossierText').value = text;
  }

  function togglePortalBtn() {
    const checked = $('consentCheck').checked;
    const btn = $('btnLaunchPortal');
    btn.disabled = !checked;
    btn.style.opacity = checked ? '1' : '0.5';
  }

  function copyDossier() {
    navigator.clipboard.writeText($('complaintDossierText').value);
    showToast('Dossier copied to clipboard.');
  }

  function launchOfficialPortal() {
    window.open(AUTHORITIES[activeAuthority].url, '_blank', 'noopener');
  }

  function openHostModal() {
    $('hostUrlInput').value = API_BASE;
    $('hostModal').classList.add('is-open');
  }

  function closeHostModal() {
    $('hostModal').classList.remove('is-open');
  }

  function saveHostConfig() {
    const val = $('hostUrlInput').value.trim().replace(/\/$/, '');
    if (val) {
      API_BASE = val;
      localStorage.setItem('medverify_api_base', val);
      closeHostModal();
      checkHealth();
    }
  }

  $('chatInputField').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitChat();
  });

  Object.assign(window, {
    setLanguage, switchMode, triggerFileSelect, clearSelectedFile,
    startLiveCamera, stopLiveCamera, switchCamera, handlePrimaryVerify,
    executeTextLookup, speakResult, submitChat, clearHistoryList,
    openComplaintModal, closeComplaintModal, setAuthority, togglePortalBtn,
    copyDossier, launchOfficialPortal, openHostModal, closeHostModal, saveHostConfig
  });

  window.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    renderHistoryFeed();
  });
})();
</script>
</body>
</html>
'''

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        os.path.join(root, "frontend", "index.html"),
        os.path.join(root, "docs", "index.html"),
        os.path.join(root, "mobile-app", "www", "index.html"),
        os.path.join(root, "mobile-app", "android", "app", "src", "main", "assets", "public", "index.html"),
    ]

    for path in targets:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(UI_HTML.strip() + "\n")
        print(f"Updated {path}")


if __name__ == "__main__":
    main()
