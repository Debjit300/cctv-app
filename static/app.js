// CCTV Dashboard Controller
let currentPage = 1;
const CAMS_PER_PAGE = 4;
let camerasData = [];

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initClock();
  fetchCameras();
  
  // Keyboard navigation for CCTV pagination
  window.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") prevPage();
    if (e.key === "ArrowRight") nextPage();
    if (e.key === "Escape") closeModal();
  });
});

// Live UTC/Local CCTV Clock
function initClock() {
  const clockEl = document.getElementById("live-clock");
  const update = () => {
    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];
    const dateStr = now.toISOString().split("T")[0];
    clockEl.innerText = `${dateStr} ${timeStr} IST`;
  };
  update();
  setInterval(update, 1000);
}

// Fetch all 9 camera definitions
async function fetchCameras() {
  try {
    const res = await fetch("/api/cameras");
    const data = await res.json();
    camerasData = data.cameras || [];
    renderCurrentPage();
  } catch (err) {
    console.error("Failed to load cameras:", err);
  }
}

// Switch pages (Page 1: CAM 1-4, Page 2: CAM 5-8, Page 3: CAM 9)
function switchPage(pageNum) {
  currentPage = pageNum;
  
  // Update button states
  document.querySelectorAll(".page-btn").forEach((btn, idx) => {
    btn.classList.toggle("active", idx + 1 === pageNum);
  });
  
  renderCurrentPage();
}

function prevPage() {
  if (currentPage > 1) switchPage(currentPage - 1);
  else switchPage(3);
}

function nextPage() {
  if (currentPage < 3) switchPage(currentPage + 1);
  else switchPage(1);
}

// Render the 4 cameras on current page
function renderCurrentPage() {
  const gridEl = document.getElementById("cctv-grid");
  gridEl.innerHTML = "";
  
  const startIdx = (currentPage - 1) * CAMS_PER_PAGE;
  const endIdx = startIdx + CAMS_PER_PAGE;
  const pageCams = camerasData.slice(startIdx, endIdx);
  
  // Page indicator update
  const totalCams = camerasData.length;
  const indText = document.getElementById("page-indicator-text");
  if (pageCams.length > 0) {
    const firstCam = pageCams[0].id;
    const lastCam = pageCams[pageCams.length - 1].id;
    indText.innerText = `PAGE ${currentPage} OF 3 (${firstCam} - ${lastCam})`;
  }

  // Adjust grid layout if single item (Page 3)
  if (pageCams.length === 1) {
    gridEl.classList.add("single-item");
  } else {
    gridEl.classList.remove("single-item");
  }
  
  document.getElementById("stat-active-grid").innerText = `${pageCams.length} STREAMS`;

  pageCams.forEach(cam => {
    const card = document.createElement("div");
    card.className = `cctv-card ${cam.has_violations ? "violation-active" : ""}`;
    card.id = `card-${cam.id}`;
    
    card.innerHTML = `
      <!-- Top HUD -->
      <div class="card-top-hud">
        <div class="cam-badge">
          <span class="cam-id">${cam.id}</span>
          <span class="cam-loc">${cam.name}</span>
        </div>
        <div class="cam-fps-badge">5 FPS ● LOOP</div>
      </div>

      <!-- Video Stream Area -->
      <div class="card-video-wrap" onclick="openModal('${cam.id}', '${cam.name}')" title="Click to enlarge">
        <img src="/stream/${cam.id}" alt="${cam.id} Stream" loading="lazy">
        <div class="cctv-scanline"></div>
      </div>

      <!-- Bottom Bar -->
      <div class="card-bottom-bar">
        <div class="status-tag ${cam.has_violations ? "alert" : "ok"}">
          <span>●</span>
          <span>${cam.has_violations ? "SAFETY VIOLATION DETECTED" : "NORMAL ACTIVITY"}</span>
        </div>
        <div class="card-actions">
          <button class="btn-inspect" onclick="openModal('${cam.id}', '${cam.name}')">
            ENLARGE ⛶
          </button>
        </div>
      </div>
    `;

    gridEl.appendChild(card);
  });
}

// Modal View
function openModal(camId, camName) {
  const modal = document.getElementById("cam-modal");
  const modalTitle = document.getElementById("modal-cam-title");
  const modalImg = document.getElementById("modal-stream-img");
  
  modalTitle.innerText = `${camId} | ${camName.toUpperCase()} - LIVE 5 FPS INSPECTION`;
  modalImg.src = `/stream/${camId}`;
  modal.classList.add("active");
}

function closeModal(e) {
  const modal = document.getElementById("cam-modal");
  const modalImg = document.getElementById("modal-stream-img");
  modalImg.src = "";
  modal.classList.remove("active");
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}
