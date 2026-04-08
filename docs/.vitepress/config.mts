import { defineConfig } from "vitepress";

export default defineConfig({
  title: "dwg2json",
  description:
    "Open-source DWG semantic deparser to one canonical JSON file",
  base: "/dwg2json/",

  head: [
    [
      "link",
      {
        rel: "icon",
        type: "image/svg+xml",
        href: "/dwg2json/logo.svg",
      },
    ],
  ],

  themeConfig: {
    logo: "/logo.svg",

    nav: [
      { text: "Guide", link: "/guide/getting-started" },
      { text: "Architecture", link: "/architecture/overview" },
      { text: "Reference", link: "/reference/json-schema" },
      {
        text: "v0.2.0",
        items: [
          {
            text: "Changelog",
            link: "https://github.com/VicLuZY/dwg2json/releases",
          },
          {
            text: "PyPI",
            link: "https://pypi.org/project/dwg2json/",
          },
        ],
      },
    ],

    sidebar: {
      "/guide/": [
        {
          text: "Introduction",
          items: [
            { text: "Getting Started", link: "/guide/getting-started" },
            { text: "Installation", link: "/guide/installation" },
            { text: "Development", link: "/guide/development" },
          ],
        },
        {
          text: "Usage",
          items: [
            { text: "Python API", link: "/guide/python-api" },
            { text: "CLI", link: "/guide/cli" },
            { text: "Output Format", link: "/guide/output-format" },
          ],
        },
        {
          text: "Concepts",
          items: [
            { text: "Xref Policy", link: "/guide/xref-policy" },
            { text: "Confidence & Completeness", link: "/guide/confidence" },
          ],
        },
      ],
      "/architecture/": [
        {
          text: "Architecture",
          items: [
            { text: "Overview", link: "/architecture/overview" },
            { text: "Pipeline", link: "/architecture/pipeline" },
            { text: "Backends", link: "/architecture/backends" },
            { text: "Schema Design", link: "/architecture/schema-design" },
          ],
        },
      ],
      "/reference/": [
        {
          text: "Reference",
          items: [
            { text: "JSON Schema", link: "/reference/json-schema" },
            { text: "Configuration", link: "/reference/configuration" },
            { text: "Third-Party Licenses", link: "/reference/licenses" },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: "github", link: "https://github.com/VicLuZY/dwg2json" },
    ],

    footer: {
      message: "Released under the AGPL-3.0-or-later License.",
      copyright: "Copyright © 2024-2026 dwg2json contributors",
    },

    search: {
      provider: "local",
    },

    editLink: {
      pattern: "https://github.com/VicLuZY/dwg2json/edit/main/docs/:path",
      text: "Edit this page on GitHub",
    },
  },
});
