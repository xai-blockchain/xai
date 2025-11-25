# Status Badges for README

Copy and paste these badges into your main README.md file. Replace `USERNAME` and `REPO` with your actual GitHub username and repository name.

## Complete Badge Section

```markdown
<!-- PROJECT SHIELDS -->
<div align="center">

[![Code Quality][quality-shield]][quality-url]
[![Security Scan][security-shield]][security-url]
[![Tests][tests-shield]][tests-url]
[![Build & Deploy][deploy-shield]][deploy-url]
[![codecov][codecov-shield]][codecov-url]

[![Python Version][python-shield]][python-url]
[![License][license-shield]][license-url]
[![GitHub Issues][issues-shield]][issues-url]
[![GitHub Pull Requests][pr-shield]][pr-url]
[![Last Commit][commit-shield]][commit-url]

</div>

<!-- BADGE LINKS -->
[quality-shield]: https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg
[quality-url]: https://github.com/USERNAME/REPO/actions/workflows/quality.yml

[security-shield]: https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg
[security-url]: https://github.com/USERNAME/REPO/actions/workflows/security.yml

[tests-shield]: https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg
[tests-url]: https://github.com/USERNAME/REPO/actions/workflows/tests.yml

[deploy-shield]: https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg
[deploy-url]: https://github.com/USERNAME/REPO/actions/workflows/deploy.yml

[codecov-shield]: https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg?token=YOUR_TOKEN
[codecov-url]: https://codecov.io/gh/USERNAME/REPO

[python-shield]: https://img.shields.io/badge/python-3.11-blue.svg
[python-url]: https://www.python.org/downloads/

[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg
[license-url]: https://opensource.org/licenses/MIT

[issues-shield]: https://img.shields.io/github/issues/USERNAME/REPO.svg
[issues-url]: https://github.com/USERNAME/REPO/issues

[pr-shield]: https://img.shields.io/github/issues-pr/USERNAME/REPO.svg
[pr-url]: https://github.com/USERNAME/REPO/pulls

[commit-shield]: https://img.shields.io/github/last-commit/USERNAME/REPO.svg
[commit-url]: https://github.com/USERNAME/REPO/commits/main
```

## Inline Badges (Simpler)

```markdown
# XAI Blockchain

![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)
![Security Scan](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)
![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)
![Build & Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)
[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/REPO)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

## Individual Badge Types

### GitHub Actions Workflows

```markdown
<!-- Code Quality -->
[![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/quality.yml)

<!-- Security -->
[![Security Scan](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/security.yml)

<!-- Tests -->
[![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/tests.yml)

<!-- Deployment -->
[![Build & Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml)
```

### Code Coverage

```markdown
<!-- Codecov -->
[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/USERNAME/REPO)

<!-- Coverage percentage -->
[![Coverage Status](https://codecov.io/gh/USERNAME/REPO/branch/main/graphs/badge.svg)](https://codecov.io/gh/USERNAME/REPO)
```

### Language & Version

```markdown
<!-- Python Version -->
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

<!-- Python 3.11+ -->
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)

<!-- Multiple versions -->
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
```

### License

```markdown
<!-- MIT License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Apache 2.0 -->
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

<!-- GPL v3 -->
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
```

### Repository Stats

```markdown
<!-- Stars -->
[![GitHub stars](https://img.shields.io/github/stars/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO/stargazers)

<!-- Forks -->
[![GitHub forks](https://img.shields.io/github/forks/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO/network)

<!-- Issues -->
[![GitHub issues](https://img.shields.io/github/issues/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO/issues)

<!-- Pull Requests -->
[![GitHub pull requests](https://img.shields.io/github/issues-pr/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO/pulls)

<!-- Last Commit -->
[![GitHub last commit](https://img.shields.io/github/last-commit/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO/commits)

<!-- Contributors -->
[![Contributors](https://img.shields.io/github/contributors/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO/graphs/contributors)

<!-- Code Size -->
[![Code Size](https://img.shields.io/github/languages/code-size/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO)

<!-- Repo Size -->
[![Repo Size](https://img.shields.io/github/repo-size/USERNAME/REPO.svg)](https://github.com/USERNAME/REPO)
```

### Code Quality Tools

```markdown
<!-- Code Style: Black -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

<!-- Linting: Pylint -->
[![Linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)

<!-- Type Checking: MyPy -->
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue)](http://mypy-lang.org/)

<!-- Pre-commit -->
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

<!-- Security: Bandit -->
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
```

### Project Status

```markdown
<!-- Active -->
[![Status](https://img.shields.io/badge/status-active-success.svg)](https://github.com/USERNAME/REPO)

<!-- Maintained -->
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/USERNAME/REPO/graphs/commit-activity)

<!-- Version -->
[![Version](https://img.shields.io/github/v/release/USERNAME/REPO)](https://github.com/USERNAME/REPO/releases)

<!-- Release Date -->
[![Release Date](https://img.shields.io/github/release-date/USERNAME/REPO)](https://github.com/USERNAME/REPO/releases)
```

### Dependencies

```markdown
<!-- Dependencies Status -->
[![Dependencies](https://img.shields.io/librariesio/github/USERNAME/REPO)](https://libraries.io/github/USERNAME/REPO)

<!-- Requirements Status -->
[![Requirements Status](https://requires.io/github/USERNAME/REPO/requirements.svg?branch=main)](https://requires.io/github/USERNAME/REPO/requirements/?branch=main)
```

### Platform Support

```markdown
<!-- Platform -->
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-blue)](https://github.com/USERNAME/REPO)

<!-- OS - Linux -->
[![OS - Linux](https://img.shields.io/badge/os-linux-blue?logo=linux&logoColor=white)](https://www.linux.org/)

<!-- OS - Windows -->
[![OS - Windows](https://img.shields.io/badge/os-windows-blue?logo=windows&logoColor=white)](https://www.microsoft.com/)

<!-- OS - macOS -->
[![OS - macOS](https://img.shields.io/badge/os-macos-blue?logo=apple&logoColor=white)](https://www.apple.com/macos/)
```

### Documentation

```markdown
<!-- Documentation -->
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://github.com/USERNAME/REPO/wiki)

<!-- Read the Docs -->
[![Documentation Status](https://readthedocs.org/projects/REPO/badge/?version=latest)](https://REPO.readthedocs.io/en/latest/?badge=latest)
```

### Blockchain Specific

```markdown
<!-- Blockchain -->
[![Blockchain](https://img.shields.io/badge/blockchain-enabled-blue.svg)](https://github.com/USERNAME/REPO)

<!-- Consensus -->
[![Consensus](https://img.shields.io/badge/consensus-PoW%2FPoS-green.svg)](https://github.com/USERNAME/REPO)

<!-- Smart Contracts -->
[![Smart Contracts](https://img.shields.io/badge/smart%20contracts-enabled-brightgreen.svg)](https://github.com/USERNAME/REPO)

<!-- Cryptocurrency -->
[![Cryptocurrency](https://img.shields.io/badge/cryptocurrency-XAI-gold.svg)](https://github.com/USERNAME/REPO)
```

### Community & Social

```markdown
<!-- Discord -->
[![Discord](https://img.shields.io/discord/YOUR_DISCORD_ID.svg?label=&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2)](https://discord.gg/YOUR_INVITE)

<!-- Telegram -->
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/YOUR_CHANNEL)

<!-- Twitter -->
[![Twitter Follow](https://img.shields.io/twitter/follow/YOUR_HANDLE?style=social)](https://twitter.com/YOUR_HANDLE)

<!-- Reddit -->
[![Reddit](https://img.shields.io/reddit/subreddit-subscribers/YOUR_SUBREDDIT?style=social)](https://reddit.com/r/YOUR_SUBREDDIT)
```

## Custom Shields.io Badges

You can create custom badges using [shields.io](https://shields.io/):

```markdown
<!-- Custom static badge -->
![Custom](https://img.shields.io/badge/label-message-color)

<!-- Examples -->
![Blockchain](https://img.shields.io/badge/Blockchain-XAI-blue)
![AI Powered](https://img.shields.io/badge/AI-Powered-brightgreen)
![Status](https://img.shields.io/badge/Status-Production-success)
```

## Recommended Combination for Blockchain Project

```markdown
<div align="center">

# XAI Blockchain

![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)
![Security Scan](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)
![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)
![Build & Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)

[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/REPO)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

![Blockchain](https://img.shields.io/badge/blockchain-enabled-blue.svg)
![AI Powered](https://img.shields.io/badge/AI-Powered-brightgreen.svg)
[![Discord](https://img.shields.io/badge/Discord-Join%20Us-7289da.svg)](https://discord.gg/YOUR_INVITE)

**A next-generation blockchain with AI integration**

[Documentation](https://github.com/USERNAME/REPO/wiki) •
[Report Bug](https://github.com/USERNAME/REPO/issues) •
[Request Feature](https://github.com/USERNAME/REPO/issues)

</div>
```

## Dynamic Badges (Update Automatically)

These badges update automatically based on your repository:

```markdown
<!-- All contributors -->
[![All Contributors](https://img.shields.io/github/all-contributors/USERNAME/REPO?color=ee8449)](https://github.com/USERNAME/REPO/graphs/contributors)

<!-- Commit activity -->
[![Commit Activity](https://img.shields.io/github/commit-activity/m/USERNAME/REPO)](https://github.com/USERNAME/REPO/graphs/commit-activity)

<!-- Top Language -->
[![Top Language](https://img.shields.io/github/languages/top/USERNAME/REPO)](https://github.com/USERNAME/REPO)

<!-- Language Count -->
[![Languages](https://img.shields.io/github/languages/count/USERNAME/REPO)](https://github.com/USERNAME/REPO)

<!-- Downloads (for releases) -->
[![Downloads](https://img.shields.io/github/downloads/USERNAME/REPO/total)](https://github.com/USERNAME/REPO/releases)
```

## Tips for Using Badges

1. **Keep it balanced**: Don't overdo it. 5-10 badges is usually enough.

2. **Group related badges**: Put CI/CD badges together, quality tools together, etc.

3. **Use centered alignment** for header badges:
   ```markdown
   <div align="center">
     <!-- badges here -->
   </div>
   ```

4. **Make badges clickable**: Always link badges to relevant pages.

5. **Update regularly**: Remove badges for discontinued services.

6. **Test links**: Make sure all badge links work after adding them.

7. **Use reference-style links** for cleaner markdown:
   ```markdown
   [![Badge][badge-shield]][badge-url]

   [badge-shield]: https://img.shields.io/...
   [badge-url]: https://github.com/...
   ```

## Getting Codecov Token

1. Go to [codecov.io](https://codecov.io)
2. Sign in with GitHub
3. Add your repository
4. Copy the upload token
5. Add to GitHub Secrets as `CODECOV_TOKEN`
6. Use in badge URL: `?token=YOUR_TOKEN`

For public repositories, the token is optional in the badge URL.

## Color Codes for Custom Badges

Common colors for shields.io badges:
- `brightgreen` - Success, passing
- `green` - Active, good
- `yellowgreen` - Acceptable
- `yellow` - Warning, attention needed
- `orange` - Important
- `red` - Error, critical
- `blue` - Information
- `lightgrey` - Neutral
- `success` - Same as brightgreen
- Hex colors: `#ff6900`

## Example Complete README Header

```markdown
<div align="center">

<img src="docs/images/logo.png" alt="XAI Logo" width="200"/>

# XAI Blockchain

**AI-Powered Decentralized Blockchain Platform**

[![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/quality.yml)
[![Security](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/security.yml)
[![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/REPO)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Features](#features) •
[Installation](#installation) •
[Documentation](https://github.com/USERNAME/REPO/wiki) •
[Contributing](CONTRIBUTING.md) •
[Community](#community)

</div>
```

Replace `USERNAME/REPO` with your actual values and customize as needed!
