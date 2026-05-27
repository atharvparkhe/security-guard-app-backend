/**
 * One-off: upload collection to Postman workspace "elsteel workspace".
 * API key read from ~/.cursor/mcp.json (same as Postman MCP).
 */
import fs from "fs";
import https from "https";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadApiKey() {
  const mcpPath = path.join(process.env.HOME, ".cursor", "mcp.json");
  const j = JSON.parse(fs.readFileSync(mcpPath, "utf8"));
  const auth = j?.mcpServers?.postman_mcp_server?.headers?.Authorization || "";
  return auth.replace(/^Bearer\s+/i, "").trim();
}

function httpJson(method, urlStr, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const opts = {
      hostname: u.hostname,
      path: u.pathname + u.search,
      method,
      headers: { "X-Api-Key": loadApiKey(), "Content-Type": "application/json" },
    };
    const req = https.request(opts, (res) => {
      let b = "";
      res.on("data", (c) => (b += c));
      res.on("end", () => {
        let parsed = b;
        try {
          parsed = JSON.parse(b);
        } catch {
          /* keep string */
        }
        resolve({ status: res.statusCode, body: parsed });
      });
    });
    req.on("error", reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

const jsonBody = (obj) => ({
  mode: "raw",
  raw: JSON.stringify(obj, null, 2),
  options: { raw: { language: "json" } },
});

const hdrJson = [{ key: "Content-Type", value: "application/json" }];

function formBody(parts) {
  return {
    mode: "formdata",
    formdata: parts.map((p) => {
      if (p.t === "file") {
        return {
          key: p.key,
          type: "file",
          src: [],
          description: p.desc || "Select file in Postman",
        };
      }
      const row = { key: p.key, type: "text", value: p.value ?? "" };
      if (p.desc) row.description = p.desc;
      return row;
    }),
  };
}

/** Postman Tests / Prerequest `event` blocks (listen: test | prerequest). */
function scriptEvent(listen, execLines) {
  return {
    listen,
    script: {
      type: "text/javascript",
      exec: execLines,
    },
  };
}

function reqItem(name, method, urlPath, { auth, body, headers, description, event, query } = {}) {
  const base = `{{base_url}}${urlPath}`;
  let url = base;
  if (query?.length) {
    const qs = query
      .filter((q) => q.enabled !== false)
      .map((q) => `${encodeURIComponent(q.key)}=${encodeURIComponent(q.value ?? "")}`)
      .join("&");
    if (qs) url = `${base}${base.includes("?") ? "&" : "?"}${qs}`;
  }
  const item = {
    name,
    request: {
      method,
      header: headers || (body?.mode === "raw" ? hdrJson : []),
      url,
      description: description || "",
    },
  };
  if (auth) item.request.auth = auth;
  if (body) item.request.body = body;
  if (event?.length) item.event = event;
  return item;
}

const noauth = { type: "noauth" };

/** Saves `content.id` or `content.entry_id` → inward_entry_id after successful inward calls. */
const saveInvoiceIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const c = json.content || {};",
  "  const id = c.id || (c.invoices && c.invoices[0] && c.invoices[0].id);",
  "  if (id) pm.collectionVariables.set('invoice_id', id);",
  "} catch (e) { console.warn(e); }",
]);

const saveInwardEntryIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const c = json.content || {};",
  "  const id = c.id || c.entry_id;",
  "  if (id) pm.collectionVariables.set('inward_entry_id', id);",
  "  const inv = c.invoice || {};",
  "  if (inv.id) pm.collectionVariables.set('invoice_id', inv.id);",
  "} catch (e) { console.warn(e); }",
]);

/** Invoice header + photo for POST /inward/ (no line items). */
const inwardInvoiceFormFields = () => [
  {
    key: "invoice_image",
    t: "file",
    desc: "Required. Invoice scan/photo (jpg, png, pdf).",
  },
  {
    key: "invoice_number",
    value: "INV-2025-001",
    desc: "Required.",
  },
  {
    key: "invoice_from",
    value: "Acme Supplies Pvt Ltd",
    desc: "Required. Supplier / invoice-from name (stored as supplier_name).",
  },
  {
    key: "po_number",
    value: "PO-2025-100",
    desc: "Required.",
  },
];

/** Guard inward create — vehicle_id + driver_id only (create masters first). */
const inwardCreateByIdFields = () => [
  {
    key: "vehicle_id",
    value: "{{truck_id}}",
    desc: "Required. Truck UUID (same as truck_id).",
  },
  {
    key: "driver_id",
    value: "{{driver_id}}",
    desc: "Required. Driver UUID.",
  },
  {
    key: "in_time",
    value: "",
    desc: "Optional. ISO datetime (e.g. 2025-05-20T14:30:00). Empty = server now.",
  },
  {
    key: "guard_remarks",
    value: "",
    desc: "Optional.",
  },
  ...inwardInvoiceFormFields(),
];

const collection = {
  info: {
    name: "Elsteel Security Guard API",
    description:
      "Django REST API (JWT). Set **base_url**. Run **Login Step 1** (OTP in email or dev logs) then **Login Step 2** — the **Tests** script saves `access` → collection variable **JWT** and `refresh` → **refresh_token**. Collection Bearer uses `{{JWT}}`. Use **Refresh access token** to rotate and update **JWT**.",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
  },
  auth: {
    type: "bearer",
    bearer: [{ key: "token", value: "{{JWT}}", type: "string" }],
  },
  variable: [
    { key: "base_url", value: "http://127.0.0.1:8000", type: "string" },
    {
      key: "JWT",
      value: "",
      type: "string",
      description: "Filled automatically after Login Step 2 (Bearer token for all authenticated requests).",
    },
    {
      key: "refresh_token",
      value: "",
      type: "string",
      description: "Filled after Login Step 2; used by **Refresh access token**.",
    },
    { key: "employee_id", value: "", type: "string", description: "UUID — target employee" },
    { key: "truck_id", value: "", type: "string" },
    { key: "driver_id", value: "", type: "string" },
    { key: "purchase_order_id", value: "", type: "string" },
    { key: "vendor_id", value: "", type: "string", description: "Vendor UUID for inward create" },
    { key: "inward_entry_id", value: "", type: "string" },
    { key: "invoice_id", value: "", type: "string", description: "Invoice UUID (from inward detail or invoice list)" },
    { key: "department_id", value: "", type: "string", description: "Department UUID for PATCH employee" },
  ],
  item: [
    {
      name: "Auth",
      description: "Public endpoints (no Bearer). Authenticated calls use collection Bearer **JWT**.",
      item: [
        reqItem("Login — Step 1 (send OTP)", "POST", "/auth/login-step-1/", {
          auth: noauth,
          body: jsonBody({
            employee_number: "EL001",
            password: "your-password",
          }),
          description:
            "Required: `employee_number` (EL + 3 digits, e.g. EL001), `password`. Sends OTP to employee email.",
        }),
        reqItem("Login — Step 2 (OTP → tokens)", "POST", "/auth/login-step-2/", {
          auth: noauth,
          body: jsonBody({
            employee_number: "EL001",
            otp: "123456",
          }),
          description:
            "After a **200** response, the **Tests** script reads `content.access` / `content.refresh` and sets collection variables **JWT** and **refresh_token**.",
          event: [
            scriptEvent("test", [
              "try {",
              "  const json = pm.response.json();",
              "  pm.test('API success', function () {",
              "    pm.expect(json.response_type).to.eql('SUCCESS');",
              "  });",
              "  const c = json.content || {};",
              "  if (c.access) {",
              "    pm.collectionVariables.set('JWT', c.access);",
              "  }",
              "  if (c.refresh) {",
              "    pm.collectionVariables.set('refresh_token', c.refresh);",
              "  }",
              "  pm.test('JWT collection variable set', function () {",
              "    pm.expect(pm.collectionVariables.get('JWT')).to.be.ok;",
              "  });",
              "} catch (e) {",
              "  pm.test('Response JSON', function () { pm.expect.fail(e.message); });",
              "}",
            ]),
          ],
        }),
        reqItem("Refresh access token", "POST", "/auth/token/refresh/", {
          auth: noauth,
          body: jsonBody({ refresh: "{{refresh_token}}" }),
          description: "Required: `refresh`. Updates **JWT** (and **refresh_token** if rotated) from `content`.",
          event: [
            scriptEvent("test", [
              "try {",
              "  const json = pm.response.json();",
              "  if (json.response_type !== 'SUCCESS') return;",
              "  const c = json.content || {};",
              "  if (c.access) { pm.collectionVariables.set('JWT', c.access); }",
              "  if (c.refresh) { pm.collectionVariables.set('refresh_token', c.refresh); }",
              "} catch (e) { console.warn(e); }",
            ]),
          ],
        }),
      ],
    },
    {
      name: "Employees & departments",
      description: "JWT required. PATCH employee: **superadmin** only.",
      item: [
        reqItem("List employees", "GET", "/employees/", {
          description: "Query: `role`, `department` (department UUID)",
        }),
        reqItem("Get employee by ID", "GET", "/employees/{{employee_id}}/", {}),
        reqItem("Update employee (superadmin)", "PATCH", "/employees/{{employee_id}}/", {
          body: jsonBody({
            role: "security_guard",
            department: "{{department_id}}",
            phone: "+919876543210",
          }),
          description:
            "Optional fields (send any subset): `role` (security_guard | stores_manager | purchase | hr | superadmin), `department` (UUID), `phone`.",
        }),
        reqItem("List departments", "GET", "/departments/", {}),
      ],
    },
    {
      name: "Trucks",
      description: "GET: guard or stores manager. POST/PATCH truck: **security guard**. Multipart form.",
      item: [
        reqItem("List trucks", "GET", "/trucks/", {
          description: "Query: `search` (registration substring)",
        }),
        reqItem("Create truck", "POST", "/trucks/", {
          body: formBody([
            { key: "registration_number", value: "MH12AB1234" },
            { key: "vehicle_type", value: "truck" },
            { key: "owner_name", value: "Owner Name" },
            { key: "truck_photo", t: "file" },
          ]),
          description:
            "Required: `registration_number`. Optional: `vehicle_type` (truck | tempo | pickup | van | two_wheeler | other), `owner_name`, `truck_photo`.",
        }),
        reqItem("Update truck (partial)", "PATCH", "/trucks/{{truck_id}}/", {
          body: formBody([
            { key: "owner_name", value: "Updated owner" },
            { key: "vehicle_type", value: "tempo" },
            { key: "truck_photo", t: "file" },
          ]),
          description: "Optional: `owner_name`, `vehicle_type`, `truck_photo`.",
        }),
      ],
    },
    {
      name: "Drivers",
      description: "GET: guard or stores manager. POST/PATCH driver: **security guard**.",
      item: [
        reqItem("List drivers", "GET", "/drivers/", {
          description: "Query: `search` (name, mobile, licence)",
        }),
        reqItem("Create driver", "POST", "/drivers/", {
          body: formBody([
            { key: "name", value: "Driver Name" },
            { key: "mobile", value: "9876543210" },
            { key: "licence_number", value: "DL-12345-2020" },
            { key: "licence_photo", t: "file" },
          ]),
          description:
            "Required: `name`, `mobile`, `licence_number`. Optional: `licence_photo`.",
        }),
        reqItem("Update driver (partial)", "PATCH", "/drivers/{{driver_id}}/", {
          body: formBody([
            { key: "name", value: "Updated name" },
            { key: "licence_photo", t: "file" },
          ]),
          description: "Optional: `name`, `licence_photo`.",
        }),
      ],
    },
    {
      name: "Purchase orders",
      description: "JWT; **guard or stores manager**.",
      item: [
        reqItem("List purchase orders", "GET", "/purchase-orders/", {
          description: "Query: `search`, `vendor` (vendor UUID), `status`",
        }),
        reqItem("Get purchase order detail", "GET", "/purchase-orders/{{purchase_order_id}}/", {}),
      ],
    },
    {
      name: "Dashboard",
      description:
        "**Superadmin JWT only.** Aggregated KPIs, charts, recent tables, and alerts. Replaces multiple parallel list calls for the admin dashboard UI.",
      item: [
        reqItem("Dashboard stats (today)", "GET", "/dashboard/stats/", {
          description:
            "Default period is today (server timezone). Response `content`: `period`, `visibility`, `kpis`, `charts`, `recent`, `alerts`.",
        }),
        reqItem("Dashboard stats (single date)", "GET", "/dashboard/stats/", {
          query: [{ key: "date", value: "2026-05-20", enabled: true }],
          description: "Filter by one day (`YYYY-MM-DD`). Do not combine with from_date/to_date.",
        }),
        reqItem("Dashboard stats (date range)", "GET", "/dashboard/stats/", {
          query: [
            { key: "from_date", value: "2026-05-01", enabled: true },
            { key: "to_date", value: "2026-05-20", enabled: true },
          ],
          description: "Inclusive range. `inward_by_hour` chart is empty for multi-day ranges.",
        }),
        reqItem("Dashboard stats (period shortcut)", "GET", "/dashboard/stats/", {
          query: [{ key: "period", value: "last_7_days", enabled: true }],
          description:
            "Shortcuts: `today` (default), `yesterday`, `last_7_days`, `last_30_days`. Ignored if `date` or from/to dates are sent.",
        }),
      ],
    },
    {
      name: "Invoices",
      description: "JWT; **guard or stores manager**. Read-only invoice catalog (linked to inward entries).",
      item: [
        reqItem("List invoices", "GET", "/invoices/", {
          description: `Date filters (on invoice \`created_at\`):
- No params → today
- \`date\` (YYYY-MM-DD) → single day
- \`from_date\` + \`to_date\` → inclusive range

Optional: \`search\` (invoice_number, supplier_name, po_number), \`vendor_id\`, \`po_id\`.

Response \`content\`: \`filters\`, \`invoices\` (summary rows with \`inward_entry_id\` when linked).`,
          query: [
            { key: "date", value: "", enabled: false },
            { key: "from_date", value: "2025-05-01", enabled: false },
            { key: "to_date", value: "2025-05-20", enabled: false },
            { key: "search", value: "", enabled: false },
            { key: "vendor_id", value: "{{vendor_id}}", enabled: false },
            { key: "po_id", value: "{{purchase_order_id}}", enabled: false },
          ],
          event: [saveInvoiceIdTest],
        }),
        reqItem("Get invoice by ID", "GET", "/invoices/{{invoice_id}}/", {
          description:
            "Invoice header (`invoice_from`, `invoice_number`, `po_number`), file URL, vendor/po when linked. No line items. `inward_entry_id` / `inward_status` when linked to an entry.",
          event: [saveInvoiceIdTest],
        }),
      ],
    },
    {
      name: "Inward (gate)",
      description:
        "GET /inward/: guard (own entries), stores & superadmin (all in range). Same stats keys for all. POST create → stores decision → guard exit.",
      item: [
        reqItem("List inward entries (guard)", "GET", "/inward/", {
          description:
            "Guard JWT: own entries only. Response: filters, stats (total_completed, vehicles_inside), full entries array.",
          query: [
            { key: "status", value: "", enabled: false, description: "pending_verification | acknowledged | completed" },
          ],
        }),
        reqItem("List inward entries (stores)", "GET", "/inward/", {
          description:
            "Stores manager JWT: all entries in date range. Use status=pending_verification for old pending-verification list.",
          query: [
            { key: "status", value: "pending_verification", enabled: true },
          ],
        }),
        reqItem("List inward entries (superadmin)", "GET", "/inward/", {
          description:
            "Superadmin JWT. entries: client_name, vehicle_number, in_time, out_time, stores_manager_acknowledgment, invoice_hardcopy_received. stats: completed, pending, pending_grn, no_invoice_hardcopy.",
        }),
        reqItem("Create inward", "POST", "/inward/", {
          body: formBody(inwardCreateByIdFields()),
          description:
            "Guard only. Required: vehicle_id, driver_id, invoice_image, invoice_number, invoice_from, po_number.",
          event: [saveInwardEntryIdTest],
        }),
        reqItem("Update inward (pending only)", "PATCH", "/inward/{{inward_entry_id}}/", {
          body: formBody([
            { key: "invoice_from", value: "Updated supplier" },
            { key: "po_number", value: "PO-2025-101" },
          ]),
          description: "Guard only. pending_verification only.",
        }),
        reqItem("Currently inside (all guards)", "GET", "/inward/currently-inside/", {}),
        reqItem("Inward detail", "GET", "/inward/{{inward_entry_id}}/", {
          description: "lifecycle_steps, stores_acknowledgment, full invoice (no line items).",
          event: [saveInwardEntryIdTest],
        }),
        reqItem("Guard exit", "POST", "/inward/{{inward_entry_id}}/exit/", {
          body: jsonBody({ guard_remarks: "Exited", out_time: "" }),
          description: "Requires acknowledged + received_invoice_hardcopy=true.",
        }),
        reqItem("Stores — decision (POST)", "POST", "/inward/{{inward_entry_id}}/decision/", {
          body: jsonBody({
            received_invoice_hardcopy: true,
            comments: "Hard copy verified at stores",
            grn_number: "GRN/25-26/001",
          }),
          description:
            "Stores manager. Required: received_invoice_hardcopy (boolean). Optional: comments (text), grn_number (GRN/YY-YY/NNN when non-empty). POST once per entry.",
          event: [saveInwardEntryIdTest],
        }),
        reqItem("Stores — decision (PATCH)", "PATCH", "/inward/{{inward_entry_id}}/decision/", {
          body: jsonBody({
            grn_number: "GRN/25-26/001",
            comments: "GRN updated",
          }),
          description:
            "Partial update: received_invoice_hardcopy, comments, grn_number (all optional). Cannot set received_invoice_hardcopy to false after true.",
          event: [saveInwardEntryIdTest],
        }),
      ],
    },
  ],
};

async function resolveWorkspaceId() {
  const explicit = process.env.POSTMAN_WORKSPACE_ID?.trim();
  if (explicit) return explicit;
  const res = await httpJson("GET", "https://api.getpostman.com/workspaces?limit=100");
  if (res.status >= 400) {
    throw new Error(`workspaces list failed: ${res.status} ${JSON.stringify(res.body)}`);
  }
  const list = res.body.workspaces || [];
  const hit =
    list.find((w) => String(w.name || "").toLowerCase() === "elsteel workspace") ||
    list.find((w) => /elsteel/i.test(w.name || ""));
  if (!hit) {
    throw new Error(
      `No workspace matching "elsteel workspace". Set POSTMAN_WORKSPACE_ID. Found: ${list.map((w) => w.name).join(", ")}`
    );
  }
  return hit.id;
}

(async () => {
  const payload = { collection };
  const updateUid = process.env.POSTMAN_COLLECTION_UID?.trim();
  const workspaceId = updateUid ? null : await resolveWorkspaceId();
  const url = updateUid
    ? `https://api.getpostman.com/collections/${updateUid}`
    : `https://api.getpostman.com/collections?workspace=${workspaceId}`;
  const res = await httpJson(updateUid ? "PUT" : "POST", url, payload);
  if (res.status >= 400) {
    console.error("Postman API error", res.status, JSON.stringify(res.body, null, 2).slice(0, 4000));
    process.exit(1);
  }
  const c = res.body.collection;
  console.log(
    JSON.stringify(
      {
        ok: true,
        collectionId: c?.id,
        name: c?.name,
        uid: c?.uid,
        workspace: workspaceId || undefined,
        hint: "Re-run with POSTMAN_COLLECTION_UID=<uid> to update instead of creating a duplicate.",
      },
      null,
      2
    )
  );
})();
