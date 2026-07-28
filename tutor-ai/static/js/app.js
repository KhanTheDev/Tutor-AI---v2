/**
 * Tutor AI Platform frontend interactions.
 */

function scrollChatToBottom(container) {
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function buildSourceBadges(sources) {
    if (!sources || sources.length === 0) {
        return "";
    }

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

    return `<div class="message-sources mt-2"><strong>Sources:</strong>${badges}</div>`;
}

function appendChatMessage(container, role, content, sources = []) {
    const emptyState = container.querySelector("#chat-empty-state");
    if (emptyState) {
        emptyState.remove();
    }

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

function showChatError(errorElement, message) {
    if (!errorElement) return;
    errorElement.textContent = message;
    errorElement.classList.remove("d-none");
}

function hideChatError(errorElement) {
    if (!errorElement) return;
    errorElement.textContent = "";
    errorElement.classList.add("d-none");
}

function initCourseChat() {
    const chatContainer = document.getElementById("chat-messages");
    const chatForm = document.getElementById("chat-form");
    const questionInput = document.getElementById("question-input");
    const askButton = document.getElementById("ask-button");
    const errorElement = document.getElementById("chat-error");
    const clearChatForm = document.getElementById("clear-chat-form");

    if (!chatContainer || !chatForm || !questionInput || !askButton) {
        return;
    }

    const courseId = chatContainer.dataset.courseId;
    const readyDocuments = Number(chatContainer.dataset.readyDocuments || "0");
    let isSubmitting = false;

    scrollChatToBottom(chatContainer);

    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideChatError(errorElement);

        const question = questionInput.value.trim();
        if (!question || isSubmitting) {
            return;
        }

        if (readyDocuments <= 0) {
            showChatError(
                errorElement,
                "Upload a file first — there's nothing to search yet."
            );
            return;
        }

        isSubmitting = true;
        askButton.disabled = true;
        questionInput.disabled = true;

        appendChatMessage(chatContainer, "user", question);
        questionInput.value = "";

        const loadingWrapper = document.createElement("div");
        loadingWrapper.className = "chat-message assistant-message loading-message";
        loadingWrapper.id = "chat-loading-message";
        loadingWrapper.innerHTML = `
            <div class="message-bubble">
                <div class="message-role">Tutor AI</div>
                <div class="message-content">Thinking...</div>
            </div>
        `;
        chatContainer.appendChild(loadingWrapper);
        scrollChatToBottom(chatContainer);

        try {
            const response = await fetch(`/api/courses/${courseId}/ask`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ question }),
            });

            const data = await response.json();
            loadingWrapper.remove();

            if (!response.ok || !data.success) {
                showChatError(errorElement, data.error || "Couldn't get an answer. Try again.");
                return;
            }

            appendChatMessage(chatContainer, "assistant", data.answer, data.sources || []);
        } catch (error) {
            loadingWrapper.remove();
            showChatError(errorElement, "Something went wrong. Check your connection and try again.");
        } finally {
            isSubmitting = false;
            askButton.disabled = false;
            questionInput.disabled = false;
            questionInput.focus();
        }
    });

    if (clearChatForm) {
        clearChatForm.addEventListener("submit", (event) => {
            const confirmed = window.confirm(
                "Clear the chat history? Your files stay put — just the messages go."
            );
            if (!confirmed) {
                event.preventDefault();
            }
        });
    }
}

function initDeleteConfirmations() {
    document.querySelectorAll(".delete-document-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const confirmed = window.confirm(
                "Delete this file? It'll be removed along with anything it taught the tutor."
            );
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll(".delete-course-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const confirmed = window.confirm(
                "Delete this course? Everything in it goes too — there's no undo."
            );
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initDeleteConfirmations();
});
