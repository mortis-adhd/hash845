# hash845: Device-Independent Quantum Zero-Knowledge Signature Suite (DI-QZKP)

Hash845 是一個基於貝爾非定域性（Bell Non-locality / CHSH 協議）的設備無關量子零知識證明與數位簽章系統。
透過多輪非對稱挑戰與雙向物理界限判定，能有效封死古典盲猜、演算法破譯與未授權節點串通作弊。

---

## 🌟 核心特色 (Key Features)

- **純 Python 實作（Zero Dependencies）**：無外部相依庫，僅使用標準庫（`math`, `cmath`, `secrets`, `hashlib`）即可運行。
- **2-Qubit 密度矩陣模擬引擎 (`quantum_engine.py`)**：支援最大糾纏態 $|\Phi^+\rangle$ 製備、Werner 退極化噪訊通道與任意 Bloch 角投影測量。
- **雙向物理界限防禦 (`hash845_core.py`)**：
  - **下界攔截**（$\le 75\%$）：封死古典演算法與隨機盲猜（符合貝爾定理古典極限）。
  - **上界攔截**（$> 88.8\%$）：偵測違反類空分離（No-signaling）的串通作弊行為（高於 Tsirelson 界限 $85.36\%$）。
- **密碼學防重放簽章 (`signature.py`)**：結合 SHA-256 雜湊承諾鏈、時間戳記與 Nonce，支援離線驗證與 JSON 序列化。

---

## 🚀 快速開始 (Quick Start)

### 執行單元與整合測試
```bash
python -m unittest test_hash845.py -v
```

### 執行多方證明者對比測試
```bash
python hash845_core.py
```

### 簽署與驗證訊息範例
```python
from provers import QuantumBellProver
from signature import Hash845Signer, Hash845SignatureVerifier

# 1. 建立量子證明節點與簽章器
prover = QuantumBellProver(noise_prob=0.0)
signer = Hash845Signer(prover=prover, rounds=1000)

# 2. 簽署交易訊息
message = "轉帳 100 顆代幣給 Alice"
signature = signer.sign(message)
print("簽章摘要:", signature.signature_digest)

# 3. 驗證簽章憑證
verifier = Hash845SignatureVerifier()
is_valid, reason = verifier.verify(signature)
print("驗證結果:", is_valid, reason)
```

---

## 📜 授權協議 (License)

本專案採用 [MIT License](LICENSE)。
