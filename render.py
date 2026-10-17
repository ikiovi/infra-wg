
import base64
import ipaddress
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NETWORK = ipaddress.ip_network("10.77.0.0/24")
PORT = 51820

node_id = (ROOT / "secrets/node-id").read_text().strip()
nodes = json.loads((ROOT / "peers.json").read_text())

# Validate inventory before writing anything.
names = set()
addresses = set()
keys = set()

for node in nodes:
    name = node["name"]
    address = ipaddress.IPv4Address(node["wg_ip"])
    ipaddress.IPv4Address(node["public_ip"])

    key = base64.b64decode(
        node["public_key"], validate=True
    )

    if len(key) != 32:
        raise ValueError(f"Invalid public key: {name}")

    if address not in NETWORK:
        raise ValueError(f"Address outside mesh: {name}")

    if name in names or address in addresses or key in keys:
        raise ValueError(f"Duplicate peer: {name}")

    names.add(name)
    addresses.add(address)
    keys.add(key)

local = next(
    (node for node in nodes if node["name"] == node_id),
    None,
)

if local is None:
    raise ValueError(f"Unknown local node: {node_id}")

# Build interface configuration.
lines = [
    "[Interface]",
    f"Address = {local['wg_ip']}/{NETWORK.prefixlen}",
    f"ListenPort = {PORT}",
    "PostUp = wg set %i private-key /run/secrets/wg_private_key",
]

# Include every peer except ourselves.
for node in sorted(nodes, key=lambda n: n["wg_ip"]):
    if node["name"] == node_id:
        continue

    lines.extend([
        "",
        f"# {node['name']}",
        "[Peer]",
        f"PublicKey = {node['public_key']}",
        f"AllowedIPs = {node['wg_ip']}/32",
        f"Endpoint = {node['public_ip']}:{PORT}",
    ])

# Write atomically.
target = ROOT / "config/wg_confs/wg0.conf"
target.parent.mkdir(parents=True, exist_ok=True)

temporary = None

try:
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=target.parent,
        prefix=".wg0-",
        delete=False,
    ) as file:
        temporary = Path(file.name)
        os.fchmod(file.fileno(), 0o600)
        file.write("\n".join(lines) + "\n")

    os.replace(temporary, target)
finally:
    if temporary and temporary.exists():
        temporary.unlink()

print(f"Generated {target} for {node_id}")
