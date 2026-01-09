# Front Office Football 9: UI/UX Reference Analysis

> Design patterns and principles extracted from Front Office Football 9 (FOF9), a game with thoughtful, information-dense UI that prioritizes function over decoration.

This document captures patterns we want to learn from and potentially adapt for Huddle.

---

## Core Design Philosophy

### Brutalist Functionality
- **No decoration for decoration's sake** - every element serves a purpose
- **Density is embraced** - lots of information per screen, but organized
- **Boxes create zones** - bordered regions with labels sitting on the border line (fieldset pattern)
- **Respects player intelligence** - teaches complexity rather than hiding it

### Color as Meaning
- **Purple/Gold palette** - creates "sports broadcast" / "official document" feel
- **Background color = record type** - cyan for draft prospects, purple for signed players
- **Semantic dots** - red for negative traits, green for positive, yellow for neutral
- **Interactive text** - purple/red colored text indicates clickable links

---

## Key UI Patterns

### 1. The Two-Tone Attribute Bars

```
┌─ Scouting (Click to view Ratings History) ──────────────────┐
│                                                              │
│  ▊ Screen Passes      ████████████░░░░░░░░░░░░░░░░░░  34    │
│  ▊ Short Passes       █████████████░░░░░░░░░░░░░░░░░  40    │
│  ▊ Medium Passes      █████████████░░░░░░░░░░░░░░░░░  40    │
│  ▊ Deep Passes        ██████████████████████████████  82    │
│  ▊ Timing             ██████████████████████████████ 100    │
│  ▊ Read Defense       ██████████░░░░░░░░░░░░░░░░░░░░  31    │
│  ▊ Overall            ███████████████░░░░░░░░░░░░░░░  47    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Experience (darker blue bar is greater)              │   │
│  │ ████████████████████████░░░░░░░░░░░░░░░░░░  QB 9    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**What makes this work:**

1. **Two layers of information:**
   - Light/gray portion = scout's estimate (opinion)
   - Dark/blue portion = experience/actual performance (fact)
   - The gap between them shows where scouts were wrong

2. **Numbers are secondary:**
   - The bar IS the primary data visualization
   - Number at right for precision if needed
   - But you evaluate by scanning bar lengths, not reading numbers

3. **For draft prospects:**
   - Only the scout estimate bar exists (no experience yet)
   - The number represents the scout's guess, which could be completely wrong
   - Creates inherent uncertainty - you're betting on opinions

4. **Category-specific attributes:**
   - QB gets: Screen Passes, Short/Medium/Long/Deep Passes, Third Down, Accuracy, Timing, Sense Rush, Read Defense, Two-Minute, Scramble Frequency
   - Each position has relevant attributes, not a universal list

5. **Clickable header:**
   - "Click to view Ratings History" - progressive disclosure
   - Summary shown by default, deep dive available

### 2. The Player Statistics Table

```
┌─ Player Statistics (click for full player statistics) ──────┐
│                                                              │
│  Year    Team   GP  GS   Att   Cmp   Yards  Av/A  TD  Int Rate│
│  ◆ 2070  NOS     4   0    45    22    286  6.36   2   1  74.8│
│  ◆ 2069  NOS    16  16   506   309   3205  6.33  27   5  93.0│
│  ◇ Career ---   73  56  1952  1163  11884  6.09  66  41  79.6│
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**What makes this work:**

1. **Just the essentials:**
   - Last 2 seasons + Career totals
   - Not 10 years of history - just what you need to evaluate quickly
   - "Click for full" if you want more

2. **Most recent first:**
   - 2070 before 2069
   - What they did lately matters most

3. **Position-contextual columns:**
   - QBs get passing stats
   - RBs would get rushing stats
   - Not a one-size-fits-all table

4. **Career row with "---" for team:**
   - Acknowledges it spans multiple teams
   - Gives lifetime context for comparison

5. **Placed at TOP of player card:**
   - Before bio, before scouting
   - What they've actually done is primary

### 3. The Player Fingerprint (Personality Panel)

```
┌─ Player Fingerprint ────────────────────────────────────────┐
│                                                              │
│  ● Health           Good                                     │
│  ● Past Injuries    View Record        (clickable link)      │
│  ● Volatility       Low (33)                                 │
│  ● QB Style         Long Passes                              │
│  ● Solecismic Test  High (31)                                │
│  ● 40-Yard Dash     4.84 seconds                             │
│  ● Bench Press      10 repetitions                           │
│  ● Agility Drill    7.80 seconds                             │
│  ● Broad Jump       8 ft., 7 in.                             │
│  ● Position Drill   69 score                                 │
│  ● Developed        100%                                     │
│  ● Mentor to        Quarterbacks                             │
│  ● Loyalty          Very High (86)                           │
│  ● Wants Winner     Very Weak (3)      (red = concerning)    │
│  ● Leadership       Very High (88)                           │
│  ● Intelligence     Low (38)                                 │
│  ● Personality      Very Weak (12)     (red = concerning)    │
│  ● Popularity       Need Scorecard (32)                      │
│  ● Attitude         Content                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**What makes this work:**

1. **Qualitative + Quantitative hybrid:**
   - "Very High (86)" - human readable with number for precision
   - "Good", "Content", "Low" - not everything needs a number
   - "Long Passes" - categorical, not numeric

2. **Color-coded values:**
   - Red text for concerning traits (Very Weak, Red Flag)
   - Normal text for neutral/positive
   - Instant visual scanning for problems

3. **Mix of physical and mental:**
   - Combine measurables (40-yard dash) with intangibles (Leadership)
   - The "fingerprint" is the whole person, not just athletic ability

4. **Clickable drill-downs:**
   - "Past Injuries → View Record"
   - "Transactions → View Transactions"
   - Summary inline, detail on demand

5. **"Developed: 100%" / "Developed: 56%":**
   - Shows how much of the player's potential you've seen
   - Draft prospects are partially developed = more uncertainty
   - Veteran at 100% = what you see is what you get

### 4. The Biographical / Status Boxes

```
┌─ Biographical Information ──────────────────────────────────┐
│                                                              │
│  ● Size            6-2, 220 lbs.                             │
│  ● Experience      12 Seasons                                │
│  ● Born            8-31-2036 (Age 34)                        │
│  ● Home Town       Durham, NC           (clickable)          │
│  ● College         Texas                                     │
│  ● League Draft    1st Round, 2060, pick 3  (clickable)      │
│  ● Drafted By      New Jersey Skyrockets                     │
│  ● QB Record       22-37                                     │
│  ● Honors          View List            (clickable)          │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─ Player Status ─────────────────────────────────────────────┐
│                                                              │
│  ● Team            New Orleans Delta Rays                    │
│  ● Acquired        Free Agency                               │
│  ● Designation     Unrestricted Free Agent                   │
│  ● Transactions    View Transactions    (clickable)          │
│  ● Joined Team     2069                                      │
│  ● Agent           Candy Heinlein                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**What makes this work:**

1. **Narrative data:**
   - "Drafted By: New Jersey Skyrockets" - tells a story
   - "QB Record: 22-37" - instant career summary
   - "Acquired: Free Agency" - how did we get this player?

2. **Consistent label:value pattern:**
   - Left column = label, right column = value
   - Easy to scan vertically for what you need

3. **The agent is visible:**
   - "Agent: Candy Heinlein"
   - Reminds you there's a human on the other side of negotiations
   - Agent personality affects negotiations

4. **Links are discoverable:**
   - Purple/red text = clickable
   - "View List", "View Transactions", "View Record"
   - You know where to go deeper

### 5. The Contract Negotiation Table

```
┌─ Negotiate Player Contract ─────────────────────────────────┐
│                                                              │
│  ┌─ Other Offers ──────────────────────────────────────┐    │
│  │                                                      │    │
│  │  (empty - but the box is present)                   │    │
│  │                                                      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Maximum Cap Value Available    $73,990,000                  │
│  Total Value of Offer           $47,280,000, 3 yrs.          │
│                                                              │
│  ────────────────────────────────────────────────────────    │
│                                                              │
│          Current   Current                   New      Cap    │
│          Salary    Bonus    Requesting      Offer    Cost    │
│  ───────────────────────────────────────────────────────    │
│  Signing                      $16,300,000  [______] $______  │
│  Bonus                                                       │
│  ───────────────────────────────────────────────────────    │
│  This      $25,230  $9,720    $8,950,000  [______] $24,100   │
│  Season    ,000     ,000                                     │
│  ───────────────────────────────────────────────────────    │
│  2070                         $10,760,000  [______] $16,190  │
│  ───────────────────────────────────────────────────────    │
│  2071                         $11,270,000  [______] $16,700  │
│  ───────────────────────────────────────────────────────    │
│  2072                         $0           [______] $0       │
│  2073                         $0           [______] $0       │
│                                                              │
│  ────────────────────────────────────────────────────────    │
│                                                              │
│  The cap cost of a season is the salary, plus a pro-rated   │
│  portion of the total bonus.                                 │
│                                                              │
│  * - Indicates this contract qualifies for the veteran      │
│  minimum salary cap discount...                              │
│                                                              │
│  # - Once the regular season has begun, only cap-out        │
│  renegotiations can take place.                              │
│                                                              │
│  [Exit]  [Franchise Salaries]  [Cap Out Offer]  [Submit]    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**What makes this work:**

1. **The gap is visible:**
   - "Requesting" column shows what THEY want
   - "New Offer" column shows what YOU'RE offering
   - The negotiation is spatial - you see the distance

2. **Year-by-year breakdown:**
   - Not just total value - see the cap implications each year
   - "Cap Cost" column shows the real impact
   - Forces you to think about cap structure

3. **"Other Offers" box exists even when empty:**
   - The absence of competing offers is information
   - When full, creates urgency and competition
   - You know what you're bidding against

4. **Explanatory footer text:**
   - Teaches cap rules in context
   - "The cap cost of a season is the salary, plus a pro-rated portion of the total bonus"
   - Doesn't assume you know everything

5. **Multiple action buttons:**
   - "Cap Out Offer" - max out at cap value
   - "Franchise Salaries" - reference other contracts
   - Different strategies, visible as options

---

## Design Principles Summary

### Information Architecture
1. **Progressive disclosure** - summary first, "click for more"
2. **Contextual density** - show what's relevant to THIS screen
3. **Position-aware content** - QB stats for QBs, not generic stats
4. **Narrative over numbers** - "Drafted by" and "QB Record: 22-37" tell stories

### Visual Language
1. **Boxes with labeled borders** - clear zones without heavy chrome
2. **Two-tone bars** - estimate vs reality, uncertainty made visible
3. **Color as semantics** - red for bad, different backgrounds for different record types
4. **Clickable text styling** - purple/red = interactive

### Uncertainty Design
1. **Bars without precise numbers** - forces qualitative thinking
2. **"Developed: 56%"** - explicitly shows how much is unknown
3. **Scout disagreement** - when scouts differ, show it
4. **No "true" values for prospects** - only opinions that could be wrong

### Interaction Patterns
1. **Actions at bottom** - data above, buttons below
2. **Edit inline** - contract negotiation has input fields in the table
3. **Links in context** - "View Record" next to the thing it expands
4. **Spatial negotiation** - "Requesting" vs "Offering" columns

---

## Patterns to Adapt for Huddle

### Player Card Improvements
- [ ] Add 2-3 year stats table at TOP of PlayerPane
- [ ] Use qualitative descriptors for scout reports ("Excellent", "Good", "Concerning")
- [ ] Show "Developed: X%" for players with remaining uncertainty
- [ ] Add narrative fields: "Acquired via", "Drafted by", "Agent"

### Draft Prospect Views
- [ ] Attribute bars as opinions, not facts
- [ ] No "true" overall rating - just scout grades
- [ ] Show scout disagreement explicitly
- [ ] "Interviewed: No" style fog indicators

### Contract Negotiation
- [ ] Year-by-year breakdown with cap implications
- [ ] "Requesting" vs "Your Offer" columns
- [ ] "Other Offers" section (even when empty)
- [ ] Explanatory text for cap rules

### Attribute Display
- [ ] Two-tone bars for signed players (estimate vs actual)
- [ ] Position-specific attribute lists
- [ ] Qualitative labels alongside numbers
- [ ] Color-coded concerning traits

---

## Screenshots Reference

Original screenshots from Front Office Football 9 are stored in the project for reference:
- Player Report (signed player): Shows two-tone bars, full data
- Player Report (draft prospect): Shows estimate-only bars, fog
- Contract Negotiation: Year-by-year table with explanatory text
- Contract Overview: Team-wide spreadsheet view

---

*This document is a living reference. Add patterns as we discover them.*
