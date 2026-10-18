"""
純 Python 雙量子位元 (2-Qubit) 量子態與密度矩陣模擬引擎
無外部依賴，純標準庫實作態向量、Werner 退極化噪訊與投影測量。
"""

import math
import cmath
import secrets
from typing import Tuple, List

# 複數矩陣基本運算型別定義
Matrix2x2 = List[List[complex]]
Matrix4x4 = List[List[complex]]
Vector4 = List[complex]


def tensor_product_2x2(m1: Matrix2x2, m2: Matrix2x2) -> Matrix4x4:
    """計算兩個 2x2 矩陣的張量積 (Kronecker product) 得到 4x4 矩陣。"""
    res: Matrix4x4 = [[complex(0, 0) for _ in range(4)] for _ in range(4)]
    for i in range(2):
        for j in range(2):
            for k in range(2):
                for l in range(2):
                    res[i * 2 + k][j * 2 + l] = m1[i][j] * m2[k][l]
    return res


def matrix_vector_mult_4(mat: Matrix4x4, vec: Vector4) -> Vector4:
    """4x4 矩陣乘以 4 維態向量。"""
    res: Vector4 = [complex(0, 0) for _ in range(4)]
    for i in range(4):
        total = complex(0, 0)
        for j in range(4):
            total += mat[i][j] * vec[j]
        res[i] = total
    return res


def matrix_mult_4x4(m1: Matrix4x4, m2: Matrix4x4) -> Matrix4x4:
    """4x4 矩陣相乘。"""
    res: Matrix4x4 = [[complex(0, 0) for _ in range(4)] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            total = complex(0, 0)
            for k in range(4):
                total += m1[i][k] * m2[k][j]
            res[i][j] = total
    return res


def matrix_trace_4x4(mat: Matrix4x4) -> complex:
    """計算 4x4 矩陣的跡 (Trace)。"""
    return mat[0][0] + mat[1][1] + mat[2][2] + mat[3][3]


def rotation_y_projectors(theta: float) -> Tuple[Matrix2x2, Matrix2x2]:
    """
    計算在 Bloch 球面以角度 theta 做投影測量的兩個正交投影運算子:
    |v_0⟩ = cos(theta/2)|0⟩ + sin(theta/2)|1⟩
    |v_1⟩ = -sin(theta/2)|0⟩ + cos(theta/2)|1⟩
    回傳 (Π_0, Π_1)
    """
    c = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)

    # Π_0 = |v_0⟩⟨v_0|
    pi_0: Matrix2x2 = [
        [complex(c * c, 0), complex(c * s, 0)],
        [complex(c * s, 0), complex(s * s, 0)]
    ]

    # Π_1 = |v_1⟩⟨v_1|
    pi_1: Matrix2x2 = [
        [complex(s * s, 0), complex(-s * c, 0)],
        [complex(-s * c, 0), complex(c * c, 0)]
    ]

    return pi_0, pi_1


class BellStateSimulator:
    """
    雙量子位元貝爾態 |Φ⁺⟩ 模擬器，支援 Werner 退極化噪訊通道與任意基底投影測量。
    |Φ⁺⟩ = (|00⟩ + |11⟩) / √2
    """

    def __init__(self, noise_prob: float = 0.0):
        """
        noise_prob: Werner 退極化噪訊參數 p ∈ [0, 1]
        ρ(p) = (1 - p)|Φ⁺⟩⟨Φ⁺| + p (I / 4)
        """
        if not 0.0 <= noise_prob <= 1.0:
            raise ValueError(f"noise_prob 必須介於 0.0 與 1.0 之間，收到: {noise_prob}")
        self.noise_prob = noise_prob
        self._density_matrix = self._build_density_matrix()

    def _build_density_matrix(self) -> Matrix4x4:
        # |Φ⁺⟩ 態向量: [1/√2, 0, 0, 1/√2]
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        phi_plus: Vector4 = [
            complex(inv_sqrt2, 0),
            complex(0, 0),
            complex(0, 0),
            complex(inv_sqrt2, 0)
        ]

        # 純態投影矩陣 ρ_pure = |Φ⁺⟩⟨Φ⁺|
        # 元素 (0,0)=0.5, (0,3)=0.5, (3,0)=0.5, (3,3)=0.5, 其餘為 0
        rho_pure: Matrix4x4 = [[complex(0, 0) for _ in range(4)] for _ in range(4)]
        for i in range(4):
            for j in range(4):
                rho_pure[i][j] = phi_plus[i] * phi_plus[j].conjugate()

        # Werner 態混合: ρ = (1-p)*ρ_pure + p*(I_4/4)
        p = self.noise_prob
        rho: Matrix4x4 = [[complex(0, 0) for _ in range(4)] for _ in range(4)]
        for i in range(4):
            for j in range(4):
                val = (1.0 - p) * rho_pure[i][j]
                if i == j:
                    val += p * complex(0.25, 0)
                rho[i][j] = val

        return rho

    @property
    def density_matrix(self) -> Matrix4x4:
        return self._density_matrix

    def measure_probabilities(self, theta_a: float, theta_b: float) -> List[float]:
        """
        根據 Alice 測量角 theta_a 與 Bob 測量角 theta_b，
        計算四種測量輸出組合 (00, 01, 10, 11) 的聯合機率:
        P(a, b) = Tr(ρ · (Π_a ⊗ Π_b))
        """
        pi_a = rotation_y_projectors(theta_a)
        pi_b = rotation_y_projectors(theta_b)

        probs = []
        for a in (0, 1):
            for b in (0, 1):
                proj_joint = tensor_product_2x2(pi_a[a], pi_b[b])
                prod = matrix_mult_4x4(self._density_matrix, proj_joint)
                prob = matrix_trace_4x4(prod).real
                # 數值誤差修正
                prob = max(0.0, min(1.0, prob))
                probs.append(prob)

        # 正規化機率總和
        total = sum(probs)
        if total > 0:
            probs = [p / total for p in probs]
        return probs

    def sample_measurement(self, theta_a: float, theta_b: float) -> Tuple[int, int]:
        """
        使用密碼學安全隨機抽樣 (secrets)，根據 Born Rule 回傳單次測量結果 (a, b)。
        """
        probs = self.measure_probabilities(theta_a, theta_b)
        # 利用 secrets.randbelow 產生高精度隨機浮點數 [0.0, 1.0)
        rand_val = secrets.randbelow(1_000_000_000) / 1_000_000_000.0

        cumulative = 0.0
        outcomes = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for outcome, prob in zip(outcomes, probs):
            cumulative += prob
            if rand_val <= cumulative:
                return outcome

        return outcomes[-1]
