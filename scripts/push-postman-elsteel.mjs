/**
 * Upload collection to Postman workspace "elsteel workspace".
 * API key from ~/.cursor/mcp.json (Postman MCP Bearer).
 *
 * Root URLs only (no /api/v1/). Variables: {{BASE_URL}}, {{ACCESS_TOKEN}} (alias {{JWT}}).
 */
import fs from "fs";
import https from "https";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadApiKey() {
  const mcpPath = path.join(process.env.HOME, ".cursor", "mcp.json");
  const j = JSON.parse(fs.readFileSync(mcpPath, "utf8"));
  const auth =
    j?.mcpServers?.postman_mcp_server?.headers?.Authorization ||
    j?.mcpServers?.["user-postman_mcp_server"]?.headers?.Authorization ||
    "";
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

function scriptEvent(listen, execLines) {
  return {
    listen,
    script: { type: "text/javascript", exec: execLines },
  };
}

function envelope(content, message = "OK", responseType = "SUCCESS") {
  return { response_type: responseType, message, content };
}

function savedResponses(examples) {
  return examples.map((ex) => ({
    name: ex.name,
    status: ex.status || "OK",
    code: ex.code || 200,
    _postman_previewlanguage: "json",
    header: [{ key: "Content-Type", value: "application/json" }],
    body:
      typeof ex.body === "string" ? ex.body : JSON.stringify(ex.body, null, 2),
  }));
}

function reqItem(
  name,
  method,
  urlPath,
  { auth, body, headers, description, event, query, response } = {}
) {
  const base = `{{BASE_URL}}${urlPath}`;
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
  if (response?.length) item.response = response;
  return item;
}

const noauth = { type: "noauth" };

const saveTokensTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const c = json.content || {};",
  "  if (c.access) {",
  "    pm.collectionVariables.set('ACCESS_TOKEN', c.access);",
  "    pm.collectionVariables.set('JWT', c.access);",
  "  }",
  "  if (c.refresh) pm.collectionVariables.set('refresh_token', c.refresh);",
  "} catch (e) { console.warn(e); }",
]);

const saveInwardEntryIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const c = json.content || {};",
  "  const id = c.id || c.entry_id;",
  "  if (id) pm.collectionVariables.set('inward_entry_id', id);",
  "} catch (e) { console.warn(e); }",
]);

const saveOutwardIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const id = (json.content || {}).id;",
  "  if (id) pm.collectionVariables.set('outward_entry_id', id);",
  "} catch (e) { console.warn(e); }",
]);

const saveVisitorIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const id = (json.content || {}).id;",
  "  if (id) pm.collectionVariables.set('visitor_entry_id', id);",
  "} catch (e) { console.warn(e); }",
]);

const saveReturnableIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const id = (json.content || {}).id;",
  "  if (id) pm.collectionVariables.set('returnable_return_id', id);",
  "} catch (e) { console.warn(e); }",
]);

const saveVendorIdTest = scriptEvent("test", [
  "try {",
  "  const json = pm.response.json();",
  "  if (json.response_type !== 'SUCCESS') return;",
  "  const id = (json.content || {}).id;",
  "  if (id) pm.collectionVariables.set('vendor_id', id);",
  "} catch (e) { console.warn(e); }",
]);

const materialItemsExample = [
  { description: "MS Angle 50x50", quantity: "120", unit: "pcs" },
  { description: "Binding wire", quantity: "25", unit: "kg" },
];

const inwardDraftSuccess = savedResponses([
  {
    name: "201 — Draft created",
    code: 201,
    status: "Created",
    body: envelope(
      {
        id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        status: "draft",
        gate_transaction_id: "11111111-2222-3333-4444-555555555555",
        vehicle: { id: "{{truck_id}}", registration_number: "MH12AB1234" },
        driver: { id: "{{driver_id}}", name: "Ramesh Kumar", mobile: "9876543210" },
        lifecycle_steps: [],
      },
      "Inward draft created successfully"
    ),
  },
]);

const inwardCreateErrorExamples = savedResponses([
  {
    name: "400 — Driver not found",
    code: 400,
    status: "Bad Request",
    body: envelope({}, "Driver not found", "ERROR"),
  },
  {
    name: "400 — Validation (missing vehicle_id)",
    code: 400,
    status: "Bad Request",
    body: envelope(
      { vehicle_id: ["This field is required."] },
      "Validation failed",
      "ERROR"
    ),
  },
]);

const visitorAllowInErrorExamples = savedResponses([
  {
    name: "400 — NDA not signed",
    code: 400,
    status: "Bad Request",
    body: envelope({}, "NDA must be signed before allow in", "ERROR"),
  },
  {
    name: "400 — NDA photo missing",
    code: 400,
    status: "Bad Request",
    body: envelope({}, "NDA photo is required before allow in", "ERROR"),
  },
  {
    name: "200 — Success",
    code: 200,
    status: "OK",
    body: envelope(
      {
        id: "{{visitor_entry_id}}",
        status: "inside",
        in_time: "2026-05-27T10:15:00+05:30",
        nda_signed: true,
      },
      "Visitor allowed in successfully"
    ),
  },
]);

const visitorCreateSuccess = savedResponses([
  {
    name: "201 — Created",
    code: 201,
    status: "Created",
    body: envelope(
      {
        id: "vvvvvvvv-wwww-xxxx-yyyy-zzzzzzzzzzzz",
        status: "created",
        visitor_name: "Priya Sharma",
        company: "TechVendor Ltd",
        nda_signed: true,
      },
      "Visitor entry created successfully"
    ),
  },
]);

const collection = {
  info: {
    name: "Elsteel Security Guard API",
    description:
      "Django REST API (JWT). Set **BASE_URL** (e.g. http://127.0.0.1:8000). Run **Login Step 1** then **Login Step 2** — Tests save `access` → **ACCESS_TOKEN** and **JWT**. Collection Bearer uses `{{ACCESS_TOKEN}}`. Root paths only (no `/api/v1/`).",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
  },
  auth: {
    type: "bearer",
    bearer: [{ key: "token", value: "{{ACCESS_TOKEN}}", type: "string" }],
  },
  variable: [
    { key: "BASE_URL", value: "http://127.0.0.1:8000", type: "string" },
    {
      key: "ACCESS_TOKEN",
      value: "",
      type: "string",
      description: "Bearer token (set after Login Step 2).",
    },
    {
      key: "JWT",
      value: "",
      type: "string",
      description: "Alias for ACCESS_TOKEN.",
    },
    { key: "refresh_token", value: "", type: "string" },
    { key: "employee_id", value: "", type: "string" },
    { key: "reference_employee_id", value: "", type: "string" },
    { key: "department_id", value: "", type: "string" },
    { key: "truck_id", value: "", type: "string" },
    { key: "driver_id", value: "", type: "string" },
    { key: "vendor_id", value: "", type: "string" },
    { key: "purchase_order_id", value: "", type: "string" },
    { key: "inward_entry_id", value: "", type: "string" },
    { key: "outward_entry_id", value: "", type: "string" },
    { key: "returnable_return_id", value: "", type: "string" },
    { key: "visitor_entry_id", value: "", type: "string" },
    { key: "transaction_id", value: "", type: "string" },
  ],
  item: [
    {
      name: "Auth",
      description: "Public endpoints. Authenticated calls use collection Bearer {{ACCESS_TOKEN}}.",
      item: [
        reqItem("Login — Step 1 (send OTP)", "POST", "/auth/login-step-1/", {
          auth: noauth,
          body: jsonBody({ employee_number: "EL001", password: "YourSecurePass1!" }),
          description: "Required: employee_number (EL + 3 digits), password. OTP emailed.",
        }),
        reqItem("Login — Step 2 (OTP → tokens)", "POST", "/auth/login-step-2/", {
          auth: noauth,
          body: jsonBody({ employee_number: "EL001", otp: "123456" }),
          description: "Tests script sets ACCESS_TOKEN, JWT, refresh_token from content.",
          event: [
            scriptEvent("test", [
              "try {",
              "  const json = pm.response.json();",
              "  pm.test('API success', () => pm.expect(json.response_type).to.eql('SUCCESS'));",
              "  const c = json.content || {};",
              "  if (c.access) {",
              "    pm.collectionVariables.set('ACCESS_TOKEN', c.access);",
              "    pm.collectionVariables.set('JWT', c.access);",
              "  }",
              "  if (c.refresh) pm.collectionVariables.set('refresh_token', c.refresh);",
              "} catch (e) { pm.test('Parse JSON', () => pm.expect.fail(e.message)); }",
            ]),
          ],
        }),
        reqItem("Refresh access token", "POST", "/auth/token/refresh/", {
          auth: noauth,
          body: jsonBody({ refresh: "{{refresh_token}}" }),
          event: [saveTokensTest],
        }),
        reqItem("Forgot password — Send OTP", "POST", "/auth/forgot-password/send-otp/", {
          auth: noauth,
          body: jsonBody({ employee_number: "EL001" }),
          description: "Sends OTP to registered employee email.",
        }),
        reqItem("Forgot password — Verify OTP", "POST", "/auth/forgot-password/verify-otp/", {
          auth: noauth,
          body: jsonBody({ employee_number: "EL001", otp: "654321" }),
        }),
        reqItem("Forgot password — Set password", "POST", "/auth/forgot-password/set-password/", {
          auth: noauth,
          body: jsonBody({
            employee_number: "EL001",
            otp: "654321",
            new_password: "NewSecurePass2!",
          }),
          description: "new_password min 8 characters.",
        }),
      ],
    },
    {
      name: "Employee",
      item: [
        reqItem("List employees", "GET", "/employees/", {
          description: "Query: role, department (UUID)",
          query: [
            { key: "role", value: "security_guard", enabled: false },
            { key: "department", value: "{{department_id}}", enabled: false },
          ],
        }),
        reqItem("Get employee by ID", "GET", "/employees/{{employee_id}}/", {}),
        reqItem("Update employee (superadmin)", "PATCH", "/employees/{{employee_id}}/", {
          body: jsonBody({
            role: "security_guard",
            department: "{{department_id}}",
            phone: "+919876543210",
          }),
        }),
        reqItem("List departments", "GET", "/departments/", {}),
      ],
    },
    {
      name: "Orders",
      item: [
        {
          name: "Vendors",
          item: [
            reqItem("List vendors", "GET", "/orders/vendors/", {}),
            reqItem("Create vendor", "POST", "/orders/vendors/", {
              body: jsonBody({
                name: "Acme Industrial Supplies",
                gstin: "27AABCU9603R1ZM",
                contact_person: "Suresh Patil",
                phone: "9822012345",
                email: "suresh@acme-industrial.example",
                address: "Plot 12, MIDC, Pune 411057",
              }),
              event: [saveVendorIdTest],
            }),
          ],
        },
        {
          name: "Purchase orders",
          item: [
            reqItem("List purchase orders", "GET", "/orders/purchase-orders/", {
              query: [
                { key: "search", value: "PO-2026", enabled: false },
                { key: "vendor", value: "{{vendor_id}}", enabled: false },
                { key: "status", value: "open", enabled: false },
              ],
            }),
            reqItem("Get purchase order detail", "GET", "/orders/purchase-orders/{{purchase_order_id}}/", {}),
            reqItem("List POs (gate alias)", "GET", "/purchase-orders/", {
              description: "Same data as orders/purchase-orders/ (legacy mount).",
            }),
            reqItem("Get PO detail (gate alias)", "GET", "/purchase-orders/{{purchase_order_id}}/", {}),
          ],
        },
      ],
    },
    {
      name: "Gate — Trucks & Drivers",
      item: [
        {
          name: "Trucks",
          item: [
            reqItem("List trucks", "GET", "/trucks/", {
              query: [{ key: "search", value: "MH12", enabled: false }],
            }),
            reqItem("Create truck", "POST", "/trucks/", {
              body: formBody([
                { key: "registration_number", value: "MH12AB1234" },
                { key: "vehicle_type", value: "truck" },
                { key: "owner_name", value: "Sharma Transport" },
                { key: "truck_photo", t: "file" },
              ]),
            }),
            reqItem("Update truck", "PATCH", "/trucks/{{truck_id}}/", {
              body: formBody([
                { key: "owner_name", value: "Sharma Transport (Updated)" },
                { key: "vehicle_type", value: "tempo" },
              ]),
            }),
          ],
        },
        {
          name: "Drivers",
          item: [
            reqItem("List drivers", "GET", "/drivers/", {
              query: [{ key: "search", value: "Ramesh", enabled: false }],
            }),
            reqItem("Create driver", "POST", "/drivers/", {
              body: formBody([
                { key: "name", value: "Ramesh Kumar" },
                { key: "mobile", value: "9876543210" },
                { key: "licence_number", value: "MH-2020-1234567" },
                { key: "licence_photo", t: "file" },
              ]),
            }),
            reqItem("Update driver", "PATCH", "/drivers/{{driver_id}}/", {
              body: formBody([{ key: "name", value: "Ramesh Kumar Singh" }]),
            }),
          ],
        },
        {
          name: "Transactions",
          description: "Superadmin for list/detail; guard/stores for currently-inside.",
          item: [
            reqItem("List transactions", "GET", "/transactions/", {
              query: [
                { key: "type", value: "inward", enabled: false },
                { key: "status", value: "inside", enabled: false },
              ],
            }),
            reqItem("Transaction detail", "GET", "/transactions/{{transaction_id}}/", {}),
            reqItem("Currently inside (transactions)", "GET", "/transactions/currently-inside/", {}),
          ],
        },
      ],
    },
    {
      name: "Gate Inward",
      description:
        "6-state flow: draft → invoice_uploaded → pending_verification → grn_generated | rejected → completed.",
      item: [
        reqItem("List inward entries", "GET", "/inward/", {
          query: [
            {
              key: "status",
              value: "pending_verification",
              enabled: false,
              description:
                "draft | invoice_uploaded | pending_verification | grn_generated | rejected | completed",
            },
            { key: "date", value: "2026-05-27", enabled: false },
          ],
        }),
        reqItem("Create inward (draft)", "POST", "/inward/", {
          body: formBody([
            { key: "vehicle_id", value: "{{truck_id}}", desc: "Required. Truck UUID." },
            { key: "driver_id", value: "{{driver_id}}", desc: "Required. Driver UUID." },
            { key: "number_of_passengers", value: "0" },
            { key: "guard_remarks", value: "Empty truck, no passengers" },
          ]),
          description:
            "Guard only. Draft create (no invoice). Legacy one-shot: add invoice_image + invoice fields instead.",
          event: [saveInwardEntryIdTest],
          response: inwardDraftSuccess.concat(inwardCreateErrorExamples),
        }),
        reqItem("Create inward (legacy one-shot)", "POST", "/inward/", {
          body: formBody([
            { key: "vehicle_id", value: "{{truck_id}}" },
            { key: "driver_id", value: "{{driver_id}}" },
            { key: "invoice_image", t: "file", desc: "Triggers legacy flow when present." },
            { key: "invoice_number", value: "INV-2026-0042" },
            { key: "invoice_from", value: "Acme Industrial Supplies" },
            { key: "po_number", value: "PO-2026-100" },
            { key: "in_time", value: "", desc: "Optional ISO datetime" },
            { key: "guard_remarks", value: "Direct create with invoice" },
          ]),
          event: [saveInwardEntryIdTest],
        }),
        reqItem("Inward detail", "GET", "/inward/{{inward_entry_id}}/", {
          event: [saveInwardEntryIdTest],
        }),
        reqItem("Update inward (draft / early)", "PATCH", "/inward/{{inward_entry_id}}/", {
          body: formBody([
            { key: "invoice_from", value: "Updated supplier name" },
            { key: "po_number", value: "PO-2026-101" },
          ]),
        }),
        reqItem("Upload invoice", "POST", "/inward/{{inward_entry_id}}/upload-invoice/", {
          body: formBody([
            {
              key: "invoice_image",
              t: "file",
              desc: "Required. Moves status draft → invoice_uploaded.",
            },
          ]),
          event: [saveInwardEntryIdTest],
        }),
        reqItem("Confirm invoice", "PATCH", "/inward/{{inward_entry_id}}/confirm-invoice/", {
          body: jsonBody({
            invoice_number: "INV-2026-0042",
            invoice_from: "Acme Industrial Supplies",
            po_number: "PO-2026-100",
            invoice_date: "2026-05-26",
            invoice_amount: "125000.50",
            material_items: materialItemsExample,
          }),
          description: "Header + material_items → pending_verification.",
        }),
        reqItem("Allow in", "POST", "/inward/{{inward_entry_id}}/allow-in/", {
          body: jsonBody({ in_time: "2026-05-27T09:30:00", guard_remarks: "" }),
          description: "Optional in_time (ISO). Empty = server now.",
        }),
        reqItem("Mark exit", "POST", "/inward/{{inward_entry_id}}/mark-exit/", {
          body: jsonBody({
            out_time: "2026-05-27T16:45:00",
            guard_remarks: "Unloaded at stores bay 3",
          }),
        }),
        reqItem("Approve (stores)", "POST", "/inward/{{inward_entry_id}}/approve/", {
          body: jsonBody({
            grn_number: "GRN/26-27/0042",
            received_invoice_hardcopy: true,
            comments: "Hard copy and GRN verified",
          }),
          description: "Stores manager. pending_verification → grn_generated.",
        }),
        reqItem("Reject (stores)", "POST", "/inward/{{inward_entry_id}}/reject/", {
          body: jsonBody({
            rejection_category: "invoice_mismatch",
            rejection_reason: "PO number does not match delivery challan",
            comments: "Ask vendor to resubmit",
          }),
        }),
        reqItem("Currently inside (inward)", "GET", "/inward/currently-inside/", {}),
      ],
    },
    {
      name: "Gate Outward",
      item: [
        reqItem("List outward entries", "GET", "/outward/", {
          query: [
            { key: "status", value: "inside", enabled: false },
            { key: "type", value: "returnable", enabled: false },
          ],
        }),
        reqItem("Create outward", "POST", "/outward/", {
          body: formBody([
            { key: "vehicle_id", value: "{{truck_id}}" },
            { key: "driver_id", value: "{{driver_id}}" },
            { key: "type", value: "returnable", desc: "standard | returnable | non_returnable" },
            { key: "document_number", value: "DC-2026-0088" },
            { key: "party_name", value: "Beta Fabricators" },
            { key: "expected_return_date", value: "2026-06-10", desc: "Required when type=returnable" },
            { key: "document_photo", t: "file", desc: "Required." },
            { key: "truck_photo_at_entry", t: "file" },
            {
              key: "items",
              value: JSON.stringify([
                { description: "Fixture jig set A", quantity: "2", unit: "nos", remarks: "" },
              ]),
              desc: "JSON array of line items",
            },
            { key: "guard_remarks", value: "Return expected within 2 weeks" },
          ]),
          event: [saveOutwardIdTest],
        }),
        reqItem("Outward detail", "GET", "/outward/{{outward_entry_id}}/", {}),
        reqItem("Allow in", "POST", "/outward/{{outward_entry_id}}/allow-in/", {
          body: jsonBody({ in_time: "2026-05-27T11:00:00" }),
        }),
        reqItem("Mark exit", "POST", "/outward/{{outward_entry_id}}/mark-exit/", {
          body: jsonBody({ out_time: "2026-05-27T14:30:00" }),
        }),
      ],
    },
    {
      name: "Returnable Return",
      item: [
        reqItem("List returnable returns", "GET", "/returnable-return/", {
          query: [{ key: "status", value: "created", enabled: false }],
        }),
        reqItem("Create returnable return", "POST", "/returnable-return/", {
          body: formBody([
            { key: "vehicle_id", value: "{{truck_id}}" },
            { key: "driver_id", value: "{{driver_id}}" },
            { key: "original_outward_id", value: "{{outward_entry_id}}" },
            { key: "condition", value: "good", desc: "good | damaged | partial" },
            { key: "quantity_returned", value: "2" },
            { key: "fully_returned", value: "true" },
            { key: "remarks", value: "All items returned in good condition" },
          ]),
          event: [saveReturnableIdTest],
        }),
        reqItem("Returnable return detail", "GET", "/returnable-return/{{returnable_return_id}}/", {}),
        reqItem("Allow in", "POST", "/returnable-return/{{returnable_return_id}}/allow-in/", {
          body: jsonBody({ in_time: "2026-05-28T09:00:00" }),
        }),
        reqItem("Mark exit", "POST", "/returnable-return/{{returnable_return_id}}/mark-exit/", {
          body: jsonBody({ out_time: "2026-05-28T10:30:00", fully_returned: true }),
          description: "Query/body fully_returned updates original outward return status.",
        }),
      ],
    },
    {
      name: "Visitors",
      item: [
        reqItem("List visitors", "GET", "/visitors/", {
          query: [{ key: "status", value: "inside", enabled: false }],
        }),
        reqItem("Create visitor", "POST", "/visitors/", {
          body: formBody([
            { key: "visitor_name", value: "Priya Sharma" },
            { key: "company", value: "TechVendor Ltd" },
            { key: "phone", value: "9123456780" },
            { key: "id_proof_type", value: "aadhar", desc: "aadhar | pan | passport | driving_licence | voter_id" },
            { key: "id_proof_number", value: "XXXX-XXXX-1234" },
            { key: "id_proof_photo", t: "file" },
            { key: "purpose", value: "Vendor audit — stores bay" },
            { key: "reference_employee_id", value: "{{reference_employee_id}}" },
            { key: "vehicle_number", value: "MH14CD5678" },
            { key: "items_carrying", value: "Laptop, sample kit" },
            { key: "nda_signed", value: "true" },
            { key: "nda_photo", t: "file", desc: "Required on create." },
            { key: "remarks", value: "Escorted by stores" },
          ]),
          event: [saveVisitorIdTest],
          response: visitorCreateSuccess,
        }),
        reqItem("Visitor detail", "GET", "/visitors/{{visitor_entry_id}}/", {}),
        reqItem("Allow in", "POST", "/visitors/{{visitor_entry_id}}/allow-in/", {
          body: jsonBody({ in_time: "2026-05-27T10:15:00" }),
          description: "400 if nda_signed=false or nda_photo missing.",
          response: visitorAllowInErrorExamples,
        }),
        reqItem("Mark exit", "POST", "/visitors/{{visitor_entry_id}}/mark-exit/", {
          body: jsonBody({ out_time: "2026-05-27T17:00:00" }),
        }),
      ],
    },
    {
      name: "Dashboard",
      description: "Superadmin JWT. KPIs, charts, recent activity, alerts.",
      item: [
        reqItem("Dashboard stats (today)", "GET", "/dashboard/stats/", {
          description:
            "content: period, visibility, kpis (inward_today, outward_today, pending_returns, visitors_today, …), charts, recent, alerts.",
        }),
        reqItem("Dashboard stats (date)", "GET", "/dashboard/stats/", {
          query: [{ key: "date", value: "2026-05-27", enabled: true }],
        }),
        reqItem("Dashboard stats (range)", "GET", "/dashboard/stats/", {
          query: [
            { key: "from_date", value: "2026-05-01", enabled: true },
            { key: "to_date", value: "2026-05-27", enabled: true },
          ],
        }),
        reqItem("Dashboard stats (period)", "GET", "/dashboard/stats/", {
          query: [{ key: "period", value: "last_7_days", enabled: true }],
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
        httpStatus: res.status,
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
