const QUICK_SUBJECTS = [
  "Mathematics",
  "Biology",
  "Chemistry",
  "Physics",
  "History",
  "English",
  "Computer Science",
];

function renderQuickSubjects() {
  const container = document.getElementById("quickSubjects");
  container.innerHTML = QUICK_SUBJECTS.map(
    (subject) => `
      <form class="quick-subject-form" data-subject="${escapeHtml(subject)}">
        <button type="submit" class="subject-chip">${escapeHtml(subject)}</button>
      </form>
    `
  ).join("");

  container.querySelectorAll(".quick-subject-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await createCourse(form.dataset.subject, "");
    });
  });
}

function renderCourseCard(course) {
  const desc = course.description ? escapeHtml(course.description) : "No description provided.";
  const docLabel = `${course.document_count} document${course.document_count !== 1 ? "s" : ""}`;
  return `
    <div class="course-card" data-course-id="${course.id}">
      <h3 class="course-card-name">${escapeHtml(course.name)}</h3>
      <p class="course-card-desc">${desc}</p>
      <div class="course-card-meta"><span>${docLabel}</span></div>
      <div class="course-card-actions">
        <a href="course.html?id=${course.id}" class="btn-primary">Open Course</a>
        <button type="button" class="btn-danger-link delete-course-btn" data-course-id="${course.id}">Delete</button>
      </div>
    </div>
  `;
}

function renderCourses(courses) {
  const grid = document.getElementById("coursesGrid");
  const empty = document.getElementById("coursesEmpty");
  const selectBar = document.getElementById("courseSelectBar");
  const select = document.getElementById("courseSelect");

  if (courses.length === 0) {
    grid.style.display = "none";
    selectBar.style.display = "none";
    empty.style.display = "block";
    grid.innerHTML = "";
    return;
  }

  empty.style.display = "none";
  grid.style.display = "grid";
  selectBar.style.display = "block";

  grid.innerHTML = courses.map(renderCourseCard).join("");
  select.innerHTML =
    '<option value="">Jump to a course&hellip;</option>' +
    courses.map((c) => `<option value="course.html?id=${c.id}">${escapeHtml(c.name)}</option>`).join("");

  grid.querySelectorAll(".delete-course-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const confirmed = window.confirm(
        "Delete this course? Everything in it goes too — there's no undo."
      );
      if (!confirmed) return;

      const { ok } = await apiFetch(`/api/courses/${btn.dataset.courseId}`, { method: "DELETE" });
      if (ok) {
        loadCourses();
      } else {
        showFlash("Failed to delete course.", "danger");
      }
    });
  });
}

function showFlash(message, category = "success") {
  const list = document.getElementById("flashList");
  list.style.display = "block";
  list.innerHTML = `<div class="flash-item ${category}">${escapeHtml(message)}</div>`;
  setTimeout(() => {
    list.style.display = "none";
  }, 5000);
}

async function createCourse(name, description) {
  if (!name.trim()) {
    showFlash("Course name is required.", "danger");
    return;
  }

  const { ok, data } = await apiFetch("/api/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });

  if (ok && data && data.success) {
    window.location.href = `course.html?id=${data.course.id}`;
  } else {
    showFlash((data && data.error) || "Failed to create course.", "danger");
  }
}

async function loadCourses() {
  const { ok, data } = await apiFetch("/api/courses");

  if (!ok || !data || !data.success) {
    showFlash("Couldn't load courses. Is the API reachable?", "danger");
    return;
  }

  const courses = data.courses;
  renderCourses(courses);

  const courseCountEl = document.getElementById("courseCountMetric");
  const docCountEl = document.getElementById("docCountMetric");
  document.getElementById("courseCountLabel").textContent = courses.length === 1 ? "Course" : "Courses";

  const readyDocs = courses.reduce((sum, c) => sum + c.ready_document_count, 0);
  animateCount(courseCountEl, courses.length);
  animateCount(docCountEl, 78 + readyDocs);
}

document.addEventListener("DOMContentLoaded", () => {
  renderQuickSubjects();
  loadCourses();

  document.getElementById("new-course-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const name = form.elements.name.value;
    const description = form.elements.description.value;
    await createCourse(name, description);
  });

  document.getElementById("courseSelect").addEventListener("change", (event) => {
    if (event.target.value) {
      window.location.href = event.target.value;
    }
  });
});
