# Security Guard App — Backend

Django 5 gate management API with Django REST Framework, Simple JWT, and Phase 1 inward entry flow.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Settings

| Module | Use |
|--------|-----|
| `core.settings.dev` | Local development (default) |
| `core.settings.prod` | Production — set `DJANGO_SETTINGS_MODULE=core.settings.prod` |

## Apps

| App | Purpose |
|-----|---------|
| `base` | BaseModel, standard API responses (`SUCCESS`/`ERROR`), permissions, exception handler |
| `employee` | Departments, employees (custom user), auth |
| `orders` | Vendors, purchase orders |
| `gate` | Trucks, drivers, inward entries |

## API response format

All endpoints return:

```json
{
  "response_type": "SUCCESS",
  "message": "Human readable message",
  "content": {}
}
```

## Auth

Two-step login: credentials, then email OTP.

| Method | Path | Body |
|--------|------|------|
| POST | `/api/v1/auth/login-step-1/` | `employee_number`, `password` |
| POST | `/api/v1/auth/login-step-2/` | `employee_number`, `otp` |
| POST | `/api/v1/auth/token/refresh/` | `refresh` |

`employee_number` must match **`EL` + exactly 3 digits** (e.g. `EL000`, `EL042`). It is stored in the **`employee_id`** field on the employee (not `username`). If login fails with “User does not exist”, set or fix `employee_id` in the admin for that user. Lookup is case-insensitive (`el000` and `EL000` are equivalent). The UUID `id` is only used internally (e.g. OTP cache key).

## Gate (Phase 1)

Prefix: `/api/v1/gate/`

- Trucks, drivers (master CRUD; truck `owner_contact`, optional driver licence)
- Purchase orders (from `orders` app)
- **Inward workflow** (status: `pending_verification` → `acknowledged` → `completed`)
  - **Guard:** `POST /inward/` — `vehicle_id`, `driver_id`, `invoice_image`, `invoice_number`, `invoice_from`, `po_number`, `in_time` (optional) → `pending_verification` with lifecycle steps 1–4 completed
  - **Guard:** `PATCH /inward/{id}/` (pending only), `POST /inward/{id}/exit/` (after stores hard copy acknowledged)
  - **Stores:** `POST /inward/{id}/decision/` (`received_invoice_hardcopy`, optional `comments`, optional `grn_number`), `PATCH /inward/{id}/decision/` (same fields, all optional)
  - **Reads:** `GET /inward/` (guard/stores: full `entries` + `total_completed` / `vehicles_inside` stats; superadmin: slim `entries` + `completed` / `pending` / `pending_grn` / `no_invoice_hardcopy` stats), `GET /inward/{id}/` (includes `lifecycle_steps`, `stores_acknowledgment`), `GET /inward/currently-inside/`
  - **Stores pending list:** `GET /inward/?status=pending_verification` (replaces removed `/inward/pending-verification/`)
- **Invoices:** `GET /invoices/` (list), `GET /invoices/{id}/` (header + file; no line items)
- **Dashboard (superadmin only):** `GET /dashboard/stats/` — aggregated KPIs, charts, recent rows, alerts

### Dashboard stats

`GET /dashboard/stats/` requires **superadmin** JWT. Other roles receive `403`.

Query params (same rules as inward/invoices lists):

- Default / `period=today` — today
- `date=YYYY-MM-DD` — single day (do not combine with `from_date`/`to_date`)
- `from_date` + `to_date` — inclusive range
- `period` — `today`, `yesterday`, `last_7_days`, `last_30_days` (used when explicit dates omitted)

Response `content` includes `period`, `visibility`, `kpis`, `charts` (`inward_by_status`, `inward_by_hour`, `daily_comparison`), `recent` (max 10 per list), and `alerts`.

Invoice header on `Invoice`; stores acknowledgment on `StoresAcknowledgment` (`received_invoice_hardcopy`, `comments`, optional `grn_number`). Admin inward change page shows seven `InwardLifecycleStep` rows (completed / pending / skipped). Sync Postman via `node scripts/push-postman-elsteel.mjs` (set `POSTMAN_API_KEY`, `POSTMAN_COLLECTION_UID`).

### Lifecycle steps

| step_key | Completed when |
|----------|----------------|
| `vehicle_driver` | Truck and driver on entry |
| `invoice_photo` | `invoice_file` set |
| `invoice_details` | Invoice number, `invoice_from`, PO non-empty |
| `gate_in` | `in_time` set |
| `stores_hardcopy` | `hardcopy_received` on acknowledgment |
| `stores_grn` | GRN on acknowledgment, or **skipped** on exit without GRN |
| `gate_out` | `out_time` set |
