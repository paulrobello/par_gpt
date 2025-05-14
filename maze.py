import random


def make_maze(w=16, h=16, scale=0):
    h0, h1, h2, h3 = "+--", "+  ", "|  ", "   "
    h0 += scale * "---"
    h1 += scale * "   "
    h2 += scale * "   "
    h3 += scale * "   "
    vis = [[0] * w + [1] for _ in range(h)] + [[1] * (w + 1)]
    ver = [[h2] * w + ["|"] for _ in range(h)] + [[]]
    hor = [[h0] * w + ["+"] for _ in range(h + 1)]

    def walk(x, y):
        vis[y][x] = 1
        d = [(x - 1, y), (x, y + 1), (x + 1, y), (x, y - 1)]
        random.shuffle(d)
        for xx, yy in d:
            if vis[yy][xx]:
                continue
            if xx == x:
                hor[max(y, yy)][x] = h1
            if yy == y:
                ver[y][max(x, xx)] = h3
            walk(xx, yy)

    walk(random.randrange(w), random.randrange(h))

    s = ""
    for a, b in zip(hor, ver):
        s += "".join(a + ["\n"] + b + ["\n"])
        for _ in range(scale):
            s += "".join(b + ["\n"])
    return s


the_seed = 1

for scale in range(0,3):
    random.seed = the_seed
    print(make_maze(scale=scale))
    print("\n\n")
