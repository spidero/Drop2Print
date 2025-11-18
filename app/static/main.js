function setupDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const statusBox = document.getElementById("upload-status");
  if (!dropzone || !fileInput) return;

  const t = (key, vars = {}) => {
    const dict = window.I18N || {};
    let value = dict[key] || key;
    Object.entries(vars).forEach(([k, v]) => {
      value = value.replace(`{${k}}`, v);
    });
    return value;
  };

  const highlight = () => dropzone.classList.add("active");
  const unhighlight = () => dropzone.classList.remove("active");

  const handleFiles = (files) => {
    const validFiles = Array.from(files).filter((file) => file.type === "application/pdf");
    if (!validFiles.length) {
      statusBox.textContent = "PDF only.";
      return;
    }
    validFiles.forEach(async (file) => {
      statusBox.textContent = t("uploading", { filename: file.name });
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        if (!res.ok) throw new Error("Błąd wysyłki");
        const job = await res.json();
        statusBox.textContent = t("status", { id: job.id, filename: job.filename, status: job.status });
        refreshJobs();
      } catch (err) {
        statusBox.textContent = err.message;
      }
    });
  };

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      highlight();
    });
  });
  ["dragleave", "drop"].forEach((eventName) => dropzone.addEventListener(eventName, unhighlight));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  });

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => handleFiles(e.target.files));
}

async function refreshJobs() {
  const list = document.getElementById("jobs-list");
  if (!list) return;
  const dict = window.I18N || {};
  list.innerHTML = dict.loading || "Loading...";
  try {
    const res = await fetch("/api/jobs?limit=5");
    if (!res.ok) throw new Error("Nie udało się pobrać zadań");
    const jobs = await res.json();
    if (!jobs.length) {
      list.textContent = dict.jobs_empty || "No jobs.";
      return;
    }
    list.innerHTML = "";
    jobs.forEach((job) => {
      const li = document.createElement("li");
      li.textContent = `#${job.id} ${job.filename} – ${job.status}`;
      list.appendChild(li);
    });
  } catch (err) {
    list.textContent = err.message;
  }
}
