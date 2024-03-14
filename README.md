# Cloudstars

This repository contains the helm charts for setting up the testing framework. This framework utilizes stress-ng application to generate artifical CPU, memory and network load, based on preconfigured 
load specification. These load specification are crafted so as to mimic actual real world application usecase. 
Human traffic is generated using k6 load testing tool. This allows us to segregate the traffic simulator and application simulator to 2 halves which each work independently. The combination of these 2 
allows us to create the necessary simulation.

In this repository you will find,

## stress-ng-web
Web wrapper around stress-ng application. It is responsible for generating REST endpoints, where external applications can send their request to trigger a workload.
Currently there are 3 endpoints,
- `$HOST/jobs`
    - GET
    - application/json
    Gives out the list of jobs configured.

    **Example request**
    ```bash
    $ curl $HOST/jobs
    ```

    **Response JSON schema**
    ```json
    {
        "jobs": [
                "cpu-crypt.job", 
                "hybrid_cpu_mem-tree.job", ...
        ]
    }
    ```

- `$HOST/jobs/<job-name>`
    - GET
    - text/plain
    Gives out the job file specified. The specific job name can be obtained from the jobs list endpoint.

    **Example request**
    ```bash
    $ curl $HOST/jobs/cpu-hash.job
    ```


    **Response text**
    ```txt
    # General options
    run parallel  # run all stress tests in sequence
    metrics
    timeout 5s
    # -------------------------------------------------- #
    #  String hasing stressor
    #

    hash 1
    hash-ops 5
    ```

- `$HOST/jobs/<job-name>`
    - POST
    - text/plain
    Execute given job task. It executes the given job configuration using stress-ng and returns the response from the tool.

    **Example request**
    ```bash
    $ curl -X POST $HOST/jobs/hybrid_cpu_mem-wcs.job
    ```

    ```txt
    stress-ng: info:  [17] setting to a 5 secs run per stressor
    stress-ng: info:  [17] dispatching hogs: 1 wcs
    stress-ng: info:  [17] note: /proc/sys/kernel/sched_autogroup_enabled is 1 and this can impact scheduling throughput for processes not attached to a tty. Setting this to 0 may improve performance metrics
    stress-ng: metrc: [17] stressor       bogo ops real time  usr time  sys time   bogo ops/s     bogo ops/s CPU used per       RSS Max
    stress-ng: metrc: [17]                           (secs)    (secs)    (secs)   (real time) (usr+sys time) instance (%)          (KB)
    stress-ng: metrc: [17] wcs                  10      0.00      0.00      0.00    193285.90       18348.62      1053.41          2960
    stress-ng: metrc: [17] miscellaneous metrics:
    stress-ng: metrc: [17] wcs            117849712.39 wcscasecmp calls per sec (harmonic mean of 1 instance)
    stress-ng: info:  [17] skipped: 0
    stress-ng: info:  [17] passed: 1: wcs (1)
    stress-ng: info:  [17] failed: 0
    stress-ng: info:  [17] metrics untrustworthy: 0
    stress-ng: info:  [17] successful run completed in 0.00 secs
    ```


## k6-job

K6 load tester is responsible for generating human traffic to the system. The configuration for k6 job can be done using the configmap. For details configuration options, 
the documentation can be found [here](https://grafana.com/docs/k6/latest/using-k6/)

--- 

# Install

### Private repository

It is assumed that user already has a kubernetes cluster as well as helm pointed to the cluster. By default the chart is pointed to a public repository. But it has the capability to pull images from 
private repository as well. If you already have a secret `.dockerconfigjson` that allows to pull in images from your private cluster, you can specify the secret as an array under 
`.image.imagePullSecret` as,
```yaml
image:
    ...
    privateRepo:
        enabled: true
        generateSecret: false
        imagePullSecret:
            - name: your-secret-name
    ...
```
If you don't already have a secret in place, then you can configure the helm charts to generate the secret for you. It requires the repository link, username and password of a user that has access to 
repository.
```yaml
image:
    ...
    privateRepo:
        enabled: true
        generateSecret: true
        imagePullSecret: {}
        credentials:
            registry: your-registry-link
            username: your-username
            password: your-super-secret-password
```

## stress-ng-web

### Networking
By default the application is set to have a `ClusterIP` service. This allows access to the service intra cluster but doesn't allow extra cluster access to the application. The most simplest way of 
allowing external access if necessary is to convert the service to a `NodePort`. This can be done by changing the `service.type` to `NodePort` as,
```yaml
service:
    type: NodePort
    nodePort: 30001
```
You can also further configure the nodePort you want the application to be listening on nodes.

### Resources limit
You can configure the resource limit each application pod can consume. Configure `requests` if you want to reserve minimum resource allocation for the pod, and configure `limits` if you want to configure
the max resource consumption allowed for pod.
```yaml
resources:
    limits: 
        cpu: 500m
        memory: 500Mi
    requests:
        cpu: 100m
        memory: 128Mi
```

### Autoscaling
The chart has capability of autoscaling using HPA. It scales the application horizontally based on either CPU or memory utilization. By default this feature is turned off, but can be enabled by setting
`autoscaling.enabled=true`. You can configure the target utilization percentage for CPU or memory, you can do so using options provided. If you want to however scale only based on CPU or memory, you can 
set the other value to null, i.e, to scale based only on CPU utilization, set `targetMemoryUtilizationPercentage=null`.
```yaml
autoscaling:
    enabled: false
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 55
    targetMemoryUtilizationPercentage: 60
```

## k6-job

### vu
The value for the IP and port of the stress-ng-web application must be set in `vu.host`. If the k6 job is deployed on same cluster, this can be done by using the name of the service. If however the 
job is configured on some external cluster then it will need the IP and nodePort of the application.
You can also configure here the job to trigger.
```yaml
vu:
    host: http://svc-name:nodePort
    job: fs-iomix
    sleep_dur: 1
```

### Options
By default k6 is configured to generate a traffic based on normal distribution. It also has thresholds set to check on SLA. The options available currently are,
```yaml
options:
    batch: 5
    normalDist:
        max: 500 # vus
        timePeriod: 120 # seconds
        stages: 100
    http_req_dur:
        value: "p(90) < 5000"
        abortOnFail: false
    http_req_failed:
        value: "rate < 0.01"
        abortOnFail: false
```

### Custom
In case above options aren't enough, you can inject your own `option` and `vu_logic`. This can be done using custom block. 
```yaml
custom:
    options:
        enabled: false
        value: "{ batch: 10, str: 'value' }"
    vu_logic:
        enabled: false
        value: ""
```



