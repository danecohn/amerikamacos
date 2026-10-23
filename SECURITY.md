# Security

- Report vulnerabilities privately through the support contact on https://altstack.io/support. Do not publish credentials or private user content in issues.
- Production API traffic requires HTTPS and normal certificate verification. Upload requests do not follow redirects. Account credentials are never attached to images, videos, arbitrary external URLs or analytics services.
- Browser pairing uses PKCE S256, a random five-minute request identifier, explicit browser approval and single-use exchange. Credentials remain out of browser URLs. API/MCP bearer keys cannot approve a full desktop session.
- Passwords stay in the browser sign-in form. Saved desktop sessions use an encrypted OS keyring; Linux without a usable keyring falls back to memory. Sessions are cleared on sign-out or expiry. Account changes invalidate pending account API responses.
- User posts are escaped before rendering in a native Qt text document; only application-generated mention, hashtag and HTTPS anchors are interactive. Links open only HTTPS URLs without embedded credentials. There is no browser engine in the social UI and no arbitrary HTML execution.
- Exact location is requested only after a native confirmation and passed to the existing optional verification/distance endpoint. The app does not persist coordinates or write private media to a local cache. Server privacy and retention policies apply.
- Attachment uploads stream from local files instead of buffering a 250 MB file on the UI thread. The backend remains responsible for authorization, limits, normalization and removal.
- Desktop notification bodies are generic. The application does not run hidden background services or post without a user action.
- Do not add production secrets, session tokens or signing certificates to Git or OneDrive project folders. Published source and CI artifacts contain no private account credentials.
