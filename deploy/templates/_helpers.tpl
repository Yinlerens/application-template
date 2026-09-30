{{- define "application.pod" -}}
{{- $root := .root -}}
automountServiceAccountToken: false
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault
{{- if $root.Values.image.pullSecret }}
imagePullSecrets:
  - name: {{ $root.Values.image.pullSecret }}
{{- end }}
containers:
  - name: {{ .name }}
    image: {{ printf "%s@%s" $root.Values.image.repository (required "An immutable image digest is required" $root.Values.image.digest) | quote }}
    imagePullPolicy: {{ $root.Values.image.pullPolicy }}
    {{- with .workload.command }}
    command: {{ toJson . }}
    {{- end }}
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    resources:
      requests: {{ toJson .workload.requests }}
      limits: {{ toJson .workload.limits }}
    env:
      - {name: APP_ENVIRONMENT, value: {{ $root.Values.environment | quote }}}
      - {name: WORKLOAD_ROLE, value: {{ .workload.role | quote }}}
      - {name: RELEASE_VERSION, value: {{ $root.Values.releaseVersion | quote }}}
      - {name: OTEL_EXPORTER_OTLP_ENDPOINT, value: {{ $root.Values.telemetryEndpoint | quote }}}
      {{- if and $root.Values.database.enabled .workload.database }}
      - {name: PGHOST, value: {{ $root.Values.database.host | quote }}}
      - {name: PGDATABASE, value: {{ $root.Values.database.name | quote }}}
      - name: PGUSER
        valueFrom:
          secretKeyRef: {name: {{ $root.Values.database.secret }}, key: username}
      - name: PGPASSWORD
        valueFrom:
          secretKeyRef: {name: {{ $root.Values.database.secret }}, key: password}
      {{- end }}
    {{- if .workload.http }}
    ports:
      - {name: http, containerPort: 8080}
    startupProbe:
      httpGet: {path: {{ .workload.healthPath | default "/healthz" }}, port: http}
      failureThreshold: 30
      periodSeconds: 5
    readinessProbe:
      httpGet: {path: {{ .workload.readyPath | default "/readyz" }}, port: http}
      periodSeconds: 10
    livenessProbe:
      httpGet: {path: {{ .workload.healthPath | default "/healthz" }}, port: http}
      periodSeconds: 20
    {{- else if and $root.Values.database.enabled (eq .workload.role "worker") }}
    livenessProbe:
      exec:
        command:
          - python
          - -c
          - "import os,psycopg;c=psycopg.connect(host=os.environ['PGHOST'],dbname=os.environ['PGDATABASE'],user=os.environ['PGUSER'],password=os.environ['PGPASSWORD'],connect_timeout=5);assert c.execute('SELECT 1').fetchone()[0]==1;c.close()"
      timeoutSeconds: 7
      periodSeconds: 30
      failureThreshold: 3
    {{- end }}
    volumeMounts:
      - {name: tmp, mountPath: /tmp}
volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 128Mi
{{- end -}}
