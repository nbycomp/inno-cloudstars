CloudStars Multi-Cluster Out-Cluster Utilities
==============================================

The set of tools that will allow provisioning multi-cluster environments. This documentation describes the out-cluster setup that enables provisioning clusters without real clusters in place. 


# Description of main dependencies

This section summarizes the principal components used by the environment and scripts.

Currently we are using following runtime tools:

* _Bash_: Primary orchestration language for scripts.
Bash is used for all orchestration logic in this repo: it wires together config generation, remote execution, and local automation in a way that is easy to run from the terminal and audit line‑by‑line.

* _Terraform_: Infrastructure provisioning (AWS mode).
Terraform provides a declarative infrastructure layer that creates EC2 instances, VPC networking, and security groups in a repeatable way before any cluster software is installed.

* _kwokctl_: KWOK cluster lifecycle management.
kwokctl is responsible for creating, deleting, and configuring simulated Kubernetes clusters on each host, including optional Prometheus, metrics‑server, and dashboard components.

* _Docker_: KWOK runtime and local Grafana container.
Docker is the runtime for KWOK’s simulated control planes and is also used locally to run Grafana as a containerized service.

* _kubectl_: Cluster access and node/workload operations.
kubectl is the primary client for interacting with the simulated clusters, used to create fake nodes, deploy workloads, and inspect HPA or metrics state.

* _jq / yq_: JSON/YAML processing in scripts.
jq and yq are used to parse and generate structured config files (plan.json, clusters.json, kubeconfigs, and derived YAML) to keep scripts deterministic and machine‑readable.

* _curl / ssh_: Remote access, downloads, and readiness checks.
curl is used to fetch remote artifacts and probe health endpoints, while SSH provides the channel for remote execution to provision KWOK clusters on hosts.

All scripts were verified on top of Ubuntu 24.04.3 LTS. Utilities with their latest available version. Versions of Terraform plugins are provided in the terraform directory.

# Infrastructure and services
Different modes of infrastructure provisioning utilize different external services:

* _AWS EC2 + VPC_: Hosts for KWOK clusters in AWS mode.
EC2 instances are the physical hosts where kwokctl runs, and the VPC provides the network boundaries and access controls needed to reach cluster APIs, Prometheus, and dashboards.

* _KWOK clusters_: Multiple simulated clusters per host.
Each host runs multiple lightweight Kubernetes control planes to emulate a multi‑cluster topology without the cost of real worker nodes.

* _Prometheus (per cluster)_: Metrics endpoint for dashboards.
Prometheus instances scrape per‑cluster metrics (including simulated resource usage) so that dashboards can visualize behavior and trends.

* _metrics-server (per cluster)_: Resource metrics for HPA.
metrics-server exposes CPU and memory metrics through the Kubernetes Metrics API, enabling HPA to react to simulated usage.

* _Grafana (local container)_: Central dashboarding for all clusters.
Grafana aggregates multiple Prometheus datasources into a single UI, making it easy to compare clusters and validate behavior across them.


# Usage and main design choices
Here, we will describe how to use the tool and navigate the repository. The utilities are configured according to the settings in the env.yaml file. The sample content looks as follows:

```` yaml copy
project:
  name_prefix: <prefix-name-of-cluster>
  aws_region: <aws region>
  availability_zone: <az within region> 

access: # aws and remote vm specific (if relevant)
  my_ip_cidr: "<your host connection ip address - sg config>"
  extra_ip_cidrs: ["<extra ip addresses for the connectivity clusters>"]
  ssh_user: <ssh user>
  ssh_private_key_path: "<path to private key for ssh access>"
  key_name: <name of the aws key pair to use for ssh access>

vm_host: "<remote vm ip address for provisioning and connectivity>" 


aws_hosts: # aws specific configuration
  count: 2 # number of aws hosts to provision
  instance_type: < instance type to use for aws hosts>
  root_volume_gb: <size of root volume in gb>
  vpc_cidr: "<vpc cidr block>"
  public_subnet_cidr: "<public subnet cidr block>"

kwok: # kwok specific configuration
  clusters_per_host: <number of clusters to run per host, in case of aws per provisioned host>
  runtime: docker # runtime to use for kwok

  version: "v0.7.0" # KWOK version to use

  enable_prometheus: true # whether to enable Prometheus for metrics collection
  enable_dashboard: true # whether to enable dashboard
  enable_metrics_server: true # whether to enable metrics server for resource metrics collection

# base port for exposed ports, each cluster will use a different port starting from this base
  prometheus_port_base: 39090 
  dashboard_port_base: 39443
# KWOK metrics usage configuration url
  metrics_usage_config_url: "https://raw.githubusercontent.com/kubernetes-sigs/kwok/refs/heads/main/kustomize/metrics/resource/metrics-resource.yaml"

````

Not all fields are mandatory - everything depends on the mode in which the user wants to provision the environment. Currently, the following options are available:

* _aws_ - provision clusters on aws infrastructure, all options are mandatory (except vm_host). In order to provision infrastructure, we use Terraform.
* _vm_ - provision clusters on a remote virtual machine. The IP is specified in the vm_host parameters. Use the SSH configuration for accessing the machine.
* _local_ - provision clusters on the local machine. This option does not use ssh (no need for remote connectivity). 

Parameters for configuring individual KWOK clusters are shared across the different provisioning options. 

# scripts/envctl.sh — main entrypoint

It is the main entry point for the utilities. Currently, it accepts the following options: 

````bash copy
ENV_FILE=./env.yaml ./scripts/envctl.sh gen <aws|local|vm>
ENV_FILE=./env.yaml ./scripts/envctl.sh provision
ENV_FILE=./env.yaml ./scripts/envctl.sh add-single-cluster
ENV_FILE=./env.yaml ./scripts/envctl.sh kubeconfigs
ENV_FILE=./env.yaml ./scripts/envctl.sh grafana
ENV_FILE=./env.yaml ./scripts/envctl.sh destroy
````

Here is short description:
* _gen_: builds terraform/terraform.tfvars (aws), inventory/plan.json, and inventory/env.effective.yaml. 
* _provision_: creates KWOK clusters per host and writes inventory/clusters.json.
* _add-single-cluster_: adds one cluster (local/vm mode only).
* _kubeconfigs_: fetches kubeconfigs into kubeconfigs/.
* _grafana_: builds datasources + dashboards and starts local Grafana.
* _destroy_: deletes KWOK clusters and cleans local inventory/kubeconfigs.

## Option: gen <aws|local|vm>
This entry point calls scripts/gen-config.sh to generate the plan and initialize Terraform vars (if needed).
Based on this plan, the entire provisioning phase is created. If the user chooses the aws option for provisioning infrastructure, additional steps are required. 
````bash copy
ENV_FILE=./env.yaml ./scripts/gen-config.sh aws
ENV_FILE=./env.yaml ./scripts/gen-config.sh local
ENV_FILE=./env.yaml ./scripts/gen-config.sh vm
````

Important to note:
* Outputs: terraform/terraform.tfvars (aws), inventory/plan.json, inventory/hosts.json, inventory/env.effective.yaml.
* Notes: local and vm modes bypass Terraform and use a single host IP (or local IP).

### Terraform (manual step)
To create infrastructure in the AWS cloud, we use Terraform. All templates are located in the terraform folder, and the user simply needs to apply them.
````bash copy
cd terraform
terraform init -upgrade (for the first time only usage)
terraform apply -auto-approve
````

In a nutshell, the scripts:
* Creates EC2 hosts, VPC, and networking as defined in terraform/.
* After apply, scripts/create-clusters.sh pulls public IPs from outputs.

If the user wants to destroy the environment, they need to call. 
````bash copy
terraform destroy -auto-approve
````

## Option: provision 
Once the infrastructure is ready, the user needs to provision the KWOK cluster by calling the provisioning entry point. It calls the script scripts/create-clusters.sh, which performs the following steps in order to create KWOK clusters:


* Ensures curl, docker, and kwokctl exist on each host.
* Downloads metrics‑usage config (URL in env.yaml).
* Creates clusters with per‑cluster API, Prometheus, and Dashboard ports.
* Waits for /livez, metrics API, and Prometheus readiness (best effort).

### Option: add-single-cluster

This entry point runs scripts/add-clusters.sh and can be used to add a single cluster to the existing infrastructure. It is only available in local or VM (single-machine) modes. In addition, it also updates inventory/clusters.json and inventory/plan.json. Finally, it fetches kubeconfig immediately into kubeconfigs/<cluster>.yaml file.

## Option: kubeconfigs

This entry point calls scripts/fetch-kubeconfigs.sh. Its main function is to fetch all kubeconfigs files for created clusters. It performs the following steps:

* Produces one kubeconfig per cluster in kubeconfigs/.
* Forces insecure-skip-tls-verify: true and removes CA fields for compatibility.

## Managing clusters scripts/kwok-nodes.sh 
To manage clusters, the user must provide the kubeconfig file for the selected cluster. Its main function is to manage fake nodes in the cluster (all nodes are control plane objects). The following options are available:
````bash copy
scripts/kwok-nodes.sh --kubeconfig <file> list [type=<template>]
scripts/kwok-nodes.sh --kubeconfig <file> add <count> type=<template>
scripts/kwok-nodes.sh --kubeconfig <file> rm <count> type=<template>
scripts/kwok-nodes.sh --kubeconfig <file> scale <desired_count> type=<template>
scripts/kwok-nodes.sh --kubeconfig <file> wipe type=<template>
````

One important parameter is the node template. It configures the resources available for scheduling in the control plane. Templates live in scripts/templates/nodes/ (e.g., light.yaml, heavy.yaml). Here is a sample file:

````yaml copy
apiVersion: v1
kind: Node
metadata:
  name: __NODE_NAME__
  annotations:
    kwok.x-k8s.io/node: fake
    # Optional: allow metrics-server to scrape kwok resource metrics for this node (common kwok pattern)
    metrics.k8s.io/resource-metrics-path: "/metrics/nodes/__NODE_NAME__/metrics/resource"
  labels:
    type: kwok
    kwok-node-type: heavy
    kubernetes.io/os: linux
    kubernetes.io/arch: amd64
    node-role.kubernetes.io/worker: ""
spec:
  # Taint to ensure only pods that tolerate it can run here
  taints: # Avoid scheduling actual running pods to fake Node unless tolerated
  - effect: NoSchedule
    key: kwok.x-k8s.io/node
    value: fake
status:
  addresses:
  - type: Hostname
    address: __NODE_NAME__
  capacity:
    cpu: "100"           # or 10 for light
    memory: "1Ti"        # or 30Gi for light
    pods: "1100"         # or 200 for light
  allocatable:
    cpu: "100"
    memory: "1Ti"
    pods: "1100"
  conditions:
  - type: Ready
    status: "True"
    reason: "KWOKReady"
    message: "Simulated node by KWOK"
  nodeInfo:
    architecture: amd64
    operatingSystem: linux
    kubeletVersion: "kwok"
````


The script includes the following metrics fix (on by default), which updates node status via the kwok‑controller endpoint.
  * KWOK_FIX_METRICS=0 disables this fix.
  * KWOK_KUBELET_PORT=10247 sets the metrics port (default).
  * KWOK_CTRL_HOST=<host> overrides the auto‑derived controller hostname.

## Option: grafana
This entry point in the main file, call scripts/gen-grafana-datasources.sh, enables observability in the environment. It creates a local Grafana container and provisions the dashboards. In detail, the phase:

* Generates Prometheus datasources from inventory/clusters.json.
* Syncs dashboards from grafana/dashboards/. Currently, there are two dashboards
** basic-dashboard.yaml - contains metrics about controller performance
** nearby-computing-deploy.yaml - contains metrics regading demo applications 
* Starts a local Grafana container at http://localhost:3000.

Optional environment overrides:

````bash copy
GRAFANA_CONTAINER_NAME=grafana
GRAFANA_IMAGE=grafana/grafana:9.4.7
GRAFANA_PORT=3000
GF_ADMIN_USER=admin
GF_ADMIN_PASSWORD=admin
````

## Option: destroy
This entry point calls scripts/destroy.sh. It tears down the deployed clusters. It performs the following tasks:

* Deletes KWOK clusters (best effort), wipes inventory and kubeconfig artifacts.
* Does not run Terraform destroy (needs to be called manually).

# Workload and end-to-end deployment
The repository also contains a demo application in the application directory. It deploys light/mid/heavy simulation workloads in the nearby-computing-app namespace. In the demo scenario, we will modify the CPU usage of pods by simply modifying the labels (as we do not execute the pods )

## End-to-end AWS example (with demo app)

This walk-through shows an end-to-end AWS path for creating multi‑cluster KWOK clusters, adding fake nodes, and deploying a demo workload.

### Generate config
````bash copy
ENV_FILE=./env.yaml ./scripts/envctl.sh gen aws
````

### Provision AWS infra (manual)

````bash copy
cd terraform
terraform init -upgrade
terraform apply -auto-approve
cd ..
````

### Create KWOK clusters on the hosts
````bash copy
ENV_FILE=./env.yaml ./scripts/envctl.sh provision
````

### Fetch kubeconfigs locally
````bash copy
ENV_FILE=./env.yaml ./scripts/envctl.sh kubeconfigs
````

### Select a cluster and verify
````bash copy
export KUBECONFIG=$PWD/kubeconfigs/kwok-h00-01.yaml
kubectl get nodes
````
Expected output: empty list (no fake nodes yet).

### Add fake nodes
````bash copy
scripts/kwok-nodes.sh --kubeconfig "$KUBECONFIG" add 10 type=light
scripts/kwok-nodes.sh --kubeconfig "$KUBECONFIG" add 3  type=heavy
kubectl get nodes
````

### Deploy the demo app
Use the following command:
````bash copy
kubectl apply -f application/
````

### Observe HPA behavior
In this step, we modify CPU usage parameters for the fake nodes and observe the HPA behaviour of the demo app (the HPA scales the light deployment to 100 pods from the initial 5). We utilize script  scale-ligh-dep.sh that simplifies modification of  simulated CPU labels: Here are the details:
````bash copy
application_scripts/scale-ligh-dep.sh <cpu>
````

Important to note:
* Patches simulation-light Deployment annotation kwok.x-k8s.io/usage-cpu.
* Example: application_scripts/scale-ligh-dep.sh 5m or ./scale-ligh-dep.sh 0m.
* Env overrides: NAMESPACE, DEPLOYMENT.

Next, we modify the values:
````bash copy
kubectl -n nearby-computing-app get hpa
application_scripts/scale-ligh-dep.sh 25m
````
And after waiting few seconds

````bash copy
kubectl -n nearby-computing-app get hpa
application_scripts/scale-ligh-dep.sh 2m
````

### Start Grafana
Finally, let's observe the changes in Grafana:
````bash copy
ENV_FILE=./env.yaml ./scripts/envctl.sh grafana
````

Open Grafana locally at http://localhost:3000.


External:

* Resource Metrics Pipeline: https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/
* metrics-server docs: https://kubernetes-sigs.github.io/metrics-server/
* Introducing KWOK: https://kubernetes.io/blog/2023/03/01/introducing-kwok/