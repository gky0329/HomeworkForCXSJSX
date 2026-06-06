Minecraft UI asset folders.

The theme resolver checks each asset name in this order:
1. `.webp`
2. `.png`
3. `.svg`

Generated image2 assets should keep the same base filename as the fallback SVG.
For example, to replace the fallback button:

`assets/ui/buttons/green_action_normal.png`

No business code changes are needed when the filename and folder stay the same.
See `docs/ui_asset_manifest.md` and `docs/image2_ui_prompts.md` for the full asset list and prompts.

Current asset hookup:

- `backgrounds/dark_stone_tile` drives the global window background through `app/ui/theme/styles.py`.
- Matching `.png` files override the fallback SVGs without changing business code.

Generated PNGs currently connected:

- `backgrounds/dark_stone_tile.png`
- `backgrounds/obsidian_tile.png`
- `panels/stone_panel.png`
- `panels/parchment_panel.png`
- `buttons/wood_nav_normal.png`
- `buttons/green_action_normal.png`
- `buttons/dark_button_normal.png`
- `buttons/icon_button.png`
- `inputs/text_input_frame.png`
- `inputs/text_input_focus.png`
- `inputs/combo_frame.png`
- `lists/item_normal.png`
- `lists/item_hover.png`
- `lists/item_selected.png`
- `icons/action_add.png`
- `icons/action_ai.png`
- `icons/action_delete.png`
- `icons/action_hint.png`
- `icons/action_quiz.png`
- `icons/action_refresh.png`
- `icons/action_run.png`
- `icons/action_search.png`
- `icons/action_upload.png`
- `icons/block_grass.png`
- `icons/empty_book.png`
- `icons/empty_chest.png`
- `icons/empty_scroll.png`
- `icons/item_arrow.png`
- `icons/nav_code.png`
- `icons/nav_file.png`
- `icons/nav_home.png`
- `icons/nav_knowledge.png`
- `icons/nav_oj.png`
- `icons/nav_review.png`
- `icons/nav_settings.png`

The remaining optional assets still use SVG fallback unless a same-name PNG/WebP is added.
