const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const siteBase = "https://efilym89.github.io/MGLending/";
const assetBase = `${siteBase}images/`;
const workAssetBase = `${siteBase}annaelle-work/assets/`;
const buildVersion = "20260823-2";
const sourceHtml = fs.readFileSync(path.join(root, "index.html"), "utf8");

const bodyMatch = sourceHtml.match(/<body>([\s\S]*?)<script src="i18n\.js\?v=[^"]+"><\/script>\s*<script src="script\.js\?v=[^"]+"><\/script>\s*<\/body>/);

if (!bodyMatch) {
  throw new Error("Не удалось извлечь содержимое body из index.html");
}

const markup = bodyMatch[1]
  .trim()
  .replaceAll("images/", assetBase)
  .replaceAll("annaelle-work/assets/", workAssetBase);

const tildaCode = `<!-- nominify begin -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://efilym89.github.io" crossorigin>
<link rel="preload" href="${workAssetBase}hero-main-960.webp" as="image" type="image/webp" fetchpriority="high">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">
<link href="${siteBase}styles.css?v=${buildVersion}" rel="stylesheet">

${markup}

<script src="${siteBase}i18n.js?v=${buildVersion}"></script>
<script src="${siteBase}script.js?v=${buildVersion}"></script>
<!-- nominify end -->
`;

fs.writeFileSync(path.join(root, "tilda-t123.html"), tildaCode);
fs.writeFileSync(path.join(root, "tilda-t123-code.txt"), tildaCode);

console.log(`T123 code generated: ${Buffer.byteLength(tildaCode, "utf8")} bytes`);
