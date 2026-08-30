---
title: "Getting Started with Blowfish Theme Features"
date: 2026-08-30T14:00:00+08:00
draft: false
tags: ["tutorial", "hugo", "blowfish", "tailwind"]
categories: ["Tutorials"]
summary: "Explore the awesome features provided out-of-the-box by the Blowfish theme in Hugo."
showTableOfContents: true
---

The **Blowfish** theme brings a lot of features to Hugo without requiring extra plugins. In this article, we'll explore some of the key capabilities.

## Key Features Overview

- **Automatic Dark Mode**: Seamlessly switches based on OS preference or user toggle.
- **Client-Side Search**: Full site search without third-party services.
- **Modular Config**: Clean organization with `config/_default/*.toml`.
- **Responsive Layouts**: Looks stunning on mobile, tablet, and desktop screens.

## Quick CLI Commands

To run your Hugo blog locally with draft previews enabled:

```bash
# From the hugo-blog directory
../bin/hugo server -D
```

To compile static assets for production deployment:

```bash
../bin/hugo --minify
```

## Callouts & Alert Blocks

Blowfish supports blockquote styling for emphasis:

> **Pro Tip:** You can easily customize the color scheme in `config/_default/params.toml` by changing `colorScheme` to options like `nord`, `sunset`, `ocean`, or `blowfish`.

Happy blogging! 🎉
