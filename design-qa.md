# Design QA — thème clair Copro Auto

## Evidence

- Source visual truth: `C:\Users\yahya\.codex\generated_images\019f7654-06df-7c03-ad8f-b6baf4f292e7\exec-bcb85e9c-444b-4d21-9228-9cb67d4150c3.png`
- Implementation screenshot: `C:\Users\yahya\Saved Games\intelligent document automation platform\work\light-theme-preview-native.png`
- Hover-state screenshot: `C:\Users\yahya\Saved Games\intelligent document automation platform\work\light-theme-license-hover-native.png`
- Combined comparison: `C:\Users\yahya\Saved Games\intelligent document automation platform\work\light-theme-comparison-native.png`
- Source pixels: 1630 × 965, including the native title bar.
- Implementation pixels: 2884 × 1760 from a native Qt window grab.
- CSS/logical viewport requested from Qt: 1600 × 920; Windows display scaling produced the higher-density native capture.
- Density normalization: the source content below its 30 px title bar was resized to the implementation capture dimensions only for the combined visual comparison.
- State: new empty dossier, `Projet` tab, validation list visible; a second capture covers the licence-button hover state.

## Findings

- No actionable P0, P1 or P2 mismatch remains.
- Fonts and typography: Segoe UI Variable/Segoe UI, hierarchy, weights and readable French copy match the reference closely.
- Spacing and layout rhythm: sidebar, header, editor card and validation panel retain the existing responsive Qt layout and align with the reference composition.
- Colors and visual tokens: white sidebar and surfaces, pale blue-gray canvas/alternating rows, dark text, teal actions and gold header accent match the target palette.
- Image quality and asset fidelity: the screen contains no custom raster artwork that required recreation; the native application icon and Qt-rendered controls remain intact.
- Copy and content: application-specific French labels and validation messages are unchanged.
- Interaction state: the licence button remains teal with white text on hover, focus and press instead of becoming white-on-white.

Focused-region comparison was needed only for the licence control because the user supplied a separate hover-state defect. The native hover capture verifies the corrected foreground/background contrast.

## Comparison history

1. Initial light-theme pass matched the main reference, but the user identified a P1 readability failure on the licence-button hover state.
2. Added explicit `:hover`, `:pressed` and `:focus` rules after the generic button states, plus a regression test.
3. The post-fix native capture shows persistent white text on a darker teal background; no P0/P1/P2 issue remains.

## Verification

- Primary interactions covered by the existing Qt UI test suite: project editing, level selection, part addition, validation refresh and unsaved-change discard.
- Theme regression: default light palette, white sidebar and licence hover rule are asserted in `tests/test_ui.py`.
- Full suite: 46 passed, 2 skipped.
- Packaged executable: both `licensed-offline` and `fresh-unlicensed` smoke modes passed.

## Follow-up polish

- P3: a future settings control could expose the retained dark palette if users request manual theme switching; it is intentionally not part of this change.

final result: passed
