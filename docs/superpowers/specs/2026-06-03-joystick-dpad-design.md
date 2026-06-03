# Joystick D-Pad Replacement — Design Spec

**Date:** 2026-06-03  
**Status:** Approved for implementation  
**Scope:** `index.html` (configurator) — visual replacement of the 3×3 D-pad button grid with a Halo Ring joystick widget

---

## What We're Building

Replace the five circular D-pad buttons (keys 16–20) in the configurator's key grid with a single **Halo Ring Joystick** widget. The widget maps the same five keys onto one interactive element:

| Zone | Key ID | Label |
|---|---|---|
| Nub (center, clickable) | 20 | D-pad center |
| Top quadrant | 19 | up |
| Bottom quadrant | 16 | down |
| Left quadrant | 17 | left |
| Right quadrant | 18 | right |

---

## Visual Design

**Outer shell:** Same dark-red gradient as the existing D-pad keys (`var(--bg-key-top)` → red tint), red border at rest.  
**Hover:** Border and glow switch to `var(--amber)` — matches `.key:hover` behavior.  
**Selected zone:** Amber bg + amber border, identical to `.key.selected`.  
**Halo ring:** Conic-gradient using `var(--amber)`, rotates continuously at ~5s per revolution.  
**Nub:** Amber-bordered capsule, draggable within a max-radius of ~22px. Springs back with `cubic-bezier(0.25, 0.8, 0.25, 1)`.

**All colors use CSS variables from `:root` — no hardcoded hex values.**

---

## Interaction Model

### Drag (visual only)
- Dragging the nub in any direction is purely cosmetic — it shows intent/direction.
- On `mouseup` / `touchend`, nub springs back to center.
- No key is fired by dragging alone.

### Click zones
- Clicking in the **top / bottom / left / right** quadrant of the joystick outer area calls `selectKey(19/16/17/18)`.
- Clicking the **nub** (center) calls `selectKey(20)`.
- Click detection uses pointer position relative to widget center angle (Math.atan2).

### Press animation (nub click)
1. Halo ring briefly brightens (`filter: brightness(2.5)`) and spins faster.
2. Amber ripple ring expands from center.
3. `selectKey(20)` is called on `mouseup`.

### Selected state
- When `selectedId` is one of 16–20, the joystick highlights the corresponding zone with an amber directional arc / nub glow.
- When any other key is selected (or none), joystick renders in rest state.

---

## DOM Structure

```
.keypad-dpad-section
  .section-label  "JOYSTICK"
  .joystick-widget     ← replaces .dpad-grid
    .halo-ring
    .joystick-gate
      .joystick-zone     (subtle ring guide)
      .joystick-nub
      .nub-ripple
    .dir-zone[data-key-id="19"]   ← top
    .dir-zone[data-key-id="16"]   ← bottom
    .dir-zone[data-key-id="17"]   ← left
    .dir-zone[data-key-id="18"]   ← right
    .key-badge "20"
```

---

## CSS Approach

- New classes: `.joystick-widget`, `.halo-ring`, `.joystick-gate`, `.joystick-nub`, `.nub-ripple`, `.dir-zone`
- All new CSS added after existing `.dpad-grid` block
- Old `.dpad-grid`, `.dpad-empty`, `.key.key-dpad`, `.key.key-dpad-center` styles kept (still referenced by `test.html` if not updated simultaneously)

---

## Scope Boundary

- **In scope:** `index.html` only (configurator)
- **Out of scope for this pass:** `test.html` (tester) — can be updated separately
- **No changes** to `keys` data array, `selectKey()`, `makeKey()`, `renderKeys()` logic except the D-pad section construction

---

## Files Changed

| File | Change |
|---|---|
| `index.html` | Add joystick CSS + replace D-pad section JS in `renderKeys()` |
