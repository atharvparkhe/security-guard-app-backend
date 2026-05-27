"""App-level constants (not secrets). Import in views and services as needed."""

# OCR
OCR_MAX_FILE_SIZE_MB = 10
OCR_ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "pdf"]
OCR_TIMEOUT_SECONDS = 30

# Inward entry business rules
INWARD_GRN_PENDING_ALERT_HOURS = 2
INWARD_GRN_ESCALATE_HOURS = 4

# GRN format e.g. GRN/26-27/001
GRN_FORMAT_REGEX = r"^GRN/\d{2}-\d{2}/\d+$"

# Dashboard alerts
DASHBOARD_VEHICLES_INSIDE_ALERT_THRESHOLD = 10
