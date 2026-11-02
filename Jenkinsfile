@Library('jenkins-shared-library') _

pipeline {
    agent {
        kubernetes {
            label 'medlab-agent'
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: jnlp
    image: jenkins/inbound-agent:3383.vc8881d4b_0e76-1
    env:
      - name: JENKINS_AGENT_WORKDIR
        value: /home/jenkins/agent
    volumeMounts:
      - name: workspace-volume
        mountPath: /home/jenkins/agent

  - name: python
    image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
    command:
      - "sleep"
      - "infinity"
    tty: true
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: "2"
        memory: 2Gi
    volumeMounts:
      - name: workspace-volume
        mountPath: /home/jenkins/agent

  - name: kaniko
    image: gcr.io/kaniko-project/executor:debug
    command:
      - "/busybox/cat"
    tty: true
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: "2"
        memory: 3Gi
    volumeMounts:
      - name: workspace-volume
        mountPath: /home/jenkins/agent

  volumes:
  - name: workspace-volume
    emptyDir: {}
"""
        }
    }

    options {
        // Stage 'Checkout' bên dưới đã checkout rồi, bỏ checkout mặc định cho đỡ fetch 2 lần
        skipDefaultCheckout(true)
    }

    environment {
        APP_NAME          = 'medlab-insight'                              // ArgoCD Application
        DOCKER_IMAGE_NAME = 'nguyenphong8852/medlab-insight'              // đổi theo Docker Hub của bạn
        IMAGE_TAG         = "${BUILD_NUMBER}"
        MANIFEST_FILE     = 'k8s/base/deployment.yaml'
        GEMINI_MODEL      = 'gemini-3.5-flash'                            // đổi model tại đây
        UV_CACHE_DIR      = '/home/jenkins/agent/.uv-cache'
        UV_HTTP_TIMEOUT   = '600'
        UV_HTTP_RETRIES   = '5'

        // LƯU Ý: không khai báo STATUS_* / ERROR_* ở đây. Biến khai báo trong environment{}
        // được bọc bằng withEnv nên env.X = '...' trong script sẽ KHÔNG ghi đè được.
        // Các biến này do runTracked() tạo ra khi chạy; khi đọc dùng env.STATUS_X ?: 'NOT_RUN'.
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    runTracked('CHECKOUT') {
                        // Mạng tới GitHub đôi khi đứt (TLS early EOF) -> thử lại, nghỉ 10s giữa các lần
                        def attempt = 0
                        retry(3) {
                            if (attempt++ > 0) {
                                sleep(time: 10, unit: 'SECONDS')
                            }
                            checkout scm
                        }
                        echo "Building image (Kaniko): ${DOCKER_IMAGE_NAME}:${IMAGE_TAG}"
                    }
                }
            }
        }

        stage('Quality Gate (ruff + pytest)') {
            when { expression { env.STATUS_CHECKOUT == 'SUCCESS' } }
            steps {
                script {
                    runTracked('QUALITY') {
                        container('python') {
                            sh '''
                                set -eu
                                cd "$WORKSPACE"

                                echo "Installing dependencies with uv..."
                                uv sync --frozen --extra dev

                                # Giữ exit code thật của từng bước, vẫn ghi log để AI đọc khi fail
                                set +e
                                {
                                  echo "===== ruff check ====="
                                  uv run ruff check src app training tests
                                  echo "RUFF=$?" > quality.rc

                                  echo "===== ruff format --check ====="
                                  uv run ruff format --check src app training tests
                                  echo "FMT=$?" >> quality.rc

                                  echo "===== pytest ====="
                                  uv run pytest --cov --cov-report=term-missing
                                  echo "PYTEST=$?" >> quality.rc
                                } 2>&1 | tee quality.log

                                . ./quality.rc
                                if [ "$RUFF" -ne 0 ] || [ "$FMT" -ne 0 ] || [ "$PYTEST" -ne 0 ]; then
                                  echo "Quality gate failed (ruff=$RUFF fmt=$FMT pytest=$PYTEST)"
                                  exit 1
                                fi
                                echo "Quality gate passed."
                            '''
                        }
                    }
                }
            }
        }

        stage('Build & Push Image (Kaniko)') {
            when { expression { env.STATUS_QUALITY == 'SUCCESS' } }
            steps {
                script {
                    runTracked('BUILD') {
                        withCredentials([
                            usernamePassword(
                                credentialsId: 'dockerhub-credentials',
                                usernameVariable: 'DOCKER_USERNAME',
                                passwordVariable: 'DOCKER_PASSWORD'
                            )
                        ]) {
                            container('kaniko') {
                                sh '''
                                    set -e
                                    cd "$WORKSPACE"

                                    echo "Preparing Docker Hub credentials for Kaniko..."
                                    mkdir -p /kaniko/.docker

                                    cat > /kaniko/.docker/config.json <<EOF
{"auths":{"https://index.docker.io/v1/":{"auth":"$(printf "%s:%s" "$DOCKER_USERNAME" "$DOCKER_PASSWORD" | base64 | tr -d '\\n')"}}}
EOF

                                    echo "Building & pushing image with Kaniko..."
                                    # Ghi log ra file (để đưa phần cuối cho AI) mà vẫn in realtime.
                                    # Pipeline qua tee luôn trả về 0 nên phải lưu exit code thật của kaniko.
                                    {
                                      set +e
                                      /kaniko/executor \
                                        --dockerfile=$WORKSPACE/Dockerfile \
                                        --context=$WORKSPACE \
                                        --destination=$DOCKER_IMAGE_NAME:$IMAGE_TAG \
                                        --image-download-retry=3 \
                                        --image-fs-extract-retry=3 \
                                        --push-retry=3 \
                                        --cleanup
                                      echo $? > $WORKSPACE/kaniko.rc
                                    } 2>&1 | tee $WORKSPACE/kaniko.log
                                    RC=$(cat $WORKSPACE/kaniko.rc)
                                    [ "$RC" -eq 0 ] || { echo "Kaniko failed with exit code $RC"; exit "$RC"; }

                                    echo "Kaniko build & push completed."
                                '''
                            }
                        }
                    }
                }
            }
        }

        stage('Update K8s Manifest') {
            // Chỉ cập nhật manifest khi image đã được push thành công
            when { expression { env.STATUS_BUILD == 'SUCCESS' } }
            steps {
                script {
                    runTracked('MANIFEST') {
                        // Thư viện nhận gitRepo dạng host/path, KHÔNG có https://
                        // -> tự lấy từ remote của repo đang build, nên Jenkinsfile dùng chung được cho nhiều repo
                        def gitRepo = sh(script: 'git config --get remote.origin.url', returnStdout: true)
                                        .trim()
                                        .replaceFirst('^https?://', '')

                        updateK8sManifest(
                            env.DOCKER_IMAGE_NAME,
                            env.IMAGE_TAG,
                            env.MANIFEST_FILE,
                            'github-credentials',
                            gitRepo
                        )
                    }
                }
            }
        }

        stage('Collect ArgoCD Status') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'argocd-credentials',
                        usernameVariable: 'ARGO_USER',
                        passwordVariable: 'ARGO_PASS'
                    )
                ]) {
                    sh '''
set +e

echo "===== Collecting ArgoCD status (best effort) =====" > argocd.log

if ! command -v argocd >/dev/null 2>&1; then
  echo "argocd CLI not found, downloading..." >> argocd.log
  mkdir -p /tmp/argocd-bin
  for i in 1 2 3; do
    rm -f /tmp/argocd-bin/argocd
    curl -fsSL --retry 3 --retry-all-errors --retry-delay 3 \
      -o /tmp/argocd-bin/argocd \
      https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64 >> argocd.log 2>&1
    chmod +x /tmp/argocd-bin/argocd
    # Binary tải cụt/hỏng sẽ gây "Bus error" khi chạy -> kiểm tra rồi tải lại
    if /tmp/argocd-bin/argocd version --client >/dev/null 2>&1; then
      break
    fi
    echo "argocd download attempt $i failed or binary is corrupt" >> argocd.log
    sleep 3
  done
  export PATH="/tmp/argocd-bin:$PATH"
else
  echo "argocd CLI already available at $(command -v argocd)" >> argocd.log
fi

echo "Using argocd from: $(command -v argocd)" >> argocd.log

echo "Logging into ArgoCD..." >> argocd.log
argocd login argocd-server.argocd.svc.cluster.local \
  --username "${ARGO_USER}" \
  --password "${ARGO_PASS}" \
  --plaintext >> argocd.log 2>&1

echo "" >> argocd.log
echo "===== argocd app get ${APP_NAME} =====" >> argocd.log
argocd app get ${APP_NAME} >> argocd.log 2>&1

exit 0
'''
                }
            }
        }

        /********** AI STAGES **********/

        stage('Prepare AI Log') {
            steps {
                script {
                    def argocdInfo = fileExists('argocd.log')
                        ? readFile('argocd.log')
                        : 'No ArgoCD log captured.'

                    // Khi test fail, đưa phần cuối log pytest/ruff cho AI thấy nguyên nhân thật
                    def qualityTail = ''
                    if (env.STATUS_QUALITY == 'FAILURE' && fileExists('quality.log')) {
                        qualityTail = sh(script: 'tail -n 40 quality.log', returnStdout: true).trim()
                    }

                    // Khi build image lỗi, đưa 25 dòng cuối của Kaniko
                    def kanikoTail = ''
                    if (env.STATUS_BUILD == 'FAILURE' && fileExists('kaniko.log')) {
                        kanikoTail = sh(script: 'tail -n 25 kaniko.log', returnStdout: true).trim()
                    }

                    def logText = """
[Pipeline] Project: ${APP_NAME}

[Checkout]
Source: ${env.GIT_URL ?: 'SCM'}
Branch: ${env.GIT_BRANCH ?: 'main'}
Status: ${env.STATUS_CHECKOUT ?: 'NOT_RUN'}
${env.ERROR_CHECKOUT ? 'Error: ' + env.ERROR_CHECKOUT : ''}

[Quality Gate (ruff + pytest)]
Command: uv sync --frozen --extra dev && ruff check/format && pytest --cov
Status: ${env.STATUS_QUALITY ?: 'NOT_RUN'}
${env.ERROR_QUALITY ? 'Error: ' + env.ERROR_QUALITY : ''}
${qualityTail ? 'Quality log (last lines):\n' + qualityTail : ''}

[Build & Push Image (Kaniko)]
Image: ${DOCKER_IMAGE_NAME}:${IMAGE_TAG}
Status: ${env.STATUS_BUILD ?: 'NOT_RUN'}
${env.ERROR_BUILD ? 'Error: ' + env.ERROR_BUILD : ''}
${kanikoTail ? 'Kaniko log (last lines):\n' + kanikoTail : ''}

[Update K8s Manifest]
Manifest: ${MANIFEST_FILE}
Git repo: ${env.GIT_URL ?: 'SCM'}
Status: ${env.STATUS_MANIFEST ?: 'NOT_RUN'}
${env.ERROR_MANIFEST ? 'Error: ' + env.ERROR_MANIFEST : ''}

[ArgoCD]
${argocdInfo}

Notes:
- Stage status NOT_RUN means the stage was skipped because an earlier stage failed.
- ArgoCD syncs k8s/base; local OrbStack uses k8s/overlays/local with image medlab-insight:local.
- Smoke endpoint: http://medlab.k8s.orb.local/_stcore/health (Streamlit health).
- HPA is optional and requires metrics-server.

If there was a failure, infer the most likely stage and root cause from this log.
"""

                    writeFile(
                        file: 'jenkins.log',
                        text: logText
                    )
                }
            }
        }

        stage('Create AI Request') {
            steps {
                script {
                    def log = readFile('jenkins.log')

                    def prompt = """
You are an expert DevOps AI specializing in Jenkins, Docker, Python/uv, Kubernetes and ArgoCD.

Analyze the combined Jenkins + ArgoCD log for a Python Streamlit app called MedLab Insight
(ruff + pytest quality gate, Kaniko image build, ArgoCD sync) and infer:
- overall status
- which stage is failing or risky
- root cause
- short summary for humans
- severity
- suggested actions

Return ONLY ONE valid JSON object.

Do NOT use markdown.

Schema:
{
  "status":"",
  "stage":"",
  "root_cause":"",
  "summary":"",
  "confidence":0,
  "suggested_actions":[],
  "affected_component":"",
  "severity":"LOW|MEDIUM|HIGH|CRITICAL"
}

Log:

${log}
"""

                    writeJSON(
                        file: "ai-request.json",
                        pretty: 4,
                        json: [
                            contents        : [[parts: [[text: prompt]]]],
                            generationConfig: [
                                responseMimeType: 'application/json',
                                temperature     : 0.2
                            ]
                        ]
                    )
                }
            }
        }

        stage('Call Gemini') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'gemini-api-key',
                        variable: 'GEMINI_API_KEY'
                    )
                ]) {
                    sh '''
curl -sS "https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary @ai-request.json \
  -o ai-response.json

echo "========== RAW RESPONSE =========="
cat ai-response.json
'''
                }
            }
        }

        stage('Parse AI Response') {
            steps {
                script {
                    def resp
                    try {
                        resp = readJSON file: "ai-response.json"
                    } catch (Exception e) {
                        unstable("AI analysis skipped: cannot parse ai-response.json (${e.message})")
                        return
                    }

                    // API trả lỗi (sai key, hết quota, sai model, ...) -> bỏ qua phân tích AI, không làm vỡ pipeline
                    if (resp.error) {
                        unstable("AI analysis skipped, Gemini API error: ${resp.error.message}")
                        return
                    }

                    // Gộp text của candidate đầu tiên (dùng vòng lặp vì sandbox chặn .find { })
                    def aiText = ''
                    if (resp.candidates) {
                        def first = resp.candidates[0]
                        if (first.content) {
                            for (part in first.content.parts) {
                                if (part.text) {
                                    aiText += part.text
                                }
                            }
                        }
                    }
                    if (!aiText) {
                        unstable("AI analysis skipped: Gemini returned no text (blockReason=${resp.promptFeedback?.blockReason}, finishReason=${resp.candidates ? resp.candidates[0].finishReason : 'n/a'})")
                        return
                    }

                    // Phòng khi model vẫn bọc JSON trong ```json ... ```
                    def cleaned = aiText.trim()
                    if (cleaned.startsWith('```')) {
                        cleaned = cleaned.replaceAll('^```[a-zA-Z]*\\s*', '').replaceAll('\\s*```$', '')
                    }

                    echo "=========== AI JSON RAW ==========="
                    echo cleaned

                    def ai
                    try {
                        ai = readJSON text: cleaned
                    } catch (Exception e) {
                        error("AI output is not valid JSON: ${e.message}\nOutput:\n${cleaned}")
                    }

                    writeJSON(
                        file: "ai-summary.json",
                        pretty: 4,
                        json: ai
                    )

                    currentBuild.description = """
${ai.severity} – ${ai.status}

${ai.summary}

Confidence: ${ai.confidence}
"""

                    // AI chỉ tư vấn: kết quả build do runTracked() quyết định,
                    // tránh việc AI chấm severity cao làm đỏ build đã thành công.

                    // Escape HTML để nội dung AI trả về không làm vỡ trang
                    def esc = { v ->
                        def t = (v == null) ? '' : v.toString()
                        return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    }

                    def actionsHtml = ''
                    for (a in ai.suggested_actions) {
                        actionsHtml += '<li>' + esc(a) + '</li>\n'
                    }

                    def html = """
<html>
<head>
<meta charset="UTF-8">
<title>AI Analysis</title>
<style>
body{
  font-family:Arial;
  margin:30px;
}
table{
  width:100%;
  border-collapse:collapse;
}
td,th{
  border:1px solid #ddd;
  padding:8px;
}
th{
  background:#efefef;
}
</style>
</head>
<body>

<h2>AI Analysis (Jenkins + ArgoCD – ${APP_NAME})</h2>

<table>
<tr><th>Status</th><td>${esc(ai.status)}</td></tr>
<tr><th>Stage</th><td>${esc(ai.stage)}</td></tr>
<tr><th>Severity</th><td>${esc(ai.severity)}</td></tr>
<tr><th>Root Cause</th><td>${esc(ai.root_cause)}</td></tr>
<tr><th>Summary</th><td>${esc(ai.summary)}</td></tr>
<tr><th>Confidence</th><td>${esc(ai.confidence)}</td></tr>
<tr><th>Affected Component</th><td>${esc(ai.affected_component)}</td></tr>
</table>

<h3>Suggested Actions</h3>
<ul>
${actionsHtml}
</ul>

</body>
</html>
"""

                    writeFile(
                        file: "ai-summary.html",
                        text: html
                    )
                }
            }
        }

        stage('Publish HTML') {
            when { expression { fileExists('ai-summary.html') } }
            steps {
                publishHTML(target: [
                    reportDir: '.',
                    reportFiles: 'ai-summary.html',
                    reportName: "AI Analysis - ${APP_NAME}",
                    keepAll: true,
                    alwaysLinkToLastBuild: true
                ])
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'jenkins.log,quality.log,kaniko.log,argocd.log,ai-request.json,ai-response.json,ai-summary.json,ai-summary.html',
                             allowEmptyArchive: true
        }
        success {
            echo "CI/CD done (Kaniko): ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} pushed, manifest updated, ArgoCD status captured, AI analysis generated."
        }
        failure {
            echo "Build failed – see AI Analysis and ArgoCD logs for details."
        }
    }
}

/**
 * Chạy một khối lệnh, ghi lại trạng thái (SUCCESS/FAILURE) và lỗi vào env.
 * catchError đánh dấu stage + build là FAILURE nhưng KHÔNG dừng pipeline,
 * nên các stage thu thập ArgoCD và phân tích AI vẫn chạy sau khi có lỗi.
 */
def runTracked(String key, Closure body) {
    env."STATUS_${key}" = 'RUNNING'
    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
        try {
            body()
            env."STATUS_${key}" = 'SUCCESS'
        } catch (err) {
            env."STATUS_${key}" = 'FAILURE'
            def msg = (err.message ?: err.toString()).toString()
            // Giữ đầu + cuối: git/kaniko in rất nhiều dòng progress ở giữa, nguyên nhân thật nằm ở cuối
            env."ERROR_${key}"  = msg.length() > 700 ? msg.substring(0, 200) + ' ... ' + msg.substring(msg.length() - 500) : msg
            throw err
        }
    }
}
