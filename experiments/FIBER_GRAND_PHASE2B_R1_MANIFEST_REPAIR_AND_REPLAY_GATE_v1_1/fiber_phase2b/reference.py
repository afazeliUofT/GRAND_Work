from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence


def bit_at(word:int,index:int)->int:return (word>>index)&1

def delete_bit(word:int,index:int)->int:
    low=(1<<index)-1; return (word&low)|((word>>(index+1))<<index)

def mismatch_vector(x:int,y:int,n:int)->tuple[int,...]:
    d=((x>>1)^y).bit_count(); out=[d]
    for j in range(n-1):
        d-=bit_at(x,j+1)!=bit_at(y,j); d+=bit_at(x,j)!=bit_at(y,j); out.append(int(d))
    return tuple(out)

def scaled_score(x:int,y:int,n:int,a:int,weights:Sequence[int]|None=None)->int:
    weights=tuple(weights or (1,)*n); m=n-1
    return sum(int(weights[j])*pow(a,m-d) for j,d in enumerate(mismatch_vector(x,y,n)))


def independent_bound(r:Sequence[int],n:int,a:int,weights:Sequence[int]|None=None)->int:
    weights=tuple(weights or (1,)*n);m=n-1
    return sum(int(weights[j])*pow(a,m-v) for j,v in enumerate(r) if v<=m)

def chain_bound(y:int,r:Sequence[int],n:int,a:int,weights:Sequence[int]|None=None)->int:
    weights=tuple(weights or (1,)*n);m=n-1
    if any(v>m for v in r):return 0
    states={(b,d):int(weights[0])*pow(a,m-d) for d in range(r[0],m+1) for b in (0,1)}
    for j in range(n-1):
        nxt={};yj=bit_at(y,j)
        for (b,d),s in states.items():
            for c in (0,1):
                d2=d-int(c!=yj)+int(b!=yj)
                if not 0<=d2<=m or d2<r[j+1]:continue
                key=(c,d2);v=s+int(weights[j+1])*pow(a,m-d2)
                if v>nxt.get(key,-1):nxt[key]=v
        states=nxt
    return max(states.values(),default=0)
def uac_bound(y:int,r:Sequence[int],n:int,a:int,weights:Sequence[int]|None=None)->int:
    weights=tuple(weights or (1,)*n);m=n-1
    if any(v>m for v in r):return 0
    states={(b,d,d):int(weights[0])*pow(a,m-d) for d in range(r[0],m+1) for b in (0,1)}
    for j in range(n-1):
        nxt={};yj=bit_at(y,j)
        for (b,d,rem),s in states.items():
            for c in (0,1):
                u=int(c!=yj)
                if u>rem:continue
                d2=d-u+int(b!=yj); rem2=rem-u
                if not 0<=d2<=m or d2<r[j+1]:continue
                key=(c,d2,rem2);v=s+int(weights[j+1])*pow(a,m-d2)
                if v>nxt.get(key,-1):nxt[key]=v
        states=nxt
    return max((s for (_b,_d,rem),s in states.items() if rem==0),default=0)

@dataclass(frozen=True)
class Code:
    n:int;k:int;rows:tuple[int,...];name:str
    def parity(self,msg:int)->int:
        p=0
        for i,row in enumerate(self.rows):p|=(((row&msg).bit_count()&1)<<i)
        return p
    def encode(self,msg:int)->int:return msg|(self.parity(msg)<<self.k)

CRC={4:(1<<4)|(1<<1)|1,5:(1<<5)|(1<<2)|1,6:(1<<6)|(1<<1)|1,8:(1<<8)|(1<<2)|(1<<1)|1,11:(1<<11)|(1<<2)|1}
def _mod(v:int,p:int)->int:
    d=p.bit_length()-1
    while v.bit_length()-1>=d:v^=p<<((v.bit_length()-1)-d)
    return v
def build_code(family:str,n:int,k:int,seed:int)->Code:
    r=n-k
    if family=="random_systematic_linear":
        g=random.Random(seed);rows=[]
        for i in range(r):
            x=g.getrandbits(k) or (1<<(i%k));rows.append(x)
        return Code(n,k,tuple(rows),family)
    if family=="crc_defined_linear":
        poly=CRC[r];rows=[0]*r
        for mi in range(k):
            rem=_mod((1<<mi)<<r,poly)
            for pi in range(r):
                if (rem>>pi)&1:rows[pi]|=1<<mi
        return Code(n,k,tuple(rows),family)
    raise ValueError(family)
