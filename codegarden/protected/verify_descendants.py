"""Independent exact string verifier. No search imports or external dependencies."""
import argparse, hashlib, itertools, json, pathlib, sys

class InvalidCode(ValueError):
    def __init__(self, kind, **details):
        self.report = {"valid": False, "error": kind, **details}
        super().__init__(kind)

def parse(value, n=16):
    if isinstance(value, dict):
        if set(value) != {"words"}:
            raise InvalidCode("expected_only_words_key")
        value = value["words"]
    if not isinstance(value, list) or not 1 <= len(value) <= 2 ** (n-2):
        raise InvalidCode("invalid_cardinality")
    seen = set()
    for i, word in enumerate(value):
        if not isinstance(word, str) or len(word) != n or any(c not in "01" for c in word):
            raise InvalidCode("invalid_word", index=i, word=word, required_length=n)
        if word in seen:
            raise InvalidCode("duplicate_word", index=i, word=word)
        seen.add(word)
    return value

def descendants(word):
    out = {}
    for i, j in itertools.combinations(range(len(word)), 2):
        child = "".join(c for k, c in enumerate(word) if k != i and k != j)
        out.setdefault(child, (i, j))
    return out

def verify(value, n=16):
    words = parse(value, n)
    owner = {}
    for word in words:
        for child, positions in descendants(word).items():
            if child in owner:
                other, other_positions = owner[child]
                raise InvalidCode("shared_descendant", words=[other, word], descendant=child,
                                  deletion_positions_zero_based=[list(other_positions), list(positions)])
            owner[child] = (word, positions)
    canonical = "".join(w + "\n" for w in sorted(words)).encode("ascii")
    return {"valid": True, "cardinality": len(words), "length": n,
            "distinct_descendants": len(owner), "witness_sha256": hashlib.sha256(canonical).hexdigest(),
            "method": "distinct_string_two_deletions"}

def read(path):
    raw = sys.stdin.read() if path == "-" else pathlib.Path(path).read_text()
    try: return json.loads(raw)
    except json.JSONDecodeError: return raw.splitlines()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("witness"); p.add_argument("--length", type=int, default=16)
    args = p.parse_args()
    try: result = verify(read(args.witness), args.length)
    except InvalidCode as e:
        print(json.dumps(e.report)); return 1
    print(json.dumps(result, sort_keys=True)); return 0

if __name__ == "__main__": sys.exit(main())
