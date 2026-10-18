"""
Hash845 證明者角色模組 (Provers)
支援量子貝爾證明者、古典局部隱變數證明者 (LHV)、隨機盲猜者與違規串通作弊者。
"""

import math
import secrets
from abc import ABC, abstractmethod
from typing import Tuple
from quantum_engine import BellStateSimulator


class BaseProver(ABC):
    """證明者抽象基底類別。"""

    @abstractmethod
    def respond(self, x: int, y: int) -> Tuple[int, int]:
        """
        接收驗證者發出的二元挑戰 (x, y) ∈ {0, 1}²，回傳測量結果 (a, b) ∈ {0, 1}²。
        """
        pass


class QuantumBellProver(BaseProver):
    """
    真實量子糾纏證明者。
    持有最大糾纏態 |Φ⁺⟩，並使用最佳 CHSH 測量基底：
    - Alice: x=0 -> θ=0, x=1 -> θ=π/4
    - Bob:   y=0 -> φ=π/8, y=1 -> φ=-π/8
    在無噪訊下理論勝率達到 Tsirelson's bound (2 + √2)/4 ≈ 85.36%。
    """

    def __init__(self, noise_prob: float = 0.0):
        self.simulator = BellStateSimulator(noise_prob=noise_prob)
        # 預計算測量角度
        self.alice_angles = {
            0: 0.0,
            1: math.pi / 4.0
        }
        self.bob_angles = {
            0: math.pi / 8.0,
            1: -math.pi / 8.0
        }

    def respond(self, x: int, y: int) -> Tuple[int, int]:
        theta_a = self.alice_angles[x]
        theta_b = self.bob_angles[y]
        return self.simulator.sample_measurement(theta_a, theta_b)


class ClassicalLHVProver(BaseProver):
    """
    局部隱變數 (Local Hidden Variable, LHV) 古典證明者。
    遵循貝爾定理，任何古典定域策略之 CHSH 勝率理論上限嚴格受限於 75% (3/4)。
    """

    def __init__(self, strategy: str = "optimal"):
        """
        strategy:
          - "optimal": 採取確定性最優策略 (例如恆定輸出 (0, 0))，其勝率恆為 75%。
          - "random": 純隨機猜測，勝率期望值為 50%。
        """
        if strategy not in ("optimal", "random"):
            raise ValueError(f"未知的策略: {strategy}，可選 'optimal' 或 'random'")
        self.strategy = strategy

    def respond(self, x: int, y: int) -> Tuple[int, int]:
        if self.strategy == "optimal":
            # 最佳確定性古典策略：恆輸出 (0, 0)
            # 當 (x, y) ∈ {(0,0), (0,1), (1,0)} 時 x·y = 0，a⊕b = 0 (勝，佔 3/4)
            # 僅當 (1,1) 時 x·y = 1，a⊕b = 0 (負，佔 1/4)
            return 0, 0
        else:
            return secrets.randbelow(2), secrets.randbelow(2)


class ColludingClassicalProver(BaseProver):
    """
    違規古典串通作弊證明者 (Signaling / Collusion Prover)。
    模擬未遵守類空分離 (Space-like separation) 的兩端惡意古典節點。
    兩者透過秘密高速通訊共享 (x, y)，直接令 a ⊕ b = x · y（例如令 a = x·y, b = 0），
    達到 100% 勝率。驗證器應能偵測其超過 Tsirelson 界限並判定為作弊。
    """

    def respond(self, x: int, y: int) -> Tuple[int, int]:
        # 直接算出正確同餘解
        correct_parity = x & y
        return correct_parity, 0
