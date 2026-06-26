---
name: Aura Enterprise Admin
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#464554'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#767586'
  outline-variant: '#c7c4d7'
  surface-tint: '#494bd6'
  primary: '#4648d4'
  on-primary: '#ffffff'
  primary-container: '#6063ee'
  on-primary-container: '#fffbff'
  inverse-primary: '#c0c1ff'
  secondary: '#516072'
  on-secondary: '#ffffff'
  secondary-container: '#d2e1f7'
  on-secondary-container: '#556477'
  tertiary: '#904900'
  on-tertiary: '#ffffff'
  tertiary-container: '#b55d00'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#d4e4fa'
  secondary-fixed-dim: '#b9c8de'
  on-secondary-fixed: '#0d1c2d'
  on-secondary-fixed-variant: '#39485a'
  tertiary-fixed: '#ffdcc5'
  tertiary-fixed-dim: '#ffb783'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#703700'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-max: 1440px
  gutter: 16px
  sidebar-width: 260px
  sidebar-collapsed: 72px
---

## Brand & Style

The design system is engineered for high-productivity enterprise management, specifically tailored for the complex logistics of print-on-demand and gift fulfillment. The brand personality is **technical, reliable, and precise**, prioritizing utility over decoration. 

The aesthetic follows a **Modern Corporate** approach with a focus on information density. It utilizes a structured hierarchy to help administrators navigate large datasets without cognitive overload. Key characteristics include:
- **Functional Minimalism:** Removing unnecessary flourishes to focus on data clarity.
- **Systematic Order:** Rigorous alignment and consistent spacing to indicate relationships between complex data points.
- **Utility-First:** Every visual element (color, stroke, or shadow) serves a functional purpose, such as indicating status or defining hit areas.

## Colors

This design system uses a logic-driven color palette designed for long-duration usage.
- **Primary (Indigo):** Used for primary actions, active navigation states, and focused input borders.
- **Neutrals (Slate/Zinc):** A cool-toned scale that provides a professional, "tech" feel. Surface colors utilize the lighter end of the spectrum to maintain a clean workspace.
- **Semantic Colors:** Emerald, Amber, and Rose are reserved strictly for status communication (Success/Completed, Warning/Pending, Error/Danger) to ensure they stand out against the neutral UI.
- **Text:** High-contrast slate (#0f172a) for headings and mid-contrast (#475569) for secondary data to maintain legibility in dense tables.

## Typography

The typography system relies on **Inter** for its exceptional legibility at small sizes and its neutral, modern tone. 
- **Hierarchy:** Use `display-lg` for dashboard overviews and `headline-md` for page titles. 
- **Data Density:** The primary workhorse is `body-md` (14px). For dense data tables and sidebars, `body-sm` (13px) is used to maximize the amount of information visible on a single screen.
- **Labels:** `label-md` uses uppercase with increased letter spacing for table headers and small category descriptors.
- **Technical Data:** For SKU numbers, tracking IDs, or order hashes, use a monospaced font (JetBrains Mono) at the `mono-sm` level to prevent character confusion.

## Layout & Spacing

The layout is built on a **4px baseline grid** to ensure precise alignment of dense components. 
- **Grid Model:** A 12-column fluid grid is used for the main content area, while the navigation is handled by a **collapsible sidebar**.
- **Information Density:** Gutters are kept tight (16px) to keep related data clusters close together. 
- **Desktop First:** As an admin portal, the primary focus is the Desktop (1440px+) and Laptop (1280px) experience. On Tablet, the sidebar automatically collapses to an icon-only view. 
- **Sectioning:** Content is grouped into "Cards" or "Panels" with `md` (16px) padding to maintain internal breathing room while allowing many elements to coexist.

## Elevation & Depth

This design system uses a **Tonal Layering** approach combined with subtle ambient shadows to define depth.
- **Level 0 (Background):** #f8fafc. The canvas upon which all elements sit.
- **Level 1 (Cards/Panels):** Pure white surface with a 1px border (#e2e8f0). Use a very soft, low-blur shadow (`0 1px 3px rgba(0,0,0,0.05)`) to create a subtle lift.
- **Level 2 (Modals/Dropdowns):** Pure white surface with a more pronounced shadow (`0 10px 15px -3px rgba(0,0,0,0.1)`) to indicate temporary interaction and focus.
- **Interaction:** Buttons and interactive cards use a "pressed" state where the shadow is removed and the border color is darkened, providing a tactile feel.

## Shapes

The design system utilizes **Soft** geometry. 
- **Radius-sm (4px):** Used for checkboxes, input fields, and small badges.
- **Radius-md (8px):** The standard for buttons, KPI cards, and modal containers.
- **Radius-lg (12px):** Reserved for large dashboard sections or decorative image containers.
The use of 4px and 8px radii ensures the UI feels modern and approachable without losing the professional "sharpness" required for an enterprise tool.

## Components

### Data Tables
- **Headers:** `label-md` text, slate-50 background, 1px bottom border.
- **Rows:** 48px height for standard density; 40px for "compact" mode. Zebra striping is not used; instead, use a subtle hover state (#f1f5f9).
- **Cells:** Vertical alignment centered. Numeric data should be tabular-lining and right-aligned.

### Buttons & Inputs
- **Primary Button:** Indigo (#6366f1) with white text. 8px radius.
- **Secondary Button:** White background with 1px border (#e2e8f0).
- **Inputs:** 1px border (#cbd5e1). On focus, border changes to primary indigo with a 2px soft indigo glow.

### Status Badges
- Small, `label-md` text.
- Use a "Soft" style: light background (10% opacity of the semantic color) with high-contrast text. For example, "Pending" is Amber-100 background with Amber-700 text.

### KPI Cards
- Large, bold metric (`display-lg`).
- Subtle 1px border.
- Include a small trend indicator (tiny sparkline or percentage chip) in the top right corner.

### Sidebar
- Dark or high-contrast slate.
- Active state: Indigo left-edge "pill" indicator (4px width) and a slightly lightened background for the active item.