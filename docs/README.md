# XAI Blockchain Documentation

Welcome to the documentation hub for the XAI Blockchain project. This directory contains various guides, roadmaps, and examples to help you understand and interact with the project.

## Getting Started

*   **Onboarding Guide**: Learn how to set up a node or miner quickly.
    *   [Node & Miner Onboarding Guide](onboarding.md)
*   **Prerequisites**: Ensure you have the necessary software installed.
    *   [Prerequisites](onboarding.md#prerequisites)

## Core Project Documentation

*   **Project Structure**: Understand the organization of the codebase.
    *   [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)
*   **Reorganization Progress**: Track the ongoing efforts to improve the project structure.
    *   [REORGANIZATION_PROGRESS.md](../REORGANIZATION_PROGRESS.md)
*   **Configuration Management**: Understand how the node's behavior is configured.
    *   [Configuration Guide](README.md#configuration-management) (This section)
    *   [Environment Variables Template](scripts/deploy/config.template.env)

## Feature Documentation

*   **AIXN Specifics**: In-depth documentation for the AIXN blockchain.
    *   [AIXN Marketing Campaign Plan](AIXN_Marketing_Campaign_Plan.md)
    *   [AML Reporting](AML_REPORTING.md)
    *   [Embedded Wallets](EMBEDDED_WALLETS.md)
    *   [Fiat On-Ramps Roadmap](fiat_onramps_roadmap.md)
    *   [Genesis Distribution](GENESIS_DISTRIBUTION.md)
    *   [Hardware Wallet](HARDWARE_WALLET.md)
    *   [Ledger Onboarding](LEDGER_ONBOARDING.md)
    *   [Light Client](LIGHT_CLIENT.md)
    *   [Micro Assistants](MICRO_ASSISTANTS.md)
    *   [Mini Apps](MINI_APPS.md)
    *   [Mining Bonus Project Complete](MINING_BONUS_PROJECT_COMPLETE.txt)
    *   [Mobile Bridge](MOBILE_BRIDGE.md)
    *   [Push Notifications](PUSH_NOTIFICATIONS.md)
*   **Time Capsules**: Information on the time capsule feature.
    *   (Refer to `onboarding.md` for initial info, or add a dedicated file if needed)
*   **Token Burning**: Details on the token burning mechanism.
    *   (Refer to `src/aixn/core/token_burning_api_endpoints.py` or add a dedicated file)

## Development & Testing

*   **Testing Framework**: How to run and contribute to tests.
    *   [README_TESTING.md](../tests/aixn_tests/README_TESTING.md)
*   **Examples**: Code examples and usage demonstrations.
    *   [Examples Directory](examples/)

## Deployment & Operations

*   **Deployment Guide**: Instructions for deploying the node.
    *   (Refer to `scripts/deploy/DEPLOYMENT_GUIDE.md` if it exists, or add one)
*   **Grafana Dashboards**: For monitoring node performance.
    *   [Grafana Dashboard JSON](grafana_dashboard.json)

## Contributing

Please refer to the main project `README.md` and `CONTRIBUTING.md` (if available) for contribution guidelines.

---

## Configuration Management

The XAI Blockchain node's behavior is controlled by a layered configuration system. Settings are loaded in a specific order, allowing for flexibility and secure management of sensitive information.

### Configuration Sources and Precedence

1.  **Environment Variables**: Settings defined as environment variables (e.g., `XAI_PORT`, `OPENAI_API_KEY`) take the highest precedence and will override any settings from configuration files. This is the recommended method for managing sensitive information and production overrides.
    *   Use the `scripts/deploy/config.template.env` file as a template to create your `.env` file.
    *   Ensure your `.env` file is added to `.gitignore` to prevent accidental commits of sensitive data.

2.  **Environment-Specific YAML Files**: Configuration settings are defined in YAML files located in `src/aixn/config/`. These files allow for environment-specific tuning:
    *   `default.yaml`: Contains the base default settings.
    *   `development.yaml`: Overrides defaults for local development.
    *   `staging.yaml`: Overrides defaults for staging environments.
    *   `testnet.yaml`: Overrides defaults for the test network.
    *   `production.yaml`: Overrides defaults for the mainnet production environment.

    The application loads the `default.yaml` first, and then applies overrides from the YAML file corresponding to the active environment (e.g., `development.yaml` if `XAI_ENV=development` or similar is set).

3.  **Application Code Defaults**: If a setting is not found in environment variables or configuration files, the application may fall back to hardcoded defaults within its code.

### Loading Mechanism

The application utilizes a configuration manager (likely `src/aixn/core/config_manager.py`) that orchestrates the loading process. It typically:
1.  Loads default settings from `src/aixn/config/default.yaml`.
2.  Loads environment-specific settings from the corresponding YAML file (e.g., `development.yaml`).
3.  Loads settings from a `.env` file (if present) and system environment variables, overriding any previous settings.

### Managing Secrets

Sensitive information such as API keys, private keys, and database credentials should **never** be hardcoded or committed to version control. Always use environment variables or a secure secrets management system. The `scripts/deploy/config.template.env` file provides a template for common environment variables.

---
*Last updated: November 12, 2025*