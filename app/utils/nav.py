"""Dashboard navigation configuration."""

NAV_ITEMS = [
    {
        "id": "dashboard",
        "label": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "endpoint": "main.dashboard",
    },
    {
        "id": "candidates",
        "label": "Candidates",
        "icon": "bi-people-fill",
        "endpoint": "main.candidates",
    },
    {
        "id": "jobs",
        "label": "Jobs",
        "icon": "bi-briefcase-fill",
        "endpoint": "main.jobs",
    },
    {
        "id": "upload",
        "label": "Upload Resumes",
        "icon": "bi-cloud-upload-fill",
        "endpoint": "resumes.upload",
    },
    {
        "id": "analytics",
        "label": "Analytics",
        "icon": "bi-bar-chart-fill",
        "endpoint": "main.analytics",
    },
    {
        "id": "emails",
        "label": "Email History",
        "icon": "bi-envelope-check-fill",
        "endpoint": "main.email_history",
    },
    {
        "id": "recruitment_ai",
        "label": "Recruitment AI",
        "icon": "bi-robot",
        "endpoint": "main.recruitment_ai",
    },
    {
        "id": "email_settings",
        "label": "Email Settings",
        "icon": "bi-gear-fill",
        "endpoint": "main.email_settings",
    },
    {
        "id": "system_status",
        "label": "System Status",
        "icon": "bi-cloud-check-fill",
        "endpoint": "main.system_status_route",
    },
]

