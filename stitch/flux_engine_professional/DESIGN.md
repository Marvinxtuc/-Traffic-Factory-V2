```markdown
# Design System Specification: The Engineering Precision Framework

## 1. Overview & Creative North Star
**Creative North Star: The Precision Instrument**

This design system moves away from the "generic SaaS" look toward a high-end, editorial-industrial aesthetic. We are not just building a dashboard; we are crafting a professional workstation. The philosophy is rooted in **Structural Logic**—where every pixel serves a functional purpose, and beauty is derived from perfect alignment, tonal depth, and typographic authority.

To break the "template" feel, we employ **Intentional Asymmetry**. While the side navigation remains a rigid anchor, the workspace utilizes varying card widths and "nested" containers to guide the eye. We replace traditional lines with **Tonal Layering**, creating an environment that feels carved rather than drawn.

---

## 2. Colors: Tonal Architecture
We utilize a sophisticated palette that moves beyond flat fills. By using Material-inspired "On-Surface" logic, we ensure every element has a defined purpose.

### The "No-Line" Rule
**Explicit Instruction:** You are prohibited from using 1px solid borders (`#CCCCCC` or similar) to section off content.
*   **The Method:** Define boundaries solely through background shifts. Place a `surface_container_lowest` card atop a `surface_container_low` background. Use white space as the primary separator.

### Surface Hierarchy & Nesting
Treat the interface as a physical stack of technical papers.
*   **Base Layer:** `surface` (#f7f9fc)
*   **Secondary Work Area:** `surface_container_low` (#f2f4f7)
*   **Primary Interaction Cards:** `surface_container_lowest` (#ffffff)
*   **Active/Elevated Overlays:** `surface_bright` (#f7f9fc)

### The "Glass & Gradient" Rule
To inject "soul" into an engineering tool, use **Subtle Industrial Gradients**. 
*   **Primary Action Area:** Transition from `primary` (#002e70) to `primary_container` (#144494) at a 135-degree angle.
*   **Floating Navigation:** Use `surface_container_highest` with a 12px Backdrop Blur (Glassmorphism) at 85% opacity to maintain context while focusing the user.

---

## 3. Typography: Editorial Authority
We use **Inter** as our typographic engine, leveraging its mathematical precision.

*   **Display (The Overview):** Use `display-sm` (2.25rem) for high-level data summaries. It should feel like a headline in a financial journal.
*   **Headlines (The Section):** `headline-sm` (1.5rem) provides clear entry points into complex modules.
*   **Body (The Workhorse):** `body-md` (0.875rem / 14px) is our standard. Use `on_surface_variant` (#434651) for secondary text to reduce visual fatigue during long sessions.
*   **Labels (The Data):** `label-sm` (0.6875rem) in all-caps with 0.05em letter spacing for table headers and technical metadata.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are too "soft" for this engineering tool. We define depth through light logic.

*   **The Layering Principle:** Instead of a shadow, use a 1-step jump in the Surface scale. An inner content box should be `surface_container_high` sitting inside a `surface_container` parent.
*   **Ambient Shadows:** For floating modals only. Use `on_surface` color at 6% opacity, with a Blur of 24px and Y-offset of 8px. This mimics a diffuse, professional studio light.
*   **The Ghost Border Fallback:** If a border is required for high-density data tables, use `outline_variant` (#c3c6d3) at **15% opacity**. It should be felt, not seen.

---

## 5. Components: The Industrial Suite

### Buttons
*   **Primary:** A solid `primary` fill. Radius: `sm` (0.125rem) for a sharp, technical look. No shadow.
*   **Secondary:** `surface_container_highest` background with `on_surface` text.
*   **States:** On `hover`, apply a 10% white overlay. On `active`, shift to `primary_container`.

### Input Fields
*   **Form Logic:** Forgo the four-sided box. Use a `surface_container_low` background with a 1px `primary` bottom-border only during `focus`. This creates a cleaner, "blueprint" feel.
*   **Error State:** Background shifts to `error_container`, text to `on_error_container`.

### Cards & Lists
*   **Strict Rule:** No dividers. Use 24px of vertical padding (`spacing-6`) between list items. 
*   **Selection:** When a list item is selected, change the background to `secondary_container` (#c9d7fd) and add a 4px `primary` "indicator bar" on the far left.

### Real-Time Feedback Indicators
*   **Generating:** A linear indeterminate progress bar (2px height) using the `tertiary` (#572100) color, moving across the top of the card.
*   **Saved:** A micro-interaction where the `on_surface` text briefly flashes to `success_green` (#52C41A) before returning to its default state.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use extreme alignment. Every component must snap to an 8px grid.
*   **Do** embrace "Empty Space." If a card has little data, let the background bleed through rather than stretching the content.
*   **Do** use `tertiary` (#572100) for "Actionable Insights" or "AI-Generated" suggestions to distinguish them from manual data.

### Don’t
*   **Don’t** use large rounded corners. Stick to `sm` (2px) or `none` (0px) for a professional, tool-like feel.
*   **Don’t** use pure black (#000). Use `on_surface` (#191c1e) for deep blacks to maintain tonal sophistication.
*   **Don’t** use standard "heavy" shadows. If the interface looks like it’s floating in space, you’ve gone too far; it should feel like it’s resting on a desk.

---
**Director's Note:** Junior designers, remember: Complexity is not the goal—**Clarity** is. Use the hierarchy of surfaces to tell the user what is important. If everything is prominent, nothing is. Move with precision.```