# Minecraft UI Design Spec

This project uses a Minecraft-inspired dark stone UI language:

- dark stone brick global background
- wood plank top navigation buttons
- grass block green selected states
- stone 9-slice panels for content and cards
- green grass primary buttons
- dark stone secondary buttons
- inventory-style list rows
- pixel icons for pages, actions, empty states, and knowledge concepts
- restrained moss, lantern, torch, diamond ore, book, chest, and workbench-inspired decoration

## Tokens

- main background: `#111611`
- stone panel: `#242820`
- content well: `#101410`
- border: `#626A59`
- focus border: `#8CB45D`
- wood: `#6B4425`
- active green: `#78A84A`
- green hover: `#8BBC57`
- green pressed: `#557B34`
- disabled: `#3A3D35`
- primary text: `#F0E5C8`
- secondary text: `#B9B39F`
- muted text: `#777B6E`
- diamond accent: `#55D1D5`
- enchant accent: `#9B6BD3`

## Components

- Top nav: wood 9-slice button with pixel icon and active grass block state.
- Primary action: green grass 9-slice button.
- Secondary action: dark stone 9-slice button.
- Inputs: recessed dark stone frames with green focus.
- Combo box: recessed frame plus right-side square arrow button.
- Lists: inventory rows with pixel icon and selected moss/grass state.
- Panels: dark stone 9-slice with moss corner accents.
- Empty states: stone panel, centered pixel icon, green title, muted body.
- Dialogs: dark stone background, themed inputs and buttons.

Generated image2 replacements should keep the same folder and base filename as the current SVG fallbacks under `assets/ui/`.
