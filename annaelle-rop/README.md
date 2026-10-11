# Annaelle — vacancy for Head of Sales

Separate landing page based on the approved ROP mockup. The laserologist landing remains in `annaelle-work/`.

- `index.html`: vacancy copy and form fields; edit these directly for further revisions.
- `base.css`: existing Annaelle styles, copied from the laserologist landing.
- `styles.css`: ROP layout, responsive rules and application result styles.
- `script.js`: menu, validation, application preparation, mobile CTA and Tilda integration.
- `application.mjs`: phone/resume checks and Telegram message formatting.
- `assets/master-client.jpg`: original Annaelle bank photo BSA08104 (Контент цвет 1), displayed at its natural aspect ratio.
- `tilda-t123.html`: a separate Tilda T123 wrapper with automatic iframe height and mobile CTA.

## Local review

Serve the repository root with a local HTTP server. Open `/annaelle-rop/?preview=1` to exercise the form without opening Telegram or sending any candidate data. The generated application remains visible locally for review. Remove `preview=1` to use the normal career flow.

The normal form prepares an application and opens `@annaellelaser`. The candidate must send the message in Telegram. A resume URL is included in the prepared text. A selected PDF/DOC/DOCX file must be attached manually in Telegram; the site does not upload the file. The client-sales API is not used for job applications.

The page includes the current ROP duties, requirements, metrics and employment conditions. Fixed team headcounts and the direct task assignment duty were removed at the owner's request. Compensation includes a KPI bonus. The spelling `Altegio` is used consistently.

## Publication

The main page is hosted on GitHub Pages at `https://efilym89.github.io/MGLending/annaelle-rop/`. Paste the complete contents of `tilda-t123-code.txt` (identical to `tilda-t123.html`) into a Tilda T123 block on the vacancy page (suggested route: `/vacancyrop`). Further content and layout edits are made in this GitHub folder; the Tilda wrapper does not need replacement unless its integration changes.

The iframe uses `embed=1`; regular iframe previews do not need this flag. The parent validates the frame origin and source and accepts only the `annaelle-rop-layout` and `annaelle-rop-scroll` messages. UTM source, campaign and content parameters are forwarded to the vacancy. No client acquisition endpoint or Meta `Lead` event is called.

Check application helpers with:

```sh
node --test annaelle-rop/tests/application.test.mjs
```
