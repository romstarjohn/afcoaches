# Definition of Done — coachsurmesure

- **Status:** draft v0.2 (2026-11-17) — to be confirmed by product owner
  - v0.2: client activity feedback with images, reminders, client profile summary, coach-editable requirements
  - v0.3: onboarding questionnaire (platform standard template → coach questionnaire → versioned answers)
  - v0.5: observability rules referenced from the Item DoD (§1); logging details in `observability.md`
  - v0.4: offline-first PWA (SPA + API), offline save and sync on reconnect (§2.8); stack decided (§5 #3)
- **Applies to:** MVP of the coachsurmesure platform
- **Basis:** market analysis of 2026-11-17 (coach platforms vs. African-food trackers)

## 0. What we are building (one paragraph)

A **multi-coach platform** for fitness and nutrition coaches serving people with an **African background**,
launched in **France**, available in **French and English**. Coaches manage paying clients with training and
nutrition plans. Anyone can register in a few steps, **follow** a coach and see the coach's public plans in a
feed — **read-only, never asked to send results**. Only **clients registered with a coach** send activity
feedback and images and are prompted to do so; the coach sees a **profile summary per client** and adjusts the
client's requirements and plans from it. The differentiator is a **verified African food and dish
library** inside a coach tool; competitors are either African-food trackers without coaching (AfriCal, Didiye,
NaijaFit, TropiNutri) or coach platforms without African food data (Trainerize, Everfit, AZEOO).

The project is "done" on three levels, each building on the previous one:

| Level | Question it answers | Section |
|---|---|---|
| **Item DoD** | Is this backlog item / feature finished? | §1 |
| **MVP Release DoD** | Can we put real users on it? | §2 |
| **Project DoD (Pilot validated)** | Did the MVP prove the idea? | §3 |

---

## 1. Item DoD — every feature / backlog item

A backlog item is only closed as `done` when **all** apply:

- [ ] Acceptance hint of the backlog doc is met and demonstrated.
- [ ] Automated tests cover the new behaviour, including **permission tests** for every role that must *not*
      have access (coach of another tenant, follower, anonymous).
- [ ] Full test suite green; no new linter errors.
- [ ] All user-facing text exists in **FR and EN** (no hard-coded strings).
- [ ] Works on mobile width (360 px) and desktop; tested on iOS Safari and Android Chrome.
- [ ] No secrets, tokens or real personal data in code, fixtures, logs or screenshots.
- [ ] If it touches personal or health data: data inventory (§2.6) updated.
- [ ] If it changes the data model: migration is reversible or rollback is documented.
- [ ] Backend changes are observable and log-safe per [`observability.md`](observability.md) §3 (failures and permission denials logged with IDs and request id, no personal data or secrets in logs).
- [ ] Deployed to staging and checked there.
- [ ] Follow-ups found during the work are captured as backlog items (with deferral context), not left in heads.

---

## 2. MVP Release DoD — ready for real users

### 2.1 Coach

- [ ] Coach can register, gets verified/activated by a platform admin, and has a public profile (photo, bio,
      specialties, language).
- [ ] Coach can create, copy and edit **training plans** (days → exercises with sets/reps/rest/notes).
- [ ] Coach can create **nutrition plans** (days → meals → dishes with portion); calories and macros
      (kcal, protein, carbs, fat) are **calculated automatically** from the library.
- [ ] Coach can create **own recipes** from library ingredients; they are visible only to that coach.
- [ ] Coach sets plan visibility: **public (followers)** or **private (assigned clients only)**.
- [ ] Coach can post to their feed (text, image, optional link to a public plan).
- [ ] Coach can invite a client and assign plans with a start date.
- [ ] Coach maintains a **client requirements profile**: goal (e.g. weight loss, muscle gain, performance),
      target values, training level, available days/equipment, dietary restrictions and allergies, food
      preferences, notes. Every change is **versioned** (who, when, old → new) and visible as history.
- [ ] Coach sees a **client summary page** per client, generated from data (no AI in MVP):
  - current requirements and active plans
  - **adherence**: share of planned training days and meals reported done / partial / skipped (last 7 / 28 days)
  - **trends**: weight and other check-in values as chart; average perceived effort
  - latest feedback notes and an **image timeline** (activity and progress photos)
  - **attention flags**: no feedback for > N days (N set by coach), adherence below threshold, pain/injury note
- [ ] From the summary the coach can **update requirements and adjust/reassign plans** in ≤ 2 clicks; the
      client is notified of the change.
- [ ] Coach configures the **feedback rhythm** per client (e.g. after each workout, daily meals, weekly
      check-in day) — this drives the reminders in §2.3.
- [ ] Coach can comment on a client's feedback entry (one-way reply, no full chat).
- [ ] Coach can end a coaching relationship; the client falls back to follower status and **feedback and
      reminders stop immediately**.
- [ ] A coach can **never** see or modify another coach's clients, private plans or recipes
      (automated tenant-isolation tests for every endpoint).

### 2.2 Follower (free, simple registration)

- [ ] Registration in **≤ 3 steps** (email or social login, name, language) — no health questions asked.
- [ ] Follower can discover coaches, follow / unfollow them.
- [ ] Feed shows posts and public plans of followed coaches; plans are fully readable (meals, portions,
      macros, exercises).
- [ ] **Follower cannot send results:** no check-in, weight, photo or progress UI anywhere, no prompts or
      notifications asking for results, **and** the server rejects any such request (403, covered by tests).
- [ ] Follower can request coaching from a coach (simple contact request; payment is out of scope).

### 2.3 Client (registered with a coach)

Only users with an **active coaching relationship** are clients. Everything in this section is unavailable
to followers (see §2.2) — enforced on the server, covered by tests.

- [ ] Client accepts an invitation and gives **explicit, separate, withdrawable consent** for processing
      health data (GDPR Art. 9) before the first feedback is possible; **photo upload has its own opt-in**.
- [ ] Client sees assigned private plans plus the public feed.
- [ ] **Activity feedback** per planned training day or meal: status (done / partial / skipped), perceived
      effort (1–10) for training, optional note, **optional images** (max. 3 per entry).
- [ ] **Periodic check-in** (e.g. weekly): weight, optional measurements, wellbeing (1–5), optional progress
      photos, free-text note (e.g. pain, injury, schedule change).
- [ ] Feedback can be submitted **in ≤ 30 seconds** for the simple case (status + effort) on mobile.
- [ ] **Prompts / reminders** follow the coach's feedback rhythm: in-app badge and email; web push where the
      PWA is installed and permission granted. Client can choose channel and quiet hours; no more than
      1 reminder per due item.
- [ ] Client sees their own history and the coach's comments; can edit or delete own entries within 24 h,
      delete images at any time.
- [ ] Only the client and **their current coach** can see feedback and images.
- [ ] Withdrawing consent stops feedback and reminders and triggers deletion of feedback data and images per
      retention rules.

### 2.4 Onboarding questionnaire (client intake)

**Model — three layers, each inheriting from the one above:**

1. **Platform standard template** — maintained by platform admins, derived from the fields that are common in
   market intake forms (contact, goals, health screening, injuries/medication, activity level, availability,
   lifestyle, nutrition habits, consent) and extended with African nutrition fields. Versioned.
2. **Coach questionnaire** — created from the standard template. Standard fields are inherited; the coach can
   hide optional standard fields, reorder them, adjust help text, and **add custom fields** at any time.
   The coach **cannot change type or meaning** of a standard field, because standard fields feed the client
   requirements profile and summary (§2.1). Mandatory standard fields (health screening, consent) cannot be
   hidden.
3. **Client answers** — always bound to the questionnaire **version** the client answered.

**Field types (MVP):**

- [ ] Short text, long text, number with unit (metric; kg/cm), single choice, multiple choice, yes/no,
      scale (1–5 / 1–10), date, image upload, section header/info text (no input).
- [ ] Every field has: label and help text in **FR and EN**, required/optional, validation (min/max, length),
      and **optional single-condition display** (show only if field X has answer Y).

**Standard template content (MVP):**

- [ ] **Personal:** date of birth, sex, height, current weight, optional target weight.
- [ ] **Goals:** top 3 from a fixed list (weight loss, muscle gain, strength, endurance/performance, general
      health, postpartum, mobility/back pain), motivation (text), target timeframe.
- [ ] **Health screening:** heart condition, chest pain, dizziness/fainting, chronic conditions (incl.
      diabetes, hypertension), medication, injuries/pain, pregnancy, surgery in last 12 months. Any "yes"
      shows the client a "medical clearance recommended" notice and sets an **attention flag** for the coach
      (no diagnosis, no automatic block).
- [ ] **Activity & training:** current activity level, training experience, available days and minutes per
      session, location (home/gym/outdoor), equipment, preferred and disliked training.
- [ ] **Lifestyle:** job activity level, sleep hours, stress (1–5), optional alcohol/smoking.
- [ ] **Nutrition:** meals per day, who cooks, allergies/intolerances, dietary pattern (client-chosen, see
      §2.6 on special-category data), **staples eaten regularly** (e.g. rice, cassava/attiéké/gari, plantain,
      yam, fonio, maize) and **dishes eaten regularly** (multiple choice from the dish library + free text),
      sugary drinks, eating out frequency.
- [ ] **Optional starting photos** (front/side/back) — only with photo opt-in, never required.
- [ ] **Confirmation & consent** block.

**Behaviour:**

- [ ] Questionnaire is sent **only to clients**, after invitation acceptance and Art. 9 consent; followers
      never get it (simple registration stays ≤ 3 steps, §2.2).
- [ ] Mobile-first, progress saved automatically, can be resumed; standard template completable in
      **≤ 10 minutes**.
- [ ] Reminders follow §2.3 until completed; coach sees status (sent / in progress / completed).
- [ ] Answers to standard fields **pre-fill the client requirements profile** (§2.1); the coach reviews and
      confirms. Custom-field answers appear in the client summary under "Additional information".
- [ ] Coach can **re-send** the questionnaire (e.g. every 3 months); new answers become a new version,
      history is kept and changes are highlighted in the summary.
- [ ] Editing a questionnaire creates a new version; existing answers are never changed. Removing a field
      hides it; stored answers follow the normal retention rules.
- [ ] When the platform standard template gets a new version, coaches are **notified and can adopt** new
      standard fields — it is never forced onto running questionnaires.
- [ ] When adding custom fields, the coach sees a data-minimisation hint ("only ask what you need for
      coaching"); image-type custom fields require the client's photo opt-in.
- [ ] Automated tests: version binding, condition logic, required validation, mapping to profile, and that
      no follower or other coach can read answers.

### 2.5 Food & dish library (core asset)

- [ ] **Source and licence documented** for every imported dataset; commercial use is confirmed in writing
      where required (open question: FAO/INFOODS West African table licence — see §5).
- [ ] Ingredients carry: name FR, name EN, local names, region/country, nutrients per 100 g, source, licence.
- [ ] **≥ 150 African dishes** composed from ingredients with gram amounts and portion sizes, covering at
      least the cuisines the pilot coach uses (target: 50 must-have dishes defined with the pilot coach).
- [ ] **100 %** of dishes visible to coaches are marked **verified** by a qualified nutrition professional
      (name and date stored); unverified entries are admin-only.
- [ ] Macro calculation is unit-tested against reference values (tolerance ±2 %).
- [ ] Admins can add, edit and verify entries without developer help.

### 2.6 Privacy, security, legal (France / EU)

- [ ] Hosting and backups in the **EU**; data processing agreements signed with every processor.
- [ ] **HDS question answered in writing** (whether French *Hébergeur de Données de Santé* certification is
      required for client check-in data) and hosting chosen accordingly.
- [ ] Record of processing activities (*registre des traitements*) and data inventory written.
- [ ] DPIA (*AIPD*) assessed — carried out if required for this health data processing.
- [ ] Privacy policy, terms for users (*CGU*), terms for coaches, legal notice (*mentions légales*) and
      cookie handling published in FR and EN.
- [ ] Clear **health disclaimer**: lifestyle coaching, not medical advice; no therapeutic claims in product or
      marketing (keeps the app outside medical device regulation).
- [ ] Users can **export** their data and **delete** their account themselves (Art. 15, 17, 20).
- [ ] **Images** (activity/progress photos are highly sensitive): stored in a **private** EU bucket, served
      only via short-lived signed URLs after permission check; **EXIF/GPS metadata stripped** on upload;
      file type and size validated (max. 10 MB, JPEG/PNG/HEIC/WebP); never public, never in the feed, never
      used for marketing; deleted with the entry, on consent withdrawal and on account deletion.
- [ ] Retention period for feedback and images defined and enforced automatically (proposal: deleted
      12 months after the coaching relationship ends).
- [ ] Dietary data that may reveal religion (e.g. halal) is stored only as a client-chosen preference and
      treated as special-category data.
- [ ] HTTPS everywhere, secure headers/CSP, hashed passwords, login rate-limiting, role checks on server side.
- [ ] Dependency audit without known high/critical vulnerabilities; secrets only in environment/secret store.
- [ ] External or peer security review of auth, permissions and tenant isolation done; findings fixed or
      accepted in writing.

### 2.7 Quality & operations

- [ ] Installable as **PWA** on iOS and Android; core pages load in **< 2.5 s (LCP)** on a mid-range phone/4G.
- [ ] Core flows (register, follow, read plan, create plan, check-in) meet **WCAG 2.1 AA** basics
      (contrast, labels, keyboard, font scaling).
- [ ] Automated deployment to staging and production; **rollback tested once**.
- [ ] Daily backups; **restore tested once** with documented duration.
- [ ] Error monitoring and uptime alerting active; no personal data in logs.
- [ ] Admin runbook: activate coach, handle deletion request, restore backup, rotate secrets.

---

### 2.8 Offline & sync (installed PWA)

Architecture and sync contract: `docs/architecture.md`.

- [ ] App shell opens **without network** once installed (iOS Safari, Android Chrome).
- [ ] **Clients** can record activity feedback and check-ins offline (incl. photos, if the photo opt-in exists);
      entries are **saved on the device** and synced automatically when the connection returns.
- [ ] **Assigned plans and followed public plans** that were opened before are readable offline.
- [ ] The UI always shows whether data is synced, pending or refused; **no offline entry is ever silently lost**
      (refused entries stay visible until the user resolves them).
- [ ] Sync is idempotent (no duplicates after retries) and resumes after app restart, reconnect and re-login.
- [ ] Updates of the app are offered, never forced while unsynced input exists.
- [ ] Logout wipes all personal data from the device (IndexedDB, caches).
- [ ] Coach features are **online-first** in the MVP (plan building, client summary); offline editing for coaches is
      out of scope.

## 3. Project DoD — pilot validated

The MVP is a means; the project is done when the pilot shows whether the platform is worth scaling.
Targets are **proposals** to confirm with the product owner before the pilot starts.

- [ ] Pilot coach has used the platform **≥ 6 consecutive weeks** as the only tool for plans.
- [ ] **≥ 10 active clients** (≥ 1 check-in per week) and **≥ 100 followers** on the pilot coach.
- [ ] **≥ 80 %** of invited clients complete onboarding; median completion time **≤ 10 minutes**.
- [ ] Pilot coach has added **≥ 1 custom field** without developer help (proves extensibility).
- [ ] **≥ 60 %** of due feedback items answered by clients during the last 4 pilot weeks.
- [ ] Pilot coach confirms the client summary is enough to **adjust requirements without asking the client
      by phone/WhatsApp** in the majority of weekly reviews (measured: requirement/plan updates per client).
- [ ] **≥ 40 %** of followers active weekly (opened feed or a plan) in the last 2 pilot weeks.
- [ ] Pilot coach reports plan creation is **faster than before** (measured: minutes per nutrition plan,
      before vs. after).
- [ ] **≥ 1 follower → client conversion** observed (validates the freemium funnel).
- [ ] **≥ 5 additional coaches** on the waitlist and **≥ 2** state a concrete willingness to pay
      (price point recorded) — compensates for skipping broader coach interviews.
- [ ] No open critical/high bugs; no data-protection incident.
- [ ] Go / no-go decision for phase 2 documented (pricing, payments, native apps, English-market launch).

---

## 4. Explicitly NOT required for done (MVP)

Captured as backlog items, not part of this DoD:

- Payments between coach and client (Stripe Connect), platform billing of coaches
- Native iOS/Android apps and app-store distribution
- Chat / messaging, video calls
- AI photo recognition of meals, calorie tracking for followers
- **AI-generated client summaries** or plan suggestions (sending health data and photos to an AI provider
  needs its own legal basis, DPA and EU processing — evaluate after pilot)
- Video uploads; full two-way chat between coach and client
- Questionnaire extras: multi-condition branching, scoring/calculated fields, document uploads (e.g. medical
  certificates), sharing templates between coaches, import of forms from other platforms
- Shopping lists, wearables integration
- Marketing launch in English-speaking markets (UK/US/Nigeria/Ghana) — the product is bilingual, marketing is
  France-first
- Cuisines beyond West Africa

## 5. Open decisions & assumptions

| # | Topic | Status |
|---|---|---|
| 1 | Licence of FAO/INFOODS West African Food Composition Table for commercial use (possibly non-commercial only) | **open — blocker for §2.5** |
| 2 | HDS certification required for client check-in data? | **open — legal advice needed** |
| 3 | Tech stack: Django + DRF + PostgreSQL API, React/Vite SPA as offline-first PWA, same-origin, EU hosting | **decided 2026-11-17** (see `docs/architecture.md`) |
| 4 | Qualified nutrition professional for dish verification (who, cost) | open |
| 5 | Pilot targets in §3 | proposals, to be confirmed |
| 6 | Business model for coaches after pilot | out of MVP scope, decided at go/no-go |
| 7 | Client summary: rule-based in MVP vs. AI-generated later | rule-based recommended |
| 8 | Retention period for feedback and images (proposal: 12 months after relationship ends) | to be confirmed (legal) |
| 9 | Attention-flag thresholds (days without feedback, adherence %) | defaults to agree with pilot coach |
| 10 | Health screening: official **PAR-Q+** (copyright PAR-Q+ Collaboration; reportedly may not be altered — licence for use in a commercial app unverified) vs. **own screening questions** reviewed by a qualified professional | **open** — own questions recommended unless PAR-Q+ licence is confirmed |
| 11 | Standard template content (§2.4) | draft based on market intake forms; to review with pilot coach |
