# The "Posting" Aesthetic: A Design System for TUIs

The secret to `posting`'s beauty is that **it does not treat the terminal like a terminal.** It treats it like a web browser canvas, using layers, transparency, state-driven animations, and semantic blocking.

## 1. The "Section" Architecture (The Core Building Block)

Instead of styling individual widgets, `posting` uses a unified container philosophy. Every major part of the screen (Request, Response, Collection) is a "Section."

### The Technique

Define a `.section` CSS class that handles the "active state" logic. When *any* child widget inside a section gains focus, the *entire* border lights up.

**SCSS Implementation:**

```scss
.section {
  /* 1. Modern Geometry */
  border: round $accent 40%; /* 40% opacity when inactive */

  /* 2. Distinctive Titles */
  border-title-color: $text-accent 50%;
  border-title-align: right; /* Pushing titles right looks cleaner/techy */

  /* 3. The "Glow" Effect */
  /* The :focus-within pseudo-class is the secret sauce. */
  &:focus-within {
    border: round $accent 100%; /* Full brightness when active */
    border-title-color: $foreground;
    border-title-style: bold;

    /* Optional: Add a subtle background tint to the active area */
    background: $surface 5%;
  }
}
```

**For Your Agent App:**
Wrap your "Chat History", "Tool Output", and "User Input" in `Vertical` containers and apply the `.section` class. As the user moves focus, the active panel will visually "wake up."

---

## 2. Semantic & Glassy Theming

`posting` avoids flat colors. It uses **Alpha Channels** (transparency) to create depth, making the app feel like a floating overlay rather than a flat console.

### The Technique

* **Semantic Names:** Define colors by function (`$surface`, `$panel`, `$accent`), not by hue (`blue`, `red`).
* **The "Glassy" Look:** Define a base `$surface` color and apply opacity in SCSS.

**SCSS Implementation:**

```scss
/* Deep background */
Screen { background: $background; }

/* Panels float above background using transparency */
Panel {
  background: $surface 50%; /* Allows background to bleed through */
}

/* Specific elements are fully opaque for readability */
Input {
  background: $surface 100%;
}
```

**For Your Agent App:**
If your agent is "thinking," use a darker transparent background. When it needs input, make the input box opaque. This creates visual depth.

---

## 3. Dynamic Feedback via State Classes

The UI feels "alive" because it reacts instantly to data. It doesn't just print text; it changes the container's physical properties (borders/colors) based on state.

### The Technique

Use Python `watch_` methods to toggle CSS classes on the container.

**Python Implementation:**

```python
# In your Agent Widget
def watch_agent_state(self, state: str):
    self.remove_class("thinking", "error", "success")
    if state == "thinking":
        self.add_class("thinking")
    elif state == "error":
        self.add_class("error")
```

**SCSS Implementation:**

```scss
/* State: Error */
/* A thick left border is a great non-intrusive error indicator */
.error {
  border-left: thick $error;
  background: $error-muted;
}

/* State: Thinking */
.thinking {
  border-color: $accent;
  border-title-color: $accent;
  /* You can even animate tints here */
}
```

---

## 4. Advanced Polish & Texture

These are the "micro-interactions" that make the app feel professional.

### A. The "Hatch" Pattern for Empty States

Don't leave empty panels blank. Use a diagonal "hatch" pattern to indicate "intentionally empty."

```scss
$empty-hatch: right $surface-lighten-1 70%;

.empty-state-label {
  hatch: $empty-hatch;
  color: $text-muted;
}
```

### B. Cinematic Modals

When a popup appears, dim the rest of the application to focus attention.

```scss
ModalScreen {
  background: black 30%; /* Dims the app behind the modal */
}

.modal-dialog {
  background: $surface;
  border: wide $accent; /* Thicker border for "lift" */
}
```

### C. The "HUD" Style Command Palette

Don't center everything. Anchoring menus to the side (like a sidebar) feels more like a dashboard/HUD.

```scss
CommandPalette {
  align-horizontal: left;
  & CommandList {
    border-left: wide $accent; /* Strong vertical line anchors the eye */
  }
}
```

### D. Custom Scrollbars

Standard terminal scrollbars ruin the immersion. Tint them to match your theme.

```scss
* {
  scrollbar-color: $primary 20%;
  scrollbar-background: $surface-darken-1;
  scrollbar-color-active: $primary;
}
```

---

## 5. Rich Text in Borders

Textual allows `rich` markup inside border titles. Use this to display status badges directly in the frame.

**Python Implementation:**

```python
def update_title(self, status: str):
    # Inject styling directly into the string
    if status == "COMPLETED":
        badge = "[bold green]● DONE[/]"
    elif status == "PROCESSING":
        badge = "[bold yellow]○ THINKING[/]"

    self.border_title = f"Agent Output {badge}"
```

This keeps the interior clean for content while using the border for metadata.

---

## Summary Checklist

1. **Block it out:** Divide your screen into `Vertical` containers and apply a `.section` class to them.
2. **Make it glow:** Add `&:focus-within { border: round $accent 100%; }` to your sections.
3. **Add depth:** Use `$surface 50%` for backgrounds instead of solid colors.
4. **Hatch empty space:** If the agent hasn't generated output yet, show a hatched placeholder.
5. **Reactive Borders:** If the agent hits an error, toggle a `.error` class that adds `border-left: thick $red`.
6. **Dim the lights:** If asking for user permission/auth, use a `ModalScreen` with `background: black 50%`.

By following this "Posting Architecture," your agent tool will feel like a cohesive, modern application rather than a script running in a console.

---

## Huddle-Specific Applications

### Field View
- Uses Rich Text rendering for colored field elements
- Team-colored end zones with hex colors from team data
- High-contrast ball marker (white on brown)
- Orange first-down line, blue scrimmage markers

### Future Improvements
- Apply `.section` class to play-log, stats-panel
- Add `:focus-within` glow effects
- Consider alpha transparency for panels
- State classes for game events (touchdown, turnover, etc.)
