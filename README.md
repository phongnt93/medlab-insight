# MedLab Insight

> MLOps demo: nhập kết quả xét nghiệm máu/nước tiểu → rule engine + mô hình nguy cơ + Gemini diễn giải.
> **Không dùng cho chẩn đoán hoặc cấp cứu.**

## Thành phần

- **Streamlit UI** (`app/streamlit_app.py`): form nhập liệu, cảnh báo critical, báo cáo.
- **Core** (`src/medlab/`): Pydantic schema, reference ranges, rule engine, CKD-EPI 2021 eGFR, risk model, Gemini client, guardrails.
- **Training** (`training/`): sinh dữ liệu tổng hợp, huấn luyện sklearn, log MLflow, model card.
- **K8s** (`k8s/`): Deployment/Service/Secret/HPA/NetworkPolicy cho OrbStack.

## Chạy local

```bash
uv venv --python 3.12
uv sync --extra dev --extra train
cp .env.example .env            # thêm GEMINI_API_KEY nếu có
uv run python -m training.train --no-mlflow   # tạo artifacts/risk_model.joblib
uv run streamlit run app/streamlit_app.py
```

Mở http://localhost:8601. Không có `GEMINI_API_KEY` thì app tự dùng fallback rule-based.

> Port 8501 đang được một app khác trên OrbStack dùng, nên project mặc định chạy ở **8601**.

### Gemini

```bash
export GEMINI_API_KEY="..."
export GEMINI_MODEL="gemini-3.5-flash"   # tùy chọn; có thể đổi sang gemini-3.6-flash / gemini-3.7-flash
```

Chỉ dữ liệu xét nghiệm đã ẩn danh (tuổi, giới, chỉ số, ghi chú đã redact) được gửi đi. Client gọi REST `generateContent` với header `x-goog-api-key` (key không nằm trong URL/log), bật JSON mode và tự fallback rule-based nếu API lỗi, timeout hoặc trả JSON không hợp lệ.

## Test

```bash
uv run pytest --cov
```

## Docker

```bash
docker build -t medlab-insight:local .
docker run --rm -p 8601:8501 --env-file .env medlab-insight:local
```

## Kubernetes (OrbStack)

```bash
kubectl apply -k k8s/overlays/local      # base + image local cho OrbStack
kubectl -n medlab rollout status deploy/medlab-insight

# Tùy chọn: bật Gemini thật
kubectl -n medlab create secret generic medlab-secrets \
  --from-literal=GEMINI_API_KEY="$GEMINI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n medlab rollout restart deploy/medlab-insight
```

Mở http://medlab.k8s.orb.local (OrbStack tự resolve `*.k8s.orb.local`).
Nếu DNS không có, dùng `kubectl -n medlab port-forward svc/medlab-insight 8601:80`.

> Cùng image `medlab-insight:local` được OrbStack chia sẻ cho cluster, không cần push registry.

HPA (1–3 replica theo CPU) là tùy chọn, cần metrics-server:

```bash
kubectl apply -f k8s/base/hpa.yaml
```

## CI/CD (Jenkins + ArgoCD)

`Jenkinsfile` theo pattern của repo `gold-profit-app`:

```
Checkout → Quality Gate (ruff + pytest) → Build & Push (Kaniko)
→ Update K8s Manifest (shared library) → ArgoCD status
→ Gemini phân tích log → HTML report
```

Chuẩn bị trên Jenkins:

- Kubernetes agent (pod template khai báo sẵn trong Jenkinsfile, không cần cài Python trên agent).
- Credentials: `dockerhub-credentials`, `github-credentials`, `argocd-credentials`, `gemini-api-key`.
- Shared library `jenkins-shared-library` có hàm `updateK8sManifest`.
- ArgoCD Application `medlab-insight` trỏ về path `k8s/base`, bật Auto-Sync + Self-Heal:

```bash
kubectl apply -f k8s/argocd/application.yaml
```

- Repo đã push lên GitHub (pipeline commit tag mới vào `k8s/base/deployment.yaml`).

AI analysis chỉ mang tính tư vấn (mô tả + HTML report); kết quả build do các stage
thực tế quyết định, không bị AI chấm severity cao làm đỏ build.

Image đích mặc định `nguyenphong8852/medlab-insight:<BUILD_NUMBER>`. Nếu Docker Hub
account khác, sửa `DOCKER_IMAGE_NAME` trong `Jenkinsfile` và `image:` trong
`k8s/base/deployment.yaml`. Tag `bootstrap` ban đầu sẽ được thay bằng tag build đầu tiên.

Local OrbStack vẫn dùng overlay riêng:

```bash
kubectl apply -k k8s/overlays/local
```

Lưu ý: khi ArgoCD Application đang bật Auto-Sync + Self-Heal, nó sẽ kéo image về
tag CI (`k8s/base/deployment.yaml`). Muốn test overlay `:local` lâu dài thì tắt
auto-sync (`argocd app set medlab-insight --sync-policy none`) trước khi apply.

## Cấu trúc

```
app/            Streamlit UI
src/medlab/     core package
training/       synthetic data + train + MLflow
tests/          unit/integration/UI smoke tests
k8s/base        manifests gốc (ArgoCD sync)
k8s/overlays    override cho local
k8s/argocd      ArgoCD Application manifest
Jenkinsfile     pipeline Jenkins + ArgoCD + Gemini
artifacts/      model.joblib + model_card.json
```

## Giới hạn

- Dữ liệu huấn luyện là **synthetic**, chưa kiểm định lâm sàng.
- Ngưỡng tham chiếu người lớn; trẻ em cần bác sĩ nhi.
- Không thay thế bác sĩ. Xem chi tiết trong tài liệu kỹ thuật.
