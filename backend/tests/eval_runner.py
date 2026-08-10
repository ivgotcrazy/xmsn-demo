"""T3.8 评估运行器：跑黄金集 v1 + 稳定性基线，输出报告（留档）。"""
import asyncio
import json
import sys
sys.path.insert(0, r"D:\code\xmsn-demo\xmsn-demo\backend")

from app.domains.conversation.eval import evaluate

CASES_PATH = r"D:\code\xmsn-demo\xmsn-demo\backend\tests\eval_cases.json"


async def main():
    with open(CASES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    print(f"黄金集: {data['version']} | {len(data['cases'])} cases | {data['description']}")
    report = await evaluate(data["cases"], stability_n=3, timing=True)
    print("\n=== 六维汇总 ===")
    print(f"avg_slot_f1      : {report['avg_slot_f1']}  (≥0.90 目标)")
    print(f"avg_completeness : {report['avg_completeness']}  (≥0.90 目标)")
    print(f"latency_cost     : {report['latency_cost']}")
    print(f"stability        : {report['stability']}")
    print("\n=== 逐 case ===")
    for r in report["reports"]:
        print(f"  {r['case_id']} [{r['category']}] f1={r['slot_f1']} comp={r['completeness']} "
              f"guidance={r['guidance']} e2e={r['e2e_top1']}")
        print(f"      pred={r['pred_slots']}")
    with open(r"D:\code\xmsn-demo\xmsn-demo\backend\tests\eval_report_v1.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n报告已存: tests/eval_report_v1.json")


asyncio.run(main())
