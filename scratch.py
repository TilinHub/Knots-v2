import sys
import math
sys.path.append('c:\\Knots-v2')
from knots_v2.pd_draw import knot_layout
from knots_v2.compute.cs_route import build_route
from knots_v2.domain.primitives import Point

def generate_interactive(name):
    layout = knot_layout(name)
    if not layout["ok"]: return None
    regions = layout["regions"]
    curve = layout["curve"]
    crossings = layout["crossings"]
    
    # 1. For each point in curve, find closest region
    # To be robust, find the TWO closest regions! They are the left and right regions.
    # At each curve point, the curve separates two regions.
    adj = {i: set() for i in range(len(regions))}
    
    # Helper to find closest regions
    def closest_two(px, py):
        dists = []
        for j, (cx, cy, r) in enumerate(regions):
            dists.append((math.hypot(px - cx, py - cy), j))
        dists.sort()
        return dists[0][1], dists[1][1]

    # Sample the curve to find adjacencies
    for i in range(0, len(curve), 5):
        p = curve[i]
        r1, r2 = closest_two(p[0], p[1])
        adj[r1].add(r2)
        adj[r2].add(r1)

    # 2-color the regions
    color = {}
    q = [ (0, 0) ] # region 0 is color 0
    while q:
        curr, c = q.pop(0)
        if curr in color: continue
        color[curr] = c
        for nbr in adj[curr]:
            if nbr not in color:
                q.append((nbr, 1 - c))

    # If disconnected, color remaining
    for i in range(len(regions)):
        if i not in color:
            color[i] = 1 # guess

    black_regions = [i for i, c in color.items() if c == 1]
    
    # Map old region index to new disk index
    old_to_new = {old: new for new, old in enumerate(black_regions)}
    
    disks = [Point(regions[i][0] * 3, regions[i][1] * 3) for i in black_regions]
    
    # Extract sequence
    # The curve is divided into segments by the crossings.
    # We can just trace the curve. At each step, one of the two closest regions is black.
    # That black region is the disk the curve is currently visiting!
    seq = []
    for i in range(len(curve)):
        p = curve[i]
        r1, r2 = closest_two(p[0], p[1])
        black_r = r1 if color.get(r1) == 1 else r2
        if color.get(black_r) != 1:
            black_r = r1 if color.get(r1) == 0 else r2 # fallback
            
        disk_idx = old_to_new.get(black_r, 0)
        if not seq or seq[-1] != disk_idx:
            seq.append(disk_idx)
            
    # Compress sequence (remove consecutive duplicates)
    compressed = []
    for s in seq:
        if not compressed or compressed[-1] != s:
            compressed.append(s)
    if len(compressed) > 1 and compressed[0] == compressed[-1]:
        compressed.pop()
        
    print(f"[{name}] Disks: {len(disks)}, Seq: {compressed}")
    
    # Orientation: assume all +1 for simplicity, build_route might correct or we can compute it.
    orient = [1] * len(compressed)
    
    # Test build
    res = build_route(disks, 0.5, compressed, orient)
    print("  Valid:", res["valid"], "OK:", res["ok"])

generate_interactive("4_1")
generate_interactive("6_2")
