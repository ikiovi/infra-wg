docker compose run --rm --no-deps -T \
  --entrypoint wg wireguard pubkey \
  < secrets/wg_private_key