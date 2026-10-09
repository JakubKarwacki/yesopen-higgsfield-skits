// The look of the ComfyUI canvas: the One Dark colours of VS Code (as a ComfyUI colour palette, chosen for everyone who
// opens this server) and JetBrains Mono (the Nerd Font build when it is installed on the viewer's computer, otherwise
// the web font) with a clear hierarchy: node titles bold and bright, socket and widget labels medium, values and prompts
// regular. Sizes stay as they are, so the nodes keep their layout (gpu/tools/comfy_geometry.json is measured with it).
import { app } from "../../scripts/app.js";

const FAMILY = '"JetBrainsMono Nerd Font", "JetBrainsMono NF", "JetBrains Mono", ui-monospace, monospace';
const WEB_FONT = "https://cdn.jsdelivr.net/npm/@fontsource/jetbrains-mono@5.1.1";   // 400, 500, 700 as a fallback

// One Dark (Atom / VS Code)
const OD = {
  bg: "#282c34", bgDark: "#21252b", bgDeep: "#1e2227", bgLight: "#2c313a", line: "#3e4451", gutter: "#4b5263",
  comment: "#5c6370", fg: "#abb2bf", fgBright: "#d7dae0", white: "#e6e9ef",
  red: "#e06c75", orange: "#d19a66", yellow: "#e5c07b", green: "#98c379", cyan: "#56b6c2", blue: "#61afef", purple: "#c678dd",
};

const PALETTE = {
  id: "one-dark",
  name: "One Dark",
  light_theme: false,
  colors: {
    node_slot: {
      IMAGE: OD.blue, MASK: OD.cyan, LATENT: OD.purple, MODEL: OD.green, CLIP: OD.yellow, VAE: OD.red,
      CONDITIONING: OD.orange, AUDIO: OD.cyan, VIDEO: OD.orange, INT: OD.orange, FLOAT: OD.orange, STRING: OD.green,
      BOOLEAN: OD.cyan, NOISE: OD.fg, SAMPLER: OD.purple, SIGMAS: OD.yellow, GUIDER: OD.blue, CLIP_VISION: OD.yellow,
    },
    litegraph_base: {
      BACKGROUND_IMAGE: "",
      CLEAR_BACKGROUND_COLOR: OD.bgDark,
      NODE_TITLE_COLOR: OD.fgBright,
      NODE_SELECTED_TITLE_COLOR: "#ffffff",
      NODE_TEXT_SIZE: 14,
      NODE_TEXT_COLOR: OD.fg,
      NODE_TEXT_HIGHLIGHT_COLOR: "#ffffff",
      NODE_SUBTEXT_SIZE: 12,
      NODE_DEFAULT_COLOR: OD.line,
      NODE_DEFAULT_BGCOLOR: OD.bg,
      NODE_DEFAULT_BOXCOLOR: OD.comment,
      NODE_DEFAULT_SHAPE: 2,
      NODE_BOX_OUTLINE_COLOR: OD.blue,
      NODE_BYPASS_BGCOLOR: OD.purple,
      NODE_ERROR_COLOUR: OD.red,
      DEFAULT_SHADOW_COLOR: "rgba(0,0,0,0.5)",
      DEFAULT_GROUP_FONT: 24,
      WIDGET_BGCOLOR: OD.bgDeep,
      WIDGET_OUTLINE_COLOR: OD.line,
      WIDGET_TEXT_COLOR: OD.white,
      WIDGET_SECONDARY_TEXT_COLOR: OD.fg,
      WIDGET_DISABLED_TEXT_COLOR: OD.comment,
      LINK_COLOR: OD.blue,
      EVENT_LINK_COLOR: OD.purple,
      CONNECTING_LINK_COLOR: OD.green,
      BADGE_FG_COLOR: OD.fg,
      BADGE_BG_COLOR: OD.line,
    },
    comfy_base: {
      "fg-color": OD.fg,
      "bg-color": OD.bg,
      "comfy-menu-bg": OD.bgDark,
      "comfy-menu-secondary-bg": OD.bgLight,
      "comfy-input-bg": OD.bgDeep,
      "input-text": OD.fgBright,
      "descrip-text": OD.fg,
      "drag-text": OD.fgBright,
      "error-text": OD.red,
      "border-color": OD.line,
      "tr-even-bg-color": OD.bg,
      "tr-odd-bg-color": OD.bgLight,
      "content-bg": OD.bgLight,
      "content-fg": OD.fg,
      "content-hover-bg": OD.line,
      "content-hover-fg": "#ffffff",
      "bar-shadow": "rgba(0,0,0,.4) 0 0 0.5rem",
    },
  },
};

const CSS = `
.lg-node, .lg-node input, .lg-node textarea, .lg-node select, .lg-node button { font-family: ${FAMILY} !important; }
.lg-node [data-testid="node-title"] { font-weight: 700 !important; color: ${OD.white} !important; letter-spacing: .01em; }
.lg-node .text-node-component-slot-text { font-weight: 500 !important; color: ${OD.fgBright} !important; }
.lg-node [data-testid="widget-layout-field-label"] { font-weight: 500 !important; color: ${OD.fg} !important; }
.lg-node input, .lg-node select, .lg-node [data-testid="widget-select-default-trigger"] { font-weight: 400 !important; color: ${OD.white} !important; }
.lg-node textarea { font-weight: 400 !important; color: ${OD.fgBright} !important; background: ${OD.bgDeep} !important; line-height: 1.45 !important; }
`;

async function usePalette() {
  const settings = app.extensionManager?.setting;
  if (!settings) return;
  const custom = settings.get("Comfy.CustomColorPalettes") || {};
  if (JSON.stringify(custom[PALETTE.id]) !== JSON.stringify(PALETTE)) {
    await settings.set("Comfy.CustomColorPalettes", { ...custom, [PALETTE.id]: PALETTE });
  }
  if (settings.get("Comfy.ColorPalette") !== PALETTE.id) await settings.set("Comfy.ColorPalette", PALETTE.id);
}

app.registerExtension({
  name: "yesopen.theme",
  async setup() {
    for (const w of [400, 500, 700]) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = `${WEB_FONT}/${w}.css`;
      document.head.appendChild(link);
    }
    const style = document.createElement("style");
    style.id = "yesopen-theme";
    style.textContent = CSS;
    document.head.appendChild(style);
    const L = window.LiteGraph;                      // text the canvas itself draws: group titles, link labels
    if (L) L.NODE_FONT = L.DEFAULT_FONT = L.GROUP_FONT = FAMILY;
    try {
      await usePalette();
    } catch (err) {
      console.warn("[yesopen.theme] palette", err);
    }
    document.fonts?.ready.then(() => app.canvas?.setDirty(true, true));
  },
});
