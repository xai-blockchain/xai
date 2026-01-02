# Docker

Docker Compose files live in this directory. Use them to run local or multi-node stacks.

## Start a local stack

```bash
docker compose -f docker/docker-compose.yml up -d
```

## Testnet configs

Additional compose files are under `docker/testnet/`. Review the YAML files for ports and service layout before starting them.

## Notes

- Environment variables are read from your shell or an optional `.env` file.
- Ports and volumes are defined in the compose files.
