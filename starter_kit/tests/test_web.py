import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from loomq.web import create_server


BELL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""

GHZ = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;
"""

HYBRID = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
classical {
  r1 = 10;
  if (c[1] == 1) { r3 = r1 + 2; } else { r3 = r1 - 8; }
}
"""


class CompatibleAgentAPIHandler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request_payload = json.loads(self.rfile.read(length))
        type(self).calls.append(request_payload)
        prompt = request_payload["messages"][-1]["content"]
        if "后端" in prompt:
            content = "推荐规范后端 spinq_taurus_simulator：24 比特、免费、零排队的本地模拟器。"
        elif "GHZ" in prompt:
            content = "```qasm\n" + GHZ + "```"
        else:
            content = "```qasm\n" + BELL + "```"
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class WebLabTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.headers, response.read()

    def test_home_page_is_a_beginner_lab_not_a_blank_server(self):
        status, headers, body = self.request("/")

        page = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("LoomQ", page)
        self.assertIn("运行电路", page)
        self.assertIn("量子比特", page)
        self.assertIn('rel="icon"', page)
        self.assertIn("/favicon.ico", page)

    def test_favicon_route_is_served_without_404(self):
        status, headers, body = self.request("/favicon.ico")

        self.assertEqual(status, 200)
        self.assertIn("image", headers["Content-Type"])
        self.assertTrue(body)

    def test_home_exposes_learn_repair_backend_and_accessible_results(self):
        _status, _headers, body = self.request("/")

        page = body.decode()
        self.assertIn('href="#hybrid-panel"', page)
        self.assertIn('href="#workspace"', page)
        self.assertIn('data-task="learn"', page)
        self.assertIn('data-task="repair"', page)
        self.assertIn('data-task="backend"', page)
        self.assertIn('id="result-table"', page)
        self.assertIn('id="proof-panel"', page)
        self.assertIn('id="download-proof"', page)
        self.assertIn('role="alert"', page)
        self.assertIn('aria-describedby="prompt-help"', page)
        self.assertIn('<details id="state-trace"', page)
        self.assertIn('aria-label="逐门量子状态"', page)
        self.assertIn('data-example="w"', page)
        self.assertIn('data-example="interference"', page)
        self.assertIn('data-example="deutsch"', page)
        self.assertIn('data-example="grover"', page)
        self.assertIn('data-example="qft"', page)
        self.assertIn('id="clear-conversation"', page)
        self.assertIn('id="assert-panel"', page)
        self.assertIn('id="hybrid-panel"', page)
        self.assertIn('id="hybrid-path-panel"', page)
        self.assertIn('id="run-hybrid-path"', page)
        self.assertIn('列出所有可能分支', page)
        self.assertIn('id="download-hybrid-path"', page)
        self.assertIn('id="counterfactual-panel"', page)
        self.assertIn('id="witness-panel"', page)
        self.assertIn('id="run-witness"', page)
        self.assertIn('id="download-witness"', page)
        self.assertIn('id="candidate-qasm"', page)
        self.assertIn('id="run-compare"', page)
        self.assertIn("不归因具体噪声机制", page)
        self.assertIn('aria-label="90 秒评委导览"', page)
        self.assertIn('id="run-judge-tour"', page)
        self.assertIn('id="judge-tour-status"', page)
        self.assertIn('href="#workspace"', page)
        self.assertIn('href="#counterfactual-panel"', page)
        self.assertIn('href="#assert-panel"', page)
        self.assertIn('href="#witness-panel"', page)
        self.assertIn('href="#hybrid-panel"', page)
        self.assertIn('href="#prompt-contract-panel"', page)
        self.assertIn('id="inspect-prompt-contract"', page)
        self.assertIn('id="prompt-contract-result"', page)

    def test_home_places_evidence_navigator_before_feature_inventory(self):
        _status, _headers, body = self.request("/")

        page = body.decode()
        self.assertIn('id="evidence-map"', page)
        self.assertIn(">1 分钟看证据</a>", page)
        self.assertIn('href="#evidence-map"', page)
        self.assertIn(">3 分钟跑示例</a>", page)
        self.assertIn('href="#workspace"', page)
        self.assertIn(">查看原始材料</a>", page)
        self.assertIn(
            'href="https://github.com/JunkaiWang-TheoPhy/LoomQ-2026/tree/main/starter_kit/evidence"',
            page,
        )

        self.assertLess(page.index('id="evidence-map"'), page.index('id="task-title"'))
        self.assertLess(page.index("编译有没有改坏电路?"), page.index("测量后程序会走哪条路?"))
        self.assertLess(page.index("测量后程序会走哪条路?"), page.index("不会 QASM 能不能用?"))
        self.assertLess(page.index("编译有没有改坏电路?"), page.index('id="task-title"'))

    def test_home_answers_three_judge_questions_with_click_and_expect_language(self):
        _status, _headers, body = self.request("/")

        page = body.decode()
        self.assertIn("编译有没有改坏电路?", page)
        self.assertIn("测量后程序会走哪条路?", page)
        self.assertIn("不会 QASM 能不能用?", page)
        self.assertIn("点击 <a href=\"#proof-panel\">ProofTrace", page)
        self.assertIn("会看到三种目标平台", page)
        self.assertIn("点击 <a href=\"#hybrid-panel\">列出所有可能分支", page)
        self.assertIn("会看到每条路径的概率", page)
        self.assertIn("点击修复一段错误 QASM", page)
        self.assertIn("会看到 Agent 先给出可运行答案", page)

    def test_frontend_renders_trace_amplitudes_and_can_clear_history(self):
        status, headers, body = self.request("/app.js")

        script = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn("state.amplitude_real", script)
        self.assertIn("state.amplitude_imag", script)
        self.assertIn("data.trace.length <= 15", script)
        self.assertIn("data.proof.portability", script)
        self.assertIn("application/json", script)
        self.assertIn("downloadProof.href = lastProofUrl", script)
        self.assertIn("downloadProof.download =", script)
        self.assertIn("coveredSourceOperations", script)
        self.assertIn("sourceMetrics.measurement_count", script)
        self.assertIn("agentHistory.splice(0)", script)
        self.assertIn('api("/api/assert"', script)
        self.assertIn('api("/api/hybrid-trace"', script)
        self.assertIn('api("/api/hybrid-paths"', script)
        self.assertIn('api("/api/compare"', script)
        self.assertIn('api("/api/causal-audit"', script)
        self.assertIn("witness_chain", script)
        self.assertIn("downloadWitness.href", script)
        self.assertIn("downloadHybridPath.href", script)
        self.assertIn("first_divergent_gate", script)
        self.assertIn("final_distribution_distance", script)
        self.assertIn("confidence_interval", script)
        self.assertIn("machine_jump_taken", script)
        self.assertIn("source_condition_true", script)
        self.assertIn("attribution_caveat", script)
        self.assertIn("这条路径会发生", script)
        self.assertIn("在当前量子态下不会发生", script)

    def test_frontend_tour_requires_semantic_evidence_and_resets_changed_inputs(self):
        status, headers, body = self.request("/app.js")

        script = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn('const TOUR_TARGETS = ["spinq", "originq", "braket"]', script)
        self.assertIn("function requireTourEvidence", script)
        self.assertIn("function markTourStep", script)
        self.assertIn("function resetTourStep", script)
        self.assertIn('api("/api/prompt-contract"', script)
        self.assertIn("contract.integrity.is_signature === false", script)
        self.assertIn("verification.valid === true", script)
        self.assertIn('$("#run-judge-tour").addEventListener', script)
        self.assertIn("addEvidenceReset", script)

    def test_styles_include_mobile_overflow_guards_for_evidence_panels(self):
        status, headers, body = self.request("/styles.css")

        stylesheet = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("css", headers["Content-Type"])
        self.assertIn("@media(max-width:900px)", stylesheet)
        self.assertIn(".evidence-header{grid-template-columns:1fr", stylesheet)
        self.assertIn(".evidence-grid{grid-template-columns:1fr", stylesheet)
        self.assertIn("@media(max-width:620px)", stylesheet)
        self.assertIn(".evidence-controls{grid-template-columns:1fr", stylesheet)
        self.assertIn(".evidence-card{padding:18px", stylesheet)
        self.assertIn("overflow-wrap:anywhere", stylesheet)
        self.assertIn("word-break:break-word", stylesheet)
        self.assertIn(".hardware-proofline", stylesheet)
        self.assertIn(".judge-tour", stylesheet)
        self.assertIn(".judge-tour a.complete", stylesheet)
        self.assertIn(".prompt-contract-panel", stylesheet)
        self.assertIn("overflow-x:auto", stylesheet)

    def test_enhancement_styles_keep_hybrid_path_evidence_shrink_safe(self):
        status, headers, body = self.request("/enhancements.css")

        stylesheet = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("css", headers["Content-Type"])
        self.assertIn(".path-summary-grid", stylesheet)
        self.assertIn(".path-outcomes", stylesheet)
        self.assertIn(".path-download", stylesheet)
        self.assertIn("min-width:0", stylesheet)
        self.assertIn("overflow-wrap:anywhere", stylesheet)
        self.assertIn("@media (max-width: 620px)", stylesheet)

    def test_run_endpoint_returns_counts_native_ir_and_probability(self):
        status, _headers, body = self.request(
            "/api/run", {"qasm": BELL, "target": "spinq", "shots": 128}
        )

        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["shots"], 128)
        self.assertEqual(set(result["result"]["counts"]), {"00", "11"})
        self.assertEqual(set(result["probabilities"]), {"00", "11"})
        self.assertIn("OPENQASM 2.0", result["native_ir"])
        self.assertEqual(result["proof"]["schema_version"], "loomq-prooftrace-v1")
        self.assertTrue(result["proof"]["equivalence"]["verified"])
        self.assertEqual(set(result["proof"]["portability"]), {"spinq", "originq", "braket"})
        self.assertTrue(
            all(
                target["roundtrip_verified"]
                for target in result["proof"]["portability"].values()
            )
        )
        self.assertEqual(
            [event["operation"]["kind"] for event in result["trace"]],
            ["initial", "gate", "gate", "measure"],
        )
        self.assertEqual(
            {state["basis"]: state["probability"] for state in result["trace"][2]["states"]},
            {"00": 0.5, "11": 0.5},
        )

    def test_run_endpoint_supports_every_required_target(self):
        for target in ("spinq", "originq", "braket"):
            with self.subTest(target=target):
                status, _headers, body = self.request(
                    "/api/run", {"qasm": BELL, "target": target, "shots": 127}
                )
                payload = json.loads(body)
                self.assertEqual(status, 200)
                self.assertTrue(payload["result"]["backend"].startswith(target))
                self.assertEqual(sum(payload["result"]["counts"].values()), 127)
                self.assertAlmostEqual(sum(payload["probabilities"].values()), 1.0)

    def test_assert_endpoint_reports_exact_local_assertions(self):
        status, _headers, body = self.request(
            "/api/assert",
            {
                "qasm": BELL,
                "assertions": [
                    {"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999},
                    {"kind": "parity", "bits": [0, 1], "expected": "even", "minimum_probability": 0.999},
                ],
            },
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["mode"], "exact-local")
        self.assertEqual([item["status"] for item in payload["assertions"]], ["pass", "pass"])
        self.assertTrue(all(item["evidence_mode"] == "exact-local" for item in payload["assertions"]))
        self.assertEqual(payload["attribution_caveat"], "本地精确断言不归因具体噪声机制。")

    def test_assert_endpoint_diagnoses_observed_execution_with_cautious_language(self):
        status, _headers, body = self.request(
            "/api/assert",
            {
                "qasm": BELL,
                "assertions": [
                    {"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}
                ],
                "observed": {"00": 48, "11": 47, "01": 3, "10": 2},
                "shots": 100,
            },
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["mode"], "observed-execution")
        self.assertEqual(payload["diagnosis"]["classification"], "inconclusive")
        self.assertEqual(
            payload["diagnosis"]["observed_assertions"][0]["evidence_mode"],
            "finite-shots",
        )
        self.assertIn(
            "confidence_interval",
            payload["diagnosis"]["observed_assertions"][0],
        )
        self.assertIn("does not identify a physical cause", payload["diagnosis"]["attribution_caveat"])

    def test_hybrid_trace_endpoint_replays_branch_evidence(self):
        status, _headers, body = self.request(
            "/api/hybrid-trace",
            {"source": HYBRID, "measurement_bits": [1, 0]},
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["schema_version"], "loomq-hybrid-trace-v1")
        self.assertEqual(payload["measurement_inputs"], [1, 0])
        self.assertEqual(payload["branch_path"], "if1:F")
        self.assertEqual(payload["final_registers"]["x3"], 2)
        branch = payload["branch_events"][0]
        self.assertEqual(branch["pc"], 3)
        self.assertTrue(branch["machine_jump_taken"])
        self.assertFalse(branch["source_condition_true"])
        self.assertEqual(branch["influencing_measurements"], ["c[1]"])

    def test_hybrid_path_endpoint_reports_certificate_and_recomputed_verification(self):
        status, _headers, body = self.request(
            "/api/hybrid-paths",
            {"source": HYBRID, "max_outcomes": 4},
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        certificate = payload["certificate"]
        verification = payload["verification"]
        self.assertEqual(certificate["schema_version"], "loomq-hybrid-path-certificate-v1")
        self.assertEqual(certificate["limits"]["max_outcomes"], 4)
        self.assertEqual(
            [item["path_id"] for item in certificate["path_groups"]],
            ["if1:F", "if1:T"],
        )
        self.assertEqual(
            [item["total_probability"] for item in certificate["path_groups"]],
            [0.5, 0.5],
        )
        self.assertEqual(certificate["unreachable_outcomes"], ["01", "10"])
        self.assertTrue(verification["valid"])
        self.assertEqual(verification["certificate_sha256"], certificate["integrity"]["body_sha256"])
        self.assertEqual(verification["recomputed_sha256"], certificate["integrity"]["body_sha256"])

        alias_status, _alias_headers, alias_body = self.request(
            "/api/hybrid-path-certificate",
            {"source": HYBRID, "max_outcomes": 4},
        )
        self.assertEqual(alias_status, 200)
        self.assertEqual(json.loads(alias_body), payload)

    def test_hybrid_path_endpoint_rejects_invalid_and_insufficient_bounds(self):
        invalid_payloads = (
            {"source": HYBRID, "max_outcomes": True},
            {"source": HYBRID, "max_outcomes": 0},
            {"source": HYBRID, "max_outcomes": 257},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                request = urllib.request.Request(
                    self.base + "/api/hybrid-paths",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=3)
                error_payload = json.loads(caught.exception.read())
                caught.exception.close()
                self.assertEqual(caught.exception.code, 400)
                self.assertEqual(error_payload["error"]["code"], "invalid_request")

        request = urllib.request.Request(
            self.base + "/api/hybrid-paths",
            data=json.dumps({"source": HYBRID, "max_outcomes": 2}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        error_payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(error_payload["error"]["code"], "invalid_request")
        self.assertIn("2**num_clbits <= max_outcomes", error_payload["error"]["message"])

    def test_prompt_contract_endpoint_exposes_rebuild_verified_semantics(self):
        prompt = "Which free 20-qubit simulator on OriginQ needs no account?"

        try:
            status, _headers, body = self.request(
                "/api/prompt-contract",
                {"prompt": prompt},
            )
        except urllib.error.HTTPError as exc:
            status, body = exc.code, exc.read()
            exc.close()

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["contract"]["task_kind"], "backend")
        self.assertEqual(
            payload["contract"]["backend_constraints"]["platforms"],
            ["originq"],
        )
        self.assertFalse(
            payload["contract"]["backend_constraints"]["requires_account"]
        )
        self.assertTrue(payload["verification"]["valid"])
        self.assertFalse(payload["contract"]["integrity"]["is_signature"])

    def test_compare_endpoint_finds_the_first_causal_divergence(self):
        candidate = BELL.replace("cx q[0],q[1];", "x q[1];")

        status, _headers, body = self.request(
            "/api/compare",
            {"reference_qasm": BELL, "candidate_qasm": candidate},
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["scope"], "exact-up-to-global-phase-at-zero-input")
        self.assertFalse(payload["equivalent_output_distribution"])
        self.assertEqual(payload["first_divergent_gate"], 1)
        self.assertEqual(payload["reference_operation"]["gate"], "cx")
        self.assertEqual(payload["candidate_operation"]["gate"], "x")
        self.assertGreater(payload["max_amplitude_delta"], 0)
        self.assertGreater(payload["final_distribution_distance"], 0)
        self.assertIn("explanation", payload)
        self.assertIn("第 2 扇门", payload["explanation"])

    def test_compare_endpoint_reports_structural_mismatch_without_false_causality(self):
        candidate = BELL.replace("measure q -> c;", "measure q[0] -> c[0];")

        status, _headers, body = self.request(
            "/api/compare",
            {"reference_qasm": BELL, "candidate_qasm": candidate},
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["scope"], "structural-mismatch")
        self.assertIsNone(payload["first_divergent_gate"])
        self.assertIn("测量映射", payload["explanation"])

    def test_causal_audit_endpoint_unifies_cross_module_witnesses(self):
        candidate = BELL.replace("cx q[0],q[1];", "x q[1];")

        status, _headers, body = self.request(
            "/api/causal-audit",
            {
                "reference_qasm": BELL,
                "candidate_qasm": candidate,
                "assertions": [
                    {
                        "kind": "support",
                        "states": ["00", "11"],
                        "minimum_probability": 0.9,
                    }
                ],
                "hybrid_source": HYBRID,
                "measurement_bits": [1, 0],
                "target": "spinq",
            },
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["schema_version"], "loomq-witness-chain-v1")
        stages = {stage["stage"]: stage for stage in payload["witness_chain"]}
        self.assertEqual(
            stages["counterfactual"]["counterfactual"]["reference_witness_id"],
            "g2",
        )
        self.assertEqual(
            stages["assertions"]["assertions"][0]["measurement_witness_ids"],
            ["m1", "m2"],
        )
        self.assertEqual(
            stages["hybrid"]["hybrid"]["branch_events"][0]["measurement_witness_ids"],
            ["m2"],
        )
        self.assertTrue(payload["verification"]["valid"])

    def test_large_valid_circuit_keeps_running_when_visual_trace_is_bounded(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[9]; creg c[9]; x q[8]; measure q -> c;
"""

        status, _headers, body = self.request(
            "/api/run", {"qasm": source, "target": "spinq", "shots": 17}
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["result"]["counts"], {"100000000": 17})
        self.assertEqual(payload["trace"], [])
        self.assertIn("at most 8 qubits", payload["trace_notice"])

    def test_invalid_run_is_a_structured_400_error(self):
        request = urllib.request.Request(
            self.base + "/api/run",
            data=json.dumps({"qasm": "bad", "target": "spinq", "shots": 0}).encode(),
            headers={"Content-Type": "application/json"},
        )

        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertTrue(payload["error"]["message"])

    def test_agent_without_credentials_explains_configuration_without_leaking_env(self):
        with mock.patch.dict(os.environ, {"PRIVATE_TOKEN": "never-show-this"}, clear=True):
            request = urllib.request.Request(
                self.base + "/api/agent",
                data=json.dumps({"prompt": "生成 Bell 态"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=3)

        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(payload["error"]["code"], "llm_not_configured")
        self.assertIn("LOOMQ_LLM_BASE_URL", payload["error"]["message"])
        self.assertNotIn("never-show-this", json.dumps(payload))

    def test_agent_rejects_unbounded_prompt_before_calling_provider(self):
        with mock.patch.dict(
            os.environ,
            {
                "LOOMQ_LLM_BASE_URL": "https://example.invalid",
                "LOOMQ_LLM_API_KEY": "secret",
                "LOOMQ_LLM_MODEL": "model",
            },
            clear=True,
        ), mock.patch("loomq.web.adapter.agent_chat") as agent_chat:
            request = urllib.request.Request(
                self.base + "/api/agent",
                data=json.dumps({"prompt": "x" * 20_001}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=3)

        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertIn("20000", payload["error"]["message"])
        agent_chat.assert_not_called()

    def test_web_agent_end_to_end_covers_generation_repair_and_backend_tasks(self):
        provider = ThreadingHTTPServer(("127.0.0.1", 0), CompatibleAgentAPIHandler)
        provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
        CompatibleAgentAPIHandler.calls = []
        provider_thread.start()
        environment = {
            "LOOMQ_LLM_BASE_URL": f"http://127.0.0.1:{provider.server_port}",
            "LOOMQ_LLM_API_KEY": "local-protocol-fixture",
            "LOOMQ_LLM_MODEL": "local-model",
            "LOOMQ_LLM_TIMEOUT_SECONDS": "2",
        }
        prompts = (
            "生成 Bell 态并测量全部量子比特",
            "修复这段 Bell 电路：cx q[0],q[2];",
            "推荐一个免费、零排队、至少 20 比特的模拟器后端",
        )
        try:
            with mock.patch.dict(os.environ, environment, clear=True):
                replies = []
                for prompt in prompts:
                    status, _headers, body = self.request("/api/agent", {"prompt": prompt})
                    self.assertEqual(status, 200)
                    replies.append(json.loads(body)["reply"])
        finally:
            provider.shutdown()
            provider.server_close()
            provider_thread.join(timeout=2)

        self.assertEqual(len(CompatibleAgentAPIHandler.calls), 3)
        self.assertTrue(all(call["model"] == "local-model" for call in CompatibleAgentAPIHandler.calls))
        self.assertIn("OPENQASM 2.0", replies[0])
        self.assertIn("OPENQASM 2.0", replies[1])
        self.assertIn("spinq_taurus_simulator", replies[2])

    def test_agent_history_is_bounded_and_reaches_provider_as_real_multi_turn_context(self):
        provider = ThreadingHTTPServer(("127.0.0.1", 0), CompatibleAgentAPIHandler)
        provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
        CompatibleAgentAPIHandler.calls = []
        provider_thread.start()
        environment = {
            "LOOMQ_LLM_BASE_URL": f"http://127.0.0.1:{provider.server_port}",
            "LOOMQ_LLM_API_KEY": "local-protocol-fixture",
            "LOOMQ_LLM_MODEL": "local-model",
            "LOOMQ_LLM_TIMEOUT_SECONDS": "2",
        }
        history = [
            {"role": "user", "content": "生成 Bell 态并测量"},
            {"role": "assistant", "content": "```qasm\n" + BELL + "```"},
        ]
        try:
            with mock.patch.dict(os.environ, environment, clear=True):
                status, _headers, body = self.request(
                    "/api/agent",
                    {"prompt": "把它改成 GHZ 三比特并测量", "history": history},
                )
        finally:
            provider.shutdown()
            provider.server_close()
            provider_thread.join(timeout=2)

        self.assertEqual(status, 200)
        self.assertIn("qreg q[3]", json.loads(body)["reply"])
        messages = CompatibleAgentAPIHandler.calls[0]["messages"]
        self.assertEqual([message["role"] for message in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[1:], history + [{"role": "user", "content": "把它改成 GHZ 三比特并测量"}])

    def test_agent_rejects_non_alternating_or_oversized_history_before_provider_call(self):
        environment = {
            "LOOMQ_LLM_BASE_URL": "https://example.invalid",
            "LOOMQ_LLM_API_KEY": "secret",
            "LOOMQ_LLM_MODEL": "model",
        }
        invalid_histories = (
            [{"role": "assistant", "content": "伪造的开场"}],
            [
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
            ] * 5,
        )
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch(
            "loomq.web.adapter.agent_chat"
        ) as agent_chat:
            for history in invalid_histories:
                with self.subTest(history_length=len(history)):
                    request = urllib.request.Request(
                        self.base + "/api/agent",
                        data=json.dumps({"prompt": "生成 Bell 态", "history": history}).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(request, timeout=3)
                    self.assertEqual(caught.exception.code, 400)
                    caught.exception.close()
            agent_chat.assert_not_called()

    def test_malformed_json_and_unsupported_method_are_structured_errors(self):
        malformed = urllib.request.Request(
            self.base + "/api/run",
            data=b"{",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(malformed, timeout=3)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

        delete = urllib.request.Request(self.base + "/api/run", method="DELETE")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(delete, timeout=3)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 405)
        self.assertEqual(payload["error"]["code"], "method_not_allowed")

    def test_security_headers_are_present_on_success_and_error(self):
        _status, headers, _body = self.request("/")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["X-Frame-Options"], "DENY")

        request = urllib.request.Request(self.base + "/missing")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(caught.exception.headers["X-Frame-Options"], "DENY")
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
