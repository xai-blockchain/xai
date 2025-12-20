# XAI Blockchain Documentation

This is the official documentation site for XAI Blockchain, built with [Docusaurus](https://docusaurus.io/).

## Local Development

```bash
npm install
npm start
```

This command starts a local development server and opens up a browser window. Most changes are reflected live without having to restart the server.

## Build

```bash
npm run build
```

This command generates static content into the `build` directory and can be served using any static contents hosting service.

## Deployment

The site is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

### Manual Deployment

```bash
GIT_USER=<Your GitHub username> npm run deploy
```

If you are using GitHub pages for hosting, this command is a convenient way to build the website and push to the `gh-pages` branch.

## Structure

- `docs/` - Documentation markdown files
  - `intro.md` - Introduction page
  - `getting-started/` - Installation and quick start guides
  - `developers/` - Developer guides and tutorials
  - `api/` - API reference documentation
- `src/` - Custom React components and pages
- `static/` - Static files like images
- `docusaurus.config.ts` - Docusaurus configuration
- `sidebars.ts` - Sidebar navigation configuration

## Contributing

To add or update documentation:

1. Edit or create markdown files in the `docs/` directory
2. Update `sidebars.ts` if adding new sections
3. Test locally with `npm start`
4. Build to verify with `npm run build`
5. Commit and push to trigger deployment

## Resources

- [Docusaurus Documentation](https://docusaurus.io/docs)
- [XAI GitHub Repository](https://github.com/xai-blockchain/xai)
