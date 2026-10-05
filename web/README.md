# Care analytics demo

Next.js App Router frontend for the committed journey figures (SYNTHETIC, seed 20260929).

On Vercel, set the project Root Directory to `web`.

```bash
npm install
npm run build
npm run dev
```

`data/kpis.json` is a copy of `reports/kpis.json`. The app formats those integer counts the same way as `reports/headlines.md`, and the build fails if a displayed rate drifts from that file.
