---
name: art-styles
description: >-
  Guidelines, prompt templates, frontend visual rules, and design principles for generating minimalist artwork, light backgrounds, and custom blog styling.
  Use this skill whenever generating images, post featured covers, or designing frontend visual assets for this Hugo blog.
---

# Minimalist Light-Background Art Styles Skill

This skill provides design principles, color palettes, frontend aesthetic directives, and structured prompt templates for generating clean, modern, minimalist artwork and styling with light backgrounds for blog posts and visual assets.

---

## 🎨 Core Design Principles

1. **Light & Airy Backgrounds**:
   - Always specify off-white, light gray, soft cream, or pastel background tones (e.g., `#F8FAFC`, `#FAFAF9`, `#F3F4F6`).
   - Avoid dark/pitch-black backdrops or heavy dark gradients.

2. **Generous Negative Space**:
   - Keep 60%+ of the canvas open and uncluttered.
   - Centralize or cleanly offset focal objects to create focus and breathing room.

3. **Curated Color Palette**:
   - **Primary Neutral**: Soft off-white, pale gray, warm porcelain.
   - **Accent Colors**: Muted sage green, soft slate blue, warm amber, dust rose, subtle terracotta.
   - Limit to 2–3 harmonious colors per artwork.

4. **Line & Shape Geometry**:
   - Clean vector lines, flat shape compositions, subtle isometric geometry, or fine continuous line art.
   - Soft, subtle drop shadows (if any); avoid harsh black outlines.

---

## 🎯 Frontend Design & Aesthetic Directives

### Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (`animation-delay`) creates more delight than scattered micro-interactions.
- **Backgrounds**: Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.

### Avoid generic AI-generated aesthetics:
- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character

---

## 🖼️ Standard Image Specifications

When using the `generate_image` tool for blog post featured covers:

- **Aspect Ratio**: `16:9` (for post headers/banners) or `4:3` (for item covers)
- **Style Keywords**: `minimalist`, `light background`, `clean vector illustration`, `flat design`, `soft lighting`, `high negative space`, `modern aesthetic`

---

## 📝 Prompt Templates

### 1. Minimalist Tech & Software
> **Prompt**: Minimalist flat vector illustration of a sleek laptop and clean code syntax, set against a soft off-white background (#FAFAF9). Elegant geometric shapes, muted slate blue and soft amber color accents, high negative space, modern clean design, 8k resolution, high quality.

### 2. Minimalist Reading & Books
> **Prompt**: Continuous line art illustration of an open book beside a steaming coffee cup, soft cream backdrop, minimal terracotta and sage green watercolor washes, light aesthetic, peaceful and uncluttered composition.

### 3. Minimalist Film & Cinema (NeoDB / Media)
> **Prompt**: Abstract minimalist icon of a vintage film reel and cinema projector, clean flat vector design, light warm gray background, soft pastel highlights, high contrast line art, minimal composition.

### 4. Minimalist Data & Analytics
> **Prompt**: Minimalist 3D isometric chart and abstract data nodes floating over a pristine light background, soft ambient occlusion, pastel color palette (sky blue, mint green, light slate), clean corporate tech aesthetic.

### 5. Minimalist Creative & Abstract
> **Prompt**: Minimalist mid-century modern abstract poster art, organic shapes and fine line art, warm off-white canvas texture, muted earth tones, Scandinavian interior design style, high negative space.

---

## 🚀 Workflow Checklist for Generating Blog Covers

1. Identify the blog post topic (Tech, Reading, Cinema, Thoughts, Projects).
2. Choose or adapt the appropriate **Prompt Template** above.
3. Ensure the prompt explicitly includes:
   - `light off-white background`
   - `minimalist clean vector`
   - `high negative space`
4. Call `generate_image` with `AspectRatio: "16:9"`.
5. Save the generated image to `assets/images/posts/` or `static/images/posts/`.
6. Embed in markdown frontmatter or body:
   ```yaml
   cover:
     image: "images/posts/your-cover-name.png"
     alt: "Minimalist Cover Description"
   ```
