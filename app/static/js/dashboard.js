/**
 * Dashboard UI interactions — sidebar toggle, responsive nav
 */
(function () {
    const sidebar = document.getElementById("dashboardSidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const toggleBtn = document.getElementById("sidebarToggle");
    const closeBtn = document.getElementById("sidebarClose");

    if (!sidebar) return;

    function openSidebar() {
        sidebar.classList.add("open");
        overlay?.classList.add("show");
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        sidebar.classList.remove("open");
        overlay?.classList.remove("show");
        document.body.style.overflow = "";
    }

    toggleBtn?.addEventListener("click", openSidebar);
    closeBtn?.addEventListener("click", closeSidebar);
    overlay?.addEventListener("click", closeSidebar);

    window.addEventListener("resize", function () {
        if (window.innerWidth >= 992) {
            closeSidebar();
        }
    });
})();

/**
 * Global Search
 */
(function() {
    const searchInput = document.querySelector('.topbar-search input');
    if (!searchInput) return;

    // Create dropdown container
    const searchContainer = document.querySelector('.topbar-search');
    const dropdown = document.createElement('div');
    dropdown.className = 'search-dropdown shadow-sm rounded border';
    dropdown.style.position = 'absolute';
    dropdown.style.top = '100%';
    dropdown.style.left = '0';
    dropdown.style.width = '100%';
    dropdown.style.background = '#fff';
    dropdown.style.zIndex = '1000';
    dropdown.style.display = 'none';
    dropdown.style.maxHeight = '400px';
    dropdown.style.overflowY = 'auto';
    dropdown.style.marginTop = '5px';
    searchContainer.style.position = 'relative';
    searchContainer.appendChild(dropdown);

    let debounceTimer;

    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    dropdown.innerHTML = '';
                    let html = '';
                    
                    if (data.candidates.length > 0) {
                        html += '<div class="p-2 bg-light fw-bold text-muted small">Candidates</div>';
                        data.candidates.forEach(c => {
                            html += `<a href="/candidates/${c.id}" class="d-block p-2 text-decoration-none border-bottom text-dark" style="background:#fff;" onmouseover="this.style.background='#f8f9fa'" onmouseout="this.style.background='#fff'">
                                <div class="fw-bold">${c.name}</div>
                                <div class="small text-muted">${c.title || 'No Title'} • ${c.email || 'No Email'}</div>
                            </a>`;
                        });
                    }
                    
                    if (data.jobs.length > 0) {
                        html += '<div class="p-2 bg-light fw-bold text-muted small">Jobs</div>';
                        data.jobs.forEach(j => {
                            html += `<a href="/jobs/${j.id}" class="d-block p-2 text-decoration-none border-bottom text-dark" style="background:#fff;" onmouseover="this.style.background='#f8f9fa'" onmouseout="this.style.background='#fff'">
                                <div class="fw-bold">${j.title}</div>
                                <div class="small text-muted">${j.department || 'General'} • Status: ${j.status}</div>
                            </a>`;
                        });
                    }

                    if (!data.candidates.length && !data.jobs.length) {
                        html = '<div class="p-3 text-muted text-center">No results found</div>';
                    }

                    dropdown.innerHTML = html;
                    dropdown.style.display = 'block';
                });
        }, 300);
    });

    document.addEventListener('click', function(e) {
        if (!searchContainer.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
})();

/**
 * Live Dashboard Polling
 */
(function() {
    // Only run if we are on the dashboard
    if (!document.getElementById('recentActivityList')) return;

    function updateDashboardStats() {
        fetch('/api/dashboard-stats')
            .then(res => res.json())
            .then(data => {
                // Update stats
                ['total_candidates', 'total_applicants', 'shortlisted', 'rejected', 'total_jobs', 'active_jobs', 'suspicious_resumes'].forEach(key => {
                    const el = document.getElementById(`stat_${key}`);
                    if (el && data[key] !== undefined) el.textContent = data[key];
                });
                
                const draftClosedEl = document.getElementById('stat_draft_closed_jobs');
                if (draftClosedEl) {
                    draftClosedEl.textContent = `${data.draft_jobs} / ${data.closed_jobs}`;
                }

                // Update pipeline
                ['new', 'reviewing', 'shortlisted', 'rejected', 'hired'].forEach(key => {
                    const el = document.getElementById(`pipe_${key}`);
                    if (el && data.pipeline[key] !== undefined) el.textContent = data.pipeline[key];
                });

                // Update recent activity
                const activityList = document.getElementById('recentActivityList');
                if (activityList && data.recent_activities) {
                    if (data.recent_activities.length === 0) {
                        activityList.innerHTML = '<div class="p-3 text-center text-muted">No recent activity</div>';
                    } else {
                        activityList.innerHTML = data.recent_activities.map(act => `
                            <div class="list-group-item px-3 py-2">
                                <div class="d-flex w-100 justify-content-between">
                                    <h6 class="mb-1" style="font-size: 0.9rem;">${act.action}</h6>
                                    <small class="text-muted">${act.timestamp}</small>
                                </div>
                                <p class="mb-1 small text-muted">${act.description}</p>
                            </div>
                        `).join('');
                    }
                }
            })
            .catch(err => console.error("Polling failed", err));
    }

    // Initial fetch
    updateDashboardStats();
    // Poll every 5 seconds
    setInterval(updateDashboardStats, 5000);
})();
