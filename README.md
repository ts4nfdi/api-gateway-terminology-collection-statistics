# Collection Statistics Service

The Collection Statistics Service calculates statistics for terminology collections provided by the Base4NFDI Terminology Service.

For each collection, the service retrieves statistics from the corresponding terminology providers and counts:

- RDF Properties
- OWL Classes
- OWL Named Individuals
- SKOS Concepts

The calculated statistics are stored in a PostgreSQL database.

## API

The service runs on port `8000` and provides two endpoints.

### Calculate statistics for selected collections

`POST /stats?collection=<collection-id>`

Multiple collections can be specified:

`POST /stats?collection=<collection-id-1>&collection=<collection-id-2>`

### Calculate statistics for all collections

`POST /stats/all`

## Docker

The Docker image is built automatically by the GitHub Actions workflow in `.github/workflows/publish-docker.yml` on every push to `main`. The workflow can also be triggered manually via GitHub Actions.

The image is published to the GitHub Container Registry (GHCR) at:

```text
ghcr.io/ts4nfdi/api-gateway-terminology-collection-statistics:latest
ghcr.io/ts4nfdi/api-gateway-terminology-collection-statistics:<commit-sha>
```
## Kubernetes Deployment

The Kubernetes configuration is located in the `k8s/` directory.

It contains:

- `deployment.yaml` – deploys the Collection Statistics container and references the existing database and API-key Secrets in the target cluster
- `service.yaml` – exposes the deployed pods through a Kubernetes Service

The deployment is intended for the target Kubernetes cluster, where the required Secrets and PostgreSQL service already exist.

Select the target cluster context and deploy the Kubernetes resources to the appropriate namespace:

```bash
kubectl apply -n <namespace> -f k8s/
```

Check the deployment:

```bash
kubectl get pods -n <namespace>
```

```bash
kubectl get services -n <namespace>
```

## Accessing the Service

Inside the Kubernetes cluster, the service is reachable at:

`http://ts4nfdi-api-gateway-collection-statistics:8000`

Example (run in the same namespace as the service):

```bash
kubectl run test-client -n <namespace> --rm -it --restart=Never --image=curlimages/curl -- curl -X POST http://ts4nfdi-api-gateway-collection-statistics:8000/stats/all
```

The service currently uses the Kubernetes `ClusterIP` type and is therefore only directly reachable from inside the cluster.

## Project Structure

`server.py` provides the HTTP interface.

`collectionStats.py` retrieves the terminology statistics and stores the calculated collection statistics in PostgreSQL.
