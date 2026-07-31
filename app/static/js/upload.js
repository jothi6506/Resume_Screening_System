/**
 * Resume upload — drag & drop, file list preview
 */
(function () {
    const dropzone = document.getElementById("uploadDropzone");
    const fileInput = document.getElementById("resumeFiles");
    const fileList = document.getElementById("fileList");
    const browseBtn = document.getElementById("browseBtn");
    const clearBtn = document.getElementById("clearFiles");
    const submitBtn = document.getElementById("uploadSubmit");

    if (!dropzone || !fileInput) return;

    let selectedFiles = [];

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    function syncInput() {
        const dt = new DataTransfer();
        selectedFiles.forEach(function (f) { dt.items.add(f); });
        fileInput.files = dt.files;
        submitBtn.disabled = selectedFiles.length === 0;
        clearBtn.disabled = selectedFiles.length === 0;
    }

    function renderList() {
        fileList.innerHTML = "";
        selectedFiles.forEach(function (file, index) {
            const item = document.createElement("div");
            item.className = "upload-file-item";
            item.innerHTML =
                '<i class="bi bi-file-earmark-pdf-fill"></i>' +
                '<span class="file-name">' + file.name + "</span>" +
                '<span class="file-size">' + formatSize(file.size) + "</span>" +
                '<button type="button" class="file-remove" aria-label="Remove">&times;</button>';
            item.querySelector(".file-remove").addEventListener("click", function (e) {
                e.stopPropagation();
                selectedFiles.splice(index, 1);
                renderList();
                syncInput();
            });
            fileList.appendChild(item);
        });
        syncInput();
    }

    function addFiles(files) {
        Array.from(files).forEach(function (file) {
            if (file.name.toLowerCase().endsWith(".pdf")) {
                selectedFiles.push(file);
            }
        });
        renderList();
    }

    dropzone.addEventListener("click", function () { fileInput.click(); });
    browseBtn?.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        selectedFiles = Array.from(fileInput.files);
        renderList();
    });

    dropzone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        addFiles(e.dataTransfer.files);
    });

    clearBtn?.addEventListener("click", function () {
        selectedFiles = [];
        fileInput.value = "";
        renderList();
    });
})();
