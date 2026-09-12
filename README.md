# Legacy PHILEMON NEWS redirects

This repository only redirects news.pbooks.com.tw to https://philemon.com.tw.
The manifest records all 43 HTML routes from the original source tree, including both C293/ and c293/.

Run `python generate_redirects.py` on a case-sensitive filesystem (such as Linux) to regenerate every route. Windows may display C293/index.html and c293/index.html as one file; both paths must remain in the Git tree. No source images, CSS, CSV, or site content are copied.

Known pages use their canonical manifest destination and preserve query strings and fragments through JavaScript. The 404 fallback preserves the requested path, changing only an uppercase first segment matching C plus digits. HTML redirects are client-side redirects, not HTTP 301 responses. Without JavaScript, the meta refresh and fallback link use the canonical URL without query or fragment preservation.

## Cutover

1. Merge the main website migration branch and align its GitHub Pages deployment source with its Deploy Pages workflow.
2. Bind philemon.com.tw to the main repository and complete its DNS and HTTPS setup.
3. Once news.pbooks.com.tw is released from the main repository, enable GitHub Pages here using branch domain-migration-philemon-com-tw, root /, and bind news.pbooks.com.tw.
4. Keep the legacy DNS pointing at GitHub Pages and enable HTTPS once its certificate is ready.
5. Verify the new site and old redirects publicly.

No DNS changes or Pages custom-domain transfer were performed by this migration commit. Do not modify the storefront, POS, zoo, or other services.
