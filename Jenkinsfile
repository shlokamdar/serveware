// ServeWare CI/CD — SIT223/SIT753 Task 7.3HD
// Build -> Test -> Code Quality -> Security -> Deploy (staging) -> Release (prod) -> Monitoring

def currentImageTag(String container) {
    def out = bat(returnStdout: true,
                  script: "@docker inspect --format \"{{.Config.Image}}\" ${container} 2>nul || exit /b 0").trim()
    return out.contains(':') ? out.substring(out.lastIndexOf(':') + 1) : ''
}

def deployEnv(String envName, String composeFile, String baseUrl, String container, boolean simulateBad = false) {
    def previous = currentImageTag(container)
    echo "Deploying ${env.IMAGE_TAG} to ${envName} (previous: ${previous ?: 'none'})"

    withEnv(["APP_VERSION=${env.IMAGE_TAG}"]) {
        bat "docker compose -f ${composeFile} up -d --remove-orphans"
    }

    def expected = simulateBad ? '0.0.0-simulated-bad' : env.VERSION
    def rc = bat(returnStatus: true,
                 script: "python scripts\\smoke_test.py --base-url ${baseUrl} --expect-version ${expected} --retries ${simulateBad ? 4 : 24}")
    if (rc != 0) {
        if (previous) {
            echo "Smoke test failed on ${envName}: rolling back to ${previous}"
            withEnv(["APP_VERSION=${previous}"]) {
                bat "docker compose -f ${composeFile} up -d"
            }
            bat "python scripts\\smoke_test.py --base-url ${baseUrl} --retries 12"
        }
        error("${envName} deployment failed smoke tests; rolled back to ${previous ?: 'nothing (first deploy)'}")
    }
    echo "${envName} is healthy on ${env.IMAGE_TAG}"
}

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    parameters {
        booleanParam(name: 'SIMULATE_BAD_DEPLOY', defaultValue: false,
                     description: 'Force the staging smoke test to fail to demonstrate automatic rollback')
    }

    environment {
        APP_DIR           = 'serveware'
        IMAGE             = 'localhost:5000/serveware'
        PYTHONIOENCODING  = 'utf-8'
        DJANGO_SECRET_KEY = "ci-only-not-a-secret-${BUILD_NUMBER}"
    }

    stages {

        stage('1. Build') {
            steps {
                script {
                    env.GIT_SHORT = bat(returnStdout: true, script: '@git rev-parse --short HEAD').trim()
                    env.VERSION   = "1.0.${env.BUILD_NUMBER}"
                    env.IMAGE_TAG = "${env.VERSION}-${env.GIT_SHORT}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.VERSION}"
                    currentBuild.description = "commit ${env.GIT_SHORT}"
                }
                bat 'python -m venv .venv'
                bat '.venv\\Scripts\\python -m pip install --upgrade pip -q'
                bat '.venv\\Scripts\\pip install -r requirements-dev.txt -q'
                dir(env.APP_DIR) {
                    bat '..\\.venv\\Scripts\\python manage.py check'
                    bat '..\\.venv\\Scripts\\python manage.py makemigrations --check --dry-run'
                }
                bat 'docker build --build-arg APP_VERSION=%IMAGE_TAG% --label git.commit=%GIT_SHORT% -t %IMAGE%:%IMAGE_TAG% -t %IMAGE%:latest .'
                bat 'docker push %IMAGE%:%IMAGE_TAG%'
                bat 'docker push %IMAGE%:latest'
                writeFile file: 'build-info.json', text: """{
  "version": "${env.VERSION}",
  "image": "${env.IMAGE}:${env.IMAGE_TAG}",
  "commit": "${env.GIT_SHORT}",
  "build": "${env.BUILD_NUMBER}",
  "branch": "${env.GIT_BRANCH}"
}"""
                archiveArtifacts artifacts: 'build-info.json', fingerprint: true
            }
        }

        stage('2. Test') {
            steps {
                dir(env.APP_DIR) {
                    echo 'Unit tests'
                    bat 'if exist test-reports rmdir /s /q test-reports'
                    bat '..\\.venv\\Scripts\\coverage run manage.py test --exclude-tag integration --verbosity 2'
                    echo 'Integration tests'
                    bat '..\\.venv\\Scripts\\coverage run -a manage.py test --tag integration --verbosity 2'
                    bat '..\\.venv\\Scripts\\coverage xml -o coverage.xml'
                    bat '..\\.venv\\Scripts\\coverage html -d htmlcov'
                    bat '..\\.venv\\Scripts\\coverage report --fail-under=60'
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'serveware/test-reports/*.xml'
                    recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'serveware/coverage.xml']],
                                   sourceDirectories: [[path: 'serveware']])
                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
                                 reportDir: 'serveware/htmlcov', reportFiles: 'index.html',
                                 reportName: 'Coverage Report'])
                }
            }
        }

        stage('3. Code Quality') {
            steps {
                dir(env.APP_DIR) {
                    // Full report (informational) with the custom rule set in ruff.toml
                    bat '..\\.venv\\Scripts\\ruff check . --output-format=concise --exit-zero > ruff-report.txt'
                    bat 'type ruff-report.txt'
                    // Gate: syntax errors, undefined names, leftover print() debugging
                    bat '..\\.venv\\Scripts\\ruff check . --select E9,F63,F7,F82,T20'
                    script {
                        def scannerHome = tool 'SonarScanner'
                        withSonarQubeEnv('SonarQube') {
                            bat "\"${scannerHome}\\bin\\sonar-scanner.bat\" -Dsonar.projectVersion=${env.VERSION}"
                        }
                    }
                }
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
            post {
                always {
                    archiveArtifacts allowEmptyArchive: true, artifacts: 'serveware/ruff-report.txt'
                }
            }
        }

        stage('4. Security') {
            steps {
                echo 'SAST: Bandit'
                dir(env.APP_DIR) {
                    bat '..\\.venv\\Scripts\\bandit -r . -c ..\\bandit.yaml -f json -o ..\\bandit-report.json --exit-zero'
                    bat '..\\.venv\\Scripts\\bandit -r . -c ..\\bandit.yaml -f html -o ..\\bandit-report.html --exit-zero'
                    bat '..\\.venv\\Scripts\\bandit -r . -c ..\\bandit.yaml --severity-level high --confidence-level medium'
                }

                echo 'Dependencies: pip-audit'
                bat '.venv\\Scripts\\pip-audit -r requirements.txt -f json -o pip-audit-report.json || exit /b 0'
                bat '.venv\\Scripts\\pip-audit -r requirements.txt'

                echo 'Container image: Trivy'
                bat 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ -v "%WORKSPACE%":/work aquasec/trivy:latest image --scanners vuln --severity HIGH,CRITICAL --format json -o /work/trivy-report.json %IMAGE%:%IMAGE_TAG%'
                bat 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ -v "%WORKSPACE%":/work aquasec/trivy:latest image --scanners vuln --severity HIGH,CRITICAL %IMAGE%:%IMAGE_TAG%'
                bat 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ -v "%WORKSPACE%":/work aquasec/trivy:latest image --scanners vuln --exit-code 1 --severity CRITICAL --ignore-unfixed --ignorefile /work/.trivyignore %IMAGE%:%IMAGE_TAG%'

                echo 'Secrets: Gitleaks'
                // Full git history -> report only (the old Gmail password WILL show up; it is revoked and documented)
                bat 'docker run --rm -v "%WORKSPACE%":/repo zricethezav/gitleaks:latest detect --source /repo --redact --report-format json --report-path /repo/gitleaks-history-report.json --exit-code 0'
                // Current code -> hard gate
                bat 'docker run --rm -v "%WORKSPACE%\\serveware":/src zricethezav/gitleaks:latest detect --no-git --source /src --redact --exit-code 1'
            }
            post {
                always {
                    archiveArtifacts allowEmptyArchive: true,
                        artifacts: 'bandit-report.*, pip-audit-report.json, trivy-report.json, gitleaks-history-report.json'
                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
                                 reportDir: '.', reportFiles: 'bandit-report.html',
                                 reportName: 'Bandit Security Report'])
                }
            }
        }

        stage('5. Deploy: Staging') {
            steps {
                withCredentials([file(credentialsId: 'serveware-env-staging', variable: 'ENV_FILE')]) {
                    bat 'copy /Y "%ENV_FILE%" deploy\\.env.staging >nul'
                }
                bat 'docker network inspect serveware-net >nul 2>&1 || docker network create serveware-net'
                script {
                    deployEnv('staging', 'deploy\\docker-compose.staging.yml', 'http://localhost:8000',
                              'serveware-staging-web', params.SIMULATE_BAD_DEPLOY)
                }
            }
        }

        stage('6. Release: Production') {
            when {
                expression { return (env.GIT_BRANCH ?: '').endsWith('main') }
            }
            steps {
                withCredentials([file(credentialsId: 'serveware-env-prod', variable: 'ENV_FILE')]) {
                    bat 'copy /Y "%ENV_FILE%" deploy\\.env.prod >nul'
                }
                script {
                    deployEnv('production', 'deploy\\docker-compose.prod.yml', 'http://localhost:8001',
                              'serveware-prod-web')
                }
                bat 'docker tag %IMAGE%:%IMAGE_TAG% %IMAGE%:v%VERSION%'
                bat 'docker tag %IMAGE%:%IMAGE_TAG% %IMAGE%:production'
                bat 'docker push %IMAGE%:v%VERSION%'
                bat 'docker push %IMAGE%:production'
                bat 'git log -15 --pretty=format:"- %%h %%s (%%an, %%ad)" --date=short > release-notes.txt'
                withCredentials([usernamePassword(credentialsId: 'github-pat',
                                                  usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN')]) {
                    bat 'git -c user.name="Jenkins CI" -c user.email="jenkins@serveware.local" tag -a v%VERSION% -m "ServeWare v%VERSION% (build %BUILD_NUMBER%, commit %GIT_SHORT%)"'
                    bat 'git push https://%GH_USER%:%GH_TOKEN%@github.com/shlokamdar/serveware.git v%VERSION%'
                }
                archiveArtifacts artifacts: 'release-notes.txt', fingerprint: true
            }
        }

        stage('7. Monitoring & Alerting') {
            when {
                expression { return (env.GIT_BRANCH ?: '').endsWith('main') }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'smtp-gmail',
                                                  usernameVariable: 'SMTP_USER', passwordVariable: 'SMTP_PASSWORD'),
                                 string(credentialsId: 'grafana-admin-password', variable: 'GRAFANA_ADMIN_PASSWORD')]) {
                    powershell 'New-Item -ItemType Directory -Force monitoring/alertmanager/secrets | Out-Null; Set-Content -NoNewline -Path monitoring/alertmanager/secrets/smtp_password -Value $env:SMTP_PASSWORD'
                    bat 'docker compose -f monitoring\\docker-compose.monitoring.yml up -d'
                }
                bat 'curl -s -X POST http://localhost:9090/-/reload || exit /b 0'
                bat 'curl -s -X POST http://localhost:9093/-/reload || exit /b 0'
                bat 'python scripts\\check_monitoring.py --job serveware-prod --job serveware-staging'
                echo 'Grafana: http://localhost:3000  |  Prometheus: http://localhost:9090/alerts  |  Alertmanager: http://localhost:9093'
            }
        }
    }

    post {
        always {
            withCredentials([usernamePassword(credentialsId: 'smtp-gmail',
                                              usernameVariable: 'SMTP_USER', passwordVariable: 'SMTP_PASSWORD')]) {
                bat "python scripts\\notify.py ${currentBuild.currentResult}"
            }
        }
    }
}
