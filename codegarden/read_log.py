"""Read compressed, content-hashed experiment logs without external packages."""
import argparse,json,pathlib,zlib
p=argparse.ArgumentParser();p.add_argument("path");a=p.parse_args()
print(json.dumps(json.loads(zlib.decompress(pathlib.Path(a.path).read_bytes())),indent=2))
