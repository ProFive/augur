[🇨🇳 中文](README.md) | [🇺🇸 English](README_EN.md) | 🇻🇳 Tiếng Việt

<div align="center">

<img src="docs/images/en/hero-banner.png" alt="Augur — Hội đồng đầu tư AI của bạn" width="100%">

# 🦉 Augur

**18 nhà đầu tư huyền thoại. Cùng một cổ phiếu. Một kết luận.**

Đặt Warren Buffett, Ray Dalio, Đoàn Vĩnh Bình và Cathie Wood vào cùng một phòng — họ sẽ không đồng ý với nhau. Và đó chính là điều cốt lõi.

[![v10.15.0](https://img.shields.io/badge/v10.15.0-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur/releases)
[![2461 Tests](https://img.shields.io/badge/2461_Tests-Passing-brightgreen?style=for-the-badge)](https://github.com/BruceLanLan/augur/actions)
[![SEC EDGAR](https://img.shields.io/badge/SEC_EDGAR-Real_Filing_Data-4a90d9?style=for-the-badge)](#-18-bậc-thầy-đầu-tư)
[![18 Masters](https://img.shields.io/badge/18-Investment_Masters-gold?style=for-the-badge)](#-18-bậc-thầy-đầu-tư)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude_%2F_Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![PWA](https://img.shields.io/badge/PWA-Installable_App-blue?style=for-the-badge)](#-bảng-điều-khiển)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 🚀 Khởi động trong 30 giây

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e ".[data]"
augur serve --open          # Mở Bảng điều khiển
```

Hoặc chạy thẳng từ terminal:

```bash
augur analyze AAPL          # 18 bậc thầy phân tích song song
augur consensus NVDA        # Đồng thuận có trọng số + tỷ trọng Kelly
augur workflow TSLA         # Toàn bộ quy trình phân tích trong một lệnh
```

---

## ✨ Có gì mới trong v10.0

<img src="docs/images/screenshots/dashboard-hd2d.png" alt="Augur v10 Trang chủ — Dữ liệu thị trường trực tiếp + terminal kiểu Bloomberg" width="100%">

### Terminal Bloomberg của riêng bạn

**Trang `/settings` giờ là một hệ thống cấu hình terminal đầy đủ:**

<img src="docs/images/screenshots/workspace-profiles.png" alt="Không gian làm việc Terminal — Lưu và chuyển đổi giữa nhiều hồ sơ" width="100%">

- **4 bố cục mẫu**: analyst / trader / committee / minimal — đổi trang mặc định và thanh điều hướng chỉ với một cú nhấp
- **Hồ sơ đặt tên**: lưu "giao dịch trong ngày" và "nghiên cứu cuối tuần" thành hai cấu hình riêng, chuyển đổi bất cứ lúc nào
- **Bộ lọc tập con bậc thầy**: chỉ giữ những bậc thầy bạn tin tưởng trong phần đồng thuận — trọng số tự động chuẩn hóa lại
- Cấu hình nằm ở `~/.augur/workspace.yaml`, xuất/nhập để mang sang máy khác

### AI Agent vận hành terminal của bạn

Không chỉ là "trò chuyện" — Claude / Hermes Agent giờ có thể **đọc và chỉnh sửa** không gian làm việc Augur của bạn trực tiếp:

```python
# Gọi từ Claude Desktop / Hermes / Claude Code:
mcp_augur_workspace_get()                       # xem bố cục hiện tại
mcp_augur_workspace_set(layout_preset="trader") # chuyển sang chế độ trader
mcp_augur_workspace_profiles()                  # quản lý toàn bộ hồ sơ
```

### Toàn bộ quy trình phân tích trong một lệnh

```bash
augur workflow NVDA --steps fetch,analyze,consensus,committee
```

`fetch → analyze → consensus → committee → debate → sentiment` — sáu bước nối tiếp, lỗi ở một bước không làm gãy cả chuỗi, và các bước mặc định tuân theo Hồ sơ đang hoạt động của bạn.

---

## 📊 Bảng Điều Khiển

<img src="docs/images/screenshots/personas-hd2d.png" alt="18 Bậc thầy đầu tư — Bốn trường phái tư duy" width="100%">

### Phân tích cổ phiếu

<img src="docs/images/screenshots/report-hd2d.png" alt="Phân tích cổ phiếu — Nhập bất kỳ mã nào để triệu tập 18 bậc thầy" width="100%">

Nhập bất kỳ mã nào (Mỹ / Hồng Kông / A-share). 18 bậc thầy sẽ trả lời với:
- **Điểm Augur** (0–10) + **MUA / TRUNG LẬP / BÁN**
- **Tỷ trọng vị thế Kelly** (dựa trên độ tin cậy của đồng thuận)
- **Lời phán của Augur**: kết luận một dòng
- Phân bổ quan điểm: `13 Tăng giá / 5 Trung lập / 0 Giảm giá`

### Hội đồng đầu tư

<img src="docs/images/screenshots/committee-hd2d.png" alt="Hội đồng đầu tư — Đội hình mẫu + ý kiến độc lập + kết luận cuối cùng" width="100%">

Năm hội đồng mẫu có sẵn, hoặc tự xây dựng đội hình riêng:
- **Giá trị kinh điển**: Buffett · Graham · Munger · Fisher
- **Giá trị Trung Quốc**: Đoàn Vĩnh Bình · Trương Lỗi · Lý Lục · Đan Bân
- **Vĩ mô toàn thời tiết**: Dalio · Soros · Marks · ARPS
- **Tăng trưởng đột phá**: Cathie Wood · Thiel · Aschenbrenner · Lynch
- **Toàn hội đồng**: Cả 18 bậc thầy

### Tranh luận Tăng / Giảm

<img src="docs/images/screenshots/04-bullish-critical.png" alt="Tranh luận có cấu trúc — luận điểm tăng và giảm được tạo tự động" width="100%">

Chọn 2–4 bậc thầy để tranh luận về cùng một mã qua nhiều vòng. Toàn bộ luận điểm tăng giá và giảm giá được tạo tự động.

### Lịch sử

<img src="docs/images/screenshots/history.png" alt="Lịch sử phân tích — bản đồ nhiệt kiểu GitHub + hồ sơ chi tiết" width="100%">

Mọi phân tích đều được lưu trữ tự động. Bản đồ nhiệt 52 tuần kiểu GitHub. Lọc theo tín hiệu, điểm số hoặc ngày.

### So sánh

<img src="docs/images/screenshots/compare-radar.png" alt="So sánh — radar 5 chiều + phân rã yếu tố" width="100%">

Đặt 2–5 bậc thầy cạnh nhau trên cùng một mã. Biểu đồ radar 5 trục (định giá / tăng trưởng / chất lượng / động lượng / an toàn) cho thấy ngay họ bất đồng ở đâu, và bảng phân rã mở rộng chỉ ra các yếu tố cụ thể (P/E, lợi thế cạnh tranh, động lượng, v.v.) mà mỗi bậc thầy đã dùng để đi tới điểm số của mình.

### Thiết lập Hermes Agent

<img src="docs/images/screenshots/hermes-setup.png" alt="Hướng dẫn thiết lập Hermes Agent — cấu hình MCP một cú nhấp" width="100%">

Hướng dẫn từng bước: cài đặt máy chủ MCP, đăng ký với Claude Desktop / Hermes, và kết nối cả 18 bậc thầy cùng hội đồng vào quy trình AI agent của bạn.

---

## 🎭 18 Bậc Thầy Đầu Tư

> Bốn trường phái. Giá trị / Tăng trưởng / Vĩ mô / Trung Quốc. Các bậc thầy Trung Quốc trả lời **bằng tiếng Trung**.

| Trường phái | Bậc thầy |
|-------------|----------|
| 🏦 Giá trị kinh điển | Warren Buffett · Benjamin Graham · Charlie Munger · Philip Fisher |
| 🚀 Tăng trưởng & Đổi mới | Peter Lynch · Cathie Wood · Peter Thiel · Leopold Aschenbrenner |
| 🌍 Vĩ mô & Chu kỳ | Ray Dalio · George Soros · Howard Marks · ARPS Crypto/Gold |
| 🇨🇳 Giá trị Trung Quốc | Đoàn Vĩnh Bình · Trương Lỗi (Hillhouse) · Lý Lục (Himalaya) · Đan Bân · Dayu BTCdayu |
| ⚙️ Đặc biệt | Serenity (chuỗi cung ứng điện toán AI) |

Mỗi bậc thầy có một [Hermes Skill](src/skills/) riêng để trò chuyện trực tiếp theo phong cách nhân vật đó.

---

## 🔌 Triển khai ở mọi nơi

| Nền tảng | Cách dùng |
|----------|-----------|
| **Bảng điều khiển Web** | `augur serve` |
| **Claude Desktop** | Cấu hình MCP → `augur mcp-server` |
| **Hermes Agent** | `/skill augur-buffett` |
| **Claude Code** | Tự động nhận diện `.mcp.json` (clone là chạy) |
| **OpenClaw** | Tự động đăng ký qua manifest YAML |
| **Telegram / Slack** | `augur telegram` / `augur slack` |

### 13 công cụ MCP

```json
// Claude Desktop
{
  "mcpServers": {
    "augur": { "command": "augur", "args": ["mcp-server"] }
  }
}
```

| Công cụ | Mục đích |
|---------|----------|
| `mcp_augur_analyze` | Phân tích toàn bộ bậc thầy hoặc một bậc thầy |
| `mcp_augur_consensus` | Đồng thuận có trọng số + vị thế Kelly |
| `mcp_augur_committee` | Hội đồng (ý kiến độc lập + kết luận) |
| `mcp_augur_debate` | Tranh luận có cấu trúc nhiều vòng |
| `mcp_augur_workflow` | Quy trình phân tích đầy đủ |
| `mcp_augur_workspace_get` | 🆕 Đọc cấu hình terminal của bạn |
| `mcp_augur_workspace_set` | 🆕 Chỉnh sửa cấu hình terminal |
| `mcp_augur_workspace_profiles` | 🆕 Quản lý hồ sơ |
| `mcp_augur_fetch` | Dữ liệu thị trường trực tiếp |
| `mcp_augur_sentiment` | Phân tích tâm lý mạng xã hội |
| `mcp_augur_create_persona` | Tạo một bậc thầy tùy chỉnh |
| `mcp_augur_list_personas` | Liệt kê toàn bộ bậc thầy |
| `mcp_augur_configure` | Đặt tham số mô hình cho từng bậc thầy |

---

## 💻 Tham chiếu CLI

```bash
# Phân tích
augur analyze AAPL                              # đồng thuận 18 bậc thầy
augur analyze AAPL --persona buffett            # một bậc thầy
augur consensus NVDA                            # đồng thuận có trọng số + Kelly
augur report AAPL -o report.md                  # báo cáo chuyên sâu
augur committee AAPL -q "Lợi thế cạnh tranh đang mở rộng hay thu hẹp?"  # hội đồng đầu tư
augur chat AAPL --persona buffett               # trò chuyện nhanh
augur workflow TSLA --steps fetch,analyze,consensus,committee

# Dữ liệu
augur fetch AAPL                                # báo giá trực tiếp + cơ bản
augur sentiment AAPL                            # tâm lý mạng xã hội
augur guidance AAPL                             # triển vọng ban lãnh đạo do AI trích xuất (tùy chọn, xem bên dưới)

# Bảng điều khiển
augur serve --port 8000 --open

# Giám sát
augur watch AAPL NVDA TSLA                     # làm mới mỗi 60 giây
augur watch NVDA --alert-above 7.5             # cảnh báo ngưỡng điểm

# Danh mục & kiểm định
augur portfolio AAPL NVDA TSLA                 # phân bổ Kelly
augur backtest AAPL --days 30                  # kiểm định lịch sử thật
augur ic-report                                # bảng xếp hạng IC của agent

# Danh mục theo dõi + lập lịch
augur watchlist-add AAPL --pe 30 --roe 0.55
augur watchlist-show
augur cron-run                                  # chạy phân tích danh mục theo dõi một lần
augur cron-start                                # khởi động tiến trình lập lịch

# Agent
augur mcp-server                               # máy chủ MCP qua stdio
augur skills / augur skills --school value
augur inject-soul -p my_profile --persona buffett  # đưa nhân cách một bậc thầy vào cấu hình agent

# Bot
augur telegram / augur slack / augur wechat / augur lark

# Cập nhật
augur update                                    # git pull + cài lại (chỉ dành cho bản cài bằng git clone)

# Khắc phục sự cố
augur doctor                                    # Kiểm tra môi trường: SSL/TLS, khóa API, kết nối nguồn dữ liệu, tiến độ dữ liệu học
augur doctor --offline                          # Tương tự, nhưng bỏ qua các lệnh gọi mạng thật
```

---

## 🎨 Nhân vật tùy chỉnh

```bash
# Cách 1: Trình tạo không cần code trên Bảng điều khiển
augur serve  →  http://localhost:8000/create-persona

# Cách 2: YAML
cat > personas/custom/my_quant.yaml << EOF
agent_id: my_quant
name: "My Quant Strategy"
philosophy: ["momentum", "value", "low_vol"]
scoring_weights:
  momentum: 0.40
  value: 0.35
  safety: 0.25
EOF
augur analyze AAPL --persona my_quant

# Cách 3: MCP
mcp_augur_create_persona(yaml_content="agent_id: ...")
```

---

## 📝 Nhật ký thay đổi

> Ghi chú phát hành cho người dùng phổ thông: [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md)

<details open>
<summary><strong>v10.15.0 — Bản đồng bộ công khai (hiện tại)</strong></summary>

Ba tuần rưỡi phát triển kể từ bản phát hành công khai trước (v10.0.0, 29/06/2026):

- 🆕 **Dữ liệu cơ bản thật từ SEC EDGAR**: P/E, ROE, biên lợi nhuận, v.v. giờ lấy từ dữ liệu 10-K/10-Q chính thức, chiều sâu lịch sử tới khoảng năm 2011; thêm tín hiệu giao dịch nội bộ, tín hiệu sở hữu tổ chức, và `augur guidance` (triển vọng ban lãnh đạo do LLM trích xuất, tùy chọn bật)
- ✅ **Ba sửa lỗi về độ tin cậy**: loại bỏ sự pha loãng của MetaModel, kiểm định mặc định dùng dữ liệu lịch sử thật, cỗ máy học giờ thực sự tích lũy dữ liệu; đồng thời trung thực gỡ bỏ hai cơ chế chưa được kiểm chứng (trọng số tâm lý X, hệ số chế độ thị trường chọn thủ công)
- 🆕 **`augur doctor` + lịch sử kết nối + kiểm tra mạng thật hằng tuần**: chẩn đoán môi trường cục bộ trong một lệnh, xu hướng kết nối 7 ngày tự động phát hiện nguồn dữ liệu đã chết
- 🆕 **Hai script nghiên cứu mới**: phân rã đóng góp ở cấp yếu tố (`factor_attribution.py`) và trình tạo `rolling_ic.json`; các lần chạy dữ liệu thật đầu tiên đã bộc lộ một hạn chế cần nói thẳng — quy trình phát lại kiểm định lịch sử còn thiếu dữ liệu lịch sử thật về tỷ lệ sở hữu nội bộ/tổ chức, xem `docs/FACTOR_ATTRIBUTION_FINDINGS_2026-07.md`
- 🔧 **Sức khỏe kỹ thuật**: hoàn tất tách `cli.py`/`dashboard/`, sửa một lỗi đóng gói thật (bản wheel trước đây thiếu toàn bộ thư mục dashboard) và một lỗi đường dẫn ảnh đại diện thật (mọi avatar đều 404 trên toàn site, chỉ phát hiện được khi thực sự mở ứng dụng trên trình duyệt)
- ✅ 2461 bài kiểm thử đạt (2136 tại thời điểm phát hành v10.0.0)

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.14.0 — Trình tạo rolling_ic.json</strong></summary>

- 🆕 **`scripts/generate_rolling_ic.py`**: cỗ máy đồng thuận từ lâu đã có cơ chế "tái phân bổ trọng số động theo IC trượt", nhưng chưa từng có gì tạo ra `feedback/rolling_ic.json`, nên nó âm thầm không hoạt động — đúng khoảng trống mà R5 đã sửa cho `agent_correlation.json`. Script này tính IC cắt ngang thật của từng bậc thầy từ dữ liệu lịch sử và ghi ra dưới dạng trọng số
- ✅ 2460 bài kiểm thử đạt

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.13.0 — Phân tích đóng góp cấp yếu tố (script nghiên cứu)</strong></summary>

- 🆕 **`scripts/factor_attribution.py`**: script nghiên cứu mới tính rank-IC cắt ngang cho từng yếu tố trong khoảng 70–90 yếu tố được đặt tên trên metadata của 18 bậc thầy (yếu tố nào thực sự dự báo được lợi nhuận tương lai), kèm kiểm tra độ ổn định chia đôi mẫu để phòng dương tính giả do so sánh bội (chính cái bẫy mà vụ trọng số chế độ thị trường đã mắc phải trước đây) — chỉ những yếu tố cùng dấu và vượt ngưỡng độ mạnh tối thiểu ở cả hai nửa cửa sổ mới được tính là ứng viên ổn định; phần còn lại vẫn được in ra nhưng gắn nhãn rõ là không đáng tin
- ✅ 2449 bài kiểm thử đạt

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.12.0 — Kiểm tra nhanh nguồn dữ liệu qua mạng thật hằng tuần</strong></summary>

- 🆕 **Kiểm tra nhanh tự động hằng tuần**: tác vụ GitHub Actions theo lịch mới (mỗi thứ Hai) thực hiện kiểm tra kết nối mạng thật tới SEC EDGAR và yfinance — EDGAR lỗi sẽ làm hỏng tác vụ (SEC hiếm khi chặn IP của CI, nên lỗi là tín hiệu thật), còn yfinance lỗi chỉ cảnh báo mà không làm hỏng tác vụ (việc Yahoo giới hạn tốc độ/chặn dải IP đám mây quá phổ biến để coi là hồi quy thật)
- ✅ 2439 bài kiểm thử đạt

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.11.0 — Lịch sử kết nối nguồn dữ liệu</strong></summary>

- 🆕 **`augur doctor` giờ theo dõi lịch sử kết nối 7 ngày**: mỗi lần chạy `augur doctor` sẽ ghi lại kết quả thăm dò đó ở máy cục bộ (`~/.augur/provider_stats.json`), dần dựng nên một xu hướng ngắn hạn — một điểm cuối đã chết như của stooq giờ sẽ hiện lên thành "0/7 kết nối được" trong `augur doctor` thay vì phải chờ ai đó tình cờ nhận ra
- ✅ 2427 bài kiểm thử đạt

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.10.0 — Kiểm tra môi trường augur doctor</strong></summary>

- 🆕 **`augur doctor`**: chẩn đoán môi trường cục bộ trong một lệnh — kiểm tra bộ công cụ Python/SSL xem có tổ hợp lỗi đã biết làm hỏng yfinance hay không (ví dụ LibreSSL), cấu hình khóa API tùy chọn, kết nối trực tiếp tới nguồn dữ liệu, và tiến độ tích lũy dữ liệu của cỗ máy học; `--offline` bỏ qua các lệnh gọi mạng thật
- ✅ 2408 bài kiểm thử đạt

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.9.0 — Dữ liệu cơ bản SEC EDGAR + ba sửa lỗi độ tin cậy</strong></summary>

- ✅ **Đồng thuận không còn bị pha loãng một nửa**: cơ chế trộn trung vị MetaModel chưa từng được kiểm chứng nay mặc định có trọng số bằng không
- ✅ **Kiểm định mặc định dùng dữ liệu lịch sử thật**: Bảng điều khiển/CLI không còn hiển thị dữ liệu tổng hợp theo mặc định (`--demo` là tùy chọn bật, có gắn nhãn rõ ràng)
- ✅ **Vòng lặp học thực sự tích lũy dữ liệu**: dự đoán được lưu ngay lập tức + một tác vụ theo lịch tự động xử lý các dự đoán đến hạn
- 🆕 **Hồ sơ SEC EDGAR thật**: P/E, ROE, biên lợi nhuận, v.v. giờ lấy từ dữ liệu 10-K/10-Q chính thức, chiều sâu lịch sử tới khoảng năm 2011 (mã Mỹ/ADR)
- 🆕 **Tín hiệu mua vào của nội bộ**: theo dõi giao dịch thị trường mở thật trong 90 ngày gần nhất của ban lãnh đạo/hội đồng quản trị
- 🆕 **Tín hiệu dòng tiền tổ chức**: theo dõi thay đổi vị thế hằng quý tại Berkshire Hathaway, Renaissance Technologies, Bridgewater và nhiều quỹ khác
- 🆕 **`augur guidance`** (tùy chọn bật): tâm lý triển vọng ban lãnh đạo + định hướng tương lai do LLM trích xuất từ hồ sơ mới nhất
- 🔧 **Sửa phân tích tâm lý**: gỡ bỏ trọng số 20% từ X (Twitter) vốn luôn là dữ liệu giả khỏi công thức tính
- 🔧 **Trung thực gỡ bỏ trọng số chế độ thị trường**: kiểm chứng bằng dữ liệu thật không thấy lợi ích rõ ràng, nên các quy tắc chọn thủ công chưa được kiểm chứng đã bị vô hiệu hóa
- ✅ 2388 bài kiểm thử đạt

Chi tiết đầy đủ tại [docs/en/RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md).
</details>

<details>
<summary><strong>v10.0.0 — Terminal Workspace + Agentic Workflow + 13 công cụ MCP + WebSocket Streaming</strong></summary>

**Điểm nhấn nâng cấp v8 → v10:**

- 🆕 **Terminal Workspace**: hệ thống bố cục đa hồ sơ kiểu Bloomberg với bộ lọc mẫu và điều khiển tập con bậc thầy
- 🆕 **3 công cụ MCP cho workspace**: agent có thể đọc/ghi cấu hình terminal của bạn (`workspace_get/set/profiles`)
- 🆕 **`augur_workflow`**: quy trình 6 bước, cô lập lỗi từng bước, các bước tuân theo Hồ sơ đang hoạt động
- 🆕 **WebSocket streaming**: `/ws/workspace` phát trạng thái + `/ws/workflow` tiến độ theo từng bước
- 🆕 **Meta-skill augur-terminal**: đầu vào hợp nhất cho Hermes — 13 công cụ, 15 trang, 4 bố cục mẫu
- 🆕 **Hermes committee.yaml**: vai trò agent Chủ tịch hội đồng
- ✅ Cỗ máy đồng thuận: trọng số ngành · định tuyến theo chế độ thị trường · MetaModel · dữ liệu cơ bản đúng thời điểm
- ✅ Bảng điều khiển: i18n 4 ngôn ngữ · bản đồ nhiệt lịch sử · PWA · phím tắt · xuất CSV
- ✅ 2136 bài kiểm thử đạt
</details>

<details>
<summary><strong>v9.0.x — Hermes Agent + Hệ thống hội đồng</strong></summary>

- 19 Hermes Skill; các bậc thầy Trung Quốc trả lời bằng tiếng Trung
- 9 công cụ MCP (committee / sentiment / create_persona / debate)
- Hội đồng mẫu + trang hướng dẫn thiết lập Hermes
- Cài đặt PWA + Ticker Tape qua WebSocket + thẻ dữ liệu trong Chat
</details>

<details>
<summary><strong>v8.2.x — Hệ thống thiết kế HD-2D + Tối ưu hóa + AI Chat</strong></summary>

- Đường biên hiệu quả Markowitz · đẩy Rules→Bot · trò chuyện LLM thật
- Hệ thống thiết kế HD-2D: ExecCard / OracleSays / ScorecardGrid
- Tuân thủ WCAG AA · an toàn luồng · gia cố scanner
</details>

---

<div align="center">

Giấy phép MIT · Được xây dựng với ❤️ bởi <a href="https://github.com/BruceLanLan">BruceLanLan</a>

*Chỉ dành cho mục đích giáo dục — không phải lời khuyên đầu tư*

</div>
