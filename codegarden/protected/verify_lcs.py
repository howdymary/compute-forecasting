"""Second verifier: dynamic-programming LCS. No descendant-generator imports."""
import argparse, hashlib, json, pathlib, sys

def lcs(a, b):
    n, m = len(a), len(b)
    table = [[0] * (m+1) for _ in range(n+1)]
    for i in range(1, n+1):
        for j in range(1, m+1):
            table[i][j] = table[i-1][j-1]+1 if a[i-1] == b[j-1] else max(table[i-1][j], table[i][j-1])
    i, j, aligned = n, m, []
    while i and j:
        if a[i-1] == b[j-1]:
            aligned.append((i-1,j-1)); i -= 1; j -= 1
        elif table[i-1][j] >= table[i][j-1]: i -= 1
        else: j -= 1
    return table[n][m], list(reversed(aligned))

def verify(value, n=16):
    if isinstance(value, dict):
        if set(value) != {"words"}: return {"valid": False, "error": "expected_only_words_key"}
        value = value["words"]
    if not isinstance(value, list) or not 1 <= len(value) <= 2 ** (n-2):
        return {"valid": False, "error": "invalid_cardinality"}
    for i,w in enumerate(value):
        if not isinstance(w,str) or len(w) != n or set(w) - {"0","1"}:
            return {"valid": False, "error": "invalid_word", "index": i}
    if len(set(value)) != len(value): return {"valid": False, "error": "duplicate_word"}
    largest = 0; pairs = 0
    for i,a in enumerate(value):
        for b in value[i+1:]:
            size, alignment = lcs(a,b); largest = max(largest,size); pairs += 1
            if size >= n-2:
                alignment = alignment[:n-2]
                ai, bi = {x for x,y in alignment}, {y for x,y in alignment}
                return {"valid": False, "error": "lcs_collision", "words":[a,b], "lcs_length":size,
                        "descendant":"".join(a[x] for x,y in alignment),
                        "deletion_positions_zero_based":[[k for k in range(n) if k not in ai],
                                                         [k for k in range(n) if k not in bi]]}
    raw = "".join(w+"\n" for w in sorted(value)).encode("ascii")
    return {"valid": True, "cardinality":len(value), "length":n, "pairs_checked":pairs,
            "largest_pairwise_lcs":largest, "witness_sha256":hashlib.sha256(raw).hexdigest(),
            "method":"independent_dynamic_programming_lcs"}

def main():
    p=argparse.ArgumentParser();p.add_argument("witness");p.add_argument("--length",type=int,default=16)
    a=p.parse_args();raw=sys.stdin.read() if a.witness=="-" else pathlib.Path(a.witness).read_text()
    try: value=json.loads(raw)
    except json.JSONDecodeError:value=raw.splitlines()
    r=verify(value,a.length);print(json.dumps(r,sort_keys=True));return 0 if r["valid"] else 1
if __name__=="__main__":sys.exit(main())
