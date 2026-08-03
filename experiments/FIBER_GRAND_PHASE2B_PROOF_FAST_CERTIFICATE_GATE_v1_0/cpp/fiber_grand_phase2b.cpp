#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace fg {
using Clock = std::chrono::steady_clock;
using u64 = std::uint64_t;

struct BigUInt {
    static constexpr int LIMBS = 8;
    std::uint64_t limb[LIMBS]{};
    BigUInt(std::uint64_t v = 0) { limb[0]=v; }
    bool is_zero() const { for(auto x:limb) if(x) return false; return true; }
    void mul_small(std::uint32_t m) {
        __uint128_t carry=0;
        for(int i=0;i<LIMBS;++i){__uint128_t z=static_cast<__uint128_t>(limb[i])*m+carry;limb[i]=static_cast<std::uint64_t>(z);carry=z>>64;}
        if(carry) throw std::overflow_error("BigUInt fixed capacity exceeded");
    }
    BigUInt times_small(std::uint32_t m) const { BigUInt r=*this;r.mul_small(m);return r; }
    void add(const BigUInt&b){__uint128_t carry=0;for(int i=0;i<LIMBS;++i){__uint128_t z=static_cast<__uint128_t>(limb[i])+b.limb[i]+carry;limb[i]=static_cast<std::uint64_t>(z);carry=z>>64;}if(carry)throw std::overflow_error("BigUInt fixed capacity exceeded");}
    friend BigUInt operator+(BigUInt a,const BigUInt&b){a.add(b);return a;}
    int cmp(const BigUInt&b)const{for(int i=LIMBS-1;i>=0;--i)if(limb[i]!=b.limb[i])return limb[i]<b.limb[i]?-1:1;return 0;}
    friend bool operator<(const BigUInt&a,const BigUInt&b){return a.cmp(b)<0;}
    friend bool operator>(const BigUInt&a,const BigUInt&b){return a.cmp(b)>0;}
    friend bool operator==(const BigUInt&a,const BigUInt&b){return a.cmp(b)==0;}
    friend bool operator!=(const BigUInt&a,const BigUInt&b){return !(a==b);}
    std::uint32_t div_small(std::uint32_t d){__uint128_t rem=0;for(int i=LIMBS-1;i>=0;--i){__uint128_t z=(rem<<64)|limb[i];limb[i]=static_cast<std::uint64_t>(z/d);rem=z%d;}return static_cast<std::uint32_t>(rem);}
    std::string str() const {if(is_zero())return "0";BigUInt t=*this;std::vector<std::uint32_t>chunks;while(!t.is_zero())chunks.push_back(t.div_small(1000000000U));std::ostringstream os;os<<chunks.back();for(std::size_t i=chunks.size()-1;i-->0;)os<<std::setw(9)<<std::setfill('0')<<chunks[i];return os.str();}
};

struct Cell { bool valid=false; BigUInt value; };
static void max_update(Cell &c, const BigUInt &v) { if(!c.valid || v>c.value){c.valid=true;c.value=v;} }

static std::vector<std::string> split(const std::string&s,char d){std::vector<std::string>o;std::string x;std::istringstream is(s);while(std::getline(is,x,d))o.push_back(x);if(!s.empty()&&s.back()==d)o.push_back("");return o;}
static u64 parse_u64(const std::string&s){std::size_t p=0;u64 v=std::stoull(s,&p,0);if(p!=s.size())throw std::runtime_error("bad integer: "+s);return v;}
static std::vector<int> parse_ints(const std::string&s){std::vector<int>v;if(s.empty())return v;for(auto &x:split(s,','))v.push_back(std::stoi(x));return v;}
static std::vector<u64> parse_hexes(const std::string&s){std::vector<u64>v;if(s.empty())return v;for(auto &x:split(s,','))v.push_back(parse_u64(x));return v;}
static void validate_bound_input(u64 y,const std::vector<int>&r,int n,int a,const std::vector<int>&w){
    if(n<2||n>63)throw std::runtime_error("Phase-2B exact kernel requires 2<=n<=63");
    if(a<=1||a>99)throw std::runtime_error("Phase-2B exact kernel requires 2<=a<=99");
    if(static_cast<int>(r.size())!=n||static_cast<int>(w.size())!=n)throw std::runtime_error("frontier/weight length mismatch");
    if(y>=(1ULL<<(n-1)))throw std::runtime_error("observation outside n-1 bit range");
    for(int v:r)if(v<0||v>n)throw std::runtime_error("frontier shell outside 0..n");
    for(int v:w)if(v<0)throw std::runtime_error("negative deletion weight");
}
static std::string join_hexes(std::vector<u64>v){std::sort(v.begin(),v.end());std::ostringstream o;for(std::size_t i=0;i<v.size();++i){if(i)o<<',';o<<"0x"<<std::hex<<v[i]<<std::dec;}return o.str();}
static std::string hex_u64(u64 v){std::ostringstream o;o<<"0x"<<std::hex<<v;return o.str();}
static int bit_at(u64 w,int i){return static_cast<int>((w>>i)&1ULL);}
static u64 insert_bit(u64 w,int index,int bit){u64 lowmask=index==0?0ULL:((1ULL<<index)-1ULL);u64 low=w&lowmask;u64 high=w>>index;return low|(static_cast<u64>(bit)<<index)|(high<<(index+1));}

static std::vector<BigUInt> powers(int a,int m){std::vector<BigUInt>p(m+1);p[0]=BigUInt(1);for(int e=1;e<=m;++e){p[e]=p[e-1];p[e].mul_small(static_cast<std::uint32_t>(a));}return p;}
static std::vector<int> mismatch_vector(u64 x,u64 y,int n){int d=0;for(int i=1;i<n;++i)d+=bit_at(x,i)!=bit_at(y,i-1);std::vector<int>out;out.reserve(n);out.push_back(d);for(int j=0;j<n-1;++j){d-=bit_at(x,j+1)!=bit_at(y,j);d+=bit_at(x,j)!=bit_at(y,j);out.push_back(d);}return out;}
static BigUInt score(u64 x,u64 y,int n,const std::vector<int>&weights,const std::vector<BigUInt>&pow){int m=n-1;auto d=mismatch_vector(x,y,n);BigUInt s;for(int j=0;j<n;++j){BigUInt t=pow[m-d[j]].times_small(static_cast<std::uint32_t>(weights[j]));s.add(t);}return s;}
static BigUInt independent_bound(const std::vector<int>&r,int n,const std::vector<int>&w,const std::vector<BigUInt>&pow){int m=n-1;BigUInt s;for(int j=0;j<n;++j)if(r[j]<=m){BigUInt t=pow[m-r[j]].times_small(static_cast<std::uint32_t>(w[j]));s.add(t);}return s;}

static BigUInt chain_bound(u64 y,const std::vector<int>&r,int n,const std::vector<int>&w,const std::vector<BigUInt>&pow){int m=n-1;if(std::any_of(r.begin(),r.end(),[&](int z){return z>m;}))return BigUInt();std::vector<Cell>cur(2*(m+1)),nxt(2*(m+1));auto idx=[&](int b,int d){return b*(m+1)+d;};for(int d=r[0];d<=m;++d)for(int b=0;b<2;++b){BigUInt t=pow[m-d].times_small(static_cast<std::uint32_t>(w[0]));max_update(cur[idx(b,d)],t);}for(int j=0;j<n-1;++j){for(auto&c:nxt)c=Cell{};int yj=bit_at(y,j);for(int b=0;b<2;++b)for(int d=0;d<=m;++d){auto &c=cur[idx(b,d)];if(!c.valid)continue;for(int nb=0;nb<2;++nb){int d2=d-(nb!=yj)+(b!=yj);if(d2<0||d2>m||d2<r[j+1])continue;BigUInt v=c.value;v.add(pow[m-d2].times_small(static_cast<std::uint32_t>(w[j+1])));max_update(nxt[idx(nb,d2)],v);}}cur.swap(nxt);}Cell best;for(auto&c:cur)if(c.valid)max_update(best,c.value);return best.valid?best.value:BigUInt();}

static BigUInt uac_bound(u64 y,const std::vector<int>&r,int n,const std::vector<int>&w,const std::vector<BigUInt>&pow){int m=n-1;if(std::any_of(r.begin(),r.end(),[&](int z){return z>m;}))return BigUInt();int D=m+1;std::vector<Cell>cur(2*D*D),nxt(2*D*D);auto idx=[&](int b,int d,int rem){return (b*D+d)*D+rem;};for(int init=r[0];init<=m;++init)for(int b=0;b<2;++b){BigUInt t=pow[m-init].times_small(static_cast<std::uint32_t>(w[0]));max_update(cur[idx(b,init,init)],t);}for(int j=0;j<n-1;++j){for(auto&c:nxt)c=Cell{};int yj=bit_at(y,j);for(int b=0;b<2;++b)for(int d=0;d<=m;++d)for(int rem=0;rem<=m;++rem){auto &c=cur[idx(b,d,rem)];if(!c.valid)continue;for(int nb=0;nb<2;++nb){int u=nb!=yj;if(u>rem)continue;int rem2=rem-u;int d2=d-u+(b!=yj);if(d2<0||d2>m||d2<r[j+1])continue;BigUInt v=c.value;v.add(pow[m-d2].times_small(static_cast<std::uint32_t>(w[j+1])));max_update(nxt[idx(nb,d2,rem2)],v);}}cur.swap(nxt);}Cell best;for(int b=0;b<2;++b)for(int d=0;d<=m;++d){auto &c=cur[idx(b,d,0)];if(c.valid)max_update(best,c.value);}return best.valid?best.value:BigUInt();}

struct Code {int n=0,k=0;std::vector<u64>rows;bool contains(u64 word)const{u64 mask=k==64?~0ULL:((1ULL<<k)-1ULL);u64 msg=word&mask;u64 parity=word>>k;u64 expected=0;for(std::size_t i=0;i<rows.size();++i)expected|=(static_cast<u64>(__builtin_popcountll(rows[i]&msg)&1)<<i);return parity==expected;}};

static std::vector<u64> masks_weight(int length,int weight){std::vector<u64>out;std::function<void(int,int,u64)>rec=[&](int start,int left,u64 mask){if(left==0){out.push_back(mask);return;}for(int p=start;p<=length-left;++p)rec(p+1,left-1,mask|(1ULL<<p));};rec(0,weight,0);return out;}
static bool forward_prefix_equal(const std::vector<int>&key,int m){int lo=*std::min_element(key.begin(),key.end()),hi=*std::max_element(key.begin(),key.end());if(hi>m)return false;if(hi==lo)return true;if(hi!=lo+1)return false;bool seen_lo=false;for(int v:key){if(v==lo)seen_lo=true;else if(v==hi){if(seen_lo)return false;}else return false;}return true;}

struct DecodeResult {
    std::string status="";bool complete=false;u64 decoded=0;bool has_decoded=false;std::vector<u64>ties;BigUInt incumbent,final_bound;std::uint64_t q_hist=0,q_disc=0,q_code=0,q_score=0,frontier_updates=0,bound_calls=0,chain_calls=0,uac_calls=0,total_ns=0,bound_ns=0;u64 first_codeword=0;bool has_first=false;
};

static DecodeResult decode(u64 y,const Code&code,int a,const std::string&schedule,int mode,std::uint64_t max_hist){
    auto started=Clock::now();int n=code.n,m=n-1;std::vector<int>w(n,1),frontier(n,0),order;if(schedule=="forward")for(int j=0;j<n;++j)order.push_back(j);else if(schedule=="even_odd"){for(int j=0;j<n;j+=2)order.push_back(j);for(int j=1;j<n;j+=2)order.push_back(j);}else throw std::runtime_error("bad schedule");auto pow=powers(a,m);std::unordered_set<u64>seen;std::vector<u64>ties;BigUInt incumbent;bool have_inc=false;DecodeResult R;
    auto cert=[&](bool frontier_event)->bool{if(!have_inc)return false;++R.bound_calls;auto t0=Clock::now();BigUInt ind=independent_bound(frontier,n,w,pow);R.final_bound=ind;if(incumbent>ind){R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return true;}if(mode==0){R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return false;}BigUInt cr;if(forward_prefix_equal(frontier,m))cr=ind;else{++R.chain_calls;cr=chain_bound(y,frontier,n,w,pow);}R.final_bound=cr;if(incumbent>cr){R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return true;}if(mode==1){R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return false;}if(mode==3){if(!frontier_event||R.q_hist<static_cast<std::uint64_t>(n)){R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return false;}int lo=*std::min_element(frontier.begin(),frontier.end()),hi=*std::max_element(frontier.begin(),frontier.end());int advanced=(hi==lo)?n:static_cast<int>(std::count(frontier.begin(),frontier.end(),hi));bool checkpoint=(advanced==n||advanced==1||(advanced>0&&(advanced&(advanced-1))==0));if(!checkpoint){R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return false;}}++R.uac_calls;BigUInt ac=uac_bound(y,frontier,n,w,pow);R.final_bound=ac;R.bound_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t0).count();return incumbent>ac;};
    auto finish=[&](const std::string&st,bool complete){R.status=st;R.complete=complete;R.incumbent=have_inc?incumbent:BigUInt();R.ties=ties;if(!ties.empty()){std::sort(R.ties.begin(),R.ties.end());R.decoded=R.ties.front();R.has_decoded=true;}R.total_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-started).count();return R;};
    for(int shell=0;shell<=m;++shell){auto masks=masks_weight(m,shell);for(std::size_t mi=0;mi<masks.size();++mi){u64 altered=y^masks[mi];for(int b=0;b<2;++b){bool final_local=(mi+1==masks.size()&&b==1);for(int j:order){++R.q_hist;if(R.q_hist>max_hist){--R.q_hist;return finish("CENSORED_MAX_HISTORIES",false);}u64 x=insert_bit(altered,j,b);bool changed=false;if(seen.insert(x).second){++R.q_disc;++R.q_code;if(code.contains(x)){if(!R.has_first){R.first_codeword=x;R.has_first=true;}++R.q_score;BigUInt s=score(x,y,n,w,pow);if(!have_inc||s>incumbent){incumbent=s;have_inc=true;ties.assign(1,x);changed=true;}else if(s==incumbent&&std::find(ties.begin(),ties.end(),x)==ties.end())ties.push_back(x);}}if(final_local){frontier[j]=shell+1;++R.frontier_updates;if(cert(true))return finish("CERTIFIED",true);}else if(changed){if(cert(false))return finish("CERTIFIED",true);}}}}}R.final_bound=BigUInt();return finish("EXHAUSTED",true);
}

static std::vector<std::string> read_lines(const std::string&path){std::ifstream f(path);if(!f)throw std::runtime_error("cannot open "+path);std::vector<std::string>v;std::string s;while(std::getline(f,s)){if(!s.empty()&&s.back()=='\r')s.pop_back();if(!s.empty())v.push_back(s);}return v;}

static int bounds_batch(const std::string&in,const std::string&out){auto lines=read_lines(in);std::ofstream f(out);f<<"id\tind\tcr\tac\tind_ns\tcr_ns\tac_ns\n";for(std::size_t z=1;z<lines.size();++z){auto c=split(lines[z],'\t');if(c.size()<6)throw std::runtime_error("bad bounds row");std::string id=c[0];int n=std::stoi(c[1]),a=std::stoi(c[2]);u64 y=parse_u64(c[3]);auto r=parse_ints(c[4]);auto w=parse_ints(c[5]);if(w.empty())w.assign(n,1);validate_bound_input(y,r,n,a,w);auto p=powers(a,n-1);auto t0=Clock::now();auto ind=independent_bound(r,n,w,p);auto t1=Clock::now();auto cr=chain_bound(y,r,n,w,p);auto t2=Clock::now();auto ac=uac_bound(y,r,n,w,p);auto t3=Clock::now();f<<id<<'\t'<<ind.str()<<'\t'<<cr.str()<<'\t'<<ac.str()<<'\t'<<std::chrono::duration_cast<std::chrono::nanoseconds>(t1-t0).count()<<'\t'<<std::chrono::duration_cast<std::chrono::nanoseconds>(t2-t1).count()<<'\t'<<std::chrono::duration_cast<std::chrono::nanoseconds>(t3-t2).count()<<'\n';}return 0;}

static void emit_mode(std::ofstream&f,const DecodeResult&r){f<<'\t'<<r.status<<'\t'<<(r.complete?1:0)<<'\t'<<(r.has_decoded?hex_u64(r.decoded):"")<<'\t'<<join_hexes(r.ties)<<'\t'<<r.incumbent.str()<<'\t'<<r.final_bound.str()<<'\t'<<r.q_hist<<'\t'<<r.q_disc<<'\t'<<r.q_code<<'\t'<<r.q_score<<'\t'<<r.frontier_updates<<'\t'<<r.bound_calls<<'\t'<<r.chain_calls<<'\t'<<r.uac_calls<<'\t'<<r.bound_ns<<'\t'<<r.total_ns;}
static int decode_batch(const std::string&in,const std::string&out){auto lines=read_lines(in);std::ofstream f(out);f<<"id\tfirst_codeword";for(auto p:{"ind","cr","ac","fast"})f<<'\t'<<p<<"_status\t"<<p<<"_complete\t"<<p<<"_decoded\t"<<p<<"_ties\t"<<p<<"_score\t"<<p<<"_bound\t"<<p<<"_q_hist\t"<<p<<"_q_disc\t"<<p<<"_q_code\t"<<p<<"_q_score\t"<<p<<"_frontier_updates\t"<<p<<"_bound_calls\t"<<p<<"_chain_calls\t"<<p<<"_uac_calls\t"<<p<<"_bound_ns\t"<<p<<"_total_ns";f<<'\n';for(std::size_t z=1;z<lines.size();++z){auto c=split(lines[z],'\t');if(c.size()<9)throw std::runtime_error("bad decode row fields="+std::to_string(c.size()));std::string id=c[0];Code code;code.n=std::stoi(c[1]);code.k=std::stoi(c[2]);int a=std::stoi(c[3]);std::string schedule=c[4];std::uint64_t cap=std::stoull(c[5]);u64 y=parse_u64(c[6]);code.rows=parse_hexes(c[8]);if(code.n<2||code.n>63||code.k<1||code.k>=code.n)throw std::runtime_error("invalid code dimensions");if(a<=1||a>99)throw std::runtime_error("odds denominator outside 2..99");if(y>=(1ULL<<(code.n-1)))throw std::runtime_error("observation outside n-1 bit range");if(cap==0)throw std::runtime_error("max_hist must be positive");if(static_cast<int>(code.rows.size())!=code.n-code.k)throw std::runtime_error("row count mismatch");for(u64 row:code.rows)if(row>=(1ULL<<code.k))throw std::runtime_error("parity row outside message range");DecodeResult rr[4];int shift=static_cast<int>(std::stoull(id)%4ULL);for(int q=0;q<4;++q){int mode=(q+shift)%4;rr[mode]=decode(y,code,a,schedule,mode,cap);}auto &r0=rr[0];auto &r1=rr[1];auto &r2=rr[2];auto &r3=rr[3];f<<id<<'\t'<<(r0.has_first?hex_u64(r0.first_codeword):"");emit_mode(f,r0);emit_mode(f,r1);emit_mode(f,r2);emit_mode(f,r3);f<<'\n';}return 0;}

static int self_test(){for(int n=2;n<=8;++n){int a=4,m=n-1;std::vector<int>w(n,1),r(n,1);u64 y=(1ULL<<m)-1;validate_bound_input(y,r,n,a,w);auto p=powers(a,m);auto ind=independent_bound(r,n,w,p),cr=chain_bound(y,r,n,w,p),ac=uac_bound(y,r,n,w,p);if(ac>cr||cr>ind)throw std::runtime_error("hierarchy failure");}BigUInt capacity(1);for(int i=0;i<62;++i)capacity.mul_small(99);if(capacity.str().empty())throw std::runtime_error("multiword conversion failure");std::cout<<"SELF_TEST=PASS\n";return 0;}
}

int main(int argc,char**argv){try{if(argc<2)throw std::runtime_error("usage: fiber_grand_phase2b <self-test|bounds-batch|decode-batch> ...");std::string cmd=argv[1];if(cmd=="self-test")return fg::self_test();if(cmd=="bounds-batch"&&argc==4)return fg::bounds_batch(argv[2],argv[3]);if(cmd=="decode-batch"&&argc==4)return fg::decode_batch(argv[2],argv[3]);throw std::runtime_error("bad command/arguments");}catch(const std::exception&e){std::cerr<<"ERROR: "<<e.what()<<"\n";return 2;}}
