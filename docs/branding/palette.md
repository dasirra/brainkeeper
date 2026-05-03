# brainkeeper color palette

Source: <https://coolors.co/2b2d42-8d99ae-edf2f4-ef233c-d80032>

Five colors. Three structural (dark / mid / light), two brand reds.
Use the structural three for layout and type, save the reds for brand
accents — never use both reds in the same composition.

| Hex | Name | Role | Where it shows up |
|---|---|---|---|
| `#2B2D42` | Space Cadet | Ink — primary text, dark UI | Body text, the "Brain" wordmark, brain illustration shadows |
| `#8D99AE` | Cool Gray | Slate — secondary text, dividers, muted icons | Brain mid-tones, captions, disabled states |
| `#EDF2F4` | Antiflash White | Paper — backgrounds, surfaces | Logo background, page background, code-block backgrounds |
| `#EF233C` | Imperial Red | Brand — primary accent | The "Keeper" wordmark, primary buttons, link hover, key callouts |
| `#D80032` | Cadmium Red | Brand-strong — pressed/hover state for the brand red | Button-pressed states, focused outlines on red elements |

## Practical guidance

- **Body text on Paper**: `#2B2D42` on `#EDF2F4` — high contrast, AAA at any size.
- **Secondary text on Paper**: `#8D99AE` on `#EDF2F4` — reads as "less important". Don't use for body copy; contrast is too low for long reads.
- **Brand red on Paper**: `#EF233C` on `#EDF2F4` — pops without being neon. Use sparingly — one accent per screen-area is the rule.
- **Don't pair the two reds**: `#EF233C` and `#D80032` are too close — together they look like a glitch. Pick one as base, use the other only as the interactive state of the same element.
- **Dark mode**: this palette is built light-first. For a dark variant, invert structural roles (Paper → Ink as background, Ink → Paper as text) and keep `#EF233C` as the accent — it remains legible on dark.

## Badge colors

For shields.io URL params, use the hex without the `#`:

- Primary brand: `?color=EF233C`
- Ink (default badge bg): `?color=2B2D42`
- Slate (info/neutral): `?color=8D99AE`

Example: `https://img.shields.io/badge/status-active-EF233C`
