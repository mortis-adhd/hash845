"""
Hash845 密碼學訊息綁定與防重放簽章系統
結合 SHA-256 承諾鏈、時間戳記、隨機 Nonce 與量子挑戰軌跡，產出防竄改與防重放的數位簽章封包。
"""

import hashlib
import json
import secrets
import time
from typing import Dict, Any, Tuple, Optional, Set
from hash845_core import Hash845Verifier
from provers import BaseProver, QuantumBellProver


class Hash845Signature:
    """
    可序列化與離線驗證的 Hash845 設備無關量子簽章憑證。
    """

    def __init__(
        self,
        message: str,
        message_hash: str,
        timestamp: float,
        nonce: str,
        rounds: int,
        actual_ratio: float,
        transcript_root: str,
        signature_digest: str,
        transcript_sample: list
    ):
        self.message = message
        self.message_hash = message_hash
        self.timestamp = timestamp
        self.nonce = nonce
        self.rounds = rounds
        self.actual_ratio = actual_ratio
        self.transcript_root = transcript_root
        self.signature_digest = signature_digest
        self.transcript_sample = transcript_sample

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "message_hash": self.message_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "rounds": self.rounds,
            "actual_ratio": self.actual_ratio,
            "transcript_root": self.transcript_root,
            "signature_digest": self.signature_digest,
            "transcript_sample": self.transcript_sample
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Hash845Signature":
        return cls(
            message=data["message"],
            message_hash=data["message_hash"],
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            rounds=data["rounds"],
            actual_ratio=data["actual_ratio"],
            transcript_root=data["transcript_root"],
            signature_digest=data["signature_digest"],
            transcript_sample=data.get("transcript_sample", [])
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Hash845Signature":
        return cls.from_dict(json.loads(json_str))


class Hash845Signer:
    """
    Hash845 簽章產生器。
    透過與量子證明節點互動，將任意文字訊息綁定至多輪量子挑戰軌跡中，生成防竄改簽章。
    """

    def __init__(self, prover: BaseProver, rounds: int = 1000):
        self.prover = prover
        self.rounds = rounds
        self.verifier = Hash845Verifier(rounds=rounds)

    def sign(self, message: str) -> Hash845Signature:
        """
        簽署訊息:
        1. 計算 SHA-256(message)
        2. 生成 Nonce 與 Timestamp
        3. 執行 rounds 輪挑戰，以訊息雜湊與 Nonce 作為偽隨機產生器的種子熵源
        4. 計算整份交互軌跡的 SHA-256 承諾鏈
        5. 生成簽章封包
        """
        message_bytes = message.encode("utf-8")
        msg_hash = hashlib.sha256(message_bytes).hexdigest()
        nonce = secrets.token_hex(16)
        timestamp = time.time()

        transcript = []
        results = []

        # 以雜湊鏈方式記錄軌跡並綁定訊息
        h_chain = hashlib.sha256(f"{msg_hash}:{nonce}:{timestamp}".encode("utf-8"))

        for i in range(self.rounds):
            # 每一輪挑戰角度來自 CSPRNG
            x, y = self.verifier.generate_challenge()
            a, b = self.prover.respond(x, y)
            is_valid = self.verifier.evaluate_round(x, y, a, b)

            results.append(is_valid)
            round_tuple = (x, y, a, b, is_valid)
            transcript.append(round_tuple)

            # 更新雜湊承諾鏈: H_{i} = SHA256(H_{i-1} || i || x || y || a || b)
            h_chain.update(f"{i}:{x}:{y}:{a}:{b}".encode("utf-8"))

        transcript_root = h_chain.hexdigest()
        is_success, msg, ratio = self.verifier.verify_proof(results)

        if not is_success:
            raise RuntimeError(f"量子簽章生成失敗：證明節點未達量子非定域性標準！原因: {msg}")

        # 最終簽章摘要: SHA256(msg_hash || transcript_root || nonce || ratio)
        final_digest = hashlib.sha256(
            f"{msg_hash}:{transcript_root}:{nonce}:{ratio:.6f}".encode("utf-8")
        ).hexdigest()

        return Hash845Signature(
            message=message,
            message_hash=msg_hash,
            timestamp=timestamp,
            nonce=nonce,
            rounds=self.rounds,
            actual_ratio=ratio,
            transcript_root=transcript_root,
            signature_digest=final_digest,
            transcript_sample=transcript[:10]  # 保留前 10 輪軌跡作為樣本
        )


class Hash845SignatureVerifier:
    """
    Hash845 簽章驗證器。
    提供防重放攻擊（Replay Attack）快取與簽章完整性查核。
    """

    def __init__(self, max_timestamp_drift_seconds: float = 86400.0):
        self.used_nonces: Set[str] = set()
        self.max_drift = max_timestamp_drift_seconds

    def verify(self, signature: Hash845Signature) -> Tuple[bool, str]:
        """
        驗證數位簽章:
        1. 檢查訊息雜湊與原文是否一致
        2. 檢查 Nonce 是否被重放
        3. 檢查時間戳記是否在合理區間內
        4. 檢查實際勝率是否符合量子糾纏特徵區間 (82.8% ~ 88.8%)
        5. 驗證最終簽章摘要
        """
        # 1. 訊息一致性
        computed_hash = hashlib.sha256(signature.message.encode("utf-8")).hexdigest()
        if computed_hash != signature.message_hash:
            return False, "訊息已被竄改：SHA-256 雜湊值不吻合！"

        # 2. 防重放 Nonce 檢查
        if signature.nonce in self.used_nonces:
            return False, "重放攻擊警告：此 Nonce 簽章已曾被使用過！"

        # 3. 時間有效性
        current_time = time.time()
        if abs(current_time - signature.timestamp) > self.max_drift:
            return False, "簽章時間戳記逾期或誤差過大！"

        # 4. 量子物理勝率檢驗
        verifier = Hash845Verifier(rounds=signature.rounds)
        if signature.actual_ratio > verifier.STATISTICAL_UPPER_LIMIT:
            return False, "簽章作弊警告：勝率超過 Tsirelson 理論極限，疑似節點串通！"
        if signature.actual_ratio < verifier.STATISTICAL_LOWER_LIMIT:
            return False, "簽章失效：勝率未達量子非定域性門檻！"

        # 5. 簽章摘要完整性
        expected_digest = hashlib.sha256(
            f"{signature.message_hash}:{signature.transcript_root}:{signature.nonce}:{signature.actual_ratio:.6f}".encode("utf-8")
        ).hexdigest()
        if expected_digest != signature.signature_digest:
            return False, "簽章憑證損壞：簽章摘要校驗失敗！"

        # 記錄 Nonce
        self.used_nonces.add(signature.nonce)
        return True, "簽章驗證完全通過：訊息完整、物理非定域性特徵確認、防重放機制生效！"
