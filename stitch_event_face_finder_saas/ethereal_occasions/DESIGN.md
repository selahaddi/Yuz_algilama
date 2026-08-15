---
name: Ethereal Occasions
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f4'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#4b463d'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f0f1f1'
  outline: '#7d766c'
  outline-variant: '#cec5ba'
  surface-tint: '#685d4a'
  primary: '#685d4a'
  on-primary: '#ffffff'
  primary-container: '#f7e7ce'
  on-primary-container: '#726753'
  inverse-primary: '#d3c5ad'
  secondary: '#8c4b55'
  on-secondary: '#ffffff'
  secondary-container: '#feaab6'
  on-secondary-container: '#7a3c46'
  tertiary: '#5f5e5e'
  on-tertiary: '#ffffff'
  tertiary-container: '#ebe8e8'
  on-tertiary-container: '#696868'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#f0e0c8'
  primary-fixed-dim: '#d3c5ad'
  on-primary-fixed: '#221b0b'
  on-primary-fixed-variant: '#4f4533'
  secondary-fixed: '#ffd9dd'
  secondary-fixed-dim: '#ffb2bc'
  on-secondary-fixed: '#3a0915'
  on-secondary-fixed-variant: '#70343e'
  tertiary-fixed: '#e4e2e1'
  tertiary-fixed-dim: '#c8c6c6'
  on-tertiary-fixed: '#1b1c1c'
  on-tertiary-fixed-variant: '#474747'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-md-mobile:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.5'
    letterSpacing: 0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 20px
  margin-mobile: 24px
  margin-desktop: 80px
---

## Brand & Style
The design system is centered on a "Modern Romantic" aesthetic, blending the timeless elegance of high-end editorial layouts with the functional clarity of modern SaaS. It targets event planners and guests who value sophistication, ease of use, and premium presentation.

The visual language utilizes **Glassmorphism** to create a sense of light and layering. This is achieved through frosted glass effects on navigation bars and cards, allowing background colors to bleed through subtly. The interface relies on generous whitespace to evoke a feeling of "breathing room" and luxury, ensuring that even complex planning tools feel approachable and serene. The emotional response should be one of calm confidence and celebratory joy.

## Colors
The palette is rooted in a refined, warm spectrum. 
- **Primary (Champagne):** Used for large surface backgrounds and subtle decorative elements. It provides a warmer, more premium feel than pure white.
- **Secondary (Rose Gold):** Reserved for primary actions, accents, and high-importance highlights. It acts as the "jewelry" of the interface.
- **Tertiary (Deep Charcoal):** Provides necessary contrast for text and structural borders, ensuring the design remains grounded and professional rather than overly ethereal.
- **Surface/Neutral:** Pure white is used for card interiors and high-focus content areas to maintain readability against the champagne background.

## Typography
The typographic hierarchy relies on the tension between the expressive **Playfair Display** and the utilitarian **Inter**. 

Headlines should use high-contrast weights to emphasize the editorial feel. For mobile, display sizes are scaled down to prevent excessive wrapping while maintaining their distinct personality. Body text is set with generous line heights to ensure long-form reading (like guest itineraries or wedding stories) remains effortless. Labels and captions utilize increased letter-spacing and semi-bold weights for clarity at small sizes.

## Layout & Spacing
The layout follows a fluid-to-fixed model. On mobile, we utilize a 4-column grid with 24px margins to accommodate touch targets comfortably. Desktop layouts transition to a 12-column grid with a maximum content width of 1280px.

Spacing is intentionally loose. Elements are grouped using a logical "8-point" scale, but the default "Medium" spacing (24px) is the standard for most component gaps. Use the "Extra Large" (64px) spacing for section breaks to maintain the airy, premium feel. Mobile-first guest views should prioritize vertical stacking with large, tappable card surfaces.

## Elevation & Depth
Depth in this design system is created through a combination of **Ambient Shadows** and **Glassmorphism**.

1.  **The Base:** Champagne-tinted background.
2.  **The Glass Layer:** Elements like navigation bars and floating action buttons use a 12px backdrop-blur with a 60% white opacity fill and a subtle 1px white border.
3.  **The Elevated Card:** White surfaces use a multi-layered shadow (0px 4px 20px rgba(51, 51, 51, 0.05)) to appear softly lifted.
4.  **Interaction:** On hover or tap, shadows should expand slightly (8px 12px 32px rgba(183, 110, 121, 0.1)) adding a rose-gold tint to the shadow to signal life and reactivity.

## Shapes
The shape language is extremely soft and welcoming. This design system uses high-radius curves to echo the organic flow of floral arrangements and celebratory decor. 

- **Standard Buttons & Inputs:** Use the "Pill" style (fully rounded) to maximize touch-friendliness.
- **Cards & Containers:** Utilize `rounded-xl` (1.5rem / 24px) or `rounded-2xl` (2rem / 32px) for primary containers.
- **Imagery:** Photos of venues and couples should feature a minimum of 16px corner radius to stay consistent with the UI elements.

## Components
- **Buttons:** Primary buttons are pill-shaped, using the Rose Gold gradient or solid fill with white text. Secondary buttons use a Rose Gold outline with a subtle frosted glass background.
- **Cards:** Large-radius containers with a soft shadow and a 1px solid Primary-tinted border. On mobile, cards span the full width minus margins.
- **Inputs:** Floating labels with high-radius corners. Active states are indicated by a 2px Rose Gold bottom border or a subtle champagne glow.
- **Chips/Badges:** Used for guest tags (e.g., "VIP", "Vegetarian"). These should be small, pill-shaped, and use the tertiary charcoal color at 10% opacity for a subtle look.
- **Floating Guest Menu:** A fixed-position glassmorphic navigation bar at the bottom of the mobile screen, ensuring "thumb-zone" reachability for guest RSVPs and maps.
- **Imagery Containers:** Use a "soft-focus" transition when loading high-resolution event photography.