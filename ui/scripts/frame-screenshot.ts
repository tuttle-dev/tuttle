/**
 * Add macOS-style window frame (rounded corners, border, drop shadow)
 * to a raw screenshot.
 *
 * Usage:
 *   npx tsx scripts/frame-screenshot.ts <input.png> <output.png>
 *
 * Can also be imported and called programmatically.
 */

import sharp from "sharp";
import * as path from "path";

const CORNER_RADIUS = 10;
const BORDER_WIDTH = 1;
const SHADOW_BLUR = 24;
const SHADOW_OFFSET_Y = 8;
const PADDING = SHADOW_BLUR + 16;
const BORDER_COLOR = "#3a3a3a";
const SHADOW_COLOR = "rgba(0,0,0,0.55)";
const BG_COLOR = "#1a1a1a";

// macOS traffic light dots (matches trafficLightPosition in main.ts)
const TRAFFIC_X = 16;
const TRAFFIC_Y = 18;
const DOT_RADIUS = 6;
const DOT_SPACING = 20;
const DOTS = [
  { color: "#ff5f57", cx: TRAFFIC_X + DOT_RADIUS, cy: TRAFFIC_Y + DOT_RADIUS },
  { color: "#febc2e", cx: TRAFFIC_X + DOT_RADIUS + DOT_SPACING, cy: TRAFFIC_Y + DOT_RADIUS },
  { color: "#28c840", cx: TRAFFIC_X + DOT_RADIUS + DOT_SPACING * 2, cy: TRAFFIC_Y + DOT_RADIUS },
];

export async function frameScreenshot(
  inputPath: string,
  outputPath: string
): Promise<void> {
  const raw = sharp(inputPath);
  const meta = await raw.metadata();
  const w = meta.width!;
  const h = meta.height!;

  const canvasW = w + PADDING * 2;
  const canvasH = h + PADDING * 2;

  // SVG mask for rounded corners on the screenshot
  const roundedMask = Buffer.from(
    `<svg width="${w}" height="${h}">
      <rect width="${w}" height="${h}" rx="${CORNER_RADIUS}" ry="${CORNER_RADIUS}" fill="white"/>
    </svg>`
  );

  // Apply rounded corners to the screenshot
  const rounded = await raw
    .composite([{ input: roundedMask, blend: "dest-in" }])
    .png()
    .toBuffer();

  // Background canvas with shadow and border
  const frameSvg = Buffer.from(
    `<svg width="${canvasW}" height="${canvasH}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="${SHADOW_OFFSET_Y}" stdDeviation="${SHADOW_BLUR / 2}" flood-color="${SHADOW_COLOR}"/>
        </filter>
      </defs>
      <rect width="${canvasW}" height="${canvasH}" fill="${BG_COLOR}"/>
      <rect x="${PADDING}" y="${PADDING}" width="${w}" height="${h}"
            rx="${CORNER_RADIUS}" ry="${CORNER_RADIUS}"
            fill="none" stroke="none" filter="url(#shadow)"/>
      <rect x="${PADDING}" y="${PADDING}" width="${w}" height="${h}"
            rx="${CORNER_RADIUS}" ry="${CORNER_RADIUS}"
            fill="black" filter="url(#shadow)"/>
      <rect x="${PADDING - BORDER_WIDTH}" y="${PADDING - BORDER_WIDTH}"
            width="${w + BORDER_WIDTH * 2}" height="${h + BORDER_WIDTH * 2}"
            rx="${CORNER_RADIUS + BORDER_WIDTH}" ry="${CORNER_RADIUS + BORDER_WIDTH}"
            fill="none" stroke="${BORDER_COLOR}" stroke-width="${BORDER_WIDTH}"/>
    </svg>`
  );

  // Traffic light dots overlay (drawn on top of the screenshot)
  const dotsSvg = Buffer.from(
    `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
      ${DOTS.map(
        (d) => `<circle cx="${d.cx}" cy="${d.cy}" r="${DOT_RADIUS}" fill="${d.color}"/>`
      ).join("\n      ")}
    </svg>`
  );

  await sharp(frameSvg)
    .composite([
      { input: rounded, left: PADDING, top: PADDING },
      { input: dotsSvg, left: PADDING, top: PADDING },
    ])
    .png()
    .toFile(outputPath);
}

async function main() {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) {
    console.error("Usage: frame-screenshot.ts <input.png> <output.png>");
    process.exit(1);
  }
  await frameScreenshot(path.resolve(input), path.resolve(output));
  console.log(`✓ ${output}`);
}

const isDirectRun = process.argv[1]?.includes("frame-screenshot");
if (isDirectRun) {
  main().catch((err) => {
    console.error("Framing failed:", err);
    process.exit(1);
  });
}
