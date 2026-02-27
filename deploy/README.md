# GitOps Manifests

Kustomize manifests under this directory describe how to run the email assistant as a Kubernetes CronJob. They are designed to be managed by a GitOps operator (Flux, Argo CD, etc.), so updating the manifests in git is the source of truth for deployments.

## Structure
```
deploy/
  base/          # Namespace, service account, config map, CronJob
  overlays/
    prod/        # Production-specific schedule/args
```

- **ConfigMap** (`email-assistant-config`) supplies non-secret env vars such as `LOG_LEVEL` and `FETCH_BATCH_SIZE`.
- **Secret** (`email-assistant-secrets`) must be created separately (manually, SealedSecrets, External Secrets, etc.) and should contain `GOOGLE_CLIENT_SECRETS_B64`, `GOOGLE_TOKEN_B64`, and any other private values the CLI expects.
- **CronJob** launches `uv run email-assistant label` on a configurable schedule. The overlay sets a 15-minute cadence and targets the `work` account.

## Usage
1. Customize `deploy/overlays/prod/kustomization.yaml` with your desired registry/repo under the `images` block.
2. Adjust `patch-cronjob.yaml` for schedule, CLI arguments, CPU/memory, etc.
3. Apply via GitOps (Flux `Kustomization`, Argo CD Application, etc.). Example Flux snippet:
   ```yaml
   apiVersion: kustomize.toolkit.fluxcd.io/v1
   kind: Kustomization
   metadata:
     name: email-assistant-prod
     namespace: flux-system
   spec:
     interval: 5m
     path: ./deploy/overlays/prod
     prune: true
     sourceRef:
       kind: GitRepository
       name: email-assistant
   ```
4. Ensure a secret named `email-assistant-secrets` exists in the `email-assistant` namespace with the required key/value pairs.
