import fs from "node:fs";
import path from "node:path";
import { request } from "playwright";

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    if (!line || line.trim().startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim();
    if (!process.env[key]) process.env[key] = value;
  }
}

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function extractToken(payload) {
  if (!payload || typeof payload !== "object") return "";
  return (
    payload.access_token ||
    payload.token ||
    payload?.data?.attributes?.token ||
    payload?.data?.token ||
    ""
  );
}

function csvEscape(value) {
  const str = value == null ? "" : String(value);
  if (str.includes('"') || str.includes(",") || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function toCsv(rows, headers) {
  const out = [headers.join(",")];
  for (const row of rows) {
    out.push(headers.map((h) => csvEscape(row[h])).join(","));
  }
  return `${out.join("\n")}\n`;
}

async function parseJsonResponse(response, context) {
  const status = response.status();
  const body = await response.text();
  let json = null;
  try {
    json = JSON.parse(body);
  } catch {
    throw new Error(`${context} returned non-JSON body (HTTP ${status}).`);
  }
  if (status >= 400) {
    throw new Error(`${context} failed (HTTP ${status}): ${JSON.stringify(json).slice(0, 500)}`);
  }
  return json;
}

async function authenticate({ apiBase, appUrl, email, password, account }) {
  const api = await request.newContext({
    extraHTTPHeaders: {
      accept: "application/vnd.api+json",
      "content-type": "application/vnd.api+json",
      origin: appUrl,
      referer: `${appUrl}/`
    }
  });
  const response = await api.post(`${apiBase}/authenticate`, {
    data: {
      username: email,
      password,
      account
    }
  });
  const payload = await parseJsonResponse(response, "/authenticate");
  await api.dispose();
  const token = extractToken(payload);
  if (!token) throw new Error("Token not found in /authenticate response.");
  return token;
}

function mapIncludedPeople(included = []) {
  const map = new Map();
  for (const item of included) {
    if (item?.type !== "people") continue;
    const attrs = item.attributes || {};
    map.set(item.id, attrs["full-name"] || attrs.name || attrs.nickname || "");
  }
  return map;
}

async function main() {
  loadEnvFile(path.resolve(".env"));

  const appUrl = process.env.CELULA_APP_URL || "https://app.celula.in";
  const apiBase = (process.env.CELULA_API_BASE || "https://api.celula.in").replace(/\/+$/, "");
  const groupId = required("CELULA_GROUP_ID");
  const maxEvents = Number(process.env.CELULA_MAX_EVENTS || 0);

  const email = process.env.CELULA_EMAIL || "";
  const password = process.env.CELULA_PASSWORD || "";
  const account = process.env.CELULA_ACCOUNT || "";
  let token = process.env.CELULA_TOKEN || "";

  if (!token) {
    if (!email || !password || !account) {
      throw new Error("Set CELULA_TOKEN or CELULA_EMAIL/CELULA_PASSWORD/CELULA_ACCOUNT.");
    }
    console.log("1/5 autenticando via /authenticate...");
    token = await authenticate({ apiBase, appUrl, email, password, account });
  } else {
    console.log("1/5 usando token fornecido em CELULA_TOKEN...");
  }

  const api = await request.newContext({
    extraHTTPHeaders: {
      accept: "application/vnd.api+json",
      "content-type": "application/vnd.api+json",
      origin: appUrl,
      referer: `${appUrl}/`,
      authorization: `Bearer ${token}`
    }
  });

  const outDir = path.resolve("artifacts", "extract");
  fs.mkdirSync(outDir, { recursive: true });

  console.log("2/5 carregando grupo e ids de eventos...");
  const groupRes = await api.get(`${apiBase}/v1/groups/${groupId}?include=events`);
  const groupJson = await parseJsonResponse(groupRes, `/v1/groups/${groupId}`);
  fs.writeFileSync(path.join(outDir, "group.json"), JSON.stringify(groupJson, null, 2), "utf8");

  const eventIds = (groupJson?.data?.relationships?.events?.data || []).map((e) => e.id);
  const selectedEventIds = maxEvents > 0 ? eventIds.slice(-maxEvents) : eventIds;
  console.log(`3/5 coletando ${selectedEventIds.length} eventos...`);

  const eventsRawPath = path.join(outDir, "group_events_raw.ndjson");
  fs.writeFileSync(eventsRawPath, "", "utf8");

  const rowRecords = [];
  const eventSummaries = [];

  for (const eventId of selectedEventIds) {
    const res = await api.get(`${apiBase}/v1/group-events/${eventId}?include=attendees,guests,group`);
    const status = res.status();
    if (status >= 400) {
      const errText = await res.text();
      eventSummaries.push({ event_id: eventId, status, error: errText.slice(0, 200) });
      continue;
    }

    const eventJson = await parseJsonResponse(res, `/v1/group-events/${eventId}`);
    fs.appendFileSync(eventsRawPath, `${JSON.stringify(eventJson)}\n`, "utf8");

    const eventData = eventJson?.data || {};
    const attrs = eventData.attributes || {};
    const rel = eventData.relationships || {};
    const attendees = new Set((rel.attendees?.data || []).map((p) => p.id));
    const guests = new Set((rel.guests?.data || []).map((p) => p.id));
    const allPeople = new Set([...guests, ...attendees]);
    const peopleById = mapIncludedPeople(eventJson.included || []);

    let present = 0;
    let absent = 0;
    for (const personId of allPeople) {
      const isPresent = attendees.has(personId);
      if (isPresent) present += 1;
      else absent += 1;
      rowRecords.push({
        event_id: eventId,
        event_date: attrs.date || "",
        event_name: attrs.name || "",
        person_id: personId,
        person_name: peopleById.get(personId) || "",
        status: isPresent ? "present" : "absent",
        group_id: rel.group?.data?.id || groupId
      });
    }

    eventSummaries.push({
      event_id: eventId,
      event_date: attrs.date || "",
      event_name: attrs.name || "",
      attendees_count: present,
      absentees_inferred_count: absent,
      people_total: allPeople.size,
      status: 200
    });
  }

  console.log("4/5 gerando artefatos normalizados...");
  fs.writeFileSync(path.join(outDir, "attendance_rows.ndjson"), rowRecords.map((r) => JSON.stringify(r)).join("\n") + (rowRecords.length ? "\n" : ""), "utf8");
  fs.writeFileSync(path.join(outDir, "event_summary.json"), JSON.stringify(eventSummaries, null, 2), "utf8");
  fs.writeFileSync(
    path.join(outDir, "attendance.csv"),
    toCsv(rowRecords, ["event_id", "event_date", "event_name", "person_id", "person_name", "status", "group_id"]),
    "utf8"
  );

  const personMap = new Map();
  for (const row of rowRecords) {
    const key = row.person_id;
    const current = personMap.get(key) || {
      person_id: row.person_id,
      person_name: row.person_name,
      present_count: 0,
      absent_count: 0,
      total_events: 0,
      attendance_rate: 0
    };
    if (row.status === "present") current.present_count += 1;
    else current.absent_count += 1;
    current.total_events += 1;
    personMap.set(key, current);
  }

  const personSummary = Array.from(personMap.values()).map((p) => ({
    ...p,
    attendance_rate: p.total_events > 0 ? Number((p.present_count / p.total_events).toFixed(4)) : 0
  }));
  personSummary.sort((a, b) => b.attendance_rate - a.attendance_rate);
  fs.writeFileSync(path.join(outDir, "attendance_summary_by_person.csv"), toCsv(personSummary, [
    "person_id",
    "person_name",
    "present_count",
    "absent_count",
    "total_events",
    "attendance_rate"
  ]), "utf8");

  await api.dispose();
  console.log("5/5 concluido.");
  console.log(`Arquivos: ${outDir}`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exitCode = 1;
});
