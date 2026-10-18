"""
Hash845 (DI-QZKP) 核心驗證系統
支援逐輪 CHSH 關聯性評估、多型態證明者互動挑戰與雙向物理界限判定（防止古典盲猜與古典串通）。
"""

import math
import secrets
from typing import List, Tuple, Dict, Any, Union
from provers import BaseProver, QuantumBellProver, ClassicalLHVProver, ColludingClassicalProver


class Hash845Verifier:
    def __init__(self, rounds: int = 1000):
        """
        初始化 Hash845 驗證器。
        rounds: 連續挑戰的輪數，預設 1000 輪以利用大數法則封死隨機盲猜與古典作弊。
        """
        if rounds <= 0:
            raise ValueError("rounds 必須為正整數")
        self.rounds = rounds

        # 量子力學 Tsirelson 界限: (2 + √2) / 4 ≈ 85.355%
        self.QUANTUM_LIMIT = (2.0 + math.sqrt(2.0)) / 4.0

        # 古典貝爾定理局域隱變數上限 (Bell/CHSH inequality bound): 75%
        self.CLASSICAL_LIMIT = 0.75
        self.CLASSICAL_UPPER_LIMIT = self.CLASSICAL_LIMIT + 0.025

        # 容許統計波動寬度 (3-sigma 容許區間，N=1000 時約 ±3.5%)
        self.STATISTICAL_UPPER_LIMIT = self.QUANTUM_LIMIT + 0.035
        self.STATISTICAL_LOWER_LIMIT = self.QUANTUM_LIMIT - 0.025

    def generate_challenge(self) -> Tuple[int, int]:
        """
        模擬區塊鏈節點利用密碼學安全偽隨機數 (CSPRNG) 生成挑戰角度位元 (x, y) ∈ {0, 1}²。
        """
        return secrets.randbelow(2), secrets.randbelow(2)

    @staticmethod
    def evaluate_round(x: int, y: int, a: int, b: int) -> bool:
        """
        評估單輪 CHSH 關聯性條款:
        a ⊕ b == x · y
        其中 a, b, x, y ∈ {0, 1}
        """
        return (a ^ b) == (x & y)

    def run_interactive_challenge(self, prover: BaseProver) -> Dict[str, Any]:
        """
        對指定的證明者執行完整的 rounds 輪互動式問答挑戰，
        收集每輪挑戰回應軌跡並進行驗證。
        """
        transcript: List[Tuple[int, int, int, int, bool]] = []
        results: List[bool] = []

        for _ in range(self.rounds):
            x, y = self.generate_challenge()
            a, b = prover.respond(x, y)
            is_valid = self.evaluate_round(x, y, a, b)
            transcript.append((x, y, a, b, is_valid))
            results.append(is_valid)

        is_success, msg, ratio = self.verify_proof(results)
        return {
            "is_success": is_success,
            "message": msg,
            "actual_ratio": ratio,
            "rounds": self.rounds,
            "transcript": transcript
        }

    def verify_proof(self, prover_results: List[bool]) -> Tuple[bool, str, float]:
        """
        核心物理零知識證明驗證邏輯。
        回傳: (is_valid: bool, status_message: str, actual_ratio: float)
        """
        if len(prover_results) != self.rounds:
            return False, f"錯誤：測試輪數 ({len(prover_results)}) 與協議規定 ({self.rounds}) 不符！", 0.0

        success_count = sum(1 for res in prover_results if res is True)
        actual_ratio = success_count / self.rounds

        # 雙向物理界限判定
        if actual_ratio > self.STATISTICAL_UPPER_LIMIT:
            # 勝率顯著超越 Tsirelson 界限 (例如接近 100%)，違反非定域性無通訊物理假定，判定為串通作弊
            return False, (
                f"【驗證失敗 - 串通作弊】實際關聯度: {actual_ratio:.2%}。超過量子力學理論極限 "
                f"({self.QUANTUM_LIMIT:.2%})，判定兩端節點秘密串通（違反類空分離無通訊原則）！"
            ), actual_ratio

        elif actual_ratio >= self.STATISTICAL_LOWER_LIMIT:
            # 成功落在量子糾纏非定域性特徵區間
            return True, (
                f"【驗證成功】實際關聯度: {actual_ratio:.2%}。吻合量子糾纏理論值 "
                f"({self.QUANTUM_LIMIT:.2%})，此為無條件安全的設備無關量子簽章！"
            ), actual_ratio

        elif actual_ratio <= self.CLASSICAL_UPPER_LIMIT:
            # 低於或等於古典上限 (含統計波動)
            return False, (
                f"【驗證失敗 - 古典盲猜】實際關聯度: {actual_ratio:.2%}。小於等於古典局域隱變數上限 "
                f"({self.CLASSICAL_LIMIT:.2%})，此為傳統電腦作弊或隨機演算法盲猜！"
            ), actual_ratio

        else:
            # 介於古典上限與量子門檻之間
            return False, (
                f"【驗證失敗 - 噪訊過高】實際關聯度: {actual_ratio:.2%}。數值介於古典上限與量子有效區間之間，"
                f"系統判定糾纏量子態遭受嚴重退極化噪訊干擾。"
            ), actual_ratio


if __name__ == "__main__":
    print("=" * 65)
    print("      Hash845 (DI-QZKP) 核心驗證系統多方對比測試啟動      ")
    print("=" * 65)

    rounds = 1000
    verifier = Hash845Verifier(rounds=rounds)
    print(f"防禦配置：連續 {verifier.rounds} 輪多維不對稱交互挑戰")
    print(f"理論邊界：古典極限 = {verifier.CLASSICAL_LIMIT:.2%} | 量子 Tsirelson 極限 = {verifier.QUANTUM_LIMIT:.2%}\n")

    test_provers = [
        ("無噪訊量子證明者 (QuantumBellProver, p=0.0)", QuantumBellProver(noise_prob=0.0)),
        ("輕度噪訊量子證明者 (QuantumBellProver, p=0.05)", QuantumBellProver(noise_prob=0.05)),
        ("嚴重噪訊量子證明者 (QuantumBellProver, p=0.30)", QuantumBellProver(noise_prob=0.30)),
        ("最佳古典局域隱變數證明者 (ClassicalLHVProver, optimal)", ClassicalLHVProver(strategy="optimal")),
        ("古典純隨機盲猜者 (ClassicalLHVProver, random)", ClassicalLHVProver(strategy="random")),
        ("違規古典串通作弊證明者 (ColludingClassicalProver, 100%)", ColludingClassicalProver()),
    ]

    for name, prover in test_provers:
        print(f"--> 測試目標: {name}")
        report = verifier.run_interactive_challenge(prover)
        print(f"    驗證結果: {'PASS' if report['is_success'] else 'FAIL'}")
        print(f"    詳細訊息: {report['message']}")
        print("-" * 65)
