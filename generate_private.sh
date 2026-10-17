docker compose run --rm --no-deps \
  --entrypoint wg wireguard genkey \
  > secrets/wg_private_key
