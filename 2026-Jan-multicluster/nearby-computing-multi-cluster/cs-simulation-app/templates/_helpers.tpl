{{- define "simulation.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "simulation.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- include "simulation.name" . | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "simulation.labels" -}}
app.kubernetes.io/name: {{ include "simulation.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
