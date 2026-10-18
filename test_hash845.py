"""
Hash845 (DI-QZKP) 完整單元與整合測試套件
涵蓋密度矩陣模擬、CHSH 協議、各類型證明者、物理邊界防禦與防重放訊息簽章驗證。
"""

import unittest
import math
import hashlib
from quantum_engine import BellStateSimulator, matrix_trace_4x4
from provers import QuantumBellProver, ClassicalLHVProver, ColludingClassicalProver
from hash845_core import Hash845Verifier
from signature import Hash845Signer, Hash845SignatureVerifier, Hash845Signature


class TestQuantumEngine(unittest.TestCase):
    def test_density_matrix_trace(self):
        """測試無噪訊與有噪訊情況下，密度矩陣之跡恆等於 1。"""
        for p in (0.0, 0.2, 0.5, 1.0):
            sim = BellStateSimulator(noise_prob=p)
            tr = matrix_trace_4x4(sim.density_matrix)
            self.assertAlmostEqual(tr.real, 1.0, places=7)
            self.assertAlmostEqual(tr.imag, 0.0, places=7)

    def test_chsh_probabilities_ideal(self):
        """
        測試無噪訊貝爾態在 CHSH 最佳角下的理論機率值。
        當 (theta_a, theta_b) = (0, pi/8) 時:
        P(0,0) = P(1,1) = 0.5 * cos²(pi/8) ≈ 0.4267767
        P(0,1) = P(1,0) = 0.5 * sin²(pi/8) ≈ 0.0732233
        """
        sim = BellStateSimulator(noise_prob=0.0)
        probs = sim.measure_probabilities(0.0, math.pi / 8.0)
        expected_p00 = 0.5 * (math.cos(math.pi / 8.0) ** 2)
        expected_p01 = 0.5 * (math.sin(math.pi / 8.0) ** 2)

        self.assertAlmostEqual(probs[0], expected_p00, places=5)
        self.assertAlmostEqual(probs[1], expected_p01, places=5)
        self.assertAlmostEqual(probs[2], expected_p01, places=5)
        self.assertAlmostEqual(probs[3], expected_p00, places=5)
        self.assertAlmostEqual(sum(probs), 1.0, places=7)


class TestProversAndVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = Hash845Verifier(rounds=800)

    def test_quantum_bell_prover_success(self):
        """量子證明者在無噪訊情況下應順利通過驗證 (勝率 ~ 85.36%)。"""
        prover = QuantumBellProver(noise_prob=0.0)
        report = self.verifier.run_interactive_challenge(prover)
        self.assertTrue(report["is_success"])
        self.assertGreaterEqual(report["actual_ratio"], self.verifier.STATISTICAL_LOWER_LIMIT)
        self.assertLessEqual(report["actual_ratio"], self.verifier.STATISTICAL_UPPER_LIMIT)

    def test_classical_lhv_prover_optimal_rejected(self):
        """古典最優 LHV 策略勝率嚴格為 75%，必須被判定為古典盲猜失敗。"""
        prover = ClassicalLHVProver(strategy="optimal")
        report = self.verifier.run_interactive_challenge(prover)
        self.assertFalse(report["is_success"])
        self.assertIn("古典盲猜", report["message"])
        self.assertAlmostEqual(report["actual_ratio"], 0.75, delta=0.05)

    def test_classical_random_prover_rejected(self):
        """古典隨機盲猜勝率約 50%，必須被攔截。"""
        prover = ClassicalLHVProver(strategy="random")
        report = self.verifier.run_interactive_challenge(prover)
        self.assertFalse(report["is_success"])
        self.assertIn("古典盲猜", report["message"])
        self.assertLess(report["actual_ratio"], 0.65)

    def test_colluding_prover_caught(self):
        """古典串通作弊勝率 100%，必須被判定為違反無通訊原則 (超量子上限攔截)。"""
        prover = ColludingClassicalProver()
        report = self.verifier.run_interactive_challenge(prover)
        self.assertFalse(report["is_success"])
        self.assertIn("串通作弊", report["message"])
        self.assertEqual(report["actual_ratio"], 1.0)


class TestSignatureSystem(unittest.TestCase):
    def setUp(self):
        self.prover = QuantumBellProver(noise_prob=0.0)
        self.signer = Hash845Signer(prover=self.prover, rounds=800)
        self.sig_verifier = Hash845SignatureVerifier()

    def test_sign_and_verify_valid(self):
        """正常訊息簽署與驗證應成功。"""
        msg = "轉帳 50000 顆代幣給 Bob - Nonce #1024"
        sig = self.signer.sign(msg)

        is_valid, reason = self.sig_verifier.verify(sig)
        self.assertTrue(is_valid, reason)

    def test_tampered_message_detected(self):
        """若訊息內容遭篡改，驗證必須報錯。"""
        msg = "原始合法合約內容"
        sig = self.signer.sign(msg)

        # 惡意篡改訊息原文
        sig.message = "遭黑客竄改後的合約內容"
        is_valid, reason = self.sig_verifier.verify(sig)
        self.assertFalse(is_valid)
        self.assertIn("訊息已被竄改", reason)

    def test_replay_attack_prevented(self):
        """同一個簽章 Nonce 重複提交應被視為重放攻擊。"""
        msg = "單次有效授權指令"
        sig = self.signer.sign(msg)

        # 第一次驗證通過
        ok1, _ = self.sig_verifier.verify(sig)
        self.assertTrue(ok1)

        # 第二次重放驗證應被拒絕
        ok2, reason = self.sig_verifier.verify(sig)
        self.assertFalse(ok2)
        self.assertIn("重放攻擊警告", reason)

    def test_serialization_json(self):
        """測試簽章封包 JSON 序列化與反序列化一致性。"""
        msg = "JSON 導出測試"
        sig = self.signer.sign(msg)
        json_data = sig.to_json()
        restored = Hash845Signature.from_json(json_data)

        self.assertEqual(sig.message, restored.message)
        self.assertEqual(sig.signature_digest, restored.signature_digest)
        self.assertEqual(sig.actual_ratio, restored.actual_ratio)


if __name__ == "__main__":
    unittest.main()
