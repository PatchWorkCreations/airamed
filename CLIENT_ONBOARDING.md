# AiraMed Client Onboarding

How health system clients are onboarded to AiraMed pilots — the process for the team, the links to send, and the technical reference for developers.

> **In one sentence:** paste an onboarding link into every proposal follow-up email; the client completes a 5-step wizard; their answers, pipeline status, and kickoff scheduling all land in the custom pilot dashboard at `/pilot-dashboard/clients/`.

---

## 1. The two links

| Link | URL | When to use |
|------|-----|-------------|
| **Evergreen link** | `https://airamed.org/onboard/` | Paste into any proposal or outreach email. Whoever fills in step 1 automatically gets their own client record and a personal resume link. |
| **Per-client invite link** | `https://airamed.org/onboard/<token>/` | Generated when you add a client in the dashboard. Pre-fills what we already know, tracks their progress, and always drops them at their next unfinished step. |

Both links are safe to re-send as many times as needed — progress is saved after every step, so the same link resumes exactly where the client left off.

---

## 2. The client journey (what they experience)

The wizard has **5 steps**, mirroring the pilot proposal deck:

| Step | Title | What we collect |
|------|-------|-----------------|
| 1 | **Your organization** | Health system name, pilot department/service line, clinical champion (name, role, email, phone), administrative contact, IT/security contact (optional — Phase 1 needs no EHR integration) |
| 2 | **Pilot scope** | Patient population (65+, limited-English, complex discharge…), languages beyond English, estimated patient count, visit types, preferred start date |
| 3 | **Governance & consent** | BAA requirement, privacy/compliance office review, patient consent preference (AiraMed script / their own form / needs guidance), notes for their security team |
| 4 | **Baseline metrics** | Weekly nurse callback volume, CAHPS communication score, 30-day readmission rate, follow-up no-show rate — *these are how we prove pilot outcomes at week 8–9*. Estimates OK; "we need help pulling them" is an option. |
| 5 | **Kickoff & training** | 2–3 proposed staff-briefing time slots, briefing attendees, acknowledgment of the 60-day timeline, final notes |

Details that matter:

- **Save & resume** — every step saves on submit; a banner shows the client their personal link with a copy button.
- **No skipping ahead** — clients can go back, but can't jump past their furthest unlocked step.
- **Validation** — required fields are checked server-side; errors highlight inline.
- **Confirmation screen** — after step 5 they see "Welcome aboard" plus the 60-day pilot timeline (setup weeks 1–2, active pilot weeks 3–7, evaluation weeks 8–9, go/no-go week 10) and are told a briefing time will be confirmed within one business day.
- **Locked after completion** — revisiting any step URL redirects to the confirmation page.

---

## 3. What happens automatically on completion

1. **Client welcome email** — branded, sent to the admin contact and clinical champion. Restates the pilot scope they confirmed (department, population, languages, start date, proposed briefing slot) and the 60-day timeline. Reply-to goes to `CONTACT_ADMIN_EMAIL`.
2. **Internal notification email** — sent to `CONTACT_ADMIN_EMAIL` with every answer from all 5 steps, plus their invite link.
3. **Status flip** — the client's stage moves to **Onboarding complete** in the dashboard.

Email failures never block the client: if Resend is down or unconfigured, the error is logged and the client still sees their confirmation screen.

---

## 4. The team workflow (per client)

1. **Send the proposal** (the pilot PDF) to the prospect.
2. **Add the client** — Dashboard → **Clients** → *Add a client & generate their invite link*. Enter org name, department, contact. This creates them at stage **Invited**.
3. **Copy their invite link** from the client detail page and paste it into your follow-up email.
4. **Watch the pipeline** — the moment they open the link, their stage moves to **Onboarding in progress**; the Clients list shows "Step X of 5" as they go. Nudge them if they stall.
5. **Completion** — you get the internal email; their stage shows **Onboarding complete** with all answers on their detail page.
6. **Confirm kickoff** — pick one of their proposed briefing slots, reply within one business day, then click **Advance to "Kickoff scheduled"** on their detail page.
7. **Run the pilot** — advance the stage manually as the engagement progresses: **Active pilot → Evaluation → Go/no-go decision**.

The pipeline stages:

```
Invited → Onboarding in progress → Onboarding complete → Kickoff scheduled → Active pilot → Evaluation → Go/no-go decision
```

Self-serve clients (who arrive via the evergreen link) skip stages 1–2 of the workflow — they appear in the dashboard automatically at **Onboarding in progress**, marked with source "Self-serve link".

---

## 5. The dashboard (`/pilot-dashboard/clients/`)

Part of the custom pilot dashboard (same login as survey responses — **not** Django admin).

- **Stat cards** — total clients, in onboarding, onboarding complete, active pilots.
- **Add a client** — collapsible form; creates the org and takes you to their detail page with the invite link ready to copy.
- **Evergreen link chip** — the `/onboard/` URL with a copy button, for proposals.
- **Clients table** — organization, department, contact, stage badge, onboarding progress, date added. Filterable by stage.
- **Client detail page** —
  - Visual 7-stage pipeline with the current stage highlighted
  - **Advance** button (one click to the next stage) and a **Set stage** dropdown (jump to any stage)
  - Invite link with copy button
  - Client record (name, contact, source, progress)
  - All onboarding answers, grouped by wizard step

---

## 6. Technical reference (for developers)

### Files

| File | Purpose |
|------|---------|
| `myApp/models.py` | `ClientOrganization` (pipeline status, invite token, contacts) and `OnboardingSubmission` (answers JSON, current step, completed_at) |
| `myApp/onboarding.py` | **Single source of truth for the wizard.** `STEPS` defines every step, section, and field. Also: answer extraction/validation, display grouping, summary snapshot. |
| `myApp/onboarding_views.py` | Public wizard views: start (evergreen), resume, step, done |
| `myApp/onboarding_email.py` | Welcome + internal notification emails via Resend |
| `myApp/pilot_dashboard_views.py` | Clients pipeline views (list, create, detail, status change) — bottom section |
| `myApp/templatetags/onboarding_extras.py` | `get_item` / `get_list` dict filters for the data-driven templates |
| `templates/myApp/onboarding/` | `base.html` (branded standalone layout), `step.html` (renders any step from its definition), `done.html` (confirmation + timeline) |
| `templates/myApp/pilot_dashboard/clients.html` | Pipeline list + add-client form |
| `templates/myApp/pilot_dashboard/client_detail.html` | Pipeline visual, invite link, grouped answers |

### URLs

```
# Public wizard
/onboard/                          onboarding_start     (evergreen; step 1 creates org+token)
/onboard/<uuid:token>/             onboarding_resume    (redirects to next unfinished step)
/onboard/<uuid:token>/step/<n>/    onboarding_step      (GET renders, POST saves & advances)
/onboard/<uuid:token>/done/        onboarding_done      (confirmation)

# Dashboard (behind pilot dashboard login)
/pilot-dashboard/clients/                  pilot_dashboard_clients
/pilot-dashboard/clients/new/              pilot_dashboard_client_new      (POST)
/pilot-dashboard/clients/<id>/             pilot_dashboard_client_detail
/pilot-dashboard/clients/<id>/status/      pilot_dashboard_client_status   (POST)
```

### Adding or changing a wizard question

Edit `STEPS` in `myApp/onboarding.py` — one dict per field:

```python
{'key': 'ehr_vendor', 'label': 'Which EHR do you use?', 'type': 'select',
 'required': False, 'options': ['Epic', 'Cerner', 'Meditech', 'Other']}
```

Supported types: `text`, `email`, `tel`, `date`, `textarea`, `select`, `radio`, `multiselect`, `checkbox`.

That single edit updates the wizard form, validation, the dashboard answer display, and the internal email — no template or view changes. Existing submissions are unaffected (missing answers display as "—").

### Behavior notes

- Invite tokens are `uuid4` — unguessable, no login needed for clients.
- Opening an invite link flips an **Invited** org to **Onboarding in progress**.
- Step 1 pre-fills org name/department/contact for dashboard-created clients.
- Final answers sync back onto the org record (name, department, primary contact).
- Both wizard emails are wrapped in `try/except` — failures log via `logging` and never interrupt the client.
- Models are intentionally **not** registered in Django admin; the custom dashboard is the only management UI.

### Environment variables (already used elsewhere in the app)

| Variable | Used for |
|----------|----------|
| `RESEND_API_KEY` | Sending both onboarding emails |
| `RESEND_FROM_EMAIL` | From address |
| `CONTACT_ADMIN_EMAIL` | Internal notifications + client reply-to |
| `PILOT_DASHBOARD_USERNAME` / `PILOT_DASHBOARD_PASSWORD` | Dashboard login |

### Testing

An end-to-end smoke test (wizard happy path, validation, skip-ahead guard, resume, completion lock, dashboard CRUD, status flips, 404s) was run against the full stack. To re-run the flow manually:

```
python manage.py runserver
# client view:    http://127.0.0.1:8000/onboard/
# team view:      http://127.0.0.1:8000/pilot-dashboard/clients/
```

---

## 7. Roadmap (agreed, not yet built)

- **Phase 2** — reminder emails for clients stalled mid-wizard; linking `PilotSurveyResponse` records to their `ClientOrganization` so pilot outcomes filter per client.
- **Phase 3** — staff training materials page; per-client outcome reports comparing baseline metrics (step 4) against pilot results for the week-10 go/no-go review.
- **Before real client data flows** — enable HTTPS enforcement in production and review dashboard access (single shared credential today).
