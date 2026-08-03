from __future__ import annotations
from fractions import Fraction
from itertools import product
from random import Random


def dvec(x: tuple[int,...], y: tuple[int,...]) -> list[int]:
    n = len(x)
    return [
        sum(x[i] != y[i] for i in range(j))
        + sum(x[i] != y[i-1] for i in range(j+1, n))
        for j in range(n)
    ]


def likelihood_formula(x, y, p, q):
    n=len(x); m=n-1
    return sum(q[j] * p**d * (1-p)**(m-d) for j,d in enumerate(dvec(x,y)))


def likelihood_exhaustive(x, y, p, q):
    n=len(x)
    total=Fraction(0)
    for z in product((0,1), repeat=n):
        wz=sum(z)
        pz=p**wz*(1-p)**(n-wz)
        xt=tuple(a^b for a,b in zip(x,z))
        for j in range(n):
            out=xt[:j]+xt[j+1:]
            if out==y:
                total += q[j]*pz
    return total


def brute_uac(y, r, p, q):
    n=len(y)+1
    best=None
    for x in product((0,1), repeat=n):
        d=dvec(x,y)
        if all(d[j]>=r[j] for j in range(n)):
            s=sum(q[j]*p**d[j]*(1-p)**(n-1-d[j]) for j in range(n))
            if best is None or s>best: best=s
    return Fraction(0) if best is None else best


def dp_uac(y, r, p, q):
    n=len(y)+1
    def g(j,d): return q[j]*p**d*(1-p)**(n-1-d)
    states={}
    for a in range(n):
        if a<r[0]: continue
        for b in (0,1):
            states[(a,b,a,0)] = g(0,a)
    for j in range(1,n):
        yj=y[j-1]
        nxt={}
        for (a,b,d,h),score in states.items():
            for c in (0,1):
                h2=h+int(c!=yj)
                d2=d-int(c!=yj)+int(b!=yj)
                if 0<=d2<=n-1 and d2>=r[j]:
                    key=(a,c,d2,h2)
                    val=score+g(j,d2)
                    if key not in nxt or val>nxt[key]: nxt[key]=val
        states=nxt
    best=None
    for (a,b,d,h),score in states.items():
        if h==a and (best is None or score>best): best=score
    return Fraction(0) if best is None else best


def main():
    p=Fraction(1,5)
    # Full likelihood/formula and recurrence checks.
    pairs=0
    for n in range(2,7):
        q=[Fraction(1,n)]*n
        for x in product((0,1), repeat=n):
            for y in product((0,1), repeat=n-1):
                a=likelihood_formula(x,y,p,q)
                b=likelihood_exhaustive(x,y,p,q)
                assert a==b,(n,x,y,a,b)
                ds=dvec(x,y)
                d=ds[0]
                for j in range(n-1):
                    d=d-int(x[j+1]!=y[j])+int(x[j]!=y[j])
                    assert d==ds[j+1]
                pairs+=1

    # Exact DP versus exhaustive bound, including nonuniform deletion weights.
    rng=Random(20260802)
    dp_cases=0
    for n in range(3,8):
        denom=n*(n+1)//2
        q=[Fraction(j+1,denom) for j in range(n)]
        for y in product((0,1), repeat=n-1):
            test_rs=[tuple([0]*n), tuple([1]*n), tuple(min(j%3,n-1) for j in range(n))]
            test_rs += [tuple(rng.randrange(0,n+1) for _ in range(n)) for _ in range(12)]
            for r in test_rs:
                a=brute_uac(y,r,p,q)
                b=dp_uac(y,r,p,q)
                assert a==b,(n,y,r,a,b)
                # Independent-list upper bound.
                ind=sum(q[j]*p**r[j]*(1-p)**(n-1-r[j]) if r[j]<=n-1 else 0 for j in range(n))
                assert a<=ind,(n,y,r,a,ind)
                dp_cases+=1

    # Strict reversal family and factorization by direct exact evaluation.
    reversal_cases=0
    for p0 in [Fraction(1,100),Fraction(1,50),Fraction(1,20),Fraction(1,10),Fraction(1,4)]:
        for n in range(4,150):
            y=(0,)*(n-3)+(1,0)
            xa=(0,)*(n-3)+(1,0,1)
            xb=(0,)*n
            q=[Fraction(1,n)]*n
            la=likelihood_formula(xa,y,p0,q)
            lb=likelihood_formula(xb,y,p0,q)
            assert (lb>la)==(n*p0>1+2*p0*p0)
            reversal_cases+=1

    print('EXACT_VALIDATION=PASS')
    print(f'LIKELIHOOD_AND_RECURRENCE_PAIRS={pairs}')
    print(f'UAC_DP_EXACT_CASES={dp_cases}')
    print(f'STRICT_REVERSAL_CASES={reversal_cases}')
    print('ARITHMETIC=fractions.Fraction')
    print('SEED=20260802')

if __name__=='__main__':
    main()
