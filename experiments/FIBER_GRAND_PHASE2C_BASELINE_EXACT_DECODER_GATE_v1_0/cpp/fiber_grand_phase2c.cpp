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
#include <unordered_set>
#include <utility>
#include <vector>

namespace fg {
using Clock = std::chrono::steady_clock;
using u64 = std::uint64_t;

struct BigUInt {
    static constexpr int LIMBS = 8; // 512 bits
    std::uint64_t limb[LIMBS]{};
    BigUInt(std::uint64_t value = 0) { limb[0] = value; }
    bool is_zero() const { for (auto x : limb) if (x) return false; return true; }
    void mul_small(std::uint32_t m) {
        __uint128_t carry = 0;
        for (int i = 0; i < LIMBS; ++i) {
            __uint128_t z = static_cast<__uint128_t>(limb[i]) * m + carry;
            limb[i] = static_cast<std::uint64_t>(z);
            carry = z >> 64;
        }
        if (carry) throw std::overflow_error("BigUInt fixed capacity exceeded");
    }
    BigUInt times_small(std::uint32_t m) const { BigUInt out = *this; out.mul_small(m); return out; }
    void add(const BigUInt &other) {
        __uint128_t carry = 0;
        for (int i = 0; i < LIMBS; ++i) {
            __uint128_t z = static_cast<__uint128_t>(limb[i]) + other.limb[i] + carry;
            limb[i] = static_cast<std::uint64_t>(z);
            carry = z >> 64;
        }
        if (carry) throw std::overflow_error("BigUInt fixed capacity exceeded");
    }
    int cmp(const BigUInt &other) const {
        for (int i = LIMBS - 1; i >= 0; --i) {
            if (limb[i] != other.limb[i]) return limb[i] < other.limb[i] ? -1 : 1;
        }
        return 0;
    }
    friend bool operator<(const BigUInt &a, const BigUInt &b) { return a.cmp(b) < 0; }
    friend bool operator>(const BigUInt &a, const BigUInt &b) { return a.cmp(b) > 0; }
    friend bool operator==(const BigUInt &a, const BigUInt &b) { return a.cmp(b) == 0; }
    friend bool operator!=(const BigUInt &a, const BigUInt &b) { return !(a == b); }
    std::uint32_t div_small(std::uint32_t d) {
        __uint128_t rem = 0;
        for (int i = LIMBS - 1; i >= 0; --i) {
            __uint128_t z = (rem << 64) | limb[i];
            limb[i] = static_cast<std::uint64_t>(z / d);
            rem = z % d;
        }
        return static_cast<std::uint32_t>(rem);
    }
    std::string str() const {
        if (is_zero()) return "0";
        BigUInt temp = *this;
        std::vector<std::uint32_t> chunks;
        while (!temp.is_zero()) chunks.push_back(temp.div_small(1000000000U));
        std::ostringstream out;
        out << chunks.back();
        for (std::size_t i = chunks.size() - 1; i-- > 0;) out << std::setw(9) << std::setfill('0') << chunks[i];
        return out.str();
    }
};

static std::vector<std::string> split(const std::string &s, char delim) {
    std::vector<std::string> out;
    std::string item;
    std::istringstream input(s);
    while (std::getline(input, item, delim)) out.push_back(item);
    if (!s.empty() && s.back() == delim) out.push_back("");
    return out;
}
static u64 parse_u64(const std::string &s) {
    std::size_t pos = 0;
    u64 value = std::stoull(s, &pos, 0);
    if (pos != s.size()) throw std::runtime_error("bad integer: " + s);
    return value;
}
static std::vector<u64> parse_hexes(const std::string &s) {
    std::vector<u64> out;
    if (s.empty()) return out;
    for (const auto &x : split(s, ',')) out.push_back(parse_u64(x));
    return out;
}
static std::string hex_u64(u64 value) { std::ostringstream o; o << "0x" << std::hex << value; return o.str(); }
static std::string join_hexes(std::vector<u64> values) {
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
    std::ostringstream out;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) out << ',';
        out << "0x" << std::hex << values[i] << std::dec;
    }
    return out.str();
}
static int bit_at(u64 word, int index) { return static_cast<int>((word >> index) & 1ULL); }
static u64 full_mask(int n) { return n == 64 ? ~0ULL : ((1ULL << n) - 1ULL); }
static u64 insert_bit(u64 word, int index, int bit) {
    const u64 low_mask = index == 0 ? 0ULL : ((1ULL << index) - 1ULL);
    const u64 low = word & low_mask;
    const u64 high = word >> index;
    return low | (static_cast<u64>(bit) << index) | (high << (index + 1));
}

static std::vector<BigUInt> powers(int a, int maximum) {
    std::vector<BigUInt> out(maximum + 1);
    out[0] = BigUInt(1);
    for (int i = 1; i <= maximum; ++i) { out[i] = out[i - 1]; out[i].mul_small(static_cast<std::uint32_t>(a)); }
    return out;
}
static std::vector<int> mismatch_vector(u64 x, u64 y, int n) {
    int d = 0;
    for (int i = 1; i < n; ++i) d += bit_at(x, i) != bit_at(y, i - 1);
    std::vector<int> out;
    out.reserve(n);
    out.push_back(d);
    for (int j = 0; j < n - 1; ++j) {
        d -= bit_at(x, j + 1) != bit_at(y, j);
        d += bit_at(x, j) != bit_at(y, j);
        out.push_back(d);
    }
    return out;
}
static BigUInt score(u64 x, u64 y, int n, const std::vector<BigUInt> &pow) {
    const int m = n - 1;
    BigUInt total;
    for (int d : mismatch_vector(x, y, n)) total.add(pow[m - d]);
    return total;
}
static BigUInt shell_bound(int n, int m, int completed_shell, const std::vector<BigUInt> &pow) {
    if (completed_shell >= m) return BigUInt();
    return pow[m - completed_shell - 1].times_small(static_cast<std::uint32_t>(n));
}

struct Code {
    int n = 0;
    int k = 0;
    std::vector<u64> generator;
    std::vector<u64> checks;
    bool contains(u64 word) const {
        for (u64 row : checks) if (__builtin_popcountll(word & row) & 1) return false;
        return true;
    }
    u64 encode(u64 message) const {
        u64 word = 0;
        int i = 0;
        while (message) {
            if (message & 1ULL) word ^= generator.at(static_cast<std::size_t>(i));
            ++i;
            message >>= 1;
        }
        return word;
    }
};

static std::vector<u64> masks_weight(int length, int weight) {
    std::vector<u64> out;
    std::function<void(int, int, u64)> rec = [&](int start, int left, u64 mask) {
        if (left == 0) { out.push_back(mask); return; }
        for (int pos = start; pos <= length - left; ++pos) rec(pos + 1, left - 1, mask | (1ULL << pos));
    };
    if (weight >= 0 && weight <= length) rec(0, weight, 0);
    return out;
}

enum class GenerationMode { DEDUP_INSERTION_SPHERE, HISTORY_PAIRS };

struct ShellResult {
    std::string status;
    bool complete = false;
    bool has_decoded = false;
    u64 decoded = 0;
    std::vector<u64> ties;
    BigUInt incumbent;
    BigUInt final_bound;
    int stop_shell = -1;
    std::uint64_t generated_attempts = 0;
    std::uint64_t q_disc = 0;
    std::uint64_t q_membership = 0;
    std::uint64_t q_score = 0;
    std::uint64_t global_duplicates = 0;
    std::uint64_t total_ns = 0;
    int bestpath_shell = -1;
    bool bestpath_has_decoded = false;
    u64 bestpath_decoded = 0;
    std::vector<u64> bestpath_ties;
};

static void update_incumbent(
    u64 candidate,
    const BigUInt &candidate_score,
    bool &have_incumbent,
    BigUInt &incumbent,
    std::vector<u64> &ties
) {
    if (!have_incumbent || candidate_score > incumbent) {
        have_incumbent = true;
        incumbent = candidate_score;
        ties.assign(1, candidate);
    } else if (candidate_score == incumbent && std::find(ties.begin(), ties.end(), candidate) == ties.end()) {
        ties.push_back(candidate);
    }
}

static ShellResult decode_shell(
    u64 y,
    const Code &code,
    int a,
    GenerationMode mode,
    std::uint64_t max_generated_attempts,
    bool collect_bestpath
) {
    const auto started = Clock::now();
    const int n = code.n;
    const int m = n - 1;
    const auto pow = powers(a, m);
    std::unordered_set<u64> seen;
    seen.reserve(static_cast<std::size_t>(std::min<std::uint64_t>(max_generated_attempts, 2000000ULL)));

    bool have_incumbent = false;
    BigUInt incumbent;
    std::vector<u64> ties;
    ShellResult result;

    for (int shell = 0; shell <= m; ++shell) {
        std::vector<u64> bestpath_shell_words;
        const auto errors = masks_weight(m, shell);
        for (u64 error : errors) {
            const u64 z = y ^ error;
            if (mode == GenerationMode::DEDUP_INSERTION_SPHERE) {
                for (int b = 0; b < 2; ++b) {
                    auto process_gap = [&](int gap) -> bool {
                        ++result.generated_attempts;
                        if (result.generated_attempts > max_generated_attempts) return false;
                        const u64 x = insert_bit(z, gap, b);
                        if (!seen.insert(x).second) { ++result.global_duplicates; return true; }
                        ++result.q_disc;
                        ++result.q_membership;
                        if (code.contains(x)) {
                            ++result.q_score;
                            const BigUInt s = score(x, y, n, pow);
                            update_incumbent(x, s, have_incumbent, incumbent, ties);
                            if (collect_bestpath && result.bestpath_shell < 0) bestpath_shell_words.push_back(x);
                        }
                        return true;
                    };
                    if (!process_gap(0)) {
                        result.status = "CENSORED_MAX_GENERATED";
                        result.complete = false;
                        result.stop_shell = shell;
                        result.incumbent = have_incumbent ? incumbent : BigUInt();
                        result.ties = ties;
                        result.total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - started).count();
                        return result;
                    }
                    for (int gap = 1; gap <= m; ++gap) {
                        if (bit_at(z, gap - 1) != b && !process_gap(gap)) {
                            result.status = "CENSORED_MAX_GENERATED";
                            result.complete = false;
                            result.stop_shell = shell;
                            result.incumbent = have_incumbent ? incumbent : BigUInt();
                            result.ties = ties;
                            result.total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - started).count();
                            return result;
                        }
                    }
                }
            } else {
                for (int b = 0; b < 2; ++b) {
                    for (int gap = 0; gap <= m; ++gap) {
                        ++result.generated_attempts;
                        if (result.generated_attempts > max_generated_attempts) {
                            result.status = "CENSORED_MAX_GENERATED";
                            result.complete = false;
                            result.stop_shell = shell;
                            result.incumbent = have_incumbent ? incumbent : BigUInt();
                            result.ties = ties;
                            result.total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - started).count();
                            return result;
                        }
                        const u64 x = insert_bit(z, gap, b);
                        if (!seen.insert(x).second) { ++result.global_duplicates; continue; }
                        ++result.q_disc;
                        ++result.q_membership;
                        if (code.contains(x)) {
                            ++result.q_score;
                            const BigUInt s = score(x, y, n, pow);
                            update_incumbent(x, s, have_incumbent, incumbent, ties);
                        }
                    }
                }
            }
        }

        if (collect_bestpath && result.bestpath_shell < 0 && !bestpath_shell_words.empty()) {
            std::sort(bestpath_shell_words.begin(), bestpath_shell_words.end());
            bestpath_shell_words.erase(std::unique(bestpath_shell_words.begin(), bestpath_shell_words.end()), bestpath_shell_words.end());
            result.bestpath_shell = shell;
            result.bestpath_ties = bestpath_shell_words;
            result.bestpath_decoded = bestpath_shell_words.front();
            result.bestpath_has_decoded = true;
        }

        result.final_bound = shell_bound(n, m, shell, pow);
        if (have_incumbent && (shell >= m || incumbent > result.final_bound)) {
            result.status = shell >= m ? "EXHAUSTED" : "CERTIFIED";
            result.complete = true;
            result.stop_shell = shell;
            result.incumbent = incumbent;
            std::sort(ties.begin(), ties.end());
            ties.erase(std::unique(ties.begin(), ties.end()), ties.end());
            result.ties = ties;
            result.decoded = ties.front();
            result.has_decoded = true;
            result.total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - started).count();
            return result;
        }
    }
    throw std::runtime_error("shell decoder reached impossible terminal state");
}

struct ExactResult {
    std::string status;
    bool complete = false;
    bool has_decoded = false;
    u64 decoded = 0;
    std::vector<u64> ties;
    BigUInt score;
    std::uint64_t evaluated = 0;
    std::uint64_t nodes = 0;
    std::uint64_t total_ns = 0;
};

static ExactResult exhaustive_ml(u64 y, const Code &code, int a) {
    const auto started = Clock::now();
    const int m = code.n - 1;
    const auto pow = powers(a, m);
    bool have = false;
    BigUInt best;
    std::vector<u64> ties;
    const u64 count = 1ULL << code.k;
    for (u64 message = 0; message < count; ++message) {
        const u64 x = code.encode(message);
        const BigUInt s = score(x, y, code.n, pow);
        if (!have || s > best) { have = true; best = s; ties.assign(1, x); }
        else if (s == best) ties.push_back(x);
    }
    std::sort(ties.begin(), ties.end());
    ExactResult out;
    out.status = "COMPLETE";
    out.complete = true;
    out.has_decoded = true;
    out.decoded = ties.front();
    out.ties = ties;
    out.score = best;
    out.evaluated = count;
    out.total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - started).count();
    return out;
}

struct BranchContext {
    const Code *code = nullptr;
    u64 y = 0;
    int m = 0;
    const std::vector<BigUInt> *pow = nullptr;
    std::vector<u64> future_or;
    std::uint64_t node_cap = 0;
    std::uint64_t time_cap_ns = 0;
    Clock::time_point started;
    bool aborted = false;
    std::uint64_t nodes = 0;
    bool have = false;
    BigUInt best;
    std::vector<u64> ties;
};

static BigUInt branch_upper(u64 partial, int depth, const BranchContext &ctx) {
    const u64 fixed = full_mask(ctx.code->n) & ~ctx.future_or.at(static_cast<std::size_t>(depth));
    BigUInt total;
    for (int j = 0; j < ctx.code->n; ++j) {
        int lower = 0;
        for (int i = 0; i < ctx.m; ++i) {
            const int xcoord = i < j ? i : i + 1;
            if (((fixed >> xcoord) & 1ULL) && bit_at(partial, xcoord) != bit_at(ctx.y, i)) ++lower;
        }
        total.add(ctx.pow->at(static_cast<std::size_t>(ctx.m - lower)));
    }
    return total;
}

static void branch_leaf(u64 word, BranchContext &ctx) {
    const BigUInt s = score(word, ctx.y, ctx.code->n, *ctx.pow);
    if (!ctx.have || s > ctx.best) { ctx.have = true; ctx.best = s; ctx.ties.assign(1, word); }
    else if (s == ctx.best) ctx.ties.push_back(word);
}

static void branch_dfs(int depth, u64 partial, const BigUInt &upper, BranchContext &ctx) {
    if (ctx.aborted) return;
    ++ctx.nodes;
    if (ctx.nodes > ctx.node_cap) { ctx.aborted = true; return; }
    if ((ctx.nodes & 1023ULL) == 0ULL) {
        const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - ctx.started).count();
        if (static_cast<std::uint64_t>(elapsed) > ctx.time_cap_ns) { ctx.aborted = true; return; }
    }
    if (ctx.have && upper < ctx.best) return;
    if (depth == ctx.code->k) { branch_leaf(partial, ctx); return; }

    const u64 child0 = partial;
    const u64 child1 = partial ^ ctx.code->generator.at(static_cast<std::size_t>(depth));
    const BigUInt upper0 = branch_upper(child0, depth + 1, ctx);
    const BigUInt upper1 = branch_upper(child1, depth + 1, ctx);
    if (upper1 > upper0) {
        branch_dfs(depth + 1, child1, upper1, ctx);
        branch_dfs(depth + 1, child0, upper0, ctx);
    } else {
        branch_dfs(depth + 1, child0, upper0, ctx);
        branch_dfs(depth + 1, child1, upper1, ctx);
    }
}

static ExactResult branch_and_bound_ml(u64 y, const Code &code, int a, std::uint64_t node_cap, std::uint64_t time_ms) {
    BranchContext ctx;
    ctx.code = &code;
    ctx.y = y;
    ctx.m = code.n - 1;
    const auto pow = powers(a, ctx.m);
    ctx.pow = &pow;
    ctx.node_cap = node_cap;
    ctx.time_cap_ns = time_ms * 1000000ULL;
    ctx.started = Clock::now();
    ctx.future_or.assign(static_cast<std::size_t>(code.k + 1), 0);
    for (int d = code.k - 1; d >= 0; --d) ctx.future_or[static_cast<std::size_t>(d)] = ctx.future_or[static_cast<std::size_t>(d + 1)] | code.generator[static_cast<std::size_t>(d)];

    // A valid initial incumbent from the all-zero message.
    branch_leaf(0, ctx);
    const BigUInt root_upper = branch_upper(0, 0, ctx);
    branch_dfs(0, 0, root_upper, ctx);

    std::sort(ctx.ties.begin(), ctx.ties.end());
    ctx.ties.erase(std::unique(ctx.ties.begin(), ctx.ties.end()), ctx.ties.end());
    ExactResult out;
    out.status = ctx.aborted ? "CENSORED" : "COMPLETE";
    out.complete = !ctx.aborted;
    out.has_decoded = ctx.have;
    out.score = ctx.best;
    out.nodes = ctx.nodes;
    out.total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - ctx.started).count();
    if (ctx.have) { out.decoded = ctx.ties.front(); out.ties = ctx.ties; }
    return out;
}

static bool tie_sets_disjoint(const std::vector<u64> &a, const std::vector<u64> &b) {
    std::unordered_set<u64> set(a.begin(), a.end());
    for (u64 x : b) if (set.count(x)) return false;
    return true;
}

static std::vector<std::string> read_lines(const std::string &path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open " + path);
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty()) lines.push_back(line);
    }
    return lines;
}

static void emit_shell(std::ofstream &out, const std::string &prefix, const ShellResult &r, u64 tx) {
    out << '\t' << r.status
        << '\t' << (r.complete ? 1 : 0)
        << '\t' << (r.has_decoded ? hex_u64(r.decoded) : "")
        << '\t' << join_hexes(r.ties)
        << '\t' << r.incumbent.str()
        << '\t' << r.final_bound.str()
        << '\t' << r.stop_shell
        << '\t' << r.generated_attempts
        << '\t' << r.q_disc
        << '\t' << r.q_membership
        << '\t' << r.q_score
        << '\t' << r.global_duplicates
        << '\t' << r.total_ns
        << '\t' << ((r.has_decoded && r.decoded != tx) ? 1 : 0);
    (void)prefix;
}
static void emit_exact(std::ofstream &out, const ExactResult &r, u64 tx) {
    out << '\t' << r.status
        << '\t' << (r.complete ? 1 : 0)
        << '\t' << (r.has_decoded ? hex_u64(r.decoded) : "")
        << '\t' << join_hexes(r.ties)
        << '\t' << r.score.str()
        << '\t' << r.evaluated
        << '\t' << r.nodes
        << '\t' << r.total_ns
        << '\t' << ((r.has_decoded && r.decoded != tx) ? 1 : 0);
}

static int batch(const std::string &input_path, const std::string &output_path) {
    const auto lines = read_lines(input_path);
    if (lines.empty()) throw std::runtime_error("empty batch input");
    std::ofstream out(output_path);
    if (!out) throw std::runtime_error("cannot create " + output_path);
    out << "trial_id";
    for (const auto &p : {"dedup", "history"}) {
        out << '\t' << p << "_status\t" << p << "_complete\t" << p << "_decoded\t" << p << "_ties\t" << p << "_score\t" << p << "_bound\t" << p << "_stop_shell\t" << p << "_generated_attempts\t" << p << "_q_disc\t" << p << "_q_membership\t" << p << "_q_score\t" << p << "_global_duplicates\t" << p << "_total_ns\t" << p << "_ml_error";
    }
    out << "\tbestpath_shell\tbestpath_decoded\tbestpath_ties\tbestpath_selected_disagreement\tbestpath_strict_disjoint";
    for (const auto &p : {"exhaustive", "branch"}) {
        out << '\t' << p << "_status\t" << p << "_complete\t" << p << "_decoded\t" << p << "_ties\t" << p << "_score\t" << p << "_evaluated\t" << p << "_nodes\t" << p << "_total_ns\t" << p << "_ml_error";
    }
    out << '\n';

    for (std::size_t row = 1; row < lines.size(); ++row) {
        const auto c = split(lines[row], '\t');
        if (c.size() != 13) throw std::runtime_error("bad batch row field count=" + std::to_string(c.size()));
        const std::string id = c[0];
        Code code;
        code.n = std::stoi(c[1]);
        code.k = std::stoi(c[2]);
        const int a = std::stoi(c[3]);
        const u64 y = parse_u64(c[4]);
        const u64 tx = parse_u64(c[5]);
        code.generator = parse_hexes(c[6]);
        code.checks = parse_hexes(c[7]);
        const std::uint64_t max_generated = std::stoull(c[8]);
        const bool run_exhaustive = std::stoi(c[9]) != 0;
        const bool run_branch = std::stoi(c[10]) != 0;
        const std::uint64_t branch_node_cap = std::stoull(c[11]);
        const std::uint64_t branch_time_ms = std::stoull(c[12]);

        if (code.n < 2 || code.n > 63 || code.k < 1 || code.k >= code.n) throw std::runtime_error("invalid dimensions");
        if (static_cast<int>(code.generator.size()) != code.k || static_cast<int>(code.checks.size()) != code.n - code.k) throw std::runtime_error("G/H row count mismatch");
        if (a <= 1 || a > 99) throw std::runtime_error("odds denominator outside 2..99");
        if (y >= (1ULL << (code.n - 1)) || tx >= (1ULL << code.n)) throw std::runtime_error("word outside range");
        if (!code.contains(tx)) throw std::runtime_error("transmitted word is not in code");

        // Rotate decoder order by row ID to reduce systematic thermal/cache bias.
        ShellResult dedup, history;
        if ((std::stoull(id) & 1ULL) == 0ULL) {
            dedup = decode_shell(y, code, a, GenerationMode::DEDUP_INSERTION_SPHERE, max_generated, true);
            history = decode_shell(y, code, a, GenerationMode::HISTORY_PAIRS, max_generated, false);
        } else {
            history = decode_shell(y, code, a, GenerationMode::HISTORY_PAIRS, max_generated, false);
            dedup = decode_shell(y, code, a, GenerationMode::DEDUP_INSERTION_SPHERE, max_generated, true);
        }

        ExactResult exhaustive;
        if (run_exhaustive) exhaustive = exhaustive_ml(y, code, a);
        else exhaustive.status = "NOT_RUN";
        ExactResult branch;
        if (run_branch) branch = branch_and_bound_ml(y, code, a, branch_node_cap, branch_time_ms);
        else branch.status = "NOT_RUN";

        const bool bp_selected_disagreement = dedup.bestpath_has_decoded && dedup.has_decoded && dedup.bestpath_decoded != dedup.decoded;
        const bool bp_strict_disjoint = dedup.bestpath_has_decoded && dedup.has_decoded && tie_sets_disjoint(dedup.bestpath_ties, dedup.ties);

        out << id;
        emit_shell(out, "dedup", dedup, tx);
        emit_shell(out, "history", history, tx);
        out << '\t' << dedup.bestpath_shell
            << '\t' << (dedup.bestpath_has_decoded ? hex_u64(dedup.bestpath_decoded) : "")
            << '\t' << join_hexes(dedup.bestpath_ties)
            << '\t' << (bp_selected_disagreement ? 1 : 0)
            << '\t' << (bp_strict_disjoint ? 1 : 0);
        emit_exact(out, exhaustive, tx);
        emit_exact(out, branch, tx);
        out << '\n';
    }
    return 0;
}

static int self_test() {
    for (int m = 0; m <= 10; ++m) {
        for (u64 z = 0; z < (1ULL << m); ++z) {
            std::unordered_set<u64> all;
            for (int b = 0; b < 2; ++b) for (int j = 0; j <= m; ++j) all.insert(insert_bit(z, j, b));
            if (all.size() != static_cast<std::size_t>(m + 2)) throw std::runtime_error("insertion sphere cardinality failure");
            std::unordered_set<u64> dedup;
            for (int b = 0; b < 2; ++b) {
                dedup.insert(insert_bit(z, 0, b));
                for (int j = 1; j <= m; ++j) if (bit_at(z, j - 1) != b) dedup.insert(insert_bit(z, j, b));
            }
            if (dedup != all) throw std::runtime_error("dedup insertion generator failure");
        }
    }
    BigUInt capacity(1);
    for (int i = 0; i < 62; ++i) capacity.mul_small(99);
    if (capacity.str().empty()) throw std::runtime_error("BigUInt conversion failure");
    std::cout << "SELF_TEST=PASS\n";
    return 0;
}
} // namespace fg

int main(int argc, char **argv) {
    try {
        if (argc < 2) throw std::runtime_error("usage: fiber_grand_phase2c <self-test|batch> ...");
        const std::string command = argv[1];
        if (command == "self-test" && argc == 2) return fg::self_test();
        if (command == "batch" && argc == 4) return fg::batch(argv[2], argv[3]);
        throw std::runtime_error("bad command or arguments");
    } catch (const std::exception &error) {
        std::cerr << "ERROR: " << error.what() << "\n";
        return 2;
    }
}
