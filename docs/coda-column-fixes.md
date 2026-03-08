# Ross OS — Column Fixes for Comet

Open the Ross OS doc at https://coda.io/d/_dnSMMjxb_b2/RossOS_suRY7HB2 and make these fixes table by table.

---

## 1. Days
- Change `Date` column type from Text → **Date**
- Change `Stale contacts` from Text → **Lookup** → Contacts (where Next touch date <= today, or just relation to Contacts for now)
- Change `Social posts today` from Text → **Lookup** → Social Post Drafts (via Target date)
- Change `Intel events today` from Text → **Lookup** → Market Intel Events (via Signal date)

## 2. Habit Logs
- Remove the `Did it` column (duplicate — keep `Done?` and rename it to `Completed?`)
- Add column: **Count** (type: Number) — times completed, 0 or 1 for binary habits
- Add column: **Streak** (type: Formula) — consecutive days completed, reference prior Habit Logs
- Rename `Done?` → `Completed?`

## 3. Social Listening Rules
- Change `Platform` from Lookup → **Select List** with options: X / LinkedIn
- Add column: **Category** (Select List: Personal brand / Asteria brand / Market intel)
- Add column: **Entity type** (Select List: Person / Company / Topic)
- Add column: **Signal type** (Select List: Mention / Job change / Funding / Hiring / Other)
- Add column: **Priority** (Select List: High / Medium / Low)
- Add column: **Type** (Select List: Mention / Keyword / Handle / List)

## 4. Social Themes
- Rename `Content pillars` → **Description**
- Add column: **Primary platform** (Select List: X / LI / Both)

## 5. Social Platforms
- Change `Target frequency` from Text → **Number** (posts per week)

## 6. Market Intel Events
- Add column: **Linked Task** (Lookup → Personal Asteria Tasks)

## 7. Workout Instances
- The `Workout` column is Text — change to **Lookup** → Workouts.Name
- The `Date` column is Text — change to **Lookup** → Days.Date (or just use the existing `Days` lookup and remove the duplicate `Date` text column)

---

That's it. 7 tables, mostly adding missing select columns and fixing types.
