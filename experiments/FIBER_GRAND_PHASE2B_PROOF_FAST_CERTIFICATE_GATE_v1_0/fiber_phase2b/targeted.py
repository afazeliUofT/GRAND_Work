from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .reference import build_code, delete_bit
from .util import median, percentile, run, stable_seed, utc_now_iso, write_csv, write_json


def _write_tsv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.writer(f, delimiter="\t", lineterminator="\n");w.writerow(header);w.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str,str]]:
    with path.open("r",encoding="utf-8",newline="") as f:return list(csv.DictReader(f,delimiter="\t"))


def _ties(s:str)->tuple[int,...]:
    return tuple(sorted(int(x,0) for x in s.replace(","," ").split())) if s.strip() else ()


def run_targeted(binary: Path, cfg: dict[str, Any], output: Path) -> dict[str, Any]:
    tc=cfg["targeted_pilot"]; n=int(tc["n"]); p_num=int(tc["p_num"]);p_den=int(tc["p_den"]);a=(p_den-p_num)//p_num
    schedule=str(tc["alignment_schedule"]);per_cell=int(tc["trials_per_cell"]);instances=int(tc["random_code_instances"]);master=int(cfg["master_seed"]);cap=int(tc["max_histories"])
    specs=[]; input_rows=[]; idx=0
    for rate in tc["rates"]:
        label=str(rate["label"]);k=round(n*float(rate["target"]))
        for family in tc["families"]:
            for t in range(per_cell):
                instance=t%instances if family=="random_systematic_linear" else 0
                code_seed=stable_seed(master,"phase2b_code",family,n,k,instance)
                code=build_code(family,n,k,code_seed)
                seed=stable_seed(master,"phase2b_trial",family,n,k,t)
                rng=random.Random(seed);msg=rng.randrange(1<<k);tx=code.encode(msg);j=rng.randrange(n)
                err=0
                for pos in range(n-1):
                    if rng.randrange(p_den)<p_num:err|=1<<pos
                y=delete_bit(tx,j)^err
                spec={"id":idx,"family":family,"rate_label":label,"n":n,"k":k,"rate":k/n,"trial_index":t,"code_instance":instance,"code_seed":code_seed,"trial_seed":seed,"p_s":p_num/p_den,"transmitted":tx,"observation":y,"deletion_position":j,"observed_error_weight":err.bit_count()}
                specs.append(spec)
                input_rows.append([idx,n,k,a,schedule,cap,hex(y),hex(tx),",".join(hex(x) for x in code.rows)])
                idx+=1
    output.mkdir(parents=True,exist_ok=True)
    _write_tsv(output/"TARGETED_INPUT.tsv",["id","n","k","a","schedule","max_hist","y","transmitted","rows"],input_rows)
    run([binary,"decode-batch",output/"TARGETED_INPUT.tsv",output/"TARGETED_CPP.tsv"],log=output/"TARGETED_CPP.log")
    got=_read_tsv(output/"TARGETED_CPP.tsv")
    rows=[];disagreements=0;censored=0
    for spec,r in zip(specs,got):
        mode_sig=[]
        for pre in ("ind","cr","ac","fast"):
            mode_sig.append((r[f"{pre}_score"],_ties(r[f"{pre}_ties"]),r[f"{pre}_decoded"]))
            censored+=int(r[f"{pre}_complete"]!="1")
        disagreement=len(set(mode_sig))!=1
        disagreements+=int(disagreement)
        ml_ties=_ties(r["ind_ties"]);ml=int(r["ind_decoded"],0);first=int(r["first_codeword"],0) if r["first_codeword"] else None
        row={**spec,"disagreement":disagreement,"ml_decoded":hex(ml),"ml_tie_count":len(ml_ties),"transmitted_in_ml_ties":spec["transmitted"] in ml_ties,"scalar_ml_error":ml!=spec["transmitted"],"best_path_first":hex(first) if first is not None else "","best_path_not_ml":first is not None and first not in ml_ties}
        for pre in ("ind","cr","ac","fast"):
            for field in ("q_hist","q_disc","q_code","q_score","bound_ns","total_ns","uac_calls","chain_calls"):
                row[f"{pre}_{field}"]=int(r[f"{pre}_{field}"])
        row["q_hist_ratio_ind_over_ac"]=row["ind_q_hist"]/row["ac_q_hist"]
        row["q_hist_ratio_ind_over_fast"]=row["ind_q_hist"]/row["fast_q_hist"]
        row["q_score_ratio_codebook_over_ind"]=(1<<spec["k"])/max(1,row["ind_q_score"])
        row["wall_ratio_ind_over_ac"]=row["ind_total_ns"]/max(1,row["ac_total_ns"])
        row["wall_ratio_ind_over_fast"]=row["ind_total_ns"]/max(1,row["fast_total_ns"])
        row["wall_ratio_ind_over_cr"]=row["ind_total_ns"]/max(1,row["cr_total_ns"])
        rows.append(row)
    write_csv(output/"TARGETED_TRIALS.csv",rows)
    groups=defaultdict(list)
    for r in rows:groups[(r["rate_label"],r["family"])].append(r)
    cells=[]
    for (rate,fam),v in sorted(groups.items()):
        ind_times=[x["ind_total_ns"] for x in v];ac_times=[x["ac_total_ns"] for x in v]
        fast_times=[x["fast_total_ns"] for x in v]
        cell={"rate_label":rate,"family":fam,"trials":len(v),"disagreements":sum(x["disagreement"] for x in v),"median_q_hist_ratio_ind_over_ac":median([x["q_hist_ratio_ind_over_ac"] for x in v]),"median_q_hist_ratio_ind_over_fast":median([x["q_hist_ratio_ind_over_fast"] for x in v]),"p95_q_hist_ratio_ind_over_fast":percentile([x["q_hist_ratio_ind_over_fast"] for x in v],.95),"p99_q_hist_ratio_ind_over_fast":percentile([x["q_hist_ratio_ind_over_fast"] for x in v],.99),"median_wall_ratio_ind_over_fast":median([x["wall_ratio_ind_over_fast"] for x in v]),"p95_latency_ratio_ind_over_fast":percentile(ind_times,.95)/max(1,percentile(fast_times,.95)),"median_codebook_over_qscore":median([x["q_score_ratio_codebook_over_ind"] for x in v]),"p05_codebook_over_qscore":percentile([x["q_score_ratio_codebook_over_ind"] for x in v],.05),"best_path_not_ml_rate":sum(x["best_path_not_ml"] for x in v)/len(v),"transmitted_not_in_ml_rate":sum(not x["transmitted_in_ml_ties"] for x in v)/len(v)}
        cells.append(cell)
    write_csv(output/"TARGETED_CELL_SUMMARY.csv",cells)
    standard=[c for c in cells if c["median_q_hist_ratio_ind_over_fast"]>=float(tc["gate"]["median_work_ratio_min"]) and c["median_wall_ratio_ind_over_fast"]>=float(tc["gate"]["median_wall_ratio_min"])]
    tail=[c for c in cells if c["median_wall_ratio_ind_over_fast"]>=1/float(tc["gate"]["median_overhead_max"]) and c["p95_latency_ratio_ind_over_fast"]>=float(tc["gate"]["p95_latency_ratio_min"])]
    gate=(disagreements==0 and censored==0 and (len(standard)>=int(tc["gate"]["cells_required"]) or len(tail)>=int(tc["gate"]["cells_required"])))
    report={"created_utc":utc_now_iso(),"status":"PASS" if disagreements==0 and censored==0 else "FAIL","trials":len(rows),"cells":len(cells),"disagreements":disagreements,"censored_mode_results":censored,"standard_gate_cells":len(standard),"tail_gate_cells":len(tail),"conference_specialization_candidate":gate,"cell_summary":cells}
    write_json(output/"TARGETED_REPORT.json",report)
    return report
