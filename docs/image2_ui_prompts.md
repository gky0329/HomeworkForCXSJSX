# Image2 Prompts For Minecraft Dark UI Assets

Use these prompts for project-bound component assets. Prefer PNG or WebP. For transparent assets, generate on a flat chroma-key background if true alpha is unavailable, then remove the key. Do not include text in any UI asset.

## Shared Style Prefix

Use this prefix for every prompt:

> Reusable UI game asset, Minecraft-inspired dark stone interface, low saturation, pixel-art material, crisp blocky edges, dark stone bricks, oak wood, mossy green accent, readable but subtle texture, no text, no watermark, no characters unless specified, orthographic flat UI component, designed for Qt desktop application, clean 9-slice-friendly borders.

## Backgrounds And Panels

- `backgrounds/dark_stone_tile`, 128x128, opaque, 9-slice no:
  Prompt: Shared prefix + "seamless tileable dark deepslate stone brick texture, very low contrast, no cracks too bright, no bevel frame, tile edges must connect perfectly."

- `backgrounds/secondary_stone_tile`, 128x128, opaque, 9-slice no:
  Prompt: Shared prefix + "seamless tileable raised dark stone slab texture, slightly lighter than main background, subtle square pixel noise, tile edges connect perfectly."

- `panels/stone_panel`, 96x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "rectangular dark stone panel frame, transparent center and transparent outside, thick blocky stone border, 12 pixel safe stretch center, corners detailed but edges repeatable."

- `panels/side_panel`, 96x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "inventory sidebar frame, dark stone with subtle iron rim, transparent center, transparent outside, 12 pixel 9-slice border, for left menu/list panels."

- `panels/card_panel`, 96x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "compact card panel, carved stone tile border, slightly raised, transparent center, transparent outside, subtle moss corner pixels, 10 pixel 9-slice."

- `panels/dialog_panel`, 128x128, transparent, 9-slice yes:
  Prompt: Shared prefix + "modal dialog frame, darker stone bricks, heavier top bevel, transparent center/outside, 16 pixel 9-slice, refined desktop UI quality."

- `panels/empty_state_panel`, 160x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "wide empty-state framed panel, dark stone border with faint moss glow, transparent center/outside, 14 pixel 9-slice, calm and not cartoonish."

## Navigation And Tabs

- `buttons/wood_nav_normal`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "horizontal oak plank navigation button, normal state, transparent outside, 8 pixel 9-slice border, subtle dark outline."

- `buttons/wood_nav_hover`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "oak plank navigation button hover state, slightly brighter wood grain, green moss edge highlight, transparent outside, 8 pixel 9-slice."

- `buttons/wood_nav_pressed`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "oak plank navigation button pressed state, darker inset center, shadowed top edge, transparent outside, 8 pixel 9-slice."

- `buttons/wood_nav_active`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "oak plank navigation button active selected state, green emerald/moss underline and corner inlays, transparent outside, 8 pixel 9-slice."

- `buttons/tab_normal`, 88x36, transparent, 9-slice yes:
  Prompt: Shared prefix + "small secondary tab button, dark stone with oak rim, normal state, transparent outside, compact 8 pixel 9-slice."

- `buttons/tab_active`, 88x36, transparent, 9-slice yes:
  Prompt: Shared prefix + "small secondary active tab, dark stone with mossy green inset, selected state, transparent outside, compact 8 pixel 9-slice."

## Action Buttons

- `buttons/green_action_normal`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "primary action button, mossy emerald green block face, dark stone outline, normal state, transparent outside, 8 pixel 9-slice."

- `buttons/green_action_hover`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "primary action button hover, brighter mossy emerald green block face, crisp pixel edge highlight, transparent outside, 8 pixel 9-slice."

- `buttons/green_action_pressed`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "primary action button pressed, darker inset emerald green, top edge shadow, transparent outside, 8 pixel 9-slice."

- `buttons/green_action_disabled`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "primary action button disabled, desaturated green-gray block face, muted outline, transparent outside, 8 pixel 9-slice."

- `buttons/dark_button_normal`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "secondary dark stone button, normal state, blocky border, subtle center texture, transparent outside, 8 pixel 9-slice."

- `buttons/dark_button_hover`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "secondary dark stone button hover, green rim highlight, slightly lighter center, transparent outside, 8 pixel 9-slice."

- `buttons/dark_button_pressed`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "secondary dark stone button pressed, inset shadow, darker center, transparent outside, 8 pixel 9-slice."

- `buttons/dark_button_disabled`, 96x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "secondary dark stone button disabled, gray muted, low contrast, transparent outside, 8 pixel 9-slice."

- `buttons/icon_button`, 40x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "square icon button frame, compact dark stone with green hover-ready rim, transparent center/outside, no icon inside, 6 pixel 9-slice."

## Inputs And Forms

- `inputs/search_frame`, 160x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "search input frame, long dark stone trough, mossy green focus-ready bottom edge, transparent center/outside, 8 pixel 9-slice."

- `inputs/text_input_frame`, 160x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "single line text input frame, dark stone recessed rectangle, subtle inner shadow, transparent center/outside, 8 pixel 9-slice."

- `inputs/editor_frame`, 160x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "multiline code editor frame, deep blackstone border, recessed center, calm texture, transparent center/outside, 12 pixel 9-slice."

- `inputs/combo_frame`, 160x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "combo box frame, dark stone input with right dropdown compartment, small carved arrow area but no arrow symbol, transparent center/outside, 8 pixel 9-slice."

- `inputs/checkbox_unchecked`, 24x24, transparent, 9-slice no:
  Prompt: Shared prefix + "small square checkbox empty, dark stone rim and black center, transparent outside, no check mark."

- `inputs/checkbox_checked`, 24x24, transparent, 9-slice no:
  Prompt: Shared prefix + "small square checkbox checked, dark stone rim, green emerald center, white pixel check mark, transparent outside."

- `inputs/slider_track`, 160x16, transparent, 9-slice yes:
  Prompt: Shared prefix + "horizontal slider track, dark stone rail with mossy green fill channel, transparent outside, 6 pixel 9-slice."

- `inputs/slider_thumb`, 24x24, transparent, 9-slice no:
  Prompt: Shared prefix + "small square slider thumb, mossy emerald block, dark outline, transparent outside."

- `inputs/scrollbar_track`, 16x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "vertical scrollbar track, narrow dark stone groove, transparent outside, 6 pixel 9-slice."

- `inputs/scrollbar_thumb`, 16x48, transparent, 9-slice yes:
  Prompt: Shared prefix + "vertical scrollbar thumb, narrow mossy stone block, green highlight edge, transparent outside, 6 pixel 9-slice."

## Lists And Containers

- `lists/item_normal`, 160x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "inventory list item normal, dark stone strip, subtle top highlight, transparent outside, 8 pixel 9-slice."

- `lists/item_hover`, 160x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "inventory list item hover, dark stone strip with mossy edge glow, transparent outside, 8 pixel 9-slice."

- `lists/item_selected`, 160x40, transparent, 9-slice yes:
  Prompt: Shared prefix + "inventory list item selected, dark stone strip with emerald green left notch and border, transparent outside, 8 pixel 9-slice."

- `lists/section_header`, 160x32, transparent, 9-slice yes:
  Prompt: Shared prefix + "section header strip, oak plank and stone mix, subtle green pins, transparent outside, 8 pixel 9-slice."

- `containers/code_editor`, 160x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "large code editor container, blackstone recessed panel, faint grid texture, transparent center/outside, 12 pixel 9-slice."

- `containers/output`, 160x96, transparent, 9-slice yes:
  Prompt: Shared prefix + "output container, dark deepslate panel with quiet border, transparent center/outside, 12 pixel 9-slice."

- `containers/analysis_panel`, 160x120, transparent, 9-slice yes:
  Prompt: Shared prefix + "AI analysis panel, dark stone frame with subtle enchanted green pixels, transparent center/outside, 14 pixel 9-slice."

- `containers/flashcard_panel`, 180x120, transparent, 9-slice yes:
  Prompt: Shared prefix + "flashcard review panel, dark stone slab with oak corner caps, transparent center/outside, 14 pixel 9-slice."

- `containers/knowledge_article_panel`, 180x160, transparent, 9-slice yes:
  Prompt: Shared prefix + "knowledge article panel, deep stone frame with book-like carved top, transparent center/outside, 14 pixel 9-slice."

## Icons

Use the shared prefix plus:

- Page icons: "32x32 pixel icon, transparent background, no text, single object only: home base, code scroll, judge scale, file parchment, review flashcard, knowledge book, settings gear."
- Knowledge icons: "32x32 pixel icon, transparent background, no text, single object only: pointer arrow, array blocks, heap array chest blocks, input-output stream pipe, constructor/destructor hammer, reference chain link, dynamic memory emerald block."
- Empty icons: "96x96 pixel empty state icon, transparent background, no text: calm creeper face, enchanted book, closed chest, crafting table."
- Action icons: "24x24 pixel icon, transparent background, no text: run triangle, refresh arrows, previous arrow, next arrow, plus, upload arrow, magnifying glass, zoom lens."

## Implementation Notes

Generated assets should be saved under `assets/ui/<category>/<asset-name>.png` or `.webp`. The theme resolver prefers generated PNG/WebP and falls back to SVG assets with the same semantic name.
