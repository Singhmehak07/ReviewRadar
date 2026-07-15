# ReviewRadar Frontend

Minimal Next.js interface for the ReviewRadar FastAPI backend.

## Design direction

- Editorial, task-first layout rather than a generic centered SaaS hero
- Solid off-white, ink, blue, green, amber, and red surfaces
- No decorative gradients
- Glassmorphism limited to the sticky header, with an opaque fallback
- Native semantic controls, visible focus states, text labels, and ARIA tab behavior
- Progressive disclosure for cleaned text and review-by-review details
- Responsive layouts for desktop and mobile
- Reduced-motion support

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000.

## Environment

```text
NEXT_PUBLIC_API_URL=https://reviewradar-dxhb.onrender.com
```

## Vercel

Set the project Root Directory to `frontend` and add `NEXT_PUBLIC_API_URL` in Vercel project settings. After deployment, set Render’s `ALLOWED_ORIGINS` to the exact Vercel frontend origin.

## UI references

- WAI-ARIA Authoring Practices: https://www.w3.org/WAI/ARIA/apg/
- Accessible forms: https://web.dev/learn/accessibility/forms
- Radix accessibility guidance: https://www.radix-ui.com/primitives/docs/overview/accessibility
- shadcn/ui documentation: https://ui.shadcn.com/docs
- Next.js production checklist: https://nextjs.org/docs/app/guides/production-checklist
- Carbon accessibility guidance: https://carbondesignsystem.com/guidelines/accessibility/overview/
