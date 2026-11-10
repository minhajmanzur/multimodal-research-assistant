const fileInput = document.querySelector("#file-input");
const dropZone = document.querySelector("#drop-zone");
const sourceList = document.querySelector("#source-list");
const sourceCount = document.querySelector("#source-count");
const welcome = document.querySelector("#welcome");
const messages = document.querySelector("#message-list");
const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question-input");
const sendButton = document.querySelector("#send-button");
const progress = document.querySelector("#upload-progress");
const progressLabel = document.querySelector("#progress-label");
const toast = document.querySelector("#toast");
let documents = [];
let toastTimer;

const icons = { pdf: "PDF", image: "IMG", audio: "AUD", video: "VID", spreadsheet: "XLS", text: "TXT" };

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3400);
}

function setBusy(busy, label = "Reading your sources…") {
  progress.hidden = !busy;
  progressLabel.textContent = label;
  sendButton.disabled = busy;
}

function renderSources() {
  sourceCount.textContent = documents.length;
  document.querySelector("#composer-status").textContent = documents.length
    ? `${documents.length} source${documents.length === 1 ? "" : "s"} ready to search`
    : "Your sources will appear here as context";
  if (!documents.length) {
    sourceList.innerHTML = '<div class="empty-source">Your library is ready.<br />Drop in a few files to begin.</div>';
    return;
  }
  sourceList.innerHTML = documents.map((doc) => {
    const type = doc.types?.[0] || "text";
    const extension = doc.name.split(".").pop().toLowerCase();
    const extensionTypes = {
      pdf: "pdf", png: "image", jpg: "image", jpeg: "image", webp: "image", gif: "image",
      mp3: "audio", wav: "audio", m4a: "audio", ogg: "audio", webm: "audio",
      mp4: "video", mov: "video", m4v: "video", avi: "video", mkv: "video",
      xlsx: "spreadsheet", xlsm: "spreadsheet", xltx: "spreadsheet", xltm: "spreadsheet",
      txt: "text", md: "text",
    };
    const iconType = extensionTypes[extension] || type;
    const icon = iconType === "spreadsheet" ? icons.spreadsheet : iconType === "image" ? icons.image : iconType === "video" ? icons.video : iconType === "audio" ? icons.audio : iconType === "text" ? icons.text : icons.pdf;
    return `<div class="source-item"><span class="file-type">${icon}</span><span class="source-name" title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)}</span><button class="remove-source" data-remove="${doc.id}" aria-label="Remove ${escapeHtml(doc.name)}">×</button></div>`;
  }).join("");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

async function refreshDocuments() {
  const response = await fetch("/api/documents");
  if (!response.ok) throw new Error("Couldn't load your sources.");
  const data = await response.json();
  documents = data.documents;
  renderSources();
}

async function uploadFiles(files) {
  const selected = [...files];
  if (!selected.length) return;
  setBusy(true, `Reading ${selected.length} source${selected.length === 1 ? "" : "s"}…`);
  const formData = new FormData();
  selected.forEach((file) => formData.append("files", file));
  try {
    const response = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Upload failed.");
    await refreshDocuments();
    welcome.hidden = true;
    showToast(`${data.documents.length} source${data.documents.length === 1 ? "" : "s"} added to your room`);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
    fileInput.value = "";
  }
}

function addMessage(role, text, metadata = {}) {
  const row = document.createElement("div");
  row.className = `message ${role}`;
  const avatar = role === "user" ? "R" : "✳";
  const label = role === "user" ? "You" : "Gather";
  const citations = metadata.sources?.length
    ? `<div class="source-citations">${metadata.sources.map((source) => `<span class="citation">${escapeHtml(source.filename)} · ${escapeHtml(source.locator)}</span>`).join("")}</div>`
    : "";
  row.innerHTML = `<div class="message-avatar">${avatar}</div><div class="message-content"><div class="message-label">${label}</div><div class="message-text"></div>${citations}${metadata.mode ? `<div class="answer-mode">${escapeHtml(metadata.mode)}</div>` : ""}</div>`;
  row.querySelector(".message-text").textContent = text;
  messages.append(row);
  row.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function ask(question) {
  if (question.trim().length < 2) return;
  if (!documents.length) {
    showToast("Add at least one source first");
    return;
  }
  welcome.hidden = true;
  questionInput.value = "";
  questionInput.style.height = "auto";
  addMessage("user", question.trim());
  setBusy(true, "Looking across your sources…");
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.trim() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Couldn't answer that question.");
    addMessage("assistant", data.answer, { sources: data.sources, mode: data.mode });
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    setBusy(false);
    questionInput.focus();
  }
}

document.querySelector("#browse-files").addEventListener("click", () => fileInput.click());
document.querySelector("#attach-button").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => uploadFiles(fileInput.files));
dropZone.addEventListener("dragover", (event) => { event.preventDefault(); dropZone.classList.add("dragging"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", (event) => { event.preventDefault(); dropZone.classList.remove("dragging"); uploadFiles(event.dataTransfer.files); });
form.addEventListener("submit", (event) => { event.preventDefault(); ask(questionInput.value); });
questionInput.addEventListener("input", () => { questionInput.style.height = "auto"; questionInput.style.height = `${Math.min(questionInput.scrollHeight, 130)}px`; });
questionInput.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
document.querySelectorAll(".suggestion").forEach((button) => button.addEventListener("click", () => { questionInput.value = button.dataset.prompt; questionInput.focus(); if (documents.length) form.requestSubmit(); else showToast("Add your sources, then try this question"); }));
document.querySelector("#new-session").addEventListener("click", () => { messages.replaceChildren(); welcome.hidden = false; questionInput.value = ""; });
sourceList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-remove]");
  if (!button) return;
  try {
    const response = await fetch(`/api/documents/${button.dataset.remove}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Couldn't remove that source.");
    await refreshDocuments();
    if (!documents.length) welcome.hidden = false;
  } catch (error) { showToast(error.message); }
});

async function initialize() {
  try {
    const health = await fetch("/api/health").then((response) => response.json());
    const pill = document.querySelector("#connection-pill");
    pill.classList.add("ready");
    document.querySelector("#connection-label").textContent = health.ai_configured ? "AI connected" : "Local mode";
    await refreshDocuments();
    if (documents.length) welcome.hidden = true;
  } catch {
    document.querySelector("#connection-label").textContent = "API offline";
  }
}

initialize();
