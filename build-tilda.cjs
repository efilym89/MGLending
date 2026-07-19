const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const assetBase = "https://efilym89.github.io/MGLending/images/";
const sourceHtml = fs.readFileSync(path.join(root, "index.html"), "utf8");
const sourceCss = fs.readFileSync(path.join(root, "styles.css"), "utf8");
const sourceJs = fs.readFileSync(path.join(root, "script.js"), "utf8");

const bodyMatch = sourceHtml.match(/<body>([\s\S]*?)<script src="script\.js\?v=\d+"><\/script>\s*<\/body>/);

if (!bodyMatch) {
  throw new Error("Не удалось извлечь содержимое body из index.html");
}

const markup = bodyMatch[1]
  .trim()
  .replaceAll('src="images/', `src="${assetBase}`);

const css = sourceCss.replaceAll('url("images/', `url("${assetBase}`);

const tildaCode = `<!-- nominify begin -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">
<style>
${css}
</style>

${markup}

<script>
${sourceJs}
</script>
<!-- nominify end -->
`;

fs.writeFileSync(path.join(root, "tilda-t123.html"), tildaCode);
