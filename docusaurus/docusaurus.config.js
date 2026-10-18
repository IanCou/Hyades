// @ts-check
import { themes as prismThemes } from "prism-react-renderer";

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Hyades",
  tagline: "A 3-node Proxmox homelab, run as code",
  favicon: "img/favicon.ico",

  future: {
    v4: true,
  },

  // Overridable so the same site builds for docs.iancoutinho.net (default)
  // and for GitHub Pages at iancou.github.io/Hyades (see pages.yml).
  url: process.env.DOCS_URL ?? "https://docs.iancoutinho.net",
  baseUrl: process.env.DOCS_BASE_URL ?? "/",

  onBrokenLinks: "warn",
  onBrokenMarkdownLinks: "warn",

  markdown: {
    format: "detect",
  },

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          path: "docs",
          routeBasePath: "docs",
          sidebarPath: "./sidebars.js",
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: "Hyades",
        items: [
          {
            type: "docSidebar",
            sidebarId: "docsSidebar",
            position: "left",
            label: "Docs",
          },
        ],
      },
      footer: {
        style: "dark",
        copyright: `Hyades docs, ${new Date().getFullYear()}`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
      },
    }),
};

export default config;
