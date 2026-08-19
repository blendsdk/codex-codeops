import { defineConfig } from 'vitepress'

/**
 * Configures the public CodeOps documentation site.
 *
 * The GitHub Pages base path must match the repository name so generated asset
 * URLs work when the site is served below the blendsdk organization domain.
 */
export default defineConfig({
  title: 'CodeOps for Codex',
  description:
    'Specification-first requirements, planning, execution, review, and project tracking for Codex.',
  base: '/codex-codeops/',
  lang: 'en-US',
  cleanUrls: true,
  lastUpdated: true,
  sitemap: {
    hostname: 'https://blendsdk.github.io/codex-codeops/',
  },

  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/introduction' },
      { text: 'Skills', link: '/skills/' },
      { text: 'Tutorials', link: '/tutorials/' },
      { text: 'Reference', link: '/reference/artifacts' },
      { text: '1.0.0', link: 'https://github.com/blendsdk/codex-codeops/releases/tag/v1.0.0' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Get started',
          items: [
            { text: 'Introduction', link: '/guide/introduction' },
            { text: 'Install', link: '/installation' },
            { text: 'Verify installation', link: '/guide/verify' },
            { text: 'Quick start', link: '/tutorial' },
          ],
        },
        {
          text: 'Use CodeOps',
          items: [
            { text: 'The workflow', link: '/guide/workflow' },
            { text: 'Choose a skill', link: '/guide/choosing-a-skill' },
            { text: 'Delegated design', link: '/guide/auto-design' },
            { text: 'Scope control', link: '/guide/scope-control' },
            { text: 'Project layout', link: '/guide/project-layout' },
            { text: 'Core concepts', link: '/concepts' },
          ],
        },
      ],
      '/skills/': [
        {
          text: 'Workflow skills',
          items: [
            { text: 'Overview', link: '/skills/' },
            { text: 'grill-me', link: '/skills/grill-me' },
            { text: 'make-requirements', link: '/skills/make-requirements' },
            { text: 'retro-requirements', link: '/skills/retro-requirements' },
            { text: 'make-plan', link: '/skills/make-plan' },
            { text: 'preflight', link: '/skills/preflight' },
            { text: 'exec-plan', link: '/skills/exec-plan' },
            { text: 'roadmap', link: '/skills/roadmap' },
          ],
        },
        {
          text: 'Project and maintenance skills',
          items: [
            { text: 'setup-codeops', link: '/skills/setup-codeops' },
            { text: 'setup-routing', link: '/skills/setup-routing' },
            { text: 'analyze-project', link: '/skills/analyze-project' },
            { text: 'techdocs', link: '/skills/techdocs' },
            { text: 'upgrade-plan', link: '/skills/upgrade-plan' },
            { text: 'clean-comments', link: '/skills/clean-comments' },
            { text: 'git-commit', link: '/skills/git-commit' },
            { text: 'github-issues', link: '/skills/github-issues' },
            { text: 'outcome-review', link: '/skills/outcome-review' },
          ],
        },
      ],
      '/tutorials/': [
        {
          text: 'Tutorials',
          items: [
            { text: 'Overview', link: '/tutorials/' },
            { text: 'Plan a new feature', link: '/tutorials/new-feature' },
            { text: 'Reverse-engineer a codebase', link: '/tutorials/existing-codebase' },
            { text: 'Execute a plan safely', link: '/tutorials/execute-plan' },
            { text: 'Migrate from Claude', link: '/tutorials/migrate-from-claude' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'Artifacts and ownership', link: '/reference/artifacts' },
            { text: 'Flags and modes', link: '/reference/flags' },
            { text: 'Quality and verification', link: '/reference/verification' },
            { text: 'Security and privacy', link: '/reference/security' },
            { text: 'Compatibility', link: '/reference/compatibility' },
            { text: 'Migration', link: '/migration' },
            { text: 'Troubleshooting', link: '/troubleshooting' },
            { text: 'Evaluation evidence', link: '/evaluation' },
          ],
        },
      ],
      '/': [
        {
          text: 'Documentation',
          items: [
            { text: 'Home', link: '/' },
            { text: 'Install', link: '/installation' },
            { text: 'Quick start', link: '/tutorial' },
            { text: 'Core concepts', link: '/concepts' },
            { text: 'Migration', link: '/migration' },
            { text: 'Troubleshooting', link: '/troubleshooting' },
            { text: 'Evaluation evidence', link: '/evaluation' },
          ],
        },
      ],
    },

    socialLinks: [{ icon: 'github', link: 'https://github.com/blendsdk/codex-codeops' }],
    editLink: {
      pattern: 'https://github.com/blendsdk/codex-codeops/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },
    search: {
      provider: 'local',
    },
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © blendsdk',
    },
  },
})
