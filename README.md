# MGLending

Landing page for Annaelle laser epilation studio.

## Files

- `index.html` - page markup
- `styles.css` - visual styles and responsive layout
- `script.js` - small UI interactions
- `images/` - landing assets
- `tilda-t123.html` - full code for the Tilda T123 block

Regenerate the T123 code after editing the main landing:

```sh
node build-tilda.cjs
```

## Lead form integration

The form sends a JSON `POST` request to a server endpoint. Configure the endpoint in one of these ways:

1. Set `data-lead-endpoint="https://example.com/api/leads"` on `#client-lead-form`.
2. Set `window.ANNAELLE_LEAD_ENDPOINT` before `script.js` runs.
3. Set the form `action` attribute.

The endpoint receives the visible form fields plus UTM parameters, `fbclid`, `fbp`, `fbc`, page metadata, `submitted_at`, `form_started_at`, `form_elapsed_ms`, the empty honeypot field `website`, and a unique `submission_id`. The phone is normalized to E.164 (`+998` plus exactly 9 digits).

The endpoint must:

- allow JSON requests from `https://annaelle.uz`;
- accept `X-Submission-Id` and `Idempotency-Key` in CORS headers;
- reject any phone that does not match `^\+998\d{9}$`;
- require `consent: true` and reject a non-empty `website` honeypot;
- deduplicate by `submission_id` / `Idempotency-Key`;
- rate-limit by IP and phone and return `429` when the limit is exceeded;
- verify Cloudflare Turnstile server-side if Turnstile is enabled later;
- return a `2xx` response only after the lead has been saved successfully in Kommo.

Browser validation, the honeypot and the disabled submit button improve UX but do not replace these server-side checks.

After a successful response the form dispatches `annaelle:lead:success`. Its `detail` contains only `eventId` and HTTP `status`, so analytics can subscribe without exposing personal form data.
