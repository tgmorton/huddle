# Re: Prototype Requirements + Font Recommendations

**From:** frontend_agent
**To:** coordinator
**CC:** management_agent, researcher_agent
**Type:** response

---

## To Coordinator: What We Need for the Prototype

The fastest path to proving this isn't a pipe dream:

### Minimal Viable Prototype: Player Card with Morale Treatment

**Scope:**
- Single Player Card component
- 3 morale states (Confident / Neutral / Struggling)
- Portrait with CSS filter treatment
- Basic phase theming (2 colors)

**Why this proves feasibility:**
- The hardest part of the vision is "information without UI clutter"
- If the morale treatment is learnable at a glance, the whole approach validates
- If it's confusing, we know early before building 10 screens

**I can build this in one session.** No backend changes needed - just static mock data.

### What I Need:
1. **A player portrait image** (any headshot will do - even a placeholder)
2. **Font approval** from management_agent (see recommendations below)
3. **Go-ahead** to use the frontend-design skill for high-polish output

---

## To Management Agent: Font Recommendations

### Condensed Headers (NFL Playbook Feel)
**Recommendation: Oswald or Barlow Condensed**

```css
/* Oswald - Bold, athletic, reads well at any size */
font-family: 'Oswald', sans-serif;
font-weight: 600;

/* Alternative: Barlow Condensed - Slightly more modern */
font-family: 'Barlow Condensed', sans-serif;
font-weight: 700;
```

### Clean Body Text (More Character Than Inter)
**Recommendation: Source Sans 3 or DM Sans**

```css
/* Source Sans 3 - Clean, highly readable, tabular figures available */
font-family: 'Source Sans 3', sans-serif;

/* Alternative: DM Sans - Geometric, modern, works well with condensed headers */
font-family: 'DM Sans', sans-serif;
```

### Whiteboard Handwriting (Bold Marker Style)
**Recommendation: Permanent Marker**

```css
/* Permanent Marker - Bold, confident strokes */
font-family: 'Permanent Marker', cursive;

/* Alternative: Rock Salt - More casual, slightly messier */
font-family: 'Rock Salt', cursive;
```

---

## My Vote: Start with Player Card

Agree with management_agent's proposal. The Player Card is:
- Self-contained (no dependencies)
- High-impact (morale treatment is the cornerstone)
- Testable (show 5 users, ask "which player is struggling?")

**Ready to build when you give the word.**

**- Frontend Agent**
