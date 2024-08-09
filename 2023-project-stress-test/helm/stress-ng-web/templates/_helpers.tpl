{{/*
Expand the name of the chart.
*/}}
{{- define "stress-ng-web.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "stress-ng-web.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "stress-ng-web.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "stress-ng-web.labels" -}}
helm.sh/chart: {{ include "stress-ng-web.chart" . }}
{{ include "stress-ng-web.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }} 
{{- end }}

{{/*
Selector labels
*/}}
{{- define "stress-ng-web.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stress-ng-web.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}



{{/*
Generate Image pull secrets from credentials
*/}}
{{- define "stress-ng-web.imagePullSecret" }}
{{- with .Values.image.privateRepo.credentials }}
{{- $registry := .registry | required ".Values.image.privateRepo.credentials.registry required when private image registry enabled" -}}
{{- $username := .username | required ".Values.image.privateRepo.credentials.username required when private image registry enabled" -}}
{{- $password := .password | required ".Values.image.privateRepo.credentials.password required when private image registry enabled" -}}
{{- printf "{\"auths\":{\"%s\":{\"username\":\"%s\",\"password\":\"%s\",\"auth\":\"%s\"}}}" $registry $username $password (printf "%s:%s" $username $password | b64enc) | b64enc }}
{{- end }}
{{- end }}
