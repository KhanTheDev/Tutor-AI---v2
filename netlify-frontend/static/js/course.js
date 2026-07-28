function getCourseId() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  return id ? Number(id) : null;
}

function showFlash(message, category = "success") {
  const list = document.getElementById("flashList");
  list.style.display = "block";
  list.innerHTML = `<div class="flash-item ${category}">${escapeHtml(message)}</div>`;
  setTimeout(() => {
    list.style.display = "none";
  }, 5000);
}

function statusBadgeClass(status) {
  return `status-badge status-${status}`;
}

function renderDocument(doc) {
  return `
    <div class="document-item" data-document-id="${doc.id}">
      <div>
        <div class="document-name">${escapeHtml(doc.original_filename)}</div>
        <div>
          <span class="${statusBadgeClass(doc.status)}">${doc.status}</span>
          <span class="document-meta">${doc.file_type.toUpperCase()}</span>
        </div>
        <div class="document-meta">Pages: ${doc.total_pages} &bull; Chunks: ${doc.total_chunks}</div>
      </div>
      <button type="button" class="btn-danger-link delete-document-btn" data-document-id="${doc.id}">Delete</button>
    </div>
  `;
}

function renderDocuments(documents) {
  const list = document.getElementById("documentList");
  const emptyMsg = document.getElementById("noDocumentsMsg");

  if (documents.length === 0) {
    list.innerHTML = "";
    emptyMsg.style.display = "block";
    return;
  }

  emptyMsg.style.display = "none";
  list.innerHTML = documents.map(renderDocument).join("");

  list.querySelectorAll(".delete-document-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const confirmed = window.confirm(
        "Delete this file? It'll be removed along with anything it taught the tutor."
      );
      if (!confirmed) return;

      const { ok, data } = await apiFetch(`/api/documents/${btn.dataset.documentId}`, {
        method: "DELETE",
      });
      if (ok) {
        loadCourse();
      } else {
        showFlash((data && data.error) || "Failed to delete document.", "danger");
      }
    });
  });
}

function scrollChatToBottom(container) {
  if (container) container.scrollTop = container.scrollHeight;
}

function buildSourceBadges(sources) {
  if (!sources || sources.length === 0) return "";

  const uniqueSources = [];
  const seen = new Set();
  sources.forEach((source) => {
    const key = `${source.document_name}|${source.page_number}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueSources.push(source);
    }
  });

  const badges = uniqueSources
    .map(
      (source) =>
        `<span class="source-badge">${escapeHtml(source.document_name)} &mdash; Page ${source.page_number}</span>`
    )
    .join("");

  return `<div class="message-sources"><strong>Sources:</strong>${badges}</div>`;
}

function appendChatMessage(container, role, content, sources = []) {
  const emptyState = container.querySelector("#chat-empty-state");
  if (emptyState) emptyState.remove();

  const wrapper = document.createElement("div");
  wrapper.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  const roleLabel = role === "user" ? "You" : "Tutor AI";
  bubble.innerHTML = `
    <div class="message-role">${roleLabel}</div>
    <div class="message-content">${escapeHtml(content)}</div>
    ${role === "assistant" ? buildSourceBadges(sources) : ""}
  `;

  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  scrollChatToBottom(container);
}

function renderMessages(messages) {
  const container = document.getElementById("chat-messages");
  if (messages.length === 0) {
    container.innerHTML = '<p class="panel-subtitle" id="chat-empty-state" style="margin-bottom: 0;">Upload something above, then ask your first question.</p>';
    return;
  }
  container.innerHTML = "";
  messages.forEach((m) => appendChatMessage(container, m.role, m.content, m.sources));
}

function showChatError(message) {
  const el = document.getElementById("chat-error");
  el.textContent = message;
  el.classList.remove("d-none");
}

function hideChatError() {
  const el = document.getElementById("chat-error");
  el.textContent = "";
  el.classList.add("d-none");
}

let currentCourseId = null;
let readyDocumentCount = 0;

async function loadCourse() {
  currentCourseId = getCourseId();

  if (!currentCourseId) {
    document.getElementById("courseName").textContent = "Course not found";
    showFlash("No course specified.", "danger");
    return;
  }

  const { ok, data } = await apiFetch(`/api/courses/${currentCourseId}`);

  if (!ok || !data || !data.success) {
    document.getElementById("courseName").textContent = "Course not found";
    document.getElementById("courseDesc").textContent = "This course doesn't exist or was deleted.";
    return;
  }

  const { course, documents, messages } = data;
  readyDocumentCount = course.ready_document_count;

  document.title = `${course.name} | Tutor AI Platform`;
  document.getElementById("pageTitle").textContent = `${course.name} | Tutor AI Platform`;
  document.getElementById("courseName").textContent = course.name;
  document.getElementById("courseDesc").textContent = course.description || "No description yet.";
  document.getElementById("courseDocCount").textContent =
    `${course.document_count} uploaded document${course.document_count !== 1 ? "s" : ""}`;
  document.getElementById("readyReadout").textContent =
    `${course.ready_document_count}/${course.document_count}`;

  renderDocuments(documents);
  renderMessages(messages);
}

document.addEventListener("DOMContentLoaded", () => {
  loadCourse();

  document.getElementById("deleteCourseBtn").addEventListener("click", async () => {
    const confirmed = window.confirm(
      "Delete this course? Everything in it goes too — there's no undo."
    );
    if (!confirmed) return;

    const { ok } = await apiFetch(`/api/courses/${currentCourseId}`, { method: "DELETE" });
    if (ok) {
      window.location.href = "index.html";
    } else {
      showFlash("Failed to delete course.", "danger");
    }
  });

  document.getElementById("upload-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const fileInput = form.querySelector('input[name="document"]');
    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append("document", fileInput.files[0]);

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    const { ok, data } = await apiFetch(`/api/courses/${currentCourseId}/upload`, {
      method: "POST",
      body: formData,
    });

    submitBtn.disabled = false;
    submitBtn.textContent = "Upload";
    form.reset();

    if (ok && data && data.success) {
      showFlash(`"${data.document.original_filename}" uploaded and processed successfully.`);
    } else {
      showFlash((data && data.error) || "Failed to process the uploaded document.", "danger");
    }
    loadCourse();
  });

  document.getElementById("clearChatBtn").addEventListener("click", async () => {
    const confirmed = window.confirm(
      "Clear the chat history? Your files stay put — just the messages go."
    );
    if (!confirmed) return;

    const { ok } = await apiFetch(`/api/courses/${currentCourseId}/clear-chat`, { method: "POST" });
    if (ok) {
      renderMessages([]);
    } else {
      showFlash("Failed to clear chat history.", "danger");
    }
  });

  const chatForm = document.getElementById("chat-form");
  const questionInput = document.getElementById("question-input");
  const askButton = document.getElementById("ask-button");
  const chatContainer = document.getElementById("chat-messages");
  let isSubmitting = false;

  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideChatError();

    const question = questionInput.value.trim();
    if (!question || isSubmitting) return;

    if (readyDocumentCount <= 0) {
      showChatError("Upload a file first — there's nothing to search yet.");
      return;
    }

    isSubmitting = true;
    askButton.disabled = true;
    questionInput.disabled = true;

    appendChatMessage(chatContainer, "user", question);
    questionInput.value = "";

    const loadingWrapper = document.createElement("div");
    loadingWrapper.className = "chat-message assistant-message loading-message";
    loadingWrapper.innerHTML = `
      <div class="message-bubble">
        <div class="message-role">Tutor AI</div>
        <div class="message-content">Thinking...</div>
      </div>
    `;
    chatContainer.appendChild(loadingWrapper);
    scrollChatToBottom(chatContainer);

    const { ok, data } = await apiFetch(`/api/courses/${currentCourseId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    loadingWrapper.remove();

    if (!ok || !data || !data.success) {
      showChatError((data && data.error) || "Couldn't get an answer. Try again.");
    } else {
      appendChatMessage(chatContainer, "assistant", data.answer, data.sources || []);
    }

    isSubmitting = false;
    askButton.disabled = false;
    questionInput.disabled = false;
    questionInput.focus();
  });
});
