# Minecraft Dark UI Asset Manifest

This manifest is the source of truth for reusable UI assets. Assets should be component-sized, replaceable, and safe to use with QSS fallback colors.

## Global Backgrounds And Panels

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `backgrounds/dark_stone_tile` | Main app background texture | 128x128 | no | no | normal | all pages, dialogs |
| `backgrounds/secondary_stone_tile` | Slightly raised secondary texture | 128x128 | no | no | normal | editors, output areas, scroll contents |
| `panels/stone_panel` | Main content panel frame | 96x96 | yes | yes, 12px | normal | home cards, OJ analysis, file results, knowledge detail, tracker cards |
| `panels/side_panel` | Left list/sidebar panel frame | 96x96 | yes | yes, 12px | normal | knowledge list, review deck area, file/OJ side sections |
| `panels/card_panel` | Compact stat/card panel | 96x96 | yes | yes, 10px | normal/hover | home quick cards, stat cards, quiz cards |
| `panels/dialog_panel` | Dialog frame | 128x128 | yes | yes, 16px | normal | settings dialog, error dialog, add-card dialog |
| `panels/empty_state_panel` | Empty state container | 160x96 | yes | yes, 14px | normal | home activity, review empty, knowledge graph empty, file empty |

## Navigation And Tabs

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `buttons/wood_nav_normal` | Top navigation tab/button | 96x40 | yes | yes, 8px | normal | main tab bar |
| `buttons/wood_nav_hover` | Top navigation hover | 96x40 | yes | yes, 8px | hover | main tab bar |
| `buttons/wood_nav_pressed` | Top navigation pressed | 96x40 | yes | yes, 8px | pressed | main tab bar |
| `buttons/wood_nav_active` | Active tab with green crystal underline/inlay | 96x40 | yes | yes, 8px | active | main tab bar |
| `buttons/tab_normal` | Secondary tab/segmented button | 88x36 | yes | yes, 8px | normal | knowledge list/graph toggle, review modes |
| `buttons/tab_active` | Secondary selected tab | 88x36 | yes | yes, 8px | active | knowledge list/graph toggle |

## Action Buttons

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `buttons/green_action_normal` | Primary action | 96x40 | yes | yes, 8px | normal | Run, Analyze, Upload, Save, Refresh |
| `buttons/green_action_hover` | Primary hover | 96x40 | yes | yes, 8px | hover | primary actions |
| `buttons/green_action_pressed` | Primary pressed | 96x40 | yes | yes, 8px | pressed | primary actions |
| `buttons/green_action_disabled` | Primary disabled | 96x40 | yes | yes, 8px | disabled | disabled primary actions |
| `buttons/dark_button_normal` | Secondary action | 96x40 | yes | yes, 8px | normal | Prev/Next/Cancel/Delete |
| `buttons/dark_button_hover` | Secondary hover | 96x40 | yes | yes, 8px | hover | secondary actions |
| `buttons/dark_button_pressed` | Secondary pressed | 96x40 | yes | yes, 8px | pressed | secondary actions |
| `buttons/dark_button_disabled` | Secondary disabled | 96x40 | yes | yes, 8px | disabled | disabled secondary actions |
| `buttons/icon_button` | Compact square icon button frame | 40x40 | yes | yes, 6px | normal/hover/pressed/disabled | settings, plus, zoom, delete |

## Inputs And Forms

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `inputs/search_frame` | Search input frame | 160x40 | yes | yes, 8px | normal/focus/disabled | knowledge search |
| `inputs/text_input_frame` | Single-line input | 160x40 | yes | yes, 8px | normal/focus/disabled | settings, add-card dialog |
| `inputs/editor_frame` | Multiline editor/code frame | 160x96 | yes | yes, 12px | normal/focus/readonly | code editor, stdin, OJ/file text |
| `inputs/combo_frame` | Combo box frame | 160x40 | yes | yes, 8px | normal/focus/disabled | examples, provider, language, file type, deck |
| `inputs/checkbox_unchecked` | Checkbox empty state | 24x24 | yes | no | unchecked | Auto Fit |
| `inputs/checkbox_checked` | Checkbox checked state | 24x24 | yes | no | checked | Auto Fit |
| `inputs/slider_track` | Slider rail | 160x16 | yes | yes, 6px | normal/disabled | autoplay speed |
| `inputs/slider_thumb` | Slider thumb | 24x24 | yes | no | normal/hover/disabled | autoplay speed |
| `inputs/scrollbar_track` | Scrollbar track | 16x96 | yes | yes, 6px | normal | all scrollbars |
| `inputs/scrollbar_thumb` | Scrollbar thumb | 16x48 | yes | yes, 6px | normal/hover | all scrollbars |

## Lists And Content Containers

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `lists/item_normal` | List item background | 160x40 | yes | yes, 8px | normal | knowledge list, deck list, activity rows |
| `lists/item_hover` | List item hover | 160x40 | yes | yes, 8px | hover | lists |
| `lists/item_selected` | List item selected with green accent | 160x40 | yes | yes, 8px | selected | lists |
| `lists/section_header` | Section header strip | 160x32 | yes | yes, 8px | normal | Knowledge Points, Recent Activity, Test Cases |
| `containers/code_editor` | Code editor container | 160x96 | yes | yes, 12px | normal/focus | code editor and code blocks |
| `containers/output` | Output/result container | 160x96 | yes | yes, 12px | normal | tracker, test output, analysis output |
| `containers/analysis_panel` | AI analysis panel | 160x120 | yes | yes, 14px | normal | OJ/File analysis |
| `containers/flashcard_panel` | Review card panel | 180x120 | yes | yes, 14px | normal | review cards |
| `containers/knowledge_article_panel` | Knowledge article panel | 180x160 | yes | yes, 14px | normal | knowledge detail |

## Icons

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `icons/page_home` | Page icon | 32x32 | yes | no | normal/active | top nav, empty states |
| `icons/page_code` | Page icon | 32x32 | yes | no | normal/active | top nav |
| `icons/page_oj` | Page icon | 32x32 | yes | no | normal/active | top nav |
| `icons/page_file` | Page icon | 32x32 | yes | no | normal/active | top nav |
| `icons/page_review` | Page icon | 32x32 | yes | no | normal/active | top nav |
| `icons/page_knowledge` | Page icon | 32x32 | yes | no | normal/active | top nav |
| `icons/page_settings` | Page icon | 32x32 | yes | no | normal/active | settings |
| `icons/kp_pointer` | Knowledge concept | 32x32 | yes | no | normal | pointer cards/list |
| `icons/kp_array` | Knowledge concept | 32x32 | yes | no | normal | array cards/list |
| `icons/kp_heap_array` | Knowledge concept | 32x32 | yes | no | normal | heap arrays |
| `icons/kp_stream` | Knowledge concept | 32x32 | yes | no | normal | stdin/stdout |
| `icons/kp_constructor` | Knowledge concept | 32x32 | yes | no | normal | constructor/destructor |
| `icons/kp_reference` | Knowledge concept | 32x32 | yes | no | normal | references |
| `icons/kp_dynamic_memory` | Knowledge concept | 32x32 | yes | no | normal | new/delete |
| `icons/empty_creeper` | Empty visual | 96x96 | yes | no | normal | empty states |
| `icons/empty_book` | Empty visual | 96x96 | yes | no | normal | review/knowledge empty |
| `icons/empty_chest` | Empty visual | 96x96 | yes | no | normal | file/import empty |
| `icons/empty_crafting_table` | Empty visual | 96x96 | yes | no | normal | code/editor empty |
| `icons/action_run` | Action icon | 24x24 | yes | no | normal | run/analyze |
| `icons/action_refresh` | Action icon | 24x24 | yes | no | normal | refresh |
| `icons/action_prev` | Action icon | 24x24 | yes | no | normal | previous |
| `icons/action_next` | Action icon | 24x24 | yes | no | normal | next |
| `icons/action_add` | Action icon | 24x24 | yes | no | normal | add |
| `icons/action_upload` | Action icon | 24x24 | yes | no | normal | upload |
| `icons/action_search` | Action icon | 24x24 | yes | no | normal | search |
| `icons/action_zoom` | Action icon | 24x24 | yes | no | normal | zoom |

## Current SVG Fallback Additions

| Asset name | Purpose | Size | Transparent | 9-slice | States | Reused by |
| --- | --- | ---: | --- | --- | --- | --- |
| `icons/nav_home` | Current top nav home fallback | 32x32 | yes | no | static | MainWindow |
| `icons/nav_code` | Current top nav editor fallback | 32x32 | yes | no | static | MainWindow, Home, Knowledge |
| `icons/nav_oj` | Current top nav OJ fallback | 32x32 | yes | no | static | MainWindow, Home |
| `icons/nav_file` | Current top nav file fallback | 32x32 | yes | no | static | MainWindow, Home |
| `icons/nav_review` | Current top nav review fallback | 32x32 | yes | no | static | MainWindow |
| `icons/nav_knowledge` | Current top nav knowledge fallback | 32x32 | yes | no | static | MainWindow, Knowledge |
| `icons/nav_settings` | Current settings gear fallback | 32x32 | yes | no | static | MainWindow |
| `icons/block_grass` | Grass block item fallback | 40x40 | yes | no | static | Home stats, activities, Knowledge |
| `icons/item_arrow` | Inventory row arrow fallback | 24x24 | yes | no | static | Home quick cards, Knowledge |
| `icons/empty_scroll` | Upload/scroll empty state fallback | 96x96 | yes | no | static | File Import |
| `decor/torch` | Edge decoration candidate | 48x96 | yes | no | static | future page accents |
| `decor/lantern` | Edge decoration candidate | 64x64 | yes | no | static | future page accents |
| `decor/diamond_ore` | Corner/stat accent candidate | 96x96 | yes | no | static | future page accents |

## Replacement Rule

Fallback SVG files use the same base names. Image2-generated PNG/WebP assets should replace or sit beside them with the same semantic name. Theme code should resolve PNG/WebP first, then SVG fallback, so business code never changes when generated assets are swapped in.
