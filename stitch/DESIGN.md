# Design System Document

## 1. Overview & Creative North Star: "The Silent Architect"

This design system is built for the high-performance developer who demands clarity over decoration. Our Creative North Star is **"The Silent Architect"**—a philosophy where the interface recedes into the background, leaving only the code and logic in focus. 

Unlike standard "dark mode" templates that rely on heavy borders and neon glows, this system utilizes **Tonal Architecture**. We break the "template" look by using extreme whitespace as a functional tool, intentional asymmetry in layout to guide the eye, and a sophisticated hierarchy of charcoal surfaces. It is an editorial approach to technical utility: precise, quiet, and premium.

---

## 2. Colors & Surface Logic

The palette is rooted in deep obsidian and charcoal tones, punctuated by a singular, high-precision blue.

### Surface Hierarchy & Nesting
To move beyond "flat" design without resorting to dated skeuomorphism, we use a **Layering Principle**. Depth is defined by the elevation of the surface-container tiers:
*   **The Foundation:** `surface` (#0c0e14) is your bottom-most layer.
*   **The Canvas:** `surface_container_low` (#10131b) defines primary working areas.
*   **The Interactive Layer:** `surface_container` (#151924) or `surface_container_high` (#1a1f2d) is used for cards, code blocks, or sidebars.

### The "No-Line" Rule
**Explicit Instruction:** Prohibit the use of 1px solid #000 or high-contrast borders for sectioning. 
Boundaries must be defined solely through background color shifts. If a sidebar needs to be separated from a main editor, the sidebar should use `surface_container_low` while the editor remains on `surface`. The transition is the boundary.

### Signature Textures
While the system is "flat," we avoid "dead" colors. Use a subtle linear gradient on primary CTAs:
*   **CTA Gradient:** `primary` (#afc6ff) to `primary_container` (#004398) at a 135° angle. This adds a "machined" metallic finish that feels premium and intentional.

---

## 3. Typography: Editorial Precision

We utilize **Inter** not as a generic sans-serif, but as a Swiss-style typographic grid.

*   **Display & Headlines:** Use `display-md` (2.75rem) with `font-weight: 600` and `letter-spacing: -0.02em`. Large headings should be used sparingly to create "Moments of Focus" in an otherwise dense data environment.
*   **The Body:** `body-md` (0.875rem) is the workhorse. Ensure a line-height of `1.6` to maintain readability during long coding sessions.
*   **Labels:** `label-sm` (0.6875rem) should always be `uppercase` with `letter-spacing: 0.05em`. Use `on_surface_variant` (#a5aac0) to de-emphasize metadata.

The hierarchy communicates brand identity by treating technical data with the same respect as a high-end magazine layout: ample margins, clear headers, and no clutter.

---

## 4. Elevation & Depth

We eschew traditional drop shadows in favor of **Tonal Layering** and **Ambient Light**.

*   **The Layering Principle:** Place a `surface_container_lowest` (#000000) element on top of a `surface_container_low` (#10131b) background to create "recessed" depth (ideal for terminal emulators or input zones).
*   **Ambient Shadows:** For floating modals, use a shadow with a blur of `32px`, an offset of `Y: 16px`, and an opacity of `6%`. The shadow color must be the `on_background` token (#dfe5fc) to simulate light reflecting off a dark surface.
*   **The "Ghost Border" Fallback:** If accessibility requires a border, use `outline_variant` (#41485a) at **15% opacity**. It should be felt, not seen.
*   **Glassmorphism:** For floating palettes (like a Command + K menu), use `surface_container` at 80% opacity with a `20px` backdrop-blur. This keeps the developer's context visible beneath the tool.

---

## 5. Components

### Buttons
*   **Primary:** Background: `primary` (#afc6ff), Text: `on_primary` (#003c8b). Roundedness: `md` (0.375rem). No shadow.
*   **Secondary:** Background: `secondary_container` (#383b43), Text: `on_secondary_container` (#bdbfc8).
*   **Tertiary/Ghost:** No background. Text: `primary`. High-contrast hover state using `surface_bright` (#242c3f).

### Input Fields & Terminal Blocks
*   **Style:** Background: `surface_container_lowest` (#000000). 
*   **Focus State:** A 1px "Ghost Border" using `primary` (#afc6ff) at 40% opacity. 
*   **Layout:** No dividers between inputs. Use `spacing-4` (1.4rem) to separate fields.

### Cards & Lists
*   **The "No Divider" Rule:** Forbid 1px lines between list items. Instead, use a `2px` hover state shift to `surface_container_high` (#1a1f2d) or simply use the `spacing-2` (0.7rem) vertical gap to define items.

### Status Chips
*   **Logic:** Small, `label-sm` text. Use `error_container` (#7f2927) with `on_error_container` (#ff9993) for failing builds, and `primary_container` with `primary` for active states.

---

## 6. Do’s and Don’ts

### Do:
*   **Use Asymmetry:** Place primary actions on the far right and metadata on the far left with a "gap" in between to create a sophisticated, custom feel.
*   **Embrace the Dark:** Trust the `surface` tokens. Don't feel the need to fill every corner with content. Whitespace (or "Blackspace") is a luxury.
*   **Type Hierarchy:** Use `on_surface_variant` for 80% of your UI text. Reserve `on_surface` (White) for only the most critical information.

### Don’t:
*   **No "Pure" Grays:** Never use `#333` or `#666`. Always use the tokens provided, as they contain a subtle blue/charcoal undertone that maintains the "Developer Tool" soul.
*   **No Heavy Glows:** Avoid the "Gamer" aesthetic. No neon outer glows or high-intensity gradients.
*   **No Structural Borders:** If you find yourself reaching for a border tool, ask if a `surface_container` shift can do the job instead. 

---

## 7. Spacing & Roundedness

*   **Rhythm:** Use the `spacing-4` (1.4rem) as your "Standard Unit" for padding containers. 
*   **Softness:** All interactive elements (buttons, inputs) use `md` (0.375rem). Main layout containers (cards) use `lg` (0.5rem). This slight difference in radius creates a visual nesting effect that feels "engineered."