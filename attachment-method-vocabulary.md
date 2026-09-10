# ToolAttachment attachment-method vocabulary

## Status

Initial reusable vocabulary for `tool_attachment.attachment_method_code` and the corresponding product-level Claim `attachment_method_code`.

This vocabulary describes the **primary physical mechanism that retains a ToolAttachment on the tool**. It is deliberately mechanism-led rather than product-led so that recommendation logic can reuse the same values across manufacturers and SKUs.

The vocabulary is an expandable, version-controlled string-code vocabulary rather than a closed database enum.

## Initial values

| Code | Meaning | Typical source language |
|---|---|---|
| `adhesive` | The attachment is retained by an adhesive bond to the tool surface. | adhesive, self-adhesive, 3M adhesive |
| `mechanical_capture` | A rigid or semi-rigid attachment is retained by mechanically capturing existing tool geometry. | bracket attaches by the handle, bracket secured around handle |
| `cinch` | A flexible loop or choke is constricted around a captive feature or the tool itself. | cinch around, choke around |
| `wrap` | Flexible material is wrapped around the tool/attachment to retain it. | wrap tape/webbing around the tool |
| `through_feature` | The attachment passes through a captive feature and is then explicitly closed or secured. | pass/thread through a captive hole or handle, then tighten/close |
| `contraction_capture` | An attachment that begins in an expanded state is retained by contracting onto an external tool section. | sleeve/tubing collapses or contracts onto the tool and fixes, grips, secures, or retains itself in place |

## Semantic boundaries

`attachment_method_code` is intentionally **not** a description of every installation detail. The following remain separate facts or future claim families:

- tool/interface geometry required by the attachment, such as a captive hole, closed handle, external section, or side handle;
- physical interface geometry provided by the attachment;
- surface or material eligibility and restrictions;
- preparation, application, curing, or dwell-time requirements;
- companion or required products;
- product names, SKUs, and branded product forms; and
- secondary installation steps when they are not the primary retention mechanism.

Examples:

- NLG Mini Adhesive D Ring -> `adhesive`; surface suitability and cure requirements are separate constraints.
- NLG Angle Grinder Bracket -> `mechanical_capture`; the required handle geometry is a separate compatibility fact.
- NLG 360 D Ring Loop / Tether Choke -> `cinch` where the source explicitly describes cinching.
- A D Ring installed by explicitly wrapping tether tape around the tool -> `wrap`; `Tether Tape` itself is a companion/product identity, not an attachment-method code.
- A loop passed through a captive hole and then closed with a threaded mechanism -> `through_feature`.
- A pre-expanded sleeve installed over an external tool section and retained when the sleeve contracts onto the tool -> `contraction_capture`; the accepted diameter envelope remains a separate dimensional-fit fact.

`contraction_capture` is deliberately not named `cold_shrink` or `heat_shrink`. Those terms describe branded/product/process families and may use different activation methods. The reusable retention fact is that an initially expanded attachment contracts onto the tool. Do not emit `contraction_capture` from a product name alone: the source must establish contraction/collapse as the retaining action.

`contraction_capture` also does not widen `mechanical_capture`, `cinch`, or `wrap`:

- a rigid bracket mechanically capturing a handle remains `mechanical_capture`;
- a loop or choke tightened around a tool remains `cinch`;
- material applied by wrapping it around a tool remains `wrap`; and
- contraction may coexist with another installation action without making those mechanisms equivalent.

## Evidence rules

A code should be emitted only when source evidence establishes the mechanism. Product names alone should not be treated as sufficient evidence when contextual installation language is available.

Negative wording must be respected. For example, an adhesive-free or no-adhesive product must not emit `adhesive` merely because the word "adhesive" appears in the source.

When a product description contains multiple installation actions, `attachment_method_code` records the primary retention mechanism. Secondary actions should be represented separately rather than collapsed into a compound method value.

## Extension rule

Add a new code only when a real product requires a retention mechanism that cannot be represented faithfully by the existing primitives. Do not add SKU-specific or application-specific aliases such as `tether_tape`, `handle_bracket`, `cold_shrink`, or `adhesive_for_metal_tools`.
