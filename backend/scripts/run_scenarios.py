"""Ejecuta los 15 usuarios de prueba contra la API (local o AWS) y valida el resultado esperado.

Uso:
    uv run python scripts/run_scenarios.py                          # http://localhost:8010
    uv run python scripts/run_scenarios.py --base-url https://xxx.execute-api.us-east-1.amazonaws.com
    uv run python scripts/run_scenarios.py --reset --write-doc      # limpia onboardings (BD local) y escribe docs/pruebas
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SCENARIOS = [
    # (id, nombre, cédula, producto, http esperado, status esperado, código esperado, descripción)
    (1, "Juan Perez", "1712345675", "cuenta_ahorros", 200, "APPROVED", "ONB-OK-000", "Caso feliz"),
    (2, "Juan Perez", "1712345678", "cuenta_ahorros", 200, "REJECTED", "ONB-DOC-001", "Cédula del enunciado: dígito verificador inválido"),
    (3, "Maria Fernanda Loor", "0918765439", "cuenta_ahorros", 200, "ESCALATED", "ONB-IDV-002", "Confianza 0.72 < 0.80"),
    (4, "Luis Ortega", "0104567896", "cuenta_ahorros", 200, "ESCALATED", "ONB-IDV-001", "No consta en Registro Civil"),
    (5, "Carlos Andrade", "1709988776", "cuenta_ahorros", 200, "ESCALATED", "ONB-RSK-001", "Riesgo alto (UAFE + OFAC)"),
    (6, "Patricia Salazar", "1805566773", "cuenta_corriente", 200, "AWAITING_CUSTOMER", "ONB-RSK-002", "PEP: riesgo medio, pide información"),
    (7, "Mateo Cedeño", "1302244668", "cuenta_ahorros", 200, "REJECTED", "ONB-IDV-004", "Menor de edad (16)"),
    (8, "Rosa Vera", "1107788992", "cuenta_ahorros", 200, "ESCALATED", "ONB-IDV-001", "FALLECIDO en Registro Civil"),
    (9, "Diego Paredes", "0603344557", "cuenta_ahorros", 503, "ERROR", "ONB-IDV-503", "Registro Civil timeout"),
    (10, "Sofia Mena", "1711122232", "cuenta_ahorros", 503, "ERROR", "ONB-RSK-503", "Listas de riesgo HTTP 500"),
    (11, "Pedro Gomez", "0922233341", "cuenta_ahorros", 200, "ESCALATED", "ONB-IDV-003", "Nombre no coincide con la cédula"),
    (12, "Juan Perez", "1712345675", "cuenta_ahorros", 409, None, "ONB-DUP-409", "Duplicado (después del #1)"),
    (13, "Juan Perez", "1712345675", "tarjeta_oro", 400, None, "ONB-VAL-400", "Producto inválido (marshmallow)"),
    (14, "Valeria Rios", "1717171712", "cuenta_ahorros", 200, "APPROVED", "ONB-OK-000", "Documentación vía RAG (tool caído)"),
    (15, "Camila Herrera", "1724680242", "cuenta_ahorros", 200, "APPROVED_PENDING_PROVISIONING", "ONB-PRV-503", "Falla creación de usuario"),
]
EDD_ANSWERS = {"actividad_economica": "Empleado privado", "origen_fondos": "Sueldo", "ingresos_mensuales": 2800}


def call(base: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(f"{base}{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def run(base: str, scenario: tuple) -> dict:
    sid, name, doc, product, http_exp, status_exp, code_exp, desc = scenario
    started = time.perf_counter()
    http, body = call(base, "POST", "/api/v1/onboarding/start",
                      {"prospect_name": name, "document_id": doc, "product": product})
    status, code = body.get("status"), body.get("reason_code") or body.get("code")
    ok = http == http_exp and status == status_exp and code == code_exp
    extra = ""
    if sid == 14:
        sources = {d.get("source") for d in body.get("required_documents", [])}
        ok = ok and sources == {"rag_fallback"}
        extra = f"fuente documentos: {', '.join(sorted(sources))}"
    if sid == 6 and ok:
        http2, body2 = call(base, "POST", f"/api/v1/onboarding/{body['onboarding_id']}/continue", {"answers": EDD_ANSWERS})
        ok = http2 == 200 and body2.get("status") == "APPROVED" and body2.get("reason_code") == "ONB-OK-001"
        extra = f"tras /continue: {http2} {body2.get('status')} {body2.get('reason_code')}"
        body = body2
    return {"id": sid, "name": name, "doc": doc, "product": product, "desc": desc, "ok": ok, "http": http,
            "status": status, "code": code, "expected": f"{http_exp} {status_exp or '-'} {code_exp}", "extra": extra,
            "message": body.get("customer_message") or body.get("message"),
            "provisioning": body.get("provisioning"), "seconds": round(time.perf_counter() - started, 1),
            "onboarding_id": body.get("onboarding_id")}


def reset_local_db() -> None:
    sys.path.insert(0, str(REPO / "backend"))
    from app.db.pool import execute
    execute("TRUNCATE core.onboarding_request CASCADE")
    execute("TRUNCATE checkpoint.checkpoints, checkpoint.checkpoint_blobs, checkpoint.checkpoint_writes")


def write_doc(results: list[dict], base: str) -> None:
    lines = [
        "# Resultados de los usuarios de prueba", "",
        f"Ejecutado el {datetime.now():%Y-%m-%d %H:%M} contra `{base}` con `backend/scripts/run_scenarios.py`.", "",
        "| # | Nombre | Cédula | Producto | Esperado | Obtenido | OK | Escenario |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['id']} | {r['name']} | {r['doc']} | {r['product']} | {r['expected']} | "
                     f"{r['http']} {r['status'] or '-'} {r['code']} | {'✅' if r['ok'] else '❌'} | {r['desc']} |")
    lines += ["", "## Mensaje al usuario final por escenario", ""]
    for r in results:
        lines += [f"**{r['id']}. {r['name']} ({r['doc']}) → {r['code']}**" + (f" — {r['extra']}" if r["extra"] else ""), "",
                  f"> {r['message']}", ""]
    out = REPO / "docs" / "pruebas" / "RESULTADOS_PRUEBAS.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Escrito {out.relative_to(REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--reset", action="store_true", help="Limpia onboardings en la BD local antes de correr")
    parser.add_argument("--write-doc", action="store_true")
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    if args.reset:
        reset_local_db()

    first = run(args.base_url, SCENARIOS[0])                       # el #12 depende de que el #1 exista
    with ThreadPoolExecutor(args.workers) as pool:
        rest = list(pool.map(lambda s: run(args.base_url, s), SCENARIOS[1:]))
    results = sorted([first, *rest], key=lambda r: r["id"])

    for r in results:
        print(f"{'✅' if r['ok'] else '❌'} #{r['id']:<2} {r['name']:<20} {r['doc']} esperado [{r['expected']}] "
              f"obtenido [{r['http']} {r['status'] or '-'} {r['code']}] {r['seconds']}s {r['extra']}")
    passed = sum(r["ok"] for r in results)
    print(f"\n{passed}/{len(results)} escenarios OK")
    if args.write_doc:
        write_doc(results, args.base_url)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
