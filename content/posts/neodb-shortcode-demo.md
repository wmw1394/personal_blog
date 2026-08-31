---
title: "NeoDB Shortcode Showcase"
date: 2026-08-31T22:00:00+08:00
draft: false
tags: ["neodb", "hugo", "shortcode"]
categories: ["Showcase"]
summary: "Demonstration of NeoDB shortcode card rendering."
---

# NeoDB Shortcode Cards Demo

Here are examples of how NeoDB items render as offline static cards in blog posts:

## 1. Book Entry (Synced with Custom Comment)

{{< neodb "https://neodb.social/books/0189a123-4567-89ab-cdef-0123456789ab" "Inner comment overriding cached comment text!" >}}

## 2. Movie Entry (Synced with Cached Comment)

{{< neodb "https://neodb.social/movies/0189b987-6543-21ba-fedc-9876543210fe" >}}

## 3. Unsynced Item (Fallback Placeholder)

{{< neodb "https://neodb.social/game/99999999-9999-9999-9999-999999999999" >}}
